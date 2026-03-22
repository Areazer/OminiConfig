use crate::utils::{self, workspace_dir};
use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher, EventKind};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use serde::Serialize;
use tokio::sync::Mutex;
use tokio::time::sleep;

/// 防抖配置
const DEBOUNCE_MS: u64 = 500;

/// 配置事件类型 - 明确的业务语义
#[derive(Debug, Clone, Serialize, PartialEq)]
pub enum ConfigEventKind {
    /// 文件被创建
    Created,
    /// 文件被修改
    Modified,
    /// 文件被删除
    Removed,
    /// 文件被重命名（编辑器常用 temp -> target）
    Renamed,
}

/// 配置事件 - 完整的业务语义
#[derive(Debug, Clone, Serialize)]
pub struct ConfigEvent {
    pub kind: ConfigEventKind,
    pub path: String,
    pub data: Option<serde_json::Value>,
    pub version_hash: Option<String>,
}

/// 文件变更事件聚合器
#[derive(Debug, Clone)]
struct PendingEvent {
    path: String,
    kind: ConfigEventKind,
    last_event: Instant,
}

/// 文件监听器持有者
/// 通过返回此结构体，让调用方管理生命周期，而不是无限 sleep
pub struct FileWatcher {
    _watcher: RecommendedWatcher,
    pending_events: Arc<Mutex<HashMap<String, PendingEvent>>>,
}

impl FileWatcher {
    /// 创建新的文件监听器
    pub async fn new<F>(workspace: &std::path::Path, event_handler: F) -> notify::Result<Self>
    where
        F: Fn(ConfigEvent) + Send + 'static,
    {
        // 确保工作目录存在
        if !workspace.exists() {
            std::fs::create_dir_all(workspace)
                .map_err(|e| notify::Error::generic(&e.to_string()))?;
        }

        let pending_events: Arc<Mutex<HashMap<String, PendingEvent>>> =
            Arc::new(Mutex::new(HashMap::new()));

        // 创建文件监听器
        let watcher = {
            let pending = pending_events.clone();

            let mut watcher: RecommendedWatcher = Watcher::new(
                move |res: notify::Result<Event>| {
                    if let Ok(event) = res {
                        handle_notify_event(event, &pending);
                    }
                },
                Config::default().with_poll_interval(Duration::from_secs(1)),
            )?;

            watcher.watch(workspace, RecursiveMode::Recursive)?;
            watcher
        };

        // 启动防抖处理器
        let pending = pending_events.clone();
        tokio::spawn(debounce_processor(pending, event_handler));

        Ok(Self {
            _watcher: watcher,
            pending_events,
        })
    }
}

/// 将 notify 事件转换为业务事件
fn classify_event(event: &Event) -> Vec<(String, ConfigEventKind)> {
    use notify::EventKind;

    match &event.kind {
        EventKind::Create(_) => {
            // 创建事件
            event
                .paths
                .iter()
                .filter(|p| is_json_file(p))
                .map(|p| (get_relative_path(p), ConfigEventKind::Created))
                .collect()
        }
        EventKind::Modify(modify_kind) => {
            use notify::event::ModifyKind;

            match modify_kind {
                ModifyKind::Name(_) => {
                    // 重命名事件（编辑器常用 temp -> target）
                    event
                        .paths
                        .iter()
                        .filter(|p| is_json_file(p))
                        .map(|p| (get_relative_path(p), ConfigEventKind::Renamed))
                        .collect()
                }
                _ => {
                    // 普通修改
                    event
                        .paths
                        .iter()
                        .filter(|p| is_json_file(p))
                        .map(|p| (get_relative_path(p), ConfigEventKind::Modified))
                        .collect()
                }
            }
        }
        EventKind::Remove(_) => {
            // 删除事件 - 必须推送明确语义，不能被读文件失败吞掉
            event
                .paths
                .iter()
                .filter(|p| is_json_file(p))
                .map(|p| (get_relative_path(p), ConfigEventKind::Removed))
                .collect()
        }
        _ => vec![],
    }
}

/// 处理 notify 事件
fn handle_notify_event(
    event: Event,
    pending_events: &Arc<Mutex<HashMap<String, PendingEvent>>>,
) {
    let classified = classify_event(&event);

    for (path, kind) in classified {
        let rt = tokio::runtime::Handle::current();
        let pending = pending_events.clone();

        rt.spawn(async move {
            let mut events = pending.lock().await;
            events.insert(
                path.clone(),
                PendingEvent {
                    path,
                    kind,
                    last_event: Instant::now(),
                },
            );
        });
    }
}

