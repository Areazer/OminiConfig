pub mod utils;
pub mod commands;
pub mod watcher;

// Re-export commonly used items
pub use utils::{ConfigError, FileMeta, validate_path, compute_hash, compute_file_hash, atomic_write, read_file_content, get_file_meta, workspace_dir};