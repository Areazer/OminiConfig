# 🤖 Agent 集成契约

**文档类型**: API 集成规范  
**目标读者**: AI Agent (Cursor, Claude, Kimi, GPT-4)  
**适用范围**: 为其他项目生成 OminiConfig Client 代码时  
**最后更新**: 2026-03-21  
**文档状态**: 强制性规范 (MUST COMPLY)

---

## ⚠️ CRITICAL: 绝对真理原则 (Source of Truth)

**MUST**: 在生成任何 Client 代码之前，**必须**直接向 OminiConfig 服务发送以下请求获取最新的 OpenAPI 3.0 Schema：

```http
GET http://<host>:<port>/openapi.json
```

**SHALL NOT**: 
- 禁止从本 Markdown 文档猜测字段类型
- 禁止基于示例代码推断接口定义
- 禁止使用过时或缓存的 Schema

**REASON**: FastAPI 的 Schema 可能随版本更新而变化，只有 `/openapi.json` 是唯一的真相来源。

---

## 🚫 CRITICAL: 路径寻址铁律 (Path Resolution)

### 禁止事项 (PROHIBITED)

**SHALL NOT** 使用以下路径格式：

```javascript
// ❌ 绝对路径 - 将被 403 拦截
"/etc/config.json"
"/var/www/app/config.yaml"
"C:\\Windows\\System32\\config.ini"

// ❌ 路径穿越 - 将被 403 拦截  
"../etc/passwd"
"../../secret.json"
"config/../../../etc/shadow"

// ❌ URL 编码的斜杠 - 不必要且可能导致错误
"app%2Fconfig%2Fsettings.json"
```

### 强制要求 (MANDATORY)

**MUST** 使用以下格式：

```javascript
// ✅ 纯相对路径 - 相对于 OminiConfig 工作目录
"app/settings.json"
"configs/database.yml"
"frontend/vite.config.ts"

// ✅ 多层级路径 - 直接拼接，无需 URL 编码
"deep/nested/path/config.json"
```

**CONSEQUENCE**: 违反此规则将收到 HTTP 403 (Security Violation) 响应。

---

## 🔒 CRITICAL: 并发防冲突契约 (Optimistic Locking)

### 读取流程 (READ Protocol)

```javascript
// Step 1: GET 读取配置
const response = await fetch(`http://localhost:8000/api/config/${sourcePath}`);
const result = await response.json();

// Step 2: 提取关键元数据
const currentData = result.data;
const currentHash = result.meta.versionHash;  // MUST: 保存此 Hash
```

### 写入流程 (WRITE Protocol)

```javascript
// Step 1: 准备请求体 - MUST 携带 oldVersionHash
const payload = {
    data: modifiedData,           // 修改后的数据
    oldVersionHash: currentHash   // MUST: 上次 GET 获取的 Hash
};

// Step 2: POST 提交
const response = await fetch(`http://localhost:8000/api/config/${sourcePath}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
});

// Step 3: MUST 处理 409 冲突
if (response.status === 409) {
    // CRITICAL: 必须执行重试逻辑，禁止直接抛出异常
    await handleConflictAndRetry(sourcePath, modifiedData);
}
```

### 冲突重试逻辑 (Conflict Resolution)

**MUST** 实现以下重试流程：

```javascript
async function handleConflictAndRetry(sourcePath, localData) {
    // 1. 重新拉取最新数据
    const latest = await fetchConfig(sourcePath);
    
    // 2. 尝试合并（根据业务逻辑）
    const mergedData = mergeConfigs(localData, latest.data);
    
    // 3. 使用新的 Hash 重新提交
    const retryPayload = {
        data: mergedData,
        oldVersionHash: latest.meta.versionHash
    };
    
    const retryResponse = await fetch(`http://localhost:8000/api/config/${sourcePath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(retryPayload)
    });
    
    if (!retryResponse.ok) {
        // 只有重试失败后才抛出异常
        throw new Error(`Write failed after retry: ${retryResponse.status}`);
    }
}
```

**SHALL NOT**:
- 禁止在收到 409 后直接抛出异常导致进程崩溃
- 禁止使用旧的 versionHash 无限重试
- 禁止在重试间隔期间不重新拉取数据

---

## 📡 SSE 监听规范 (EventSource)

### 连接建立

```javascript
const es = new EventSource(`http://localhost:8000/api/watch/${sourcePath}`);
```

### 事件处理 (MUST HANDLE ALL)

| 事件类型 | 触发时机 | 处理要求 |
|---------|----------|----------|
| **connected** | SSE 连接建立成功 | 记录日志，初始化监听状态 |
| **modified** | 配置文件被修改 | **CRITICAL**: 对比 `newVersionHash` 与本地 Hash，如不一致提示用户刷新 |
| **deleted** | 配置文件被删除 | 提示用户文件已删除，清理本地状态 |
| **heartbeat** | 保活心跳（每 30 秒） | **MUST IGNORE**: 静默处理，无需任何回应 |

### 实现示例

```javascript
es.addEventListener('connected', (event) => {
    const data = JSON.parse(event.data);
    console.log('SSE connected:', data.message);
});