/// 防抖处理器 - 500ms 聚合后推送
async fn debounce_processor<F>(
    pending_events: Arc<Mutex<HashMap<String, PendingEvent>>>,
    event_handler: F,
) where
    F: Fn(ConfigEvent),
{
    let debounce_duration = Duration::from_millis(DEBOUNCE_MS);

    loop {
        sleep(debounce_duration).await;

        let now = Instant::now();
        let ready_events: Vec<(String, ConfigEventKind)> = {
            let events = pending_events.lock().await;
            events
                .iter()
                .filter(|(_, event)| now.duration_since(event.last_event) >= debounce_duration)
                .map(|(path, event)| (path.clone(), event.kind.clone()))
                .collect()
        };

        // 处理就绪的事件
        for (path, kind) in ready_events {
            // 从待处理列表中移除
            {
                let mut events = pending_events.lock().await;
                events.remove(&path);
            }

            // 根据事件类型处理
            let event = match kind {
                ConfigEventKind::Removed => {
                    // 删除事件：直接推送，不需要读取文件
                    ConfigEvent {
                        kind: ConfigEventKind::Removed,
                        path: path.clone(),
                        data: None,
                        version_hash: None,
                    }
                }
                _ => {
                    // 其他事件：尝试读取文件内容
                    match read_config_data(&path).await {
                        Ok((hash, data)) => ConfigEvent {
                            kind,
                            path: path.clone(),
                            data: Some(data),
                            version_hash: Some(hash),
                        },
                        Err(_) => {
                            // 读取失败，可能是文件已被删除
                            // 降级为删除事件推送
                            ConfigEvent {
                                kind: ConfigEventKind::Removed,
                                path: path.clone(),
                                data: None,
                                version_hash: None,
                            }
                        }
                    }
                }
            };

            event_handler(event);
        }
    }
}

/// 读取配置数据
async fn read_config_data(
    relative_path: &str,
) -> Result<(String, serde_json::Value), Box<dyn std::error::Error>> {
    let full_path = utils::validate_path(relative_path)?;

    if !full_path.exists() {
        return Err("文件不存在".into());
    }

    let content = utils::read_file_content(&full_path)?;
    let data: serde_json::Value = serde_json::from_str(&content)?;
    let hash = utils::compute_file_hash(&full_path)?;

    Ok((hash, data))
}

/// 检查是否为 JSON 文件
fn is_json_file(path: &std::path::Path) -> bool {
    path.extension()
        .map(|ext| ext == "json")
        .unwrap_or(false)
}

/// 获取相对路径
fn get_relative_path(path: &std::path::Path) -> String {
    let workspace = workspace_dir();
    path.strip_prefix(&workspace)
        .unwrap_or(path)
        .to_string_lossy()
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use serial_test::serial;

    fn setup_test_workspace() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        std::env::set_current_dir(&temp_dir).unwrap();
        let workspace = utils::workspace_dir();
        std::fs::create_dir_all(&workspace).unwrap();
        temp_dir
    }

    #[test]
    fn test_classify_event_create() {
        let event = Event {
            kind: EventKind::Create(notify::event::CreateKind::File),
            paths: vec![std::path::PathBuf::from("/workspace/test.json")],
            attrs: notify::event::EventAttributes::new(),
        };

        let result = classify_event(&event);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].1, ConfigEventKind::Created);
    }

    #[test]
    fn test_classify_event_modify() {
        let event = Event {
            kind: EventKind::Modify(notify::event::ModifyKind::Data(
                notify::event::DataChange::Content,
            )),
            paths: vec![std::path::PathBuf::from("/workspace/test.json")],
            attrs: notify::event::EventAttributes::new(),
        };

        let result = classify_event(&event);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].1, ConfigEventKind::Modified);
    }

    #[test]
    fn test_classify_event_remove() {
        let event = Event {
            kind: EventKind::Remove(notify::event::RemoveKind::File),
            paths: vec![std::path::PathBuf::from("/workspace/test.json")],
            attrs: notify::event::EventAttributes::new(),
        };

        let result = classify_event(&event);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].1, ConfigEventKind::Removed);
    }

    #[test]
    fn test_classify_event_rename() {
        let event = Event {
            kind: EventKind::Modify(notify::event::ModifyKind::Name(
                notify::event::RenameMode::To,
            )),
            paths: vec![std::path::PathBuf::from("/workspace/test.json")],
            attrs: notify::event::EventAttributes::new(),
        };

        let result = classify_event(&event);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].1, ConfigEventKind::Renamed);
    }

    #[test]
    fn test_classify_event_filters_non_json() {
        let event = Event {
            kind: EventKind::Modify(notify::event::ModifyKind::Data(
                notify::event::DataChange::Content,
            )),
            paths: vec![std::path::PathBuf::from("/workspace/test.txt")],
            attrs: notify::event::EventAttributes::new(),
        };

        let result = classify_event(&event);
        assert!(result.is_empty());
    }

    #[tokio::test]
    #[serial]
    async fn test_read_config_data_success() {
        let _temp = setup_test_workspace();

        let test_data = serde_json::json!({"name": "test"});
        let file_path = utils::workspace_dir().join("test.json");
        std::fs::write(&file_path, serde_json::to_string_pretty(&test_data).unwrap()).unwrap();

        let result = read_config_data("test.json").await;
        assert!(result.is_ok());

        let (hash, data) = result.unwrap();
        assert!(!hash.is_empty());
        assert_eq!(data["name"], "test");
    }

    #[tokio::test]
    #[serial]
    async fn test_read_config_data_not_found() {
        let _temp = setup_test_workspace();

        let result = read_config_data("nonexistent.json").await;
        assert!(result.is_err());
    }

    #[test]
    fn test_is_json_file() {
        assert!(is_json_file(std::path::Path::new("test.json")));
        assert!(is_json_file(std::path::Path::new("/path/to/config.json")));
        assert!(!is_json_file(std::path::Path::new("test.txt")));
        assert!(!is_json_file(std::path::Path::new("test")));
    }

    #[test]
    fn test_get_relative_path() {
        // 测试相对路径计算
        // 注意：get_relative_path 只是去除 workspace 前缀
        let workspace = workspace_dir();
        let test_file = workspace.join("test.json");
        let result = get_relative_path(&test_file);
        assert_eq!(result, "test.json");
    }
}