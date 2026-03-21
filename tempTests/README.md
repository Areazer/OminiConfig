# tempTests/ - 临时验证脚本目录

**文档类型**: 开发工具  
**适用范围**: 开发阶段  
**最后更新**: 2026-03-21  
**维护者**: OminiConfig Team

## 目录用途

本目录用于存放**临时的、一次性的验证脚本**，区别于 `tests/` 目录的正式单元测试。

**典型使用场景**:
- 🔍 快速验证某个功能是否正常工作
- 🧪 临时测试某个边界条件
- 📊 生成测试数据或性能基准
- 🔧 调试特定问题的复现脚本
- 📈 临时性能测试或分析

## 与 tests/ 的区别

| 特性 | tempTests/ | tests/ |
|------|------------|--------|
| **用途** | 临时验证脚本 | 功能单元测试 |
| **生命周期** | 短期使用，用完删除 | 长期维护 |
| **代码质量** | 不要求（只要能跑通）| 高（完整断言、覆盖率）|
| **自动化** | 手动执行 | pytest 自动化 |
| **Git 提交** | ❌ 不提交（已添加到 .gitignore）| ✅ 必须提交 |
| **CI 运行** | ❌ 不运行 | ✅ 必须全部通过 |

## 使用规范

### 1. 文件命名

```bash
# 格式: <日期>_<简要描述>.py
tempTests/2026-03-21_test_sse_connection.py
tempTests/2026-03-21_benchmark_schema_generation.py
tempTests/2026-03-22_debug_config_corruption.py
```

### 2. 文件模板

```python
#!/usr/bin/env python3
"""
临时验证脚本: <简要描述>

用途: <详细说明>
创建日期: YYYY-MM-DD
作者: <作者名>

使用方法:
    python tempTests/YYYY-MM-DD_description.py

备注:
    - <任何需要注意的事项>
"""

import sys
sys.path.insert(0, '.')

# 导入需要测试的模块
from core.security import PathSecurityValidator

def main():
    print("开始验证...")
    
    # 你的验证代码
    validator = PathSecurityValidator("./configs")
    result = validator.validate("test.json")
    print(f"结果: {result}")
    
    print("验证完成!")

if __name__ == "__main__":
    main()
```

### 3. 使用流程

```bash
# 1. 创建临时脚本
touch tempTests/2026-03-21_test_feature_x.py

# 2. 编写验证代码
# ... 编辑脚本 ...

# 3. 运行验证
python tempTests/2026-03-21_test_feature_x.py

# 4. 验证完成，决定是否保留
# - 如果有价值，重构为正式测试放入 tests/
# - 如果只是临时验证，直接删除
rm tempTests/2026-03-21_test_feature_x.py
```

## 何时使用 tempTests/ vs tests/

### 使用 tempTests/ 的场景

- ✅ 快速验证一个新想法
- ✅ 临时调试某个问题
- ✅ 一次性数据生成脚本
- ✅ 探索性测试（还不确定如何写成正式测试）
- ✅ 性能基准测试（临时的）

### 使用 tests/ 的场景

- ✅ 功能单元测试（需要长期维护）
- ✅ 回归测试（防止 Bug 再次出现）
- ✅ CI/CD 流程的一部分
- ✅ 需要高代码覆盖率的部分
- ✅ 需要详细文档的测试用例

## 清理策略

**定期清理本目录**（建议每月一次）：

```bash
# 查看所有临时脚本
ls -la tempTests/

# 删除一个月前的旧脚本
find tempTests/ -name "*.py" -mtime +30 -delete

# 或者全部清空（如果都已验证完毕）
rm tempTests/*.py
```

## 注意事项

⚠️ **不要提交到 Git！**

本目录已添加到 `.gitignore`：
```gitignore
# 临时测试脚本
tempTests/
!tempTests/README.md
```

**为什么？**
- 临时脚本通常是一次性的，不需要版本控制
- 避免仓库被临时文件污染
- 鼓励将有价值的验证转化为正式测试

## 最佳实践

### DO（应该做）
- ✅ 添加清晰的注释说明用途
- ✅ 使用有意义的文件名（包含日期和描述）
- ✅ 验证完成后决定是否转化为正式测试
- ✅ 定期清理旧脚本
- ✅ 在脚本顶部添加使用说明

### DON'T（不应该做）
- ❌ 不要提交到 Git（这是临时目录）
- ❌ 不要把需要长期维护的代码放在这里
- ❌ 不要依赖这里的脚本（它们可能被删除）
- ❌ 不要在这里放置敏感信息（如密码、密钥）

## 转化为正式测试

如果临时验证脚本有价值，应该转化为 `tests/` 中的正式测试：

```python
# tempTests/2026-03-21_test_feature.py（临时脚本）
from core.adapter import JsonAdapter

adapter = JsonAdapter("./configs")
result = adapter.read_config("test.json")
print(result)

# 转化为 tests/test_adapter.py（正式测试）
import pytest
from core.adapter import JsonAdapter

class TestJsonAdapter:
    @pytest.fixture
    def adapter(self):
        return JsonAdapter("./test_configs")
    
    def test_read_config_returns_valid_result(self, adapter):
        result = adapter.read_config("test.json")
        assert result.data is not None
        assert result.meta.version_hash is not None
```

---

**记住**: 本目录是"草稿纸"，`tests/` 才是"正式文档"！
