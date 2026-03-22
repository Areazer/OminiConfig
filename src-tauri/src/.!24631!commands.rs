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
