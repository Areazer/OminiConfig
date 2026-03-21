# OminiConfig 开发规范与最佳实践

> 本文件定义了 OminiConfig 项目的开发规则，所有代码变更必须遵循以下规范。

## 1. 开发工作流程（强制）

### 1.1 代码编写完成后的强制检查清单

每次完成代码编写或重构后，**必须**按顺序执行以下步骤：

#### ✅ 步骤 1：单元测试（Test）【强制】

**核心原则：每个功能必须有对应的单元测试，测试未通过不能提交**

- [ ] **为每个新功能/修改编写对应的单元测试（强制）**
  - **每个功能都要有测试**：任何新增功能、bug修复、重构都必须有对应的单元测试
  - **测试覆盖率目标**：核心逻辑 ≥ 90%，新增代码必须 100% 覆盖
  - **测试文件命名**：`tests/test_<module_name>.py`
  - **测试类命名**：`Test<被测类名>`，如 `TestPathSecurityValidator`
  - **测试方法命名**：`test_<被测功能>_<场景>_<预期结果>`，如 `test_validate_path_with_traversal_attack_blocked`
  
- [ ] **编写完整的测试场景（强制）**
  - 正常流程（Happy Path）：标准输入下的预期行为
  - 边界条件：空值、极值、最大/最小长度等
  - 异常处理：非法输入、异常情况下的行为
  - 并发场景（如适用）：多线程/多进程竞争条件
  - 安全场景：恶意输入防御测试
  
- [ ] **运行完整测试套件并确保通过（强制）**
  ```bash
  # 运行所有测试
  python -m pytest tests/ -v --tb=short
  
  # 运行特定模块测试
  python -m pytest tests/test_<module>.py -v
  
  # 生成覆盖率报告
  python -m pytest tests/ --cov=core --cov-report=html
  ```
  
- [ ] **测试通过标准（强制）**
  - ✅ 所有测试必须 PASS，不允许有失败的测试
  - ✅ 代码覆盖率 ≥ 90%
  - ✅ 如果测试失败，必须修复代码或更新测试（禁止删除测试来绕过失败）
  - ✅ 禁止提交带有 `@pytest.mark.skip` 或 `@pytest.mark.xfail` 的测试，除非有充分的理由并添加注释说明

#### ✅ 步骤 2：项目文档（Documentation）

**⚠️ 重要：doc/ 目录是项目的官方文档中心**

- [ ] **更新根目录 README.md**
  - 如果新增 API 端点，更新 API 使用示例章节
  - 如果新增依赖，更新安装说明
  - 如果变更项目结构，更新目录树
  - 如果新增功能特性，更新特性列表
  - **原则**：README.md 是用户第一眼看到的文档，必须保持最新和完整
  
- [ ] **更新 doc/ 目录下的具体文档**
  - **架构设计** (`doc/architecture/`): 如果修改架构设计
  - **API 文档** (`doc/api/`): 如果新增或修改 API
  - **开发指南** (`doc/guides/`): 如果变更开发流程
  - **规范标准** (`doc/standards/`): 如果变更规范
  
- [ ] **文档文件头部信息**
  - 所有文档必须包含标准头部（文档类型、适用范围、最后更新、维护者）
  - 修改文档后更新 `最后更新` 日期
  
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

#### 测试目录结构

项目使用两个测试相关目录，明确区分功能单元测试和临时验证脚本：

```
project_root/
├── tests/                    # ✅ 功能单元测试（必须提交到 Git）
│   ├── README.md            # tests 目录说明
│   ├── __init__.py
│   ├── conftest.py          # pytest 共享 fixtures
│   ├── test_security.py     # core/security.py 测试
│   ├── test_adapter.py      # core/adapter.py 测试
│   ├── test_router.py       # api/router.py 测试
│   └── utils/               # 测试工具函数（可选）
│       ├── __init__.py
│       └── helpers.py
│
└── tempTests/               # 📝 临时验证脚本（不提交到 Git）
    ├── README.md            # tempTests 目录说明
    └── 2026-03-21_test_feature_x.py  # 临时脚本示例
```

