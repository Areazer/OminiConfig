"""
tests/test_gui.py

GUI 相关功能测试

测试内容：
1. 静态文件服务
2. 根路径返回 GUI 页面
3. GUI 使用的 API 集成
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestStaticFiles:
    """测试静态文件服务"""

    def test_root_path_returns_gui_page(self, client):
        """测试：根路径返回 GUI 页面"""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "OminiConfig" in response.text
        assert "Vue 3" in response.text or "vue" in response.text.lower()

    def test_static_index_html_accessible(self, client):
        """测试：static/index.html 可访问"""
        response = client.get("/static/index.html")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE html>" in response.text

    def test_gui_contains_essential_elements(self, client):
        """测试：GUI 页面包含必要元素"""
        response = client.get("/")
        content = response.text

        # 检查关键元素
        assert "Vue 3" in content or "vue@3" in content, "应加载 Vue 3"
        assert "tailwindcss" in content.lower(), "应加载 Tailwind CSS"
        assert "SchemaForm" in content, "应包含 SchemaForm 组件"
        assert "EventSource" in content, "应使用 SSE"
        assert "versionHash" in content, "应处理 versionHash"


class TestGUIApiIntegration:
    """测试 GUI 使用的 API 端点"""

    def test_api_config_for_gui(self, client):
        """测试：GUI 可以正常读取配置"""
        # 先创建一个测试配置
        client.post(
            "/api/config/gui/test.json",
            json={
                "data": {"name": "test", "value": 123},
                "oldVersionHash": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        )

        # 读取配置
        response = client.get("/api/config/gui/test.json")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert "versionHash" in data["meta"]

    def test_api_schema_for_gui(self, client):
        """测试：GUI 可以正常获取 Schema"""
        # 创建测试配置
        client.post(
            "/api/config/gui/schema_test.json",
            json={
                "data": {"app_name": "Test", "port": 8080},
                "oldVersionHash": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        )

        # 获取 Schema
        response = client.get("/api/schema/gui/schema_test.json")

        assert response.status_code == 200
        data = response.json()
        assert "schema" in data
        schema = data["schema"]
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_gui_save_with_version_hash(self, client):
        """测试：GUI 保存时携带 versionHash"""
        # 创建初始配置
        response = client.get("/api/config/gui/save_test.json")
        initial_hash = response.json()["meta"]["versionHash"]

        # 使用正确的 versionHash 保存
        save_response = client.post(
            "/api/config/gui/save_test.json",
            json={"data": {"updated": True}, "oldVersionHash": initial_hash},
        )

        assert save_response.status_code == 200
        result = save_response.json()
        assert result["success"] is True
        assert result["meta"]["versionHash"] != initial_hash

    def test_gui_conflict_detection(self, client):
        """测试：GUI 能检测到并发冲突"""
        # 创建初始配置
        response = client.get("/api/config/gui/conflict_test.json")
        initial_hash = response.json()["meta"]["versionHash"]

        # 第一次保存（成功）
        client.post(
            "/api/config/gui/conflict_test.json",
            json={"data": {"version": 1}, "oldVersionHash": initial_hash},
        )

        # 使用旧的 versionHash 再次保存（应该失败）
        conflict_response = client.post(
            "/api/config/gui/conflict_test.json",
            json={
                "data": {"version": 2},
                "oldVersionHash": initial_hash,  # 已过期的 hash
            },
        )

        assert conflict_response.status_code == 409
        assert "ConcurrencyConflictException" in conflict_response.text


class TestGUISchemaRendering:
    """测试 GUI Schema 渲染支持的数据类型"""

    @pytest.mark.parametrize(
        "config_data,expected_types",
        [
            (
                {"name": "test", "count": 42, "enabled": True},
                ["string", "number", "boolean"],
            ),
            ({"nested": {"value": 123}}, ["object", "number"]),
            ({"items": ["a", "b", "c"]}, ["object", "array", "string"]),
        ],
    )
    def test_schema_type_detection(self, client, config_data, expected_types):
        """测试：Schema 正确推导各种数据类型"""
        # 创建配置
        client.post(
            "/api/config/gui/type_test.json",
            json={
                "data": config_data,
                "oldVersionHash": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        )

        # 获取 Schema
        response = client.get("/api/schema/gui/type_test.json")
        schema = response.json()["schema"]

        # 验证 Schema 包含预期的类型
        def extract_types(obj):
            types = [obj.get("type")]
            if obj.get("properties"):
                for prop in obj["properties"].values():
                    types.extend(extract_types(prop))
            if obj.get("items"):
                types.extend(extract_types(obj["items"]))
            return [t for t in types if t]

        schema_types = extract_types(schema)

        for expected_type in expected_types:
            assert expected_type in schema_types, f"Schema 应包含类型: {expected_type}"


class TestGUISSESupport:
    """测试 GUI SSE 实时推送功能"""

    def test_sse_endpoint_exists(self, client):
        """测试：SSE 端点存在且返回事件流"""
        response = client.get("/api/watch/gui/sse_test.json")

        # 注意：SSE 连接会保持打开状态，这里我们只检查端点是否可访问
        # 实际 SSE 测试需要异步客户端
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_sse_accepts_any_path(self, client):
        """测试：SSE 端点接受任意配置路径"""
        test_paths = [
            "app/config.json",
            "deep/nested/path/settings.json",
            "simple.json",
        ]

        for path in test_paths:
            response = client.get(f"/api/watch/{path}")
            # 应该返回 200（事件流）或 403（路径安全拦截）
            assert response.status_code in [200, 403], (
                f"路径 {path} 应该可访问或被安全拦截"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
