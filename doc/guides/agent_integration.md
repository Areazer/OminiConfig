# 🤖 AI Agent 接入桌面版标准协议 (Desktop Integration Guide)

**WARNING: V1.1 (HTTP) 协议已作废。V2.0 桌面应用已完全抛弃 HTTP 和 SSE 协议。**

---

## 1. 寻址规则与沙箱 (Path Resolution)

绝对禁止使用绝对路径（如 `/etc/config.json`）或包含 `../` 的穿越路径。必须使用纯相对路径，否则触发 Rust 沙箱拦截 (`PathSecurityViolationException`)。

### 允许的路径格式

```javascript
// ✅ 纯相对路径
"app/settings.json"
"configs/database.yml"
"frontend/vite.config.ts"
"deep/nested/path/config.json"
```

### 禁止的路径格式

```javascript
// ❌ 绝对路径 - 将被 403 拦截
"/etc/config.json"
"/var/www/app/config.yaml"
"C:\\Windows\\System32\\config.ini"

// ❌ 路径穿越 - 将被 403 拦截  
"../etc/passwd"
"../../secret.json"
"config/../../../etc/shadow"
```

---

## 2. 乐观锁同步契约 (Optimistic Locking)

修改配置必须携带 `oldVersionHash`。如果发生 `ConcurrencyConflictException` 冲突，Agent 脚本**必须**实现自动重试：重新读取 -> 合并 -> 重新提交。

### 读取流程

```javascript
const { data, meta } = await invoke('read_config', { 
    path: 'app/settings.json' 
});

const currentData = data;
const currentHash = meta.version_hash;  // 保存此 Hash
```

### 写入流程

```javascript
try {
    const result = await invoke('write_config', {
        path: 'app/settings.json',
        data: modifiedData,
        oldHash: currentHash  // 必须携带
    });
} catch (error) {
    if (error.includes('ConcurrencyConflict')) {
        // 必须实现重试逻辑
        await handleConflictAndRetry();
    }
}
```

### 冲突重试逻辑

```javascript
async function handleConflictAndRetry() {
    // 1. 重新拉取最新数据
    const latest = await invoke('read_config', { path: 'app/settings.json' });
    
    // 2. 尝试合并（根据业务逻辑）
    const mergedData = mergeConfigs(localData, latest.data);
    
    // 3. 使用新的 Hash 重新提交
    const result = await invoke('write_config', {
        path: 'app/settings.json',
        data: mergedData,
        oldHash: latest.meta.version_hash
    });
}
```

---

## 3. IPC 通信协议 (IPC Source of Truth)

前端通信基于 Tauri 原生 IPC。外部脚本接入请引入 `@tauri-apps/api` 并严格遵照 Rust 后端暴露的 Command 签名。

### 安装 Tauri API

```bash
npm install @tauri-apps/api
```

### IPC 接口定义

#### `read_config(path: string): Promise<ConfigData>`

读取配置文件。

**Parameters**:
- `path`: 相对路径 (如 `"app/settings.json"`)

**Returns**:
```typescript
interface ConfigData {
    data: any;
    meta: {
        version_hash: string;
        last_modified: number;
    };
}
```

**Errors**:
- `PathSecurityViolation`: 路径违规
- `ConfigNotFound`: 文件不存在
- `InvalidConfigFormat`: JSON 格式错误

#### `write_config(params: WriteParams): Promise<ConfigData>`

写入配置。

**Parameters**:
```typescript
interface WriteParams {
    path: string;           // 相对路径
    data: any;              // 配置数据
    oldHash: string;        // 上次读取的 version_hash
}
```

**Errors**:
- `ConcurrencyConflict`: 版本哈希不匹配 (409)
- `PathSecurityViolation`: 路径违规 (403)
- `InvalidConfigFormat`: 数据无法序列化为 JSON

#### `get_schema(path: string): Promise<Schema>`

获取 JSON Schema。

**Returns**:
```typescript
interface Schema {
    type: 'object' | 'array' | 'string' | 'number' | 'boolean' | 'null';
    properties?: Record<string, Schema>;
    items?: Schema;
    required?: string[];
}
```