#### tests/ vs tempTests/ 对比

| 特性 | tests/ | tempTests/ |
|------|--------|------------|
| **用途** | 功能单元测试 | 临时验证脚本 |
| **生命周期** | 长期维护 | 短期使用，用完删除 |
| **代码质量** | 高（完整断言、覆盖率≥90%） | 低（只要能验证即可） |
| **自动化** | ✅ pytest 自动化运行 | ❌ 手动执行 |
| **Git 提交** | ✅ **必须提交** | ❌ **禁止提交**（已在 .gitignore） |
| **CI 检查** | ✅ 必须通过 | ❌ 不运行 |
| **文件命名** | `test_<模块>.py` | `<日期>_<描述>.py` |

#### 何时使用 tests/？

- ✅ **功能单元测试**：每个新功能/修复必须有对应测试
- ✅ **回归测试**：防止 Bug 再次出现
- ✅ **CI/CD 集成**：自动化测试流程
- ✅ **高覆盖率要求**：核心模块≥90%，新增代码100%

#### 何时使用 tempTests/？

- ✅ **快速验证**：临时测试某个想法
- ✅ **调试脚本**：复现特定问题的脚本
- ✅ **探索性测试**：还不确定如何写成正式测试
- ✅ **性能基准**：临时性能测试或分析
- ✅ **数据生成**：一次性测试数据生成

#### tempTests/ 使用规范

1. **文件命名**：`YYYY-MM-DD_<简要描述>.py`
   - 示例：`2026-03-21_test_sse_connection.py`

2. **使用流程**：
   ```bash
   # 创建临时脚本
   touch tempTests/2026-03-21_test_feature_x.py
   
   # 编写验证代码...
   
   # 运行验证
   python tempTests/2026-03-21_test_feature_x.py
   
   # 验证完成后：
   # - 如果有价值 → 重构为正式测试放入 tests/
   # - 如果只是临时 → 删除脚本
   rm tempTests/2026-03-21_test_feature_x.py
   ```

3. **清理策略**：
   - 定期清理（建议每月一次）
   - 不要将 tempTests/ 提交到 Git（已添加到 .gitignore）
   - 有价值的验证必须转化为 tests/ 中的正式测试

#### 测试文件命名规范

- **正式测试**（tests/）：`test_<被测模块名>.py`
  - `test_security.py` - 测试 core/security.py
  - `test_adapter.py` - 测试 core/adapter.py
  - `test_router.py` - 测试 api/router.py

- **临时脚本**（tempTests/）：`<日期>_<描述>.py`
  - `2026-03-21_test_config_validation.py`
  - `2026-03-22_debug_concurrency_issue.py`

#### 目录说明文档

- `tests/README.md` - 功能单元测试目录说明
- `tempTests/README.md` - 临时脚本目录说明

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

### 2.4 测试执行与提交流程

**【强制】无测试禁止提交原则**

任何代码变更（包括功能新增、Bug修复、重构）都必须满足：

1. **必须有对应的测试覆盖**
   - 新增功能 → 新增测试
   - Bug修复 → 添加回归测试（防止再次出现问题）
   - 重构 → 确保原有测试仍然通过，必要时更新测试

2. **测试必须在提交前本地通过**
   ```bash
   # 提交前必须执行的命令
   python -m pytest tests/ -v
   ```
   - 如果测试失败，禁止提交
   - 不能通过删除或跳过测试来绕过失败

3. **CI/CD 检查**
   - Pull Request 必须通过所有自动化测试
   - 代码覆盖率不能低于 90%
   - 新增代码必须 100% 覆盖

4. **测试失败的处理**
   - ❌ **禁止**：删除失败的测试以通过检查
   - ❌ **禁止**：使用 `@pytest.mark.skip` 跳过失败的测试（除非有充分理由）
   - ✅ **正确**：修复代码使测试通过
   - ✅ **正确**：如果测试本身有问题，修正测试（而非删除）