es.addEventListener('modified', (event) => {
    const data = JSON.parse(event.data);
    
    // CRITICAL: 必须对比 Hash
    if (data.newVersionHash !== localVersionHash) {
        // 提示用户外部修改，让用户决定是否刷新
        showConflictToast(data.newVersionHash, localVersionHash);
    }
});

es.addEventListener('deleted', (event) => {
    const data = JSON.parse(event.data);
    console.warn('Config file deleted:', data.path);
    handleConfigDeleted();
});

es.addEventListener('heartbeat', (event) => {
    // MUST: 完全忽略，不做任何处理
    // 禁止 console.log，禁止回应服务器
});

// 错误处理
es.onerror = (error) => {
    console.error('SSE connection error:', error);
    // 实现重连逻辑
};
```

**WARNING**: 对 `heartbeat` 事件做出任何响应（包括日志输出）都是不必要的资源浪费。

---

## 📖 状态码字典 (Status Code Dictionary)

### 精确语义定义

| 状态码 | 英文标识 | 业务场景 | 处理建议 |
|--------|----------|----------|----------|
| **200** | OK | 读写成功 | 正常处理响应数据 |
| **400** | Bad Request | 请求体格式错误（非法 JSON、缺少必填字段） | 检查请求体格式，修复后重试 |
| **403** | Forbidden | 安全沙箱拦截（检测到绝对路径或 `../` 穿越） | 检查路径格式，使用纯相对路径 |
| **404** | Not Found | 读取时：配置文件不存在；写入时：不会返回此状态（会自动创建） | 读取时确认文件存在；写入时无需处理 |
| **409** | Conflict | 乐观锁冲突（`oldVersionHash` 与服务器最新 Hash 不匹配） | **必须**: 重新拉取数据 → 合并 → 使用新 Hash 重试 |

### 状态码检查优先级

```javascript
// RECOMMENDED: 按以下顺序检查状态码
if (response.status === 403) {
    // 路径安全违规
    handleSecurityViolation();
} else if (response.status === 409) {
    // 乐观锁冲突 - 必须重试
    await handleConflictAndRetry();
} else if (response.status === 404) {
    // 文件不存在
    handleFileNotFound();
} else if (response.status === 400) {
    // 请求格式错误
    handleBadRequest();
} else if (!response.ok) {
    // 其他错误
    handleGenericError();
}
```

---

## 🎯 接入代码模板

### Python (httpx)

```python
import httpx
from typing import Dict, Any, Optional

