use tauri_plugin_dialog::DialogExt;

#[tauri::command]
async fn save_file(app: tauri::AppHandle, contents: String, filename: String) -> Result<bool, String> {
    let path = app
        .dialog()
        .file()
        .set_file_name(&filename)
        .add_filter("CSV", &["csv"])
        .blocking_save_file();

    match path {
        Some(file_path) => {
            std::fs::write(file_path.as_path().unwrap(), contents)
                .map_err(|e| e.to_string())?;
            Ok(true)
        }
        None => Ok(false),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![save_file])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
