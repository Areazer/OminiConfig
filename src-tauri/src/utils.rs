use std::path::{Path, PathBuf};
use std::fs;
use sha2::{Sha256, Digest};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("路径安全违规: {0}")]
    PathSecurityViolation(String),
    
    #[error("配置文件不存在: {0}")]
    ConfigNotFound(String),
    
    #[error("并发冲突: 版本哈希不匹配 (期望: {0}, 实际: {1})")]
    ConcurrencyConflict(String, String),
    
    #[error("无效的配置格式: {0}")]
    InvalidConfigFormat(String),
    
    #[error("IO 错误: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("序列化错误: {0}")]
    SerializationError(#[from] serde_json::Error),
}

/// 工作目录 - 所有配置文件的根目录
pub fn workspace_dir() -> PathBuf {
    std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("configs")
}

/// 验证路径安全性
/// 禁止绝对路径和包含 .. 的路径穿越
pub fn validate_path(source_path: &str) -> Result<PathBuf, ConfigError> {
    // 检查空路径
    if source_path.is_empty() {
        return Err(ConfigError::PathSecurityViolation(
            "路径不能为空".to_string()
        ));
    }
    
    // 检查绝对路径
    if Path::new(source_path).is_absolute() {
        return Err(ConfigError::PathSecurityViolation(
            format!("禁止使用绝对路径: {}", source_path)
        ));
    }
    
    // 检查路径穿越 (../)
    if source_path.contains("..") {
        return Err(ConfigError::PathSecurityViolation(
            format!("检测到路径穿越: {}", source_path)
        ));
    }
    
    // 构建完整路径
    let full_path = workspace_dir().join(source_path);
    
    // 规范化路径并验证仍在工作目录内
    let canonical = full_path.canonicalize().unwrap_or(full_path.clone());
    let workspace = workspace_dir().canonicalize().unwrap_or(workspace_dir());
    
    if !canonical.starts_with(&workspace) {
        return Err(ConfigError::PathSecurityViolation(
            format!("路径超出工作目录范围: {}", source_path)
        ));
    }
    
    Ok(full_path)
}

/// 计算文件的 SHA256 哈希
pub fn compute_hash(data: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    hex::encode(hasher.finalize())
}

/// 计算文件内容的哈希
pub fn compute_file_hash(path: &Path) -> Result<String, ConfigError> {
    if !path.exists() {
        return Ok(compute_hash(""));
    }
    
    let content = fs::read_to_string(path)?;
    Ok(compute_hash(&content))
}

/// 原子写入文件
/// 1. 写入临时文件
/// 2. 原子重命名覆盖目标文件
pub fn atomic_write(path: &Path, content: &str) -> Result<(), ConfigError> {
    use std::io::Write;
    
    // 确保父目录存在
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    
    // 生成临时文件路径
    let temp_path = path.with_extension(format!("tmp.{}", fastrand::u32(..)));
    
    // 写入临时文件
    {
        let mut file = fs::File::create(&temp_path)?;
        file.write_all(content.as_bytes())?;
        file.sync_all()?; // 确保数据落盘
    }
    
    // 原子重命名
    fs::rename(&temp_path, path)?;
    
    // 清理临时文件（如果还存在）
    if temp_path.exists() {
        let _ = fs::remove_file(&temp_path);
    }
    
    Ok(())
}

/// 读取配置文件内容
pub fn read_file_content(path: &Path) -> Result<String, ConfigError> {
    if !path.exists() {
        return Err(ConfigError::ConfigNotFound(
            path.display().to_string()
        ));
    }
    
    fs::read_to_string(path)
        .map_err(|e| ConfigError::IoError(e))
}

/// 获取文件元信息
pub fn get_file_meta(path: &Path) -> Result<FileMeta, ConfigError> {
    let hash = compute_file_hash(path)?;
    
    let modified = if path.exists() {
        let metadata = fs::metadata(path)?;
        metadata
            .modified()?
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64()
    } else {
        0.0
    };
    
    Ok(FileMeta {
        version_hash: hash,
        last_modified: modified,
    })
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct FileMeta {
    pub version_hash: String,
    pub last_modified: f64,
}