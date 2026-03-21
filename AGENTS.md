# OminiConfig 开发规范与最佳实践

> 本文件定义了 OminiConfig 项目的开发规则，所有代码变更必须遵循以下规范。

## 1. 开发工作流程（强制）

### 1.1 代码编写完成后的强制检查清单

每次完成代码编写或重构后，**必须**按顺序执行以下步骤：

#### ✅ 步骤 1：单元测试（Test）
- [ ] **为新功能编写对应的单元测试**
  - 测试覆盖率目标：核心逻辑 ≥ 90%
  - 必须包含：正常流程、异常边界、并发场景（如适用）
  - 测试文件路径：`tests/test_<module_name>.py`
  
- [ ] **运行完整测试套件**
  ```bash
  python -m pytest tests/ -v --tb=short
  ```
  
- [ ] **确保所有测试通过**
  - 不允许提交失败的测试
  - 如果测试失败，修复代码或更新测试（而非删除测试）

#### ✅ 步骤 2：项目文档（Documentation）
- [ ] **更新 README.md**
  - 如果新增 API 端点，更新 API 文档部分
  - 如果新增依赖，更新安装说明
  - 如果变更配置方式，更新使用示例
  
- [ ] **更新 ARCHITECTURE.md**
  - 如果修改架构设计，更新架构图和说明
  - 如果新增模块，添加模块职责说明
  - 如果修改数据流，更新流程图
  
- [ ] **更新 CHANGELOG.md**（如适用）
  - 记录新增功能、修复的 Bug、破坏性变更
  - 遵循语义化版本规范（SemVer）

#### ✅ 步骤 3：代码质量检查（Quality）
- [ ] **类型检查**
  ```bash
  python -m mypy core/ api/ --ignore-missing-imports
  ```
  
- [ ] **代码风格检查**
  ```bash
  python -m ruff check .
  python -m black --check .
  ```
  
- [ ] **导入排序检查**
  ```bash
  python -m isort --check-only .
  ```

#### ✅ 步骤 4：功能验证（Verification）
- [ ] **本地手动测试**
  - 启动服务：`python main.py`
  - 使用 curl 或 Postman 测试新增端点
  - 验证 SSE 实时推送（如适用）
  
- [ ] **并发测试**（如修改并发逻辑）
  - 使用脚本模拟多客户端并发写入
  - 验证乐观锁冲突检测是否正常工作

### 1.2 提交流程

```
代码编写完成
    ↓
[强制] 更新/添加单元测试
    ↓
[强制] 运行 pytest 确保全量通过
    ↓
[强制] 更新项目文档（README、ARCHITECTURE）
    ↓
[强制] 代码质量检查（类型、风格）
    ↓
[推荐] 本地功能验证
    ↓
git add → git commit → git push
```

## 2. 测试规范

### 2.1 测试文件组织

```
tests/
├── __init__.py
├── test_security.py      # 安全模块测试
├── test_adapter.py       # 适配器模块测试
├── test_router.py        # API 路由测试
└── conftest.py          # pytest 共享 fixtures
```

### 2.2 测试编写规范

```python
# ✅ 好的测试：描述性行为、独立、可重复
class TestPathSecurityValidator:
    """路径安全校验器测试套件"""
    
    @pytest.fixture
    def validator(self):
        """每个测试方法独立的 validator 实例"""
        return PathSecurityValidator("./test_workspace")
    
    def test_valid_path_allowed(self, validator):
        """测试：正常路径应通过校验"""
        path = validator.validate("config.json")
        assert path.name == "config.json"
    
    def test_path_traversal_blocked(self, validator):
        """测试：路径穿越攻击应被拦截"""
        with pytest.raises(SecurityError) as exc_info:
            validator.validate("../../../etc/passwd")
        assert "路径穿越" in str(exc_info.value)
```

### 2.3 必须测试的场景

| 场景类型 | 说明 | 示例 |
|---------|------|------|
| **正常流程** | 标准输入下的预期行为 | 读取存在的配置文件 |
| **边界条件** | 极端输入值 | 空文件、超大文件、嵌套层级超过限制 |
| **异常处理** | 错误输入下的行为 | 非法路径、损坏的 JSON、并发冲突 |
| **并发场景** | 多线程/多进程竞争 | 同时写入同一文件、读写竞争 |
| **安全场景** | 恶意输入防御 | 路径穿越、空字节注入、符号链接劫持 |

## 3. 文档规范

### 3.1 README.md 结构

```markdown
# OminiConfig

## 简介
一句话描述项目核心价值。

## 功能特性
- 特性 1：简要说明
- 特性 2：简要说明

## 快速开始
### 安装
### 启动服务

## API 文档
### 读取配置
### 保存配置
### 实时监控

## 开发指南
### 项目结构
### 运行测试

## 许可证
```

### 3.2 ARCHITECTURE.md 结构

```markdown
# 架构设计

## 系统架构图
[Mermaid 图或 ASCII 图]

## 核心模块
### 1. 模块名
- **职责**：一句话说明
- **关键类**：类名及说明
- **设计模式**：使用的模式

## 数据流
[描述请求从接收到响应的完整流程]

## 关键设计决策
### 决策 1：为什么选择方案 A 而非 B？
- 背景：...
- 考量：...
- 结论：...
```

### 3.3 代码注释规范

