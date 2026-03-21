#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;
mod utils;
mod watcher;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let app_handle = app.handle();
            
            // 启动文件监听器
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async {
                    if let Err(e) = watcher::start_watcher(app_handle).await {
                        eprintln!("文件监听器启动失败: {}", e);
                    }
                });
            });
            
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