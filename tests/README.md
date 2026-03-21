# tests/ - 功能单元测试目录

**文档类型**: 测试规范  
**适用范围**: 全版本  
**最后更新**: 2026-03-21  
**维护者**: OminiConfig Team

## 目录用途

本目录用于存放项目的**功能单元测试**，所有测试必须是：
- ✅ 可重复运行的
- ✅ 独立的（不依赖外部状态）
- ✅ 自动化的（可在 CI 中运行）
- ✅ 有断言的（验证具体行为）

## 与 tempTests/ 的区别

| 特性 | tests/ | tempTests/ |
|------|--------|------------|
| **用途** | 功能单元测试 | 临时验证脚本 |
| **生命周期** | 长期维护 | 短期使用，用完删除 |
| **运行方式** | pytest 自动化运行 | 手动执行 |
| **质量要求** | 高（断言完整、覆盖率） | 低（只要能验证即可） |
| **提交到 Git** | ✅ 必须提交 | ❌ 可选，通常不提交 |
| **CI 检查** | ✅ 会运行 | ❌ 不运行 |

## 目录结构

```
tests/
├── README.md                  # 本文件
├── __init__.py               # 包初始化
├── conftest.py               # pytest 共享 fixtures
├── test_security.py          # core/security.py 测试
├── test_adapter.py           # core/adapter.py 测试
├── test_router.py            # api/router.py 测试
└── utils/                    # 测试工具函数（可选）
    ├── __init__.py
    └── helpers.py
```

## 测试文件命名规范

- **格式**: `test_<被测模块名>.py`
- **示例**:
  - `test_security.py` - 测试 core/security.py
  - `test_adapter.py` - 测试 core/adapter.py
  - `test_router.py` - 测试 api/router.py

## 测试编写规范

### 1. 基本结构

```python
import pytest
from core.security import PathSecurityValidator

class TestPathSecurityValidator:
    """PathSecurityValidator 测试类"""
    
    @pytest.fixture
    def validator(self):
        """创建测试用的 validator 实例"""
        return PathSecurityValidator("./test_workspace")
    
    def test_valid_path_allowed(self, validator):
        """测试：正常路径应该被允许"""
        # Arrange
        source_path = "config.json"
        
        # Act
        result = validator.validate(source_path)
        
        # Assert
        assert result.name == "config.json"
    
    def test_path_traversal_blocked(self, validator):
        """测试：路径穿越攻击应该被拦截"""
        # Arrange
        malicious_path = "../../../etc/passwd"
        
        # Act & Assert
        with pytest.raises(SecurityError) as exc_info:
            validator.validate(malicious_path)
        
        assert "路径穿越" in str(exc_info.value)
```

### 2. 命名规范

- **测试类**: `Test<被测类名>`
  - 示例: `TestPathSecurityValidator`, `TestJsonAdapter`
  
- **测试方法**: `test_<被测功能>_<场景>_<预期结果>`
  - 示例: 
    - `test_validate_path_with_traversal_attack_blocked`
    - `test_read_config_with_missing_file_initializes_empty`
    - `test_write_config_with_concurrent_conflict_raises_exception`

### 3. 必须覆盖的场景

每个功能必须测试以下场景：

| 场景类型 | 说明 | 示例 |
|---------|------|------|
| **正常流程** | 标准输入下的预期行为 | `test_valid_path_allowed` |
| **边界条件** | 极端输入值 | `test_empty_file_initializes_empty` |
| **异常处理** | 错误输入下的行为 | `test_malformed_json_raises_format_exception` |
| **并发场景** | 多线程/多进程竞争 | `test_concurrent_writes_race_condition` |
| **安全场景** | 恶意输入防御 | `test_path_traversal_blocked` |

### 4. Fixture 使用

共享的测试数据和对象应定义在 `conftest.py`：

```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def temp_workspace(tmp_path):
    """提供临时工作目录"""
    return tmp_path

@pytest.fixture
def sample_config():
    """提供标准测试配置数据"""
    return {
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }
```

## 运行测试

### 运行所有测试
```bash
python -m pytest tests/ -v
```

### 运行特定模块测试
```bash
python -m pytest tests/test_security.py -v
```

### 运行特定测试方法
```bash
python -m pytest tests/test_security.py::TestPathSecurityValidator::test_valid_path_allowed -v
```

### 生成覆盖率报告
```bash
python -m pytest tests/ --cov=core --cov-report=html
```

### 带详细错误信息的测试
```bash
python -m pytest tests/ -v --tb=short
```

## 覆盖率要求

- **核心模块 (core/)**: ≥ 90%
- **新增代码**: 必须 100% 覆盖
- **API 路由 (api/)**: ≥ 80%

## 最佳实践

### DO（应该做）
- ✅ 每个新功能都要有对应的测试
- ✅ 使用描述性的测试方法名
- ✅ 使用 fixtures 共享测试数据
- ✅ 测试失败时提供清晰的错误信息
- ✅ 保持测试独立，不依赖执行顺序
- ✅ 使用临时目录，不污染工作目录

### DON'T（不应该做）
- ❌ 在测试中使用 `print()` 调试（使用断点或日志）
- ❌ 测试之间共享可变状态
- ❌ 测试外部依赖（使用 mock）
- ❌ 提交失败的测试或跳过测试（除非有充分理由）
- ❌ 测试私有方法（除非必要）

## 临时脚本存放

如果只是临时验证某个功能，不需要完整的测试：
- 请将脚本放在 `tempTests/` 目录
- 不要提交到 Git（添加到 .gitignore）
- 验证完成后删除

---

**注意**: 所有提交到本目录的代码都必须通过 pytest 检查！
