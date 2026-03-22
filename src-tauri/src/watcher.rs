use crate::utils::{self, workspace_dir};
use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tauri::Manager;
use tokio::sync::Mutex;
use tokio::time::sleep;

/// 防抖配置
const DEBOUNCE_MS: u64 = 500;

/// 文件变更事件聚合器
#[derive(Debug, Clone)]
struct PendingEvent {
    path: String,
    last_event: Instant,
}

/// 启动文件监听器
pub async fn start_watcher(app_handle: tauri::AppHandle) -> notify::Result<()> {
    let workspace = workspace_dir();
    
    // 确保工作目录存在
    if !workspace.exists() {
        std::fs::create_dir_all(&workspace)
            .map_err(|e| notify::Error::generic(&e.to_string()))?;
    }
    
    // 待处理事件映射 (路径 -> 事件信息)
    let pending_events: Arc<Mutex<HashMap<String, PendingEvent>>> = 
        Arc::new(Mutex::new(HashMap::new()));
    
    // 创建文件监听器
    let watcher = {
        let app_handle = app_handle.clone();
        let pending_events = pending_events.clone();
        
        let mut watcher: RecommendedWatcher = 
            Watcher::new(
                move |res: notify::Result<Event>| {
                    if let Ok(event) = res {
                        handle_notify_event(
                            event,
                            &app_handle,
                            &pending_events
                        );
                    }
                },
                Config::default().with_poll_interval(Duration::from_secs(1))
            )?;
        
        // 递归监听工作目录
        watcher.watch(&workspace, 
            RecursiveMode::Recursive
        )?;
        
        watcher
    };
    
    // 启动防抖处理器
    tokio::spawn(debounce_processor(
        app_handle,
        pending_events
    ));
    
    // 保持监听器存活
    loop {
        sleep(Duration::from_secs(60)).await;
    }
}

/// 处理 notify 事件
fn handle_notify_event(
    event: Event,
    _app_handle: &tauri::AppHandle,
    pending_events: &Arc<Mutex<HashMap<String, PendingEvent>>>,
) {
    use notify::EventKind;
    
    // 只关心修改和删除事件
    let is_relevant = matches!(
        event.kind,
        EventKind::Modify(_) | EventKind::Remove(_)
    );
    
    if !is_relevant {
        return;
    }
    
    for path in &event.paths {
        // 只处理 JSON 文件
        if let Some(ext) = path.extension() {
            if ext != "json" {
                continue;
            }
        } else {
            continue;
        }
        
        // 获取相对路径
        let workspace = workspace_dir();
        let relative_path = path.strip_prefix(&workspace)
            .unwrap_or(path)
            .to_string_lossy()
            .to_string();
        
        // 添加到待处理事件
        let rt = tokio::runtime::Handle::current();
        let pending = pending_events.clone();
        let rel_path = relative_path.clone();
        
        rt.spawn(async move {
            let mut events = pending.lock().await;
            events.insert(rel_path.clone(), PendingEvent {
                path: rel_path,
                last_event: Instant::now(),
            });
        });
    }
}

/// 防抖处理器 - 500ms 聚合后推送
async fn debounce_processor(
    app_handle: tauri::AppHandle,
    pending_events: Arc<Mutex<HashMap<String, PendingEvent>>>,
) {
    let debounce_duration = Duration::from_millis(DEBOUNCE_MS);
    
    loop {
        sleep(debounce_duration).await;
        
        let now = Instant::now();
        let ready_events: Vec<String> = {
            let events = pending_events.lock().await;
            events
                .iter()
                .filter(|(_, event)| {
                    now.duration_since(event.last_event) >= debounce_duration
                })
                .map(|(path, _)| path.clone())
                .collect()
        };
        
        // 处理就绪的事件
        for path in ready_events {
            // 从待处理列表中移除
            {
                let mut events = pending_events.lock().await;
                events.remove(&path);
            }
            
            // 读取最新配置并推送
            if let Ok((new_hash, new_data)) = read_latest_config(&path
            ).await {
                let payload = serde_json::json!({
                    "path": path,
                    "new_version_hash": new_hash,
                    "new_data": new_data
                });
                
                let _ = app_handle.emit_all(
                    "config_modified",
                    payload
                );
            }
        }
    }
}

/// 读取最新配置数据
async fn read_latest_config(
    relative_path: &str
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