**测试提交检查清单（Commit Checklist）**

```markdown
## 提交前检查

- [ ] 为新功能/修复编写了对应的单元测试
- [ ] 测试覆盖了正常流程、边界条件、异常处理
- [ ] 运行 `pytest tests/ -v` 所有测试通过
- [ ] 代码覆盖率 ≥ 90%
- [ ] 没有使用 @pytest.mark.skip 或 @pytest.mark.xfail（除非有注释说明）
```

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

## 9. 会话上下文管理规范【强制】

### 9.1 目的

会话上下文文档用于记录开发会话的状态、进展和决策，确保：
1. **知识传递**：新会话快速了解项目当前状态
2. **连续性**：会话间的开发工作无缝衔接
3. **可追溯性**：项目演进历史有完整记录
4. **协作效率**：团队成员了解彼此的工作进展

### 9.2 文件结构

```
doc/context/
├── README.md                    # 目录说明
├── current.md                   # 📌 当前会话上下文（必须保持最新）
├── history/                     # 历史会话上下文归档
│   ├── 2026-03-21_init.md
│   └── 2026-03-22_feature.md
└── templates/                   # 模板文件
    ├── session_start.md
    └── session_end.md
```

### 9.3 核心文件定义

#### current.md（当前上下文）【必须保持最新】

**更新时机**: 每次开发会话结束时  
**用途**: 新会话的第一个读取点  
**必须包含的内容**:
1. 项目概览（版本、分支、最新提交）
2. 近期开发进展（已完成/进行中/计划中）
3. 技术债务与待办事项（按优先级分类）
4. 当前架构状态（模块状态、已知限制）
5. 最近的决策记录（决策内容+理由）
6. 测试与质量状态（覆盖率、Bug列表）
7. 文档状态（已更新/待完成/缺失）
8. 下次会话建议（优先级排序）
9. 环境信息（Python版本、依赖、配置）
10. 快速参考（常用命令、关键文件）

#### history/（历史归档）

**命名规范**: `YYYY-MM-DD_简要描述.md`  
**归档时机**: 每次更新 `current.md` 后，将旧版本复制到 history/  
**保留策略**: 保留最近 20 个或 3 个月的历史文件

#### templates/（模板文件）

- **session_start.md**: 会话开始检查清单
- **session_end.md**: 会话结束总结模板

### 9.4 工作流程【强制】

#### 会话开始

```
1. 读取 doc/context/current.md
   ↓
2. 使用 templates/session_start.md 检查环境
   ↓
3. 明确本次会话目标
   ↓
4. 开始开发
```

**检查清单**:
- [ ] 阅读 current.md 了解项目状态
- [ ] 查看最近的 git log
- [ ] 检查环境（Python版本、依赖）
- [ ] 运行测试确保基准状态
- [ ] 启动服务验证功能正常

#### 会话结束【强制更新上下文】

```
1. 完成开发和测试
   ↓
2. 使用 templates/session_end.md 总结会话
   ↓
3. 【强制】更新 doc/context/current.md
   ↓
4. 【强制】将旧的 current.md 复制到 doc/context/history/
   ↓
5. 提交所有变更（包括上下文文档）
   ↓
6. 推送至 GitHub
```

**强制检查项**:
- [ ] 已更新 `doc/context/current.md`
- [ ] 已将旧的 `current.md` 归档到 `history/`
- [ ] 历史文件命名符合规范
- [ ] 上下文文档已提交到 Git

### 9.5 上下文更新规范

#### DO（应该做）
- ✅ 每次会话结束都更新 `current.md`
- ✅ 保持 `current.md` 简洁，聚焦于当前状态
- ✅ 记录关键决策的理由
- ✅ 使用具体数据（覆盖率百分比、测试数量）
- ✅ 定期归档历史文件
- ✅ 使用模板确保内容完整

#### DON'T（不应该做）
- ❌ 让 `current.md` 过时（禁止！）
- ❌ 在 `current.md` 中记录过长的实现细节
- ❌ 删除历史上下文文件
- ❌ 提交敏感信息（密码、密钥）
- ❌ 跳过上下文更新直接提交代码

