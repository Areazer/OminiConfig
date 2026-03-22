use crate::utils::{self, CommandError, FileMeta};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigData {
    pub data: serde_json::Value,
    pub meta: FileMeta,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WriteRequest {
    pub data: serde_json::Value,
    pub old_hash: String,
}

#[tauri::command]
pub async fn read_config(path: String) -> Result<ConfigData, CommandError> {
    let full_path = utils::validate_path(&path)
        .map_err(CommandError::from)?;

    // 如果文件不存在，初始化空配置
    if !full_path.exists() {
        let empty_config = serde_json::json!({});
        let content = serde_json::to_string_pretty(&empty_config)
            .map_err(CommandError::serialization_error)?;

        utils::atomic_write(&full_path, &content)
            .map_err(CommandError::from)?;
    }

    // 读取文件内容
    let content = utils::read_file_content(&full_path)
        .map_err(CommandError::from)?;

    // 解析 JSON
    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(CommandError::serialization_error)?;

    // 获取元信息
    let meta = utils::get_file_meta(&full_path)
        .map_err(CommandError::from)?;

    Ok(ConfigData { data, meta })
}

#[tauri::command]
pub async fn write_config(
    path: String,
    data: serde_json::Value,
    old_hash: String
) -> Result<ConfigData, CommandError> {
    let full_path = utils::validate_path(&path)
        .map_err(CommandError::from)?;

    // 读取当前文件哈希进行乐观锁检查
    let current_hash = utils::compute_file_hash(&full_path)
        .map_err(CommandError::from)?;

    // 检查乐观锁
    if current_hash != old_hash {
        return Err(CommandError::concurrency_conflict(&old_hash, &current_hash));
    }

    // 序列化数据
    let content = serde_json::to_string_pretty(&data)
        .map_err(CommandError::serialization_error)?;

    // 原子写入
    utils::atomic_write(&full_path, &content)
        .map_err(CommandError::from)?;

    // 获取新的元信息
    let meta = utils::get_file_meta(&full_path)
        .map_err(CommandError::from)?;

    Ok(ConfigData { data, meta })
}

#[tauri::command]
pub async fn get_schema(path: String) -> Result<serde_json::Value, CommandError> {
    let full_path = utils::validate_path(&path)
        .map_err(CommandError::from)?;

    // 如果文件不存在，先初始化
    if !full_path.exists() {
        let _ = read_config(path.clone()).await?;
    }

    // 读取配置数据
    let content = utils::read_file_content(&full_path)
        .map_err(CommandError::from)?;

    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(CommandError::serialization_error)?;

    // 推导表单 Schema（不是完整 JSON Schema）
    let schema = derive_form_schema(&data, &full_path.display().to_string());

    Ok(schema)
}

/// 递归推导表单 Schema
/// 
/// 注意：这不是完整的 JSON Schema，而是用于表单渲染的简化结构。
/// 
/// 当前实现的特点：
/// 1. 数组类型只取第一个元素推导 items（简化策略）
/// 2. 不自动推导 required 字段（已移除"非 null 就 required"逻辑）
/// 3. 仅支持基本类型：null, boolean, number, string, array, object
/// 
/// 用于根据示例配置数据生成可编辑的表单界面。
fn derive_form_schema(value: &serde_json::Value, id: &str) -> serde_json::Value {
    match value {
        serde_json::Value::Null => {
            serde_json::json!({
                "type": "null"
            })
        }
        serde_json::Value::Bool(_) => {
            serde_json::json!({
                "type": "boolean"
            })
        }
        serde_json::Value::Number(n) => {
            // 区分整数和浮点数，为前端展示预留空间
            if n.is_i64() || n.is_u64() {
                serde_json::json!({
                    "type": "number",
                    "format": "integer"
                })
            } else {
                serde_json::json!({
                    "type": "number",
                    "format": "float"
                })
            }
        }
        serde_json::Value::String(_) => {
            serde_json::json!({
                "type": "string"
            })
        }
        serde_json::Value::Array(arr) => {
            // 简化策略：只取第一个元素推导 items 类型
            // 这是启发式行为，不是严谨的类型推导
            let items_schema = if arr.is_empty() {
                serde_json::json!({})
            } else {
                derive_form_schema(&arr[0], &format!("{}/items", id))
            };

            serde_json::json!({
                "type": "array",
                "items": items_schema
            })
        }
        serde_json::Value::Object(obj) => {
            let mut properties = HashMap::new();

            for (key, val) in obj {
                let prop_schema = derive_form_schema(
                    val,
                    &format!("{}/properties/{}", id, key)
                );
                properties.insert(key.clone(), prop_schema);
            }

            // 不推导 required 字段
            // 之前的"非 null 就 required"逻辑不合理，已移除
            serde_json::json!({
                "type": "object",
                "properties": properties
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use serial_test::serial;

    // 为测试设置临时工作目录
    fn setup_test_workspace() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        // 设置当前目录为临时目录
        std::env::set_current_dir(&temp_dir).unwrap();
        // 创建工作目录 configs（workspace_dir() 会返回 temp_dir/configs）
        let workspace = utils::workspace_dir();
        std::fs::create_dir_all(&workspace).unwrap();
        temp_dir
    }

    #[tokio::test]
    #[serial]
    #[serial]
    async fn test_read_config_creates_empty_if_not_exists() {
        let _temp = setup_test_workspace();

        // 读取不存在的配置
        let result = read_config("test/new_config.json".to_string()).await;

        assert!(result.is_ok());
        let config = result.unwrap();
        assert_eq!(config.data, serde_json::json!({}));
        assert!(!config.meta.version_hash.is_empty());

        // 验证文件被创建
        assert!(utils::workspace_dir().join("test/new_config.json").exists());
    }

    #[tokio::test]
    #[serial]
    #[serial]
    async fn test_read_config_returns_existing_data() {
        let _temp = setup_test_workspace();

        // 先写入一些数据
        let test_data = serde_json::json!({"name": "test", "value": 42});
        let _ = write_config(
            "existing.json".to_string(),
            test_data.clone(),
            utils::compute_hash("")  // 空文件的哈希
        ).await;

        // 读取配置
        let result = read_config("existing.json".to_string()).await;

        assert!(result.is_ok());
        let config = result.unwrap();
        assert_eq!(config.data["name"], "test");
        assert_eq!(config.data["value"], 42);
    }

    #[tokio::test]
    #[serial]
    #[serial]
    async fn test_write_config_success() {
        let _temp = setup_test_workspace();

        // 先创建空文件获取初始哈希
        let initial_result = read_config("write_test.json".to_string()).await.unwrap();
        let initial_hash = initial_result.meta.version_hash;

        // 写入新数据
        let new_data = serde_json::json!({"updated": true, "count": 100});
        let result = write_config(
            "write_test.json".to_string(),
            new_data.clone(),
            initial_hash.clone()
        ).await;

        assert!(result.is_ok());
        let config = result.unwrap();
        assert_eq!(config.data["updated"], true);
        assert_eq!(config.data["count"], 100);
        // 哈希应该改变
        assert_ne!(config.meta.version_hash, initial_hash);
    }

    #[tokio::test]
    #[serial]
    async fn test_write_config_concurrency_conflict() {
        let _temp = setup_test_workspace();

        // 先创建文件并获取初始哈希
        let initial_result = read_config("conflict_test.json".to_string()).await.unwrap();
        let initial_hash = initial_result.meta.version_hash;

        // 写入一些数据（更新哈希）
        let first_data = serde_json::json!({"version": 1});
        let first_write_result = write_config(
            "conflict_test.json".to_string(),
            first_data,
            initial_hash.clone()
        ).await;

        assert!(first_write_result.is_ok(), "第一次写入应该成功: {:?}", first_write_result);

        // 尝试使用旧的哈希写入（应该失败）
        let second_data = serde_json::json!({"version": 2});
        let result = write_config(
            "conflict_test.json".to_string(),
            second_data,
            initial_hash  // 使用第一次读取时的旧哈希
        ).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert_eq!(err.code, "CONCURRENCY_CONFLICT");
        // 验证 details 包含 expected_hash 和 actual_hash
        assert!(err.details.is_some());
        let details = err.details.unwrap();
        assert!(details.get("expected_hash").is_some());
        assert!(details.get("actual_hash").is_some());
    }

    #[tokio::test]
    #[serial]
    async fn test_write_config_invalid_path() {
        let _temp = setup_test_workspace();

        let result = write_config(
            "../etc/passwd".to_string(),
            serde_json::json!({"test": true}),
            "dummy_hash".to_string()
        ).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert_eq!(err.code, "PATH_SECURITY_VIOLATION");
    }

    #[tokio::test]
    #[serial]
    async fn test_get_schema_for_simple_types() {
        let _temp = setup_test_workspace();

        // 创建包含各种类型数据的配置
        let data = serde_json::json!({
            "name": "test",
            "count": 42,
            "enabled": true,
            "ratio": 3.14
        });

        let _ = write_config(
            "schema_test.json".to_string(),
            data,
            utils::compute_hash("")
        ).await;

        // 获取 schema
        let result = get_schema("schema_test.json".to_string()).await;

        assert!(result.is_ok());
        let schema = result.unwrap();

        // 验证 schema 结构
        assert_eq!(schema["type"], "object");
        assert!(schema["properties"]["name"]["type"].as_str().unwrap() == "string");
        assert!(schema["properties"]["count"]["type"].as_str().unwrap() == "number");
        assert!(schema["properties"]["enabled"]["type"].as_str().unwrap() == "boolean");
    }

    #[tokio::test]
    #[serial]
    async fn test_get_schema_for_nested_objects() {
        let _temp = setup_test_workspace();

        let data = serde_json::json!({
            "app": {
                "name": "MyApp",
                "settings": {
                    "port": 8080
                }
            }
        });

        let _ = write_config(
            "nested_schema.json".to_string(),
            data,
            utils::compute_hash("")
        ).await;

        let result = get_schema("nested_schema.json".to_string()).await;

        assert!(result.is_ok());
        let schema = result.unwrap();

        // 验证嵌套结构
        assert_eq!(schema["type"], "object");
        assert_eq!(schema["properties"]["app"]["type"], "object");
        assert_eq!(schema["properties"]["app"]["properties"]["name"]["type"], "string");
        assert_eq!(schema["properties"]["app"]["properties"]["settings"]["type"], "object");
    }

    #[tokio::test]
    #[serial]
    async fn test_get_schema_for_arrays() {
        let _temp = setup_test_workspace();

        let data = serde_json::json!({
            "items": ["a", "b", "c"],
            "numbers": [1, 2, 3]
        });

        let _ = write_config(
            "array_schema.json".to_string(),
            data,
            utils::compute_hash("")
        ).await;

        let result = get_schema("array_schema.json".to_string()).await;

        assert!(result.is_ok());
        let schema = result.unwrap();

        // 验证数组结构
        assert_eq!(schema["properties"]["items"]["type"], "array");
        assert_eq!(schema["properties"]["items"]["items"]["type"], "string");
        assert_eq!(schema["properties"]["numbers"]["type"], "array");
        assert_eq!(schema["properties"]["numbers"]["items"]["type"], "number");
    }

    #[test]
    fn test_derive_form_schema_null() {
        let value = serde_json::Value::Null;
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "null");
    }

    #[test]
    fn test_derive_form_schema_boolean() {
        let value = serde_json::json!(true);
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "boolean");
    }

    #[test]
    fn test_derive_form_schema_number() {
        let value = serde_json::json!(42);
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "number");
    }

    #[test]
    fn test_derive_form_schema_string() {
        let value = serde_json::json!("hello");
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "string");
    }

    #[test]
    fn test_derive_form_schema_empty_array() {
        let value = serde_json::json!([]);
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "array");
        assert!(schema["items"].as_object().unwrap().is_empty());
    }

    #[test]
    fn test_derive_form_schema_array_with_items() {
        let value = serde_json::json!([1, 2, 3]);
        let schema = derive_form_schema(&value, "test");
        assert_eq!(schema["type"], "array");
        assert_eq!(schema["items"]["type"], "number");
    }

    #[test]
    fn test_derive_form_schema_object_properties() {
        let value = serde_json::json!({
            "name": "test",
            "count": 5,
            "enabled": true
        });
        let schema = derive_form_schema(&value, "test");

        assert_eq!(schema["type"], "object");
        assert!(schema["properties"]["name"]["type"] == "string");
        assert!(schema["properties"]["count"]["type"] == "number");
        assert!(schema["properties"]["enabled"]["type"] == "boolean");

        // 不推导 required 字段，schema 中不应有 required 字段
        assert!(schema.get("required").is_none());
    }
}