class OminiConfigClient:
    """
    OminiConfig Client - 严格遵循机器可读契约
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self._client = httpx.Client()
        
    def _get_schema(self) -> Dict[str, Any]:
        """MUST: 获取 OpenAPI Schema 作为真相来源"""
        response = self._client.get(f"{self.base_url}/openapi.json")
        response.raise_for_status()
        return response.json()
    
    def read_config(self, source_path: str) -> Dict[str, Any]:
        """
        读取配置
        
        Args:
            source_path: 相对路径（如 "app/settings.json"）
            
        Returns:
            { data: Any, meta: { versionHash: str, lastModified: float } }
        """
        # SHALL NOT: 使用绝对路径或包含 ../
        if source_path.startswith('/') or '../' in source_path:
            raise ValueError("Path must be relative and not contain '../'")
        
        response = self._client.get(f"{self.base_url}/api/config/{source_path}")
        
        if response.status_code == 403:
            raise SecurityError("Path violates security policy")
        elif response.status_code == 404:
            raise FileNotFoundError(f"Config file not found: {source_path}")
            
        response.raise_for_status()
        return response.json()
    
    def write_config(
        self, 
        source_path: str, 
        data: Dict[str, Any], 
        version_hash: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        写入配置（自动处理乐观锁冲突）
        
        Args:
            source_path: 相对路径
            data: 配置数据
            version_hash: 上次读取获取的 versionHash
            max_retries: 最大重试次数
        """
        payload = {
            "data": data,
            "oldVersionHash": version_hash  # MUST: 携带 versionHash
        }
        
        for attempt in range(max_retries):
            response = self._client.post(
                f"{self.base_url}/api/config/{source_path}",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 409:
                # CRITICAL: 必须重试，禁止直接抛出异常
                if attempt < max_retries - 1:
                    # 重新拉取最新数据
                    latest = self.read_config(source_path)
                    payload["oldVersionHash"] = latest["meta"]["versionHash"]
                    # 这里可以实现合并逻辑
                    continue
            else:
                response.raise_for_status()
                
        raise ConflictError(f"Failed to write after {max_retries} retries")

class SecurityError(Exception):
    """路径安全违规"""
    pass

class ConflictError(Exception):
    """乐观锁冲突"""
    pass
```

### TypeScript (Node.js)

```typescript
interface ConfigMeta {
  versionHash: string;
  lastModified: number;
}

interface ConfigResult {
  data: any;
  meta: ConfigMeta;
}

interface SSEEventData {
  event: 'connected' | 'modified' | 'deleted' | 'heartbeat';
  timestamp: number;
  path?: string;
  newVersionHash?: string;
  newData?: any;
  message?: string;
}

class OminiConfigClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }
  
  /**
   * MUST: 获取 OpenAPI Schema 作为真相来源
   */
  async getSchema(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/openapi.json`);
    if (!response.ok) {
      throw new Error(`Failed to get schema: ${response.status}`);
    }
    return response.json();
  }
  
  /**
   * 读取配置
   * 
   * @param sourcePath - 相对路径（如 "app/settings.json"）
   * SHALL NOT: 使用绝对路径或包含 ../
   */
  async readConfig(sourcePath: string): Promise<ConfigResult> {
    // 路径安全检查
    if (sourcePath.startsWith('/') || sourcePath.includes('../')) {
      throw new Error("Path must be relative and not contain '../'");
    }
    
    const response = await fetch(`${this.baseUrl}/api/config/${sourcePath}`);
    
    switch (response.status) {
      case 403:
        throw new Error("Security violation: path not allowed");
      case 404:
        throw new Error(`Config file not found: ${sourcePath}`);
      case 200:
        return response.json();
      default:
        throw new Error(`Failed to read config: ${response.status}`);
    }
  }
  
  /**
   * 写入配置（自动处理乐观锁冲突）
   * 
   * MUST: 携带 versionHash
   * MUST: 处理 409 冲突并重试
   */
  async writeConfig(
    sourcePath: string,
    data: any,
    versionHash: string,
    maxRetries: number = 3
  ): Promise<ConfigResult> {
    let payload = {
      data,
      oldVersionHash: versionHash
    };
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const response = await fetch(`${this.baseUrl}/api/config/${sourcePath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.status === 200) {
        return response.json();
      } else if (response.status === 409) {
        // CRITICAL: 必须重试，禁止直接抛出异常
        if (attempt < maxRetries - 1) {
          const latest = await this.readConfig(sourcePath);
          payload.oldVersionHash = latest.meta.versionHash;
          continue;
        }
      } else if (!response.ok) {
        throw new Error(`Failed to write config: ${response.status}`);
      }
    }
    
    throw new Error(`Conflict persisted after ${maxRetries} retries`);
  }
  
  /**
   * 监听配置变化（SSE）
   * 
   * MUST: 处理 connected, modified, deleted 事件
   * MUST: 静默忽略 heartbeat 事件
   */
  watchConfig(
    sourcePath: string,
    callbacks: {
      onConnected?: (data: SSEEventData) => void;
      onModified?: (data: SSEEventData) => void;
      onDeleted?: (data: SSEEventData) => void;
      onError?: (error: Event) => void;
    }
  ): () => void {
    const es = new EventSource(`${this.baseUrl}/api/watch/${sourcePath}`);
    
    es.addEventListener('connected', (event) => {
      const data: SSEEventData = JSON.parse(event.data);
      callbacks.onConnected?.(data);
    });
    
    es.addEventListener('modified', (event) => {
      const data: SSEEventData = JSON.parse(event.data);
      callbacks.onModified?.(data);
    });
    
    es.addEventListener('deleted', (event) => {
      const data: SSEEventData = JSON.parse(event.data);
      callbacks.onDeleted?.(data);
    });
    
    // CRITICAL: 必须静默忽略 heartbeat
    es.addEventListener('heartbeat', () => {
      // SHALL NOT: 做任何处理，包括 console.log
    });
    
    es.onerror = (error) => {
      callbacks.onError?.(error);
    };
    
    // 返回清理函数
    return () => es.close();
  }
}

