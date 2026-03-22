#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;
mod utils;
mod watcher;

use std::sync::Arc;
use tauri::Manager;

/// Watcher 持有者状态
/// 通过 Tauri 的 state 管理 watcher 生命周期，避免无限 sleep
struct WatcherState {
    _watcher: Arc<watcher::FileWatcher>,
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let app_handle = app.handle();
            let workspace = utils::workspace_dir();
            
            // 创建文件监听器
            // 新的架构：FileWatcher 返回持有者，由 app state 保持存活
            // 不再需要无限 sleep 保活
            let watcher = std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async {
                    match watcher::FileWatcher::new(
                        &workspace,
                        move |event| {
                            // 处理配置事件并推送到前端
                            let payload = serde_json::json!({
                                "kind": match event.kind {
                                    watcher::ConfigEventKind::Created => "created",
                                    watcher::ConfigEventKind::Modified => "modified",
                                    watcher::ConfigEventKind::Removed => "removed",
                                    watcher::ConfigEventKind::Renamed => "renamed",
                                },
                                "path": event.path,
                                "version_hash": event.version_hash,
                                "data": event.data,
                            });
                            
                            let _ = app_handle.emit_all("config_changed", payload);
                        }
                    ).await {
                        Ok(w) => Arc::new(w),
                        Err(e) => {
                            eprintln!("文件监听器启动失败: {}", e);
                            std::process::exit(1);
                        }
                    }
                })
            });
            
            // 等待 watcher 初始化完成
            let watcher = watcher.join().expect("watcher 线程启动失败");
            
            // 将 watcher 存入 app state，保持其生命周期
            app.manage(WatcherState { _watcher: watcher });
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::read_config,
            commands::write_config,
            commands::get_schema
        ])
        .run(tauri::generate_context!())
        .expect("启动 Tauri 应用失败");
}