```python
# ✅ 好的注释：解释"为什么"而非"做了什么"

# ❌ 不好的注释
# 递增计数器
counter += 1

# ✅ 好的注释
# 乐观锁：使用版本号而非悲观锁，因为配置修改是低频操作，
# 冲突概率低，无锁性能更好
counter += 1

# ✅ 好的文档字符串
def validate(self, source_path: str) -> Path:
    """
    校验并规范化用户传入的路径
    
    安全策略：
    1. 拒绝包含空字节的路径（防止空字节注入攻击）
    2. 拒绝绝对路径（强制使用相对路径）
    3. 使用 Path.resolve() 规范化路径并解析符号链接
    4. 使用 os.path.commonpath() 严格校验前缀匹配
    
    Args:
        source_path: 前端传入的原始路径字符串
        
    Returns:
        Path: 规范化后的绝对路径对象
        
    Raises:
        SecurityError: 当检测到路径穿越攻击时抛出 403 异常
    """
```

## 4. 代码规范

### 4.1 类型注解（强制）

所有函数、方法、类属性**必须**包含类型注解：

```python
from typing import Dict, Any, Optional, Union
from pathlib import Path

# ✅ 好的类型注解
async def read_config(
    self,
    file_path: Path,
    options: Optional[Dict[str, Any]] = None
) -> ConfigResult:
    ...

# ✅ 复杂的 Union 类型应使用 TypeAlias
ConfigValue = Union[str, int, float, bool, None, Dict[str, Any], list]
```

### 4.2 异步编程规范

```python
# ✅ 文件 I/O 必须使用线程池，避免阻塞事件循环
async def read_file_async(file_path: Path) -> str:
    return await anyio.to_thread.run_sync(_sync_read, file_path)

def _sync_read(file_path: Path) -> str:
    with open(file_path, 'r') as f:
        return f.read()

# ❌ 错误：在 async 函数中直接进行同步 I/O
async def read_file_wrong(file_path: Path) -> str:
    with open(file_path, 'r') as f:  # 这会阻塞整个服务器！
        return f.read()
```

### 4.3 错误处理规范

```python
# ✅ 自定义异常继承自 HTTPException，统一错误响应
class ConcurrencyConflictException(HTTPException):
    def __init__(self, expected: str, actual: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ConcurrencyConflictException",
                "message": f"版本冲突...",
                "expected_hash": expected,
                "actual_hash": actual
            }
        )

# ✅ 异常链：保留原始异常信息
try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    raise ConfigFormatException(
        f"JSON 解析错误: {e.msg}"
    ) from e  # 保留原始异常链
```

## 5. 版本控制规范

### 5.1 提交信息格式

```
<type>: <subject>

<body>

<footer>
```

**Type 类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 仅文档变更
- `test`: 添加或修复测试
- `refactor`: 代码重构（不影响功能）
- `perf`: 性能优化
- `security`: 安全修复

**示例：**
```
feat: 添加 YAML 格式适配器支持

- 实现 YamlAdapter 类，支持 .yaml 和 .yml 文件
- 使用 PyYAML 库进行解析和序列化
- 注册到 AdapterFactory，自动根据扩展名选择

Closes #123
```

### 5.2 分支策略

```
main          # 生产分支，只能接收 PR
  ↓
develop       # 开发分支，日常开发
  ↓
feature/xxx   # 功能分支，从 develop 切出
  ↓
hotfix/xxx    # 紧急修复，从 main 切出
```

## 6. 安全检查清单

### 6.1 代码安全

- [ ] 所有用户输入的路径都经过 `PathSecurityValidator` 校验
- [ ] 没有使用 `eval()`、`exec()` 或动态代码执行
- [ ] 敏感信息（密钥、密码）不硬编码，使用环境变量
- [ ] 文件上传功能（如有）限制文件类型和大小

### 6.2 依赖安全

- [ ] 新增依赖需经过安全审查
- [ ] 定期更新依赖版本：`pip list --outdated`
- [ ] 使用 `pip-audit` 扫描已知漏洞

## 7. 性能优化清单

- [ ] 使用连接池（如数据库连接）
- [ ] 大文件使用流式处理，避免一次性加载到内存
- [ ] 频繁访问的数据考虑缓存（如 Schema 推导结果）
- [ ] 使用 `anyio.to_thread` 避免阻塞主循环

## 8. 自动化检查脚本

创建 `scripts/check.sh` 一键执行所有检查：

```bash
#!/bin/bash
set -e

echo "🔍 运行单元测试..."
pytest tests/ -v --tb=short

echo "📚 检查文档更新..."
# 检查 README.md 是否被修改
if ! git diff --name-only HEAD~1 | grep -q "README.md"; then
    echo "⚠️ 警告: README.md 未更新"
fi

echo "📝 类型检查..."
mypy core/ api/ --ignore-missing-imports

echo "🎨 代码风格检查..."
ruff check .
black --check .

echo "✅ 所有检查通过！"
```

---

## 附录：快速参考

### 添加新适配器的完整流程

```bash
# 1. 创建适配器文件
touch core/adapters/yaml_adapter.py

# 2. 实现适配器（参见 templates/adapter_template.py）
# ... 编写代码 ...

# 3. 注册适配器
# 在 adapter.py 中: AdapterFactory.register(YamlAdapter)

# 4. 编写单元测试
touch tests/test_yaml_adapter.py
# ... 编写测试 ...

# 5. 运行测试
pytest tests/test_yaml_adapter.py -v

# 6. 更新文档
# - README.md: 添加 YAML 支持说明
# - ARCHITECTURE.md: 添加 YamlAdapter 说明

# 7. 提交
git add .
git commit -m "feat: 添加 YAML 格式适配器支持"
```

### 提交前检查命令

```bash
# 一键检查（推荐在 git commit 前运行）
python -m pytest tests/ -v && \
python -m mypy core/ api/ --ignore-missing-imports && \
python -m ruff check . && \
echo "✅ 准备提交"
```

---

**最后更新**: 2026-03-21
**维护者**: OminiConfig Team
**生效版本**: v2.0+