// 使用示例
const client = new OminiConfigClient();

// 监听配置变化
const unsubscribe = client.watchConfig('app/settings.json', {
  onConnected: (data) => console.log('Connected:', data.message),
  onModified: (data) => {
    if (data.newVersionHash !== localVersionHash) {
      // 提示用户刷新
      showConflictWarning();
    }
  },
  onDeleted: () => handleConfigDeleted(),
  onError: (err) => console.error('SSE error:', err)
});

// 清理时取消监听
// unsubscribe();
```

---

## 🚫 禁止事项清单 (PROHIBITED ACTIONS)

**SHALL NOT**:

1. ❌ **猜测字段类型** - 必须从 `/openapi.json` 获取 Schema
2. ❌ **使用绝对路径** - 如 `/etc/config.json` 将被 403 拦截
3. ❌ **路径穿越** - 包含 `../` 的路径将被安全沙箱拦截
4. ❌ **URL 编码斜杠** - 多层级路径直接拼接，不要编码
5. ❌ **忽略 409 冲突** - 必须实现重试逻辑，禁止直接崩溃
6. ❌ **响应 heartbeat** - 必须静默忽略心跳事件
7. ❌ **自动刷新用户数据** - 检测到冲突时必须让用户确认
8. ❌ **使用过时 Schema** - 每次生成代码前必须重新获取 OpenAPI

---

## 📋 验证清单 (Verification Checklist)

生成 Client 代码后，使用以下清单验证：

- [ ] **Schema 获取**: 代码中包含 `GET /openapi.json` 请求逻辑
- [ ] **路径检查**: 所有路径都是相对路径，无绝对路径或 `../`
- [ ] **Hash 携带**: POST 请求体中包含 `oldVersionHash` 字段
- [ ] **409 处理**: 捕获 409 状态码并实现重试逻辑
- [ ] **SSE 事件**: 处理 `connected`, `modified`, `deleted` 三种事件
- [ ] **心跳忽略**: `heartbeat` 事件处理函数为空，无任何操作
- [ ] **错误处理**: 403/404/409/400 都有明确的处理分支

---

**WARNING**: 违反上述任何契约可能导致：
- 安全沙箱拦截 (403)
- 并发冲突数据丢失 (409)
- SSE 连接异常
- 用户体验下降

**MUST**: 严格遵循本契约，确保生成的代码符合 OminiConfig 的设计规范。
