// Sin ventana de consola extra en Windows al compilar en modo release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // La ventana (transparente, sin bordes y siempre visible) se define en tauri.conf.json;
    // toda la lógica de la mascota vive en ../web (HTML + JS).
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("no se pudo iniciar la mascota de MEKA");
}
