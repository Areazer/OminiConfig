#!/usr/bin/env python3
"""
OminiConfig 演示脚本

展示如何使用 JsonConfigAdapter 进行配置的读写操作
"""

import sys
import json

sys.path.insert(0, "omini_config")

from omini_config.adapter import JsonConfigAdapter, ConcurrencyConflictException


def demo_read_write():
    """演示基本的读写操作"""
    print("=" * 60)
    print("演示 1: 基本读写操作")
    print("=" * 60)

    # 创建适配器
    adapter = JsonConfigAdapter(base_dir="./demo_configs")

    # 1. 读取配置（如果不存在会自动创建空配置）
    print("\n1. 读取配置...")
    result = adapter.read_config("app.json")
    print(f"   配置数据: {result.data}")
    print(f"   版本哈希: {result.meta.version_hash[:16]}...")
    print(f"   最后修改: {result.meta.last_modified}")

    # 2. 保存新配置
    print("\n2. 保存新配置...")
    new_config = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {"username": "admin", "password": "secret"},
        },
        "features": {"caching": True, "timeout": 30},
    }

    adapter.write_config(
        source_path="app.json",
        data=new_config,
        old_version_hash=result.meta.version_hash,
    )
    print("   配置保存成功！")

    # 3. 重新读取验证
    print("\n3. 重新读取配置...")
    result = adapter.read_config("app.json")
    print(f"   配置数据:\n{json.dumps(result.data, indent=4, ensure_ascii=False)}")
    print(f"   新版本哈希: {result.meta.version_hash[:16]}...")


def demo_concurrency():
    """演示并发冲突检测"""
    print("\n" + "=" * 60)
    print("演示 2: 并发冲突检测")
    print("=" * 60)

    adapter = JsonConfigAdapter(base_dir="./demo_configs")

    # 1. 模拟客户端 A 读取配置
    print("\n1. 客户端 A 读取配置...")
    result_a = adapter.read_config("shared.json")
    print(f"   获取版本哈希: {result_a.meta.version_hash[:16]}...")

    # 2. 模拟客户端 B 读取相同配置
    print("\n2. 客户端 B 读取相同配置...")
    result_b = adapter.read_config("shared.json")
    print(f"   获取版本哈希: {result_b.meta.version_hash[:16]}...")

    # 3. 客户端 B 先保存配置
    print("\n3. 客户端 B 保存配置...")
    config_b = {"updated_by": "client_b", "timestamp": 123456}
    adapter.write_config(
        source_path="shared.json",
        data=config_b,
        old_version_hash=result_b.meta.version_hash,
    )
    print("   客户端 B 保存成功！")

    # 4. 客户端 A 使用过期的哈希尝试保存
    print("\n4. 客户端 A 使用过期的哈希尝试保存...")
    config_a = {"updated_by": "client_a", "timestamp": 789012}
    try:
        adapter.write_config(
            source_path="shared.json",
            data=config_a,
            old_version_hash=result_a.meta.version_hash,  # 已过期的哈希
        )
        print("   错误：应该抛出并发冲突异常！")
    except ConcurrencyConflictException as e:
        print(f"   ✓ 正确捕获并发冲突异常！")
        print(f"   期望哈希: {e.expected_hash[:16]}...")
        print(f"   实际哈希: {e.actual_hash[:16]}...")
        print(f"   错误信息: {e}")

    # 5. 客户端 A 重新读取并保存
    print("\n5. 客户端 A 重新读取并保存...")
    result_a_new = adapter.read_config("shared.json")
    adapter.write_config(
        source_path="shared.json",
        data=config_a,
        old_version_hash=result_a_new.meta.version_hash,
    )
    print("   客户端 A 保存成功！")


def demo_schema_generation():
    """演示 Schema 推导"""
    print("\n" + "=" * 60)
    print("演示 3: JSON Schema 推导")
    print("=" * 60)

    adapter = JsonConfigAdapter(base_dir="./demo_configs")

    # 创建一个复杂配置
    print("\n1. 创建复杂配置...")
    complex_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "ssl": {
                "enabled": True,
                "cert": "/path/to/cert.pem",
                "key": "/path/to/key.pem",
            },
        },
        "database": {
            "connections": [
                {"name": "primary", "url": "postgres://localhost/db1"},
                {"name": "replica", "url": "postgres://replica/db1"},
            ],
            "pool_size": 10,
        },
        "features": ["auth", "logging", "metrics"],
        "debug_mode": False,
    }

    result = adapter.read_config("complex.json")
    adapter.write_config(
        source_path="complex.json",
        data=complex_config,
        old_version_hash=result.meta.version_hash,
    )

    # 生成 Schema
    print("\n2. 生成 JSON Schema...")
    schema = adapter.generate_schema("complex.json")
    print(json.dumps(schema, indent=2, ensure_ascii=False))


def demo_error_handling():
    """演示错误处理"""
    print("\n" + "=" * 60)
    print("演示 4: 错误处理")
    print("=" * 60)

    import tempfile
    import os

    adapter = JsonConfigAdapter(base_dir="./demo_configs")

    # 1. 处理损坏的 JSON
    print("\n1. 处理损坏的 JSON 文件...")
    os.makedirs("./demo_configs", exist_ok=True)
    with open("./demo_configs/corrupted.json", "w") as f:
        f.write('{"invalid": json, "missing": bracket}')

    try:
        adapter.read_config("corrupted.json")
    except Exception as e:
        print(f"   ✓ 正确捕获格式错误: {e}")

    # 2. 处理空文件
    print("\n2. 处理空文件...")
    with open("./demo_configs/empty.json", "w") as f:
        f.write("")

    result = adapter.read_config("empty.json")
    print(f"   ✓ 空文件自动初始化为: {result.data}")


if __name__ == "__main__":
    import os
    import shutil

    # 清理之前的演示数据
    if os.path.exists("./demo_configs"):
        shutil.rmtree("./demo_configs")

    try:
        demo_read_write()
        demo_concurrency()
        demo_schema_generation()
        demo_error_handling()

        print("\n" + "=" * 60)
        print("所有演示完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理演示数据
        if os.path.exists("./demo_configs"):
            shutil.rmtree("./demo_configs")
            print("\n已清理演示数据")