### 9.6 与 AGENTS.md 的关系

| 文档 | 用途 | 更新频率 |
|------|------|----------|
| **AGENTS.md** | 定义开发规范和流程（不变的标准） | 规范变更时更新 |
| **current.md** | 记录项目实时状态和进展 | 每次会话结束更新 |

**配合使用**:
1. 新会话开始时，先读 AGENTS.md 了解规范
2. 再读 current.md 了解项目状态
3. 开发过程中遵循 AGENTS.md 的规范
4. 会话结束时更新 current.md

### 9.7 提交检查清单

**代码提交前必须检查**:

```markdown
## 上下文更新检查

- [ ] 已更新 doc/context/current.md
- [ ] current.md 包含所有必需章节（1-10）
- [ ] 已将旧的 current.md 复制到 history/
- [ ] 历史文件命名格式: YYYY-MM-DD_简要描述.md
- [ ] current.md 中的"最后更新时间"已更新
- [ ] "下次会话建议"部分已填写
- [ ] 文档已添加到 git（git add doc/context/）
```

### 9.8 示例场景

#### 场景 1：隔日继续开发
```
1. 阅读 doc/context/current.md
2. 查看 "下次会话计划" 了解今天的任务
3. 检查 "遇到的问题" 是否有遗留问题
4. 运行测试确认基准状态
5. 开始开发
```

#### 场景 2：新功能开发完成
```
1. 完成功能开发和测试
2. 使用 session_end.md 模板总结
3. 更新 current.md：
   - 将功能从"进行中"移到"已完成"
   - 添加决策记录（如采用某种设计方案）
   - 更新测试覆盖率数据
   - 更新文档状态
   - 填写下次会话建议
4. 将旧的 current.md 复制到 history/
5. git add doc/context/
6. git commit -m "feat: 添加新功能

- 实现 XXX
- 添加 YYY 测试
- 更新文档

更新上下文: doc/context/current.md"
```

---

## 10. 🤖 机器智能体接入指南 (Agent Integration Guide)

本文件专为 AI Agent（如 Claude, GPT-4, Kimi）编写。在为其他项目生成接入 OminiConfig 的代码时，请严格遵守以下契约，禁止任何猜测。

### 10.1 核心寻址规则 (Addressing Rule)

- OminiConfig 的所有 API 均不接受绝对路径（如 `/etc/config.json`）。
- API 路径中的 `{source_path}` 必须是相对于 **OminiConfig 服务启动目录** 的相对路径。
- **编码要求**：在发起 HTTP 请求前，如果路径包含特殊字符或多层级（如 `folder/sub/conf.json`），不需要对 `/` 进行 URL Encode，直接作为 Path Variable 拼接。

### 10.2 严格状态码契约 (Status Code Contract)

在编写 HTTP Client 时，你必须实现对以下状态码的精确捕获：

| 状态码 | 含义 | 处理建议 |
|--------|------|----------|
| `200 OK` | 读写成功 | 正常处理响应数据 |
| `400 Bad Request` | 请求体格式错误（如非法的 JSON） | 检查请求体格式，重试 |
| `403 Forbidden` | 触发安全沙箱（检测到 `../` 路径穿越行为） | 检查路径是否包含非法字符，使用合法相对路径 |
| `404 Not Found` | 目标配置文件不存在 | 读取时需确保文件存在；写入时会自动创建，无需处理 |
| `409 Conflict` | 乐观锁冲突 | 请求体中的 `oldVersionHash` 与服务端最新 Hash 不一致，需要重新读取配置获取最新 Hash 后重试 |

### 10.3 终极接口定义 (The Source of Truth)

OminiConfig 基于 FastAPI 构建。不要试图从 Markdown 中猜测详细的字段类型。

**你的第一动作：** 请直接向 OminiConfig 服务发送 `GET /openapi.json` 请求，获取完整的、符合 OpenAPI 3.0 规范的 Schema 定义，并严格按照该 JSON 定义生成接入代码或强类型接口（Type Definitions）。

