# 快速开始指南

**文档类型**: 开发指南  
**适用范围**: v2.0+  
**最后更新**: 2026-03-21  
**维护者**: OminiConfig Team

## 文档用途

本文档帮助新用户在 5 分钟内快速上手 OminiConfig，包括安装、启动和基础使用。

---

## 🎯 5 分钟快速开始

### 第 1 步：安装依赖（1 分钟）

```bash
# 克隆仓库
git clone https://github.com/Areazer/OminiConfig.git
cd OminiConfig

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

**依赖清单**:
- Python 3.8+
- FastAPI 0.104+
- Pydantic 2.5+
- anyio 4.0+
- watchdog 3.0+（可选，用于文件监控）

### 第 2 步：启动服务（1 分钟）

```bash
python main.py
```

启动成功后你会看到：

```
============================================================
🚀 OminiConfig Enterprise 启动中...
============================================================
📁 工作目录: /path/to/OminiConfig/configs
🖥️  GUI 界面: http://localhost:8000
📖 API 文档: http://localhost:8000/docs
📚 备用文档: http://localhost:8000/redoc
============================================================
```

### 第 3 步：使用 GUI 管理配置（3 分钟）

打开浏览器访问 http://localhost:8000

#### 界面概览

```
┌─────────────────────────────────────────────────────┐
│  🔧 OminiConfig          🟢 实时同步中      [保存]   │
├─────────────────────────────────────────────────────┤
│  版本哈希: abc123...    最后修改: 2026-03-21 10:30   │
├─────────────────────────────────────────────────────┤
│  配置编辑                                            │
│  ├─ 🔵 debug: [true ▼]                             │
│  ├─ 🟢 port: [8080    ]                            │
│  └─ 🟣 database: [object]                          │
│       ├─ 🔵 host: [localhost    ]                  │
│       └─ 🟢 port: [5432    ]                       │
└─────────────────────────────────────────────────────┘
```

#### 基础操作

1. **编辑配置**
   - 点击任意字段即可编辑
   - 支持类型：字符串、数字、布尔值、对象、数组
   - 对象和数组会自动展开显示子字段

2. **保存配置**
   - 点击右上角绿色"保存"按钮
   - 系统会自动携带 versionHash 防止冲突
   - 保存成功后会显示绿色提示

3. **处理冲突**
   - 如果外部程序修改了配置，会显示黄色 Toast 提示
   - 点击"刷新页面"加载最新配置
   - 或点击"稍后处理"继续编辑当前内容

---

## 📚 进阶使用

### 使用 REST API

除了 GUI，你也可以直接使用 REST API：

```bash
# 读取配置
curl http://localhost:8000/api/config/app/settings.json

# 保存配置
curl -X POST http://localhost:8000/api/config/app/settings.json \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"debug": true},
    "oldVersionHash": "abc123..."
  }'
```

### 实时监控（SSE）

JavaScript 示例：

```javascript
const es = new EventSource('/api/watch/app/settings.json');

es.addEventListener('modified', (event) => {
  const data = JSON.parse(event.data);
  console.log('配置已更新:', data.newVersionHash);
});
```

### 配置多格式支持

默认支持 JSON，可以扩展支持 YAML：

```python
# 创建 core/adapters/yaml_adapter.py
import yaml
from core.adapter import BaseConfigAdapter, AdapterFactory

@AdapterFactory.register
class YamlAdapter(BaseConfigAdapter):
    supported_extensions = ['.yaml', '.yml']
    
    async def read_config(self, file_path):
        # 实现读取逻辑
        pass
    
    async def write_config(self, file_path, data, old_hash):
        # 实现写入逻辑
        pass
```

---

## 🔧 配置工作目录

默认工作目录是 `./configs`，可以修改环境变量：

```bash
export OMINI_WORKSPACE=/path/to/your/configs
python main.py
```

或者在代码中修改：

```python
# main.py
WORKSPACE_DIR = Path("/path/to/your/configs").resolve()
```

---

## 🐛 常见问题

### Q: 端口 8000 被占用怎么办？

```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程后重新启动
kill -9 <PID>
python main.py
```

### Q: GUI 页面无法加载？

检查：
1. 服务是否已启动（看控制台输出）
2. 浏览器是否支持 JavaScript
3. 网络连接是否正常

### Q: 保存配置时提示"并发冲突"？

这意味着在你编辑期间，配置文件被其他程序修改了：
1. 刷新页面加载最新配置
2. 重新应用你的修改
3. 再次保存

### Q: 如何修改默认配置文件路径？

编辑 `static/index.html` 中的 `CONFIG_PATH`：

```javascript
const CONFIG_PATH = 'your/config/path.json';
```

---

## 📖 下一步

- 阅读 [架构设计文档](../architecture/v2_enterprise.md) 了解实现原理
- 查看 [API 文档](../api/README.md) 了解完整接口
- 参考 [开发规范](../../AGENTS.md) 参与贡献

---

## 💡 提示

- **开发模式**: 使用 `python main.py` 会自动重载代码变更
- **生产模式**: 建议使用 `uvicorn main:app --host 0.0.0.0 --port 8000`
- **日志**: 默认输出到控制台，可以重定向到文件：`python main.py > app.log 2>&1`

---

**遇到问题？** 查看 [FAQ](./faq.md) 或在 [GitHub Issues](https://github.com/Areazer/OminiConfig/issues) 提问。
