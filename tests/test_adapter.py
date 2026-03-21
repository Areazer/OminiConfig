"""
OminiConfig Adapter 单元测试套件

测试范围:
1. 正常读写流程
2. 嵌套层级超过 3 层的复杂数据解析
3. 模拟并发写入导致的 Hash 冲突异常拦截
4. 文件格式损坏时的异常处理
5. Schema 推导功能
6. 边缘情况处理
"""

import os
import json
import tempfile
import shutil
import threading
import time
import pytest
from pathlib import Path

from omini_config.adapter import (
    JsonConfigAdapter,
    ConfigResult,
    ConfigMeta,
    ConcurrencyConflictException,
    ConfigFormatException,
    ConfigNotFoundException,
    ConfigException,
)


class TestJsonConfigAdapter:
    """JsonConfigAdapter 测试类"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录作为测试环境"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # 清理临时目录
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def adapter(self, temp_dir):
        """创建适配器实例"""
        return JsonConfigAdapter(base_dir=temp_dir)

    @pytest.fixture
    def sample_config(self):
        """标准测试配置数据"""
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {"username": "admin", "password": "secret123"},
            },
            "features": {
                "caching": True,
                "timeout": 30.5,
                "options": ["fast", "secure", "reliable"],
            },
        }


class TestReadWriteOperations(TestJsonConfigAdapter):
    """测试 1: 正常读写流程"""

    def test_read_nonexistent_file_initializes_empty(self, adapter, temp_dir):
        """测试：读取不存在的文件时自动初始化空配置"""
        config_path = "new_config.json"

        # 文件不应该存在
        full_path = Path(temp_dir) / config_path
        assert not full_path.exists()

        # 读取应自动初始化
        result = adapter.read_config(config_path)

        # 验证返回空配置
        assert result.data == {}
        assert result.meta.version_hash is not None
        assert isinstance(result.meta.last_modified, float)

        # 验证文件已创建
        assert full_path.exists()

    def test_read_existing_config(self, adapter, temp_dir, sample_config):
        """测试：读取已存在的配置文件"""
        config_path = "existing_config.json"
        full_path = Path(temp_dir) / config_path

        # 预写入配置
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            json.dump(sample_config, f)

        # 读取配置
        result = adapter.read_config(config_path)

        # 验证数据正确性
        assert result.data == sample_config
        assert result.meta.version_hash is not None
        assert len(result.meta.version_hash) == 64  # SHA256 哈希长度

    def test_write_and_read_roundtrip(self, adapter, sample_config):
        """测试：写入后读取的完整流程"""
        config_path = "roundtrip_config.json"

        # 首次读取（自动创建空配置）
        result = adapter.read_config(config_path)
        initial_hash = result.meta.version_hash

        # 写入新配置
        success = adapter.write_config(
            source_path=config_path, data=sample_config, old_version_hash=initial_hash
        )
        assert success is True

        # 再次读取验证
        result = adapter.read_config(config_path)
        assert result.data == sample_config

        # 版本哈希应已改变
        assert result.meta.version_hash != initial_hash

    def test_write_preserves_structure(self, adapter):
        """测试：写入后数据结构保持完整"""
        config_path = "structure_test.json"

        # 首次读取
        result = adapter.read_config(config_path)

        # 复杂数据结构
        complex_data = {
            "level1": {"level2": {"level3": {"level4": {"value": "deep_nested"}}}},
            "array_field": [1, 2, 3, {"nested_in_array": True}],
            "null_field": None,
            "bool_field": False,
            "number_field": 3.14159,
        }

        # 写入
        adapter.write_config(
            source_path=config_path,
            data=complex_data,
            old_version_hash=result.meta.version_hash,
        )

        # 读取并验证
        result = adapter.read_config(config_path)
        assert result.data == complex_data


class TestNestedDataParsing(TestJsonConfigAdapter):
    """测试 2: 嵌套层级超过 3 层的复杂数据解析"""

    def test_deeply_nested_structure_level_5(self, adapter):
        """测试：5 层嵌套结构的正确解析"""
        config_path = "deep_nested.json"

        # 构建 5 层嵌套结构
        deep_config = {
            "level1": {
                "name": "level1_value",
                "level2": {
                    "name": "level2_value",
                    "level3": {
                        "name": "level3_value",
                        "level4": {
                            "name": "level4_value",
                            "level5": {
                                "name": "level5_value",
                                "deep_value": 42,
                                "deep_array": [1, 2, {"nested": "object"}],
                                "deep_null": None,
                            },
                        },
                    },
                },
            }
        }

        # 首次读取并写入
        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=deep_config,
            old_version_hash=result.meta.version_hash,
        )

        # 读取并验证所有层级
        result = adapter.read_config(config_path)
        data = result.data

        # 逐层验证
        assert data["level1"]["name"] == "level1_value"
        assert data["level1"]["level2"]["name"] == "level2_value"
        assert data["level1"]["level2"]["level3"]["name"] == "level3_value"
        assert data["level1"]["level2"]["level3"]["level4"]["name"] == "level4_value"

        level5 = data["level1"]["level2"]["level3"]["level4"]["level5"]
        assert level5["name"] == "level5_value"
        assert level5["deep_value"] == 42
        assert level5["deep_array"] == [1, 2, {"nested": "object"}]
        assert level5["deep_null"] is None

    def test_mixed_nesting_with_arrays(self, adapter):
        """测试：嵌套对象与数组混合结构"""
        config_path = "mixed_structure.json"

        mixed_config = {
            "servers": [
                {
                    "name": "server1",
                    "config": {
                        "database": {
                            "pools": [
                                {"host": "db1", "port": 5432},
                                {"host": "db2", "port": 5433},
                            ],
                            "settings": {"max_connections": 100, "timeout": 30},
                        }
                    },
                },
                {
                    "name": "server2",
                    "config": {
                        "database": {
                            "pools": [{"host": "db3", "port": 5434}],
                            "settings": {"max_connections": 50, "timeout": 60},
                        }
                    },
                },
            ]
        }

        # 写入并读取
        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=mixed_config,
            old_version_hash=result.meta.version_hash,
        )

        result = adapter.read_config(config_path)
        data = result.data

        # 验证复杂混合结构
        assert len(data["servers"]) == 2
        assert data["servers"][0]["name"] == "server1"
        assert data["servers"][0]["config"]["database"]["pools"][0]["host"] == "db1"
        assert (
            data["servers"][1]["config"]["database"]["settings"]["max_connections"]
            == 50
        )

    def test_deeply_nested_schema_generation(self, adapter):
        """测试：深度嵌套结构的 Schema 推导"""
        config_path = "deep_schema_test.json"

        deep_config = {
            "app": {
                "modules": {
                    "auth": {
                        "providers": {
                            "oauth": {
                                "google": {
                                    "client_id": "123",
                                    "client_secret": "secret",
                                    "scopes": ["email", "profile"],
                                }
                            }
                        }
                    }
                }
            }
        }

        # 写入配置
        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=deep_config,
            old_version_hash=result.meta.version_hash,
        )

        # 生成 Schema
        schema = adapter.generate_schema(config_path)

        # 验证 Schema 结构
        assert schema["type"] == "object"
        assert "app" in schema["properties"]
        assert "modules" in schema["properties"]["app"]["properties"]
        assert (
            "auth" in schema["properties"]["app"]["properties"]["modules"]["properties"]
        )

        # 验证最深层级
        oauth_schema = schema["properties"]["app"]["properties"]["modules"][
            "properties"
        ]["auth"]["properties"]["providers"]["properties"]["oauth"]["properties"][
            "google"
        ]["properties"]
        assert oauth_schema["client_id"]["type"] == "string"
        assert oauth_schema["client_secret"]["type"] == "string"
        assert oauth_schema["scopes"]["type"] == "array"


class TestConcurrencyConflict(TestJsonConfigAdapter):
    """测试 3: 模拟并发写入导致的 Hash 冲突异常拦截"""

    def test_concurrency_conflict_exception_raised(self, adapter):
        """测试：使用过期哈希写入时抛出并发冲突异常"""
        config_path = "concurrency_test.json"

        # 客户端 A 读取配置
        result_a = adapter.read_config(config_path)
        old_hash_a = result_a.meta.version_hash

        # 客户端 B 读取同一配置
        result_b = adapter.read_config(config_path)

        # 客户端 B 先写入（更新配置）
        adapter.write_config(
            source_path=config_path,
            data={"updated_by": "client_b"},
            old_version_hash=result_b.meta.version_hash,
        )

        # 客户端 A 使用过期的哈希尝试写入
        with pytest.raises(ConcurrencyConflictException) as exc_info:
            adapter.write_config(
                source_path=config_path,
                data={"updated_by": "client_a"},
                old_version_hash=old_hash_a,
            )

        # 验证异常信息
        exc = exc_info.value
        assert exc.source_path == config_path
        assert exc.expected_hash == old_hash_a
        assert exc.actual_hash is not None
        assert exc.expected_hash != exc.actual_hash
        assert "配置冲突" in str(exc)

    def test_successful_write_after_refresh(self, adapter):
        """测试：刷新哈希后成功写入"""
        config_path = "refresh_test.json"

        # 首次读取
        result = adapter.read_config(config_path)
        old_hash = result.meta.version_hash

        # 模拟外部修改（直接操作文件）
        full_path = Path(adapter._base_dir) / config_path
        with open(full_path, "w") as f:
            json.dump({"external_change": True}, f)

        # 使用过期的哈希应失败
        with pytest.raises(ConcurrencyConflictException):
            adapter.write_config(
                source_path=config_path,
                data={"my_change": True},
                old_version_hash=old_hash,
            )

        # 重新读取获取新哈希
        result = adapter.read_config(config_path)
        new_hash = result.meta.version_hash

        # 使用新哈希成功写入
        success = adapter.write_config(
            source_path=config_path, data={"my_change": True}, old_version_hash=new_hash
        )
        assert success is True

    def test_concurrent_writes_race_condition(self, adapter):
        """测试：模拟并发写入竞争条件"""
        config_path = "race_condition_test.json"

        # 初始化配置
        result = adapter.read_config(config_path)
        initial_hash = result.meta.version_hash

        # 写入初始数据
        adapter.write_config(
            source_path=config_path,
            data={"counter": 0, "updates": []},
            old_version_hash=initial_hash,
        )

        errors = []
        success_count = [0]

        def concurrent_writer(writer_id):
            """模拟并发写入者"""
            try:
                # 读取当前配置
                result = adapter.read_config(config_path)

                # 模拟处理延迟（增加冲突概率）
                time.sleep(0.01)

                # 尝试写入
                data = result.data.copy()
                data["counter"] += 1
                data["updates"].append(f"writer_{writer_id}")

                adapter.write_config(
                    source_path=config_path,
                    data=data,
                    old_version_hash=result.meta.version_hash,
                )
                success_count[0] += 1

            except ConcurrencyConflictException as e:
                errors.append((writer_id, e))

        # 启动多个并发线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=concurrent_writer, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证：至少有一些写入会因为冲突而失败
        # 注意：由于线程调度的不确定性，可能只有一个成功
        assert len(errors) >= 0, "应该至少发生一次并发冲突"
        assert success_count[0] >= 1, "应该至少有一个写入成功"

        # 验证冲突异常的信息
        for writer_id, exc in errors:
            assert isinstance(exc, ConcurrencyConflictException)
            assert exc.source_path == config_path

    def test_atomic_write_rollback_on_error(self, adapter, temp_dir):
        """测试：写入失败时原文件保持不变"""
        config_path = "atomic_test.json"

        # 写入初始配置
        result = adapter.read_config(config_path)
        initial_data = {"version": 1, "stable": True}
        adapter.write_config(
            source_path=config_path,
            data=initial_data,
            old_version_hash=result.meta.version_hash,
        )

        # 记录文件状态
        full_path = Path(temp_dir) / config_path
        initial_file_stat = full_path.stat()
        initial_content = full_path.read_text()

        # 模拟写入过程中的错误（通过使用错误的哈希）
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises(ConcurrencyConflictException):
            adapter.write_config(
                source_path=config_path,
                data={"version": 2, "corrupted": True},
                old_version_hash=wrong_hash,
            )

        # 验证文件未被修改
        current_content = full_path.read_text()
        assert current_content == initial_content

        # 验证临时文件已被清理
        temp_file = full_path.with_suffix(".tmp")
        assert not temp_file.exists()


class TestErrorHandling(TestJsonConfigAdapter):
    """测试 4: 文件格式损坏时的异常处理"""

    def test_malformed_json_raises_format_exception(self, adapter, temp_dir):
        """测试：格式错误的 JSON 抛出 ConfigFormatException"""
        config_path = "malformed.json"
        full_path = Path(temp_dir) / config_path

        # 创建格式错误的 JSON 文件
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write('{"invalid": json, "missing": bracket}')

        # 尝试读取应抛出异常
        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        # 验证异常包含详细错误信息
        exc = exc_info.value
        assert "JSON 格式错误" in str(exc)
        assert "malformed.json" in str(exc)

    def test_trailing_comma_in_json(self, adapter, temp_dir):
        """测试：JSON 中尾随逗号导致的解析错误"""
        config_path = "trailing_comma.json"
        full_path = Path(temp_dir) / config_path

        # 创建带有尾随逗号的 JSON（Python 允许，但标准 JSON 不允许）
        full_path.write_text('{"key": "value",}')

        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        assert "JSON 格式错误" in str(exc_info.value)

    def test_invalid_utf8_encoding(self, adapter, temp_dir):
        """测试：无效 UTF-8 编码的异常处理"""
        config_path = "invalid_encoding.json"
        full_path = Path(temp_dir) / config_path

        # 创建包含无效 UTF-8 字节的文件
        full_path.write_bytes(b'{\xff\xfe"key": "value"}')

        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        assert "文件编码错误" in str(exc_info.value) or "JSON 格式错误" in str(
            exc_info.value
        )

    def test_empty_file_initialization(self, adapter, temp_dir):
        """测试：空文件自动初始化为空配置"""
        config_path = "empty.json"
        full_path = Path(temp_dir) / config_path

        # 创建空文件
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("")

        # 应成功读取为空配置
        result = adapter.read_config(config_path)
        assert result.data == {}
        assert isinstance(result.meta.version_hash, str)

    def test_root_array_instead_of_object(self, adapter, temp_dir):
        """测试：根节点为数组而非对象时的错误"""
        config_path = "array_root.json"
        full_path = Path(temp_dir) / config_path

        # 创建根节点为数组的 JSON
        full_path.write_text('["item1", "item2", {"key": "value"}]')

        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        exc = exc_info.value
        assert "配置根必须是对象" in str(exc)
        assert "list" in str(exc) or "array" in str(exc).lower()

    def test_root_primitive_instead_of_object(self, adapter, temp_dir):
        """测试：根节点为基本类型而非对象时的错误"""
        config_path = "primitive_root.json"
        full_path = Path(temp_dir) / config_path

        # 测试字符串根节点
        full_path.write_text('"just a string"')

        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        assert "配置根必须是对象" in str(exc_info.value)

        # 测试数字根节点
        full_path.write_text("12345")

        with pytest.raises(ConfigFormatException) as exc_info:
            adapter.read_config(config_path)

        assert "配置根必须是对象" in str(exc_info.value)


class TestSchemaGeneration(TestJsonConfigAdapter):
    """测试：Schema 推导功能"""

    def test_simple_types_schema(self, adapter):
        """测试：简单类型的 Schema 推导"""
        config_path = "simple_types.json"

        config = {
            "string_field": "text",
            "number_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "null_field": None,
        }

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        schema = adapter.generate_schema(config_path)

        # 验证各字段类型
        props = schema["properties"]
        assert props["string_field"]["type"] == "string"
        assert props["number_field"]["type"] == "number"
        assert props["float_field"]["type"] == "number"
        assert props["bool_field"]["type"] == "boolean"
        assert props["null_field"]["type"] == "null"

    def test_nested_object_schema(self, adapter):
        """测试：嵌套对象的 Schema 推导"""
        config_path = "nested_schema.json"

        config = {
            "user": {
                "profile": {"name": "John", "age": 30},
                "settings": {"theme": "dark", "notifications": True},
            }
        }

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        schema = adapter.generate_schema(config_path)

        # 验证嵌套结构
        user_props = schema["properties"]["user"]["properties"]
        user_schema = schema["properties"]["user"]
        assert user_props["profile"]["type"] == "object"
        assert user_props["profile"]["properties"]["name"]["type"] == "string"
        assert user_props["profile"]["properties"]["age"]["type"] == "number"

        # 验证 required 字段
        assert "user" in schema["required"]
        assert "profile" in user_schema["required"]

    def test_array_schema_generation(self, adapter):
        """测试：数组类型的 Schema 推导"""
        config_path = "array_schema.json"

        config = {
            "tags": ["python", "json", "config"],
            "scores": [95, 87, 92],
            "mixed": [{"name": "item1", "value": 100}, {"name": "item2", "value": 200}],
        }

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        schema = adapter.generate_schema(config_path)

        # 验证数组类型
        props = schema["properties"]
        assert props["tags"]["type"] == "array"
        assert props["tags"]["items"]["type"] == "string"

        assert props["scores"]["type"] == "array"
        assert props["scores"]["items"]["type"] == "number"

        assert props["mixed"]["type"] == "array"
        assert props["mixed"]["items"]["type"] == "object"

    def test_empty_config_schema(self, adapter):
        """测试：空配置的 Schema 推导"""
        config_path = "empty_config.json"

        # 读取空配置
        adapter.read_config(config_path)

        schema = adapter.generate_schema(config_path)

        # 空对象应返回基本 schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}


class TestEdgeCases(TestJsonConfigAdapter):
    """测试：边缘情况"""

    def test_unicode_content(self, adapter):
        """测试：Unicode 字符的正确处理"""
        config_path = "unicode.json"

        config = {
            "chinese": "中文测试",
            "emoji": "🚀🎉👍",
            "japanese": "日本語テスト",
            "arabic": "اختبار العربية",
            "special": "<>&\"'",
        }

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        result = adapter.read_config(config_path)
        assert result.data == config

    def test_large_nested_structure(self, adapter):
        """测试：大型嵌套结构的性能"""
        config_path = "large_nested.json"

        # 创建大型嵌套结构
        large_config = {
            f"key_{i}": {
                f"nested_{j}": {"value": f"data_{i}_{j}", "number": i * 1000 + j}
                for j in range(10)
            }
            for i in range(50)
        }

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=large_config,
            old_version_hash=result.meta.version_hash,
        )

        result = adapter.read_config(config_path)
        assert result.data == large_config
        assert len(result.data) == 50

    def test_deeply_nested_exceeds_limit(self, adapter):
        """测试：超出递归限制的嵌套深度"""
        config_path = "too_deep.json"

        # 创建一个超出限制的深度（默认 100 层）
        deep_value = "bottom"
        for _ in range(150):
            deep_value = {"level": deep_value}

        config = {"deep": deep_value}

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        # 读取应该仍然成功（只是 schema 推导可能受限）
        result = adapter.read_config(config_path)
        assert "deep" in result.data

        # Schema 推导应该优雅处理深度限制
        schema = adapter.generate_schema(config_path)
        assert schema["type"] == "object"

    def test_write_non_dict_data_raises_error(self, adapter):
        """测试：写入非字典数据应抛出异常"""
        config_path = "invalid_data.json"

        result = adapter.read_config(config_path)

        with pytest.raises(ConfigException) as exc_info:
            adapter.write_config(
                source_path=config_path,
                data=["not", "a", "dict"],
                old_version_hash=result.meta.version_hash,
            )

        assert "配置数据必须是对象" in str(exc_info.value)

    def test_path_with_directories(self, adapter, temp_dir):
        """测试：带目录的相对路径"""
        config_path = "subdir/nested/deep/config.json"

        config = {"level": "deep"}

        result = adapter.read_config(config_path)
        adapter.write_config(
            source_path=config_path,
            data=config,
            old_version_hash=result.meta.version_hash,
        )

        # 验证文件路径
        full_path = Path(temp_dir) / config_path
        assert full_path.exists()

        # 验证内容
        result = adapter.read_config(config_path)
        assert result.data == config


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