---

## 4. 实时监听约定 (Native Events)

禁止使用 SSE。使用 `window.__TAURI__.event.listen` 监听事件。防抖逻辑已上移至 Rust，前端会直接收到携带最新 Hash 的 `modified` 事件。

### 事件类型

| 事件名称 | 触发时机 | Payload |
|---------|---------|---------|
| `config_modified` | 配置文件被修改 | `{ path: string, new_version_hash: string, new_data: any }` |

### 监听示例

```javascript
import { listen } from '@tauri-apps/api/event';

// 监听配置变更
const unlisten = await listen('config_modified', (event) => {
    const { path, new_version_hash, new_data } = event.payload;
    
    // 对比 Hash，如不一致提示用户
    if (new_version_hash !== localVersionHash) {
        showConflictToast(new_version_hash, localVersionHash);
    }
});

// 清理监听
unlisten();
```

### 禁止行为

- ❌ 禁止使用 `EventSource` 或 SSE
- ❌ 禁止在前端实现防抖逻辑（Rust 已处理）
- ❌ 禁止自动刷新用户正在编辑的数据

---

## 5. 完整接入示例

### TypeScript 客户端封装

```typescript
import { invoke } from '@tauri-apps/api/tauri';
import { listen } from '@tauri-apps/api/event';

interface ConfigMeta {
    version_hash: string;
    last_modified: number;
}

interface ConfigData {
    data: any;
    meta: ConfigMeta;
}

class OminiConfigClient {
    private path: string;
    private currentHash: string = '';
    
    constructor(path: string) {
        this.path = path;
    }
    
    async read(): Promise<ConfigData> {
        const result = await invoke<ConfigData>('read_config', {
            path: this.path
        });
        this.currentHash = result.meta.version_hash;
        return result;
    }
    
    async write(data: any): Promise<ConfigData> {
        try {
            const result = await invoke<ConfigData>('write_config', {
                path: this.path,
                data: data,
                oldHash: this.currentHash
            });
            this.currentHash = result.meta.version_hash;
            return result;
        } catch (error: any) {
            if (error.includes('ConcurrencyConflict')) {
                // 自动重试
                const latest = await this.read();
                // 这里可以实现合并逻辑
                return this.write(data);
            }
            throw error;
        }
    }
    
    watch(onChange: (data: ConfigData) => void) {
        return listen('config_modified', (event) => {
            const payload = event.payload as any;
            if (payload.path === this.path) {
                onChange({
                    data: payload.new_data,
                    meta: {
                        version_hash: payload.new_version_hash,
                        last_modified: Date.now() / 1000
                    }
                });
            }
        });
    }
}

// 使用示例
const client = new OminiConfigClient('app/settings.json');

// 读取配置
const { data } = await client.read();

// 修改并保存
data.debug = true;
await client.write(data);

// 监听变更
const unlisten = await client.watch((newData) => {
    console.log('配置已更新:', newData);
});
```

---

## 6. 错误处理规范

### 错误类型映射

| Rust Error | TypeScript Exception |
|-----------|---------------------|
| `PathSecurityViolation` | `Error: PathSecurityViolation` |
| `ConfigNotFound` | `Error: ConfigNotFound` |
| `ConcurrencyConflict` | `Error: ConcurrencyConflict` |
| `InvalidConfigFormat` | `Error: InvalidConfigFormat` |
| `IoError` | `Error: IoError` |

### 错误处理优先级

```javascript
try {
    await invoke('write_config', params);
} catch (error) {
    if (error.includes('PathSecurityViolation')) {
        // 路径违规 - 检查路径格式
    } else if (error.includes('ConcurrencyConflict')) {
        // 乐观锁冲突 - 必须重试
    } else if (error.includes('ConfigNotFound')) {
        // 文件不存在
    } else {
        // 其他错误
    }
}
```

---

**MUST**: 严格遵循以上契约，禁止任何猜测。所有接口定义以 Rust 源码为准。