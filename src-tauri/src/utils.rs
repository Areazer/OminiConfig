use std::path::{Path, PathBuf, Component};
use std::fs;
use sha2::{Sha256, Digest};
use thiserror::Error;
use serde::Serialize;

/// 错误码常量 - 必须稳定，前端依赖这些值
pub const ERR_PATH_SECURITY: &str = "PATH_SECURITY_VIOLATION";
pub const ERR_CONFIG_NOT_FOUND: &str = "CONFIG_NOT_FOUND";
pub const ERR_INVALID_FORMAT: &str = "INVALID_CONFIG_FORMAT";
pub const ERR_CONCURRENCY_CONFLICT: &str = "CONCURRENCY_CONFLICT";
pub const ERR_IO_ERROR: &str = "IO_ERROR";
pub const ERR_SERIALIZATION: &str = "SERIALIZATION_ERROR";
pub const ERR_INTERNAL: &str = "INTERNAL_ERROR";

/// 结构化命令错误 - 面向前端协议
#[derive(Debug, Clone, Serialize)]
pub struct CommandError {
    pub code: String,
    pub message: String,
    pub details: Option<serde_json::Value>,
}

impl CommandError {
    pub fn path_security(reason: &str) -> Self {
        Self {
            code: ERR_PATH_SECURITY.to_string(),
            message: format!("路径安全违规: {}", reason),
            details: None,
        }
    }

    pub fn config_not_found(path: &str) -> Self {
        Self {
            code: ERR_CONFIG_NOT_FOUND.to_string(),
            message: format!("配置文件不存在: {}", path),
            details: Some(serde_json::json!({ "path": path })),
        }
    }

    pub fn invalid_format(reason: &str) -> Self {
        Self {
            code: ERR_INVALID_FORMAT.to_string(),
            message: format!("无效的配置格式: {}", reason),
            details: None,
        }
    }

    pub fn concurrency_conflict(expected: &str, actual: &str) -> Self {
        Self {
            code: ERR_CONCURRENCY_CONFLICT.to_string(),
            message: "并发冲突: 版本哈希不匹配".to_string(),
            details: Some(serde_json::json!({
                "expected_hash": expected,
                "actual_hash": actual,
            })),
        }
    }

    pub fn io_error(err: std::io::Error) -> Self {
        Self {
            code: ERR_IO_ERROR.to_string(),
            message: format!("IO 错误: {}", err),
            details: None,
        }
    }

    pub fn serialization_error(err: serde_json::Error) -> Self {
        Self {
            code: ERR_SERIALIZATION.to_string(),
            message: format!("序列化错误: {}", err),
            details: None,
        }
    }

    /// 用于用户配置文件 JSON 解析失败（INVALID_CONFIG_FORMAT）
    pub fn invalid_config_format(reason: &str) -> Self {
        Self {
            code: ERR_INVALID_FORMAT.to_string(),
            message: format!("无效的配置格式: {}", reason),
            details: None,
        }
    }

    pub fn internal(message: &str) -> Self {
        Self {
            code: ERR_INTERNAL.to_string(),
            message: message.to_string(),
            details: None,
        }
    }
}

impl std::fmt::Display for CommandError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[{}] {}", self.code, self.message)
    }
}

impl std::error::Error for CommandError {}

/// 内部错误类型（向后兼容，逐步迁移到 CommandError）
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

impl From<ConfigError> for CommandError {
    fn from(err: ConfigError) -> Self {
        match err {
            ConfigError::PathSecurityViolation(msg) => CommandError::path_security(&msg),
            ConfigError::ConfigNotFound(path) => CommandError::config_not_found(&path),
            ConfigError::ConcurrencyConflict(exp, act) => CommandError::concurrency_conflict(&exp, &act),
            ConfigError::InvalidConfigFormat(msg) => CommandError::invalid_format(&msg),
            ConfigError::IoError(e) => CommandError::io_error(e),
            ConfigError::SerializationError(e) => CommandError::serialization_error(e),
        }
    }
}

/// 工作目录 - 所有配置文件的根目录
/// 使用当前工作目录下的 configs 文件夹作为工作区
/// 注：在生产环境中应考虑使用 app data 目录而非 current_dir
pub fn workspace_dir() -> PathBuf {
    std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("configs")
}

