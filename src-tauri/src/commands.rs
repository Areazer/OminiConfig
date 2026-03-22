use crate::utils::{self, ConfigError, FileMeta};
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
pub async fn read_config(path: String) -> Result<ConfigData, String> {
    let full_path = utils::validate_path(&path)
        .map_err(|e| e.to_string())?;
    
    // 如果文件不存在，初始化空配置
    if !full_path.exists() {
        let empty_config = serde_json::json!({});
        let content = serde_json::to_string_pretty(&empty_config)
            .map_err(|e| e.to_string())?;
        
        utils::atomic_write(&full_path, &content)
            .map_err(|e| e.to_string())?;
    }
    
    // 读取文件内容
    let content = utils::read_file_content(&full_path)
        .map_err(|e| e.to_string())?;
    
    // 解析 JSON
    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| {
            ConfigError::InvalidConfigFormat(
                format!("JSON 解析错误: {}", e)
            ).to_string()
        })?;
    
    // 获取元信息
    let meta = utils::get_file_meta(&full_path)
        .map_err(|e| e.to_string())?;
    
    Ok(ConfigData { data, meta })
}

#[tauri::command]
pub async fn write_config(
    path: String,
    data: serde_json::Value,
    old_hash: String
) -> Result<ConfigData, String> {
    let full_path = utils::validate_path(&path)
        .map_err(|e| e.to_string())?;
    
    // 读取当前文件哈希进行乐观锁检查
    let current_hash = utils::compute_file_hash(&full_path)
        .map_err(|e| e.to_string())?;
    
    // 检查乐观锁
    if current_hash != old_hash {
        return Err(
            ConfigError::ConcurrencyConflict(
                old_hash,
                current_hash
            ).to_string()
        );
    }
    
    // 序列化数据
    let content = serde_json::to_string_pretty(&data)
        .map_err(|e| e.to_string())?;
    
    // 原子写入
    utils::atomic_write(&full_path, &content)
        .map_err(|e| e.to_string())?;
    
    // 获取新的元信息
    let meta = utils::get_file_meta(&full_path)
        .map_err(|e| e.to_string())?;
    
    Ok(ConfigData { data, meta })
}

#[tauri::command]
pub async fn get_schema(path: String) -> Result<serde_json::Value, String> {
    let full_path = utils::validate_path(&path)
        .map_err(|e| e.to_string())?;
    
    // 如果文件不存在，先初始化
    if !full_path.exists() {
        let _ = read_config(path.clone()).await?;
    }
    
    // 读取配置数据
    let content = utils::read_file_content(&full_path)
        .map_err(|e| e.to_string())?;
    
    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| e.to_string())?;
    
    // 推导 Schema
    let schema = derive_schema(&data,&full_path.display().to_string()
    );
    
    Ok(schema)
}

/// 递归推导 JSON Schema
fn derive_schema(value: &serde_json::Value, id: &str) -> serde_json::Value {
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
            if n.is_i64() || n.is_u64() || n.is_f64() {
                serde_json::json!({
                    "type": "number"
                })
            } else {
                serde_json::json!({
                    "type": "number"
                })
            }
        }
        serde_json::Value::String(_) => {
            serde_json::json!({
                "type": "string"
            })
        }
        serde_json::Value::Array(arr) => {
            let items_schema = if arr.is_empty() {
                serde_json::json!({})
            } else {
                derive_schema(&arr[0], &format!("{}/items", id))
            };
            
            serde_json::json!({
                "type": "array",
                "items": items_schema
            })
        }
        serde_json::Value::Object(obj) => {
            let mut properties = HashMap::new();
            let mut required = Vec::new();
            
            for (key, val) in obj {
                let prop_schema = derive_schema(
                    val,
                    &format!("{}/properties/{}", id, key)
                );
                properties.insert(key.clone(), prop_schema);
                
                // 非 null 值视为 required
                if !val.is_null() {
                    required.push(key.clone());
                }
            }
            
            serde_json::json!({
                "type": "object",
                "properties": properties,
                "required": required
            })
        }
    }
}