**示例**：
```bash
curl http://localhost:8000/openapi.json
```

### 10.4 实时监听约定 (SSE Contract)

如果目标项目需要监听配置变化，请使用 Server-Sent Events 连接 `/api/watch/{source_path}`。

**必须处理的事件类型**：

| 事件类型 | 触发时机 | 处理建议 |
|----------|----------|----------|
| `connected` | SSE 连接建立成功 | 记录日志，初始化监听状态 |
| `modified` | 配置文件被修改 | **关键事件**：Event Data 包含 `newVersionHash` 和 `newData`，需要对比本地 Hash，如果不一致则提示用户刷新 |
| `deleted` | 配置文件被删除 | 提示用户配置文件已删除，清理本地状态 |
| `heartbeat` | 保活心跳（每 30 秒） | 忽略即可，无需回应，仅用于检测连接状态 |

**JavaScript 示例**：
```javascript
const es = new EventSource('http://localhost:8000/api/watch/app/config.json');

es.addEventListener('modified', (event) => {
  const data = JSON.parse(event.data);
  if (data.newVersionHash !== localVersionHash) {
    // 显示冲突提示，让用户选择是否刷新
    showConflictWarning();
  }
});

es.addEventListener('heartbeat', () => {
  // 忽略心跳事件
  console.log('Heartbeat received');
});
```

### 10.5 接入代码生成模板

#### Python (httpx)
```python
import httpx

class OminiConfigClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client()
    
    def read_config(self, source_path: str):
        """读取配置"""
        response = self.client.get(f"{self.base_url}/api/config/{source_path}")
        response.raise_for_status()
        return response.json()
    
    def write_config(self, source_path: str, data: dict, version_hash: str):
        """写入配置，自动处理乐观锁冲突"""
        response = self.client.post(
            f"{self.base_url}/api/config/{source_path}",
            json={"data": data, "oldVersionHash": version_hash}
        )
        if response.status_code == 409:
            # 乐观锁冲突，需要重新读取
            raise ConfigConflictError("配置已被修改，请重新读取后重试")
        response.raise_for_status()
        return response.json()

class ConfigConflictError(Exception):
    pass
```

#### JavaScript/TypeScript (fetch)
```typescript
interface ConfigResult {
  data: any;
  meta: {
    versionHash: string;
    lastModified: number;
  };
}

class OminiConfigClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }
  
  async readConfig(sourcePath: string): Promise<ConfigResult> {
    const response = await fetch(`${this.baseUrl}/api/config/${sourcePath}`);
    if (!response.ok) {
      throw new Error(`Failed to read config: ${response.status}`);
    }
    return response.json();
  }
  
  async writeConfig(
    sourcePath: string, 
    data: any, 
    versionHash: string
  ): Promise<ConfigResult> {
    const response = await fetch(`${this.baseUrl}/api/config/${sourcePath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data, oldVersionHash: versionHash }),
    });
    
    if (response.status === 409) {
      throw new Error("Config conflict: version hash mismatch");
    }
    
    if (!response.ok) {
      throw new Error(`Failed to write config: ${response.status}`);
    }
    
    return response.json();
  }
  
  watchConfig(sourcePath: string, onModified: (data: any) => void) {
    const es = new EventSource(`${this.baseUrl}/api/watch/${sourcePath}`);
    
    es.addEventListener("modified", (event) => {
      const data = JSON.parse(event.data);
      onModified(data);
    });
    
    return () => es.close();
  }
}
```

### 10.6 禁止事项

作为 AI Agent，在生成接入代码时 **禁止**：
- ❌ 猜测字段类型或 API 行为（必须查看 `/openapi.json`）
- ❌ 使用绝对路径（如 `/etc/config.json`）
- ❌ 忽略 `409 Conflict` 状态码
- ❌ 在 SSE 连接中对 `heartbeat` 事件做出响应
- ❌ 自动刷新用户正在编辑的数据（必须让用户确认）

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