/// 验证路径安全性
/// 基于 Path::components() 进行严格的组件级校验
/// 
/// 安全策略：
/// 1. 拒绝 Prefix 组件（Windows 盘符如 C:）
/// 2. 拒绝 RootDir 组件（Unix / 或 Windows \\）
/// 3. 拒绝 ParentDir 组件（.. 路径穿越）
/// 4. 忽略 CurDir 组件（. 当前目录）
/// 5. 只允许 Normal 组件
/// 6. 最终路径必须在 workspace 范围内
pub fn validate_path(source_path: &str) -> Result<PathBuf, ConfigError> {
    // 检查空路径
    if source_path.is_empty() {
        return Err(ConfigError::PathSecurityViolation(
            "路径不能为空".to_string()
        ));
    }
    
    // 使用 Path::components() 进行组件级解析
    // 这是核心改进：不再依赖 contains("..") 这种粗糙判断
    let path = Path::new(source_path);
    let mut has_normal = false;
    
    for component in path.components() {
        match component {
            // 1. 拒绝 Windows 盘符前缀（如 C:）
            Component::Prefix(_) => {
                return Err(ConfigError::PathSecurityViolation(
                    "禁止使用带盘符前缀的路径".to_string()
                ));
            }
            // 2. 拒绝根目录（Unix / 或 Windows \\）
            Component::RootDir => {
                return Err(ConfigError::PathSecurityViolation(
                    "禁止使用绝对路径".to_string()
                ));
            }
            // 3. 拒绝父目录引用（.. 路径穿越）
            Component::ParentDir => {
                return Err(ConfigError::PathSecurityViolation(
                    "禁止路径穿越（包含 ..）".to_string()
                ));
            }
            // 4. 忽略当前目录引用（.）
            Component::CurDir => {
                continue;
            }
            // 5. 允许普通路径组件
            Component::Normal(_) => {
                has_normal = true;
            }
        }
    }
    
    // 确保路径中至少有一个普通组件
    if !has_normal {
        return Err(ConfigError::PathSecurityViolation(
            "路径无效：缺少文件名".to_string()
        ));
    }
    
    // 构建完整路径
    let full_path = workspace_dir().join(path);
    
    // 边界检查：验证路径在工作目录范围内
    // 关键改进：即使文件不存在，也要检查路径是否在安全范围内
    // 通过人工拼接路径进行比较，避免 canonicalize 要求文件存在
    let workspace = workspace_dir();
    
    // 使用规范化路径进行比较
    // 如果 canonicalize 失败（文件不存在），使用原始路径但附加安全检查
    let (canonical_full, canonical_workspace) = match (full_path.canonicalize(), workspace.canonicalize()) {
        (Ok(full), Ok(ws)) => (full, ws),
        _ => {
            // 文件不存在时的备选策略：
            // 手动解析路径组件，移除所有 . 和冗余的 /
            // 由于我们已经拒绝了 ..，所以可以直接使用清理后的路径
            let cleaned_full = clean_path(&full_path);
            let cleaned_ws = clean_path(&workspace);
            (cleaned_full, cleaned_ws)
        }
    };
    
    // 严格边界检查：规范化后的路径必须在 workspace 内
    if !canonical_full.starts_with(&canonical_workspace) {
        return Err(ConfigError::PathSecurityViolation(
            format!("路径超出工作目录范围: {}", source_path)
        ));
    }
    
    Ok(full_path)
}

/// 清理路径（移除 . 和冗余分隔符）
/// 不处理 ..，因为前面已经拒绝
fn clean_path(path: &Path) -> PathBuf {
    let mut result = PathBuf::new();
    for component in path.components() {
        match component {
            Component::Normal(name) => result.push(name),
            _ => {} // 忽略其他组件（除 Normal 外，其他已被前面拒绝）
        }
    }
    result
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

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FileMeta {
    pub version_hash: String,
    pub last_modified: f64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;
    use serial_test::serial;

    #[test]
    fn test_validate_path_rejects_absolute() {
        let result = validate_path("/etc/passwd");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("绝对路径"));
    }

    #[test]
    fn test_validate_path_rejects_traversal() {
        let result = validate_path("../etc/passwd");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("路径穿越"));
    }

    #[test]
    #[serial]
    fn test_validate_path_accepts_relative() {
        // 保存原工作目录
        let original_dir = std::env::current_dir().unwrap();
        let temp_dir = TempDir::new().unwrap();
        std::env::set_current_dir(&temp_dir).unwrap();
        std::fs::create_dir_all(workspace_dir()).unwrap();

        let result = validate_path("app/config.json");
        assert!(result.is_ok());

        // 恢复原工作目录
        std::env::set_current_dir(original_dir).unwrap();
    }

    #[test]
    fn test_compute_hash() {
        let hash1 = compute_hash("test");
        let hash2 = compute_hash("test");
        let hash3 = compute_hash("different");

        // 相同输入产生相同哈希
        assert_eq!(hash1, hash2);
        // 不同输入产生不同哈希
        assert_ne!(hash1, hash3);
        // SHA256 产生 64 位十六进制字符串
        assert_eq!(hash1.len(), 64);
    }

    #[test]
    fn test_atomic_write() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test.txt");

        // 原子写入
        atomic_write(&file_path, "Hello, World!").unwrap();

        // 验证内容
        let content = fs::read_to_string(&file_path).unwrap();
        assert_eq!(content, "Hello, World!");
    }

    #[test]
    fn test_atomic_write_overwrite() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test.txt");

        // 先写入旧内容
        fs::write(&file_path, "Old content").unwrap();

        // 原子覆盖
        atomic_write(&file_path, "New content").unwrap();

        // 验证新内容
        let content = fs::read_to_string(&file_path).unwrap();
        assert_eq!(content, "New content");
    }
}