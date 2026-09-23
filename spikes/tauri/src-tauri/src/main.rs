// Phase 1 スパイク：Tauri（Rust + WebView2）。使い捨て。本体に持ち込まない。共通の約束は spikes/README.md。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use rusqlite::Connection;
use serde::Serialize;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Mutex;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State, WindowEvent};

#[link(name = "kernel32")]
extern "system" {
    fn GetConsoleWindow() -> *mut std::ffi::c_void;
}

struct Args {
    run_dir: String,
    auto_send: Option<String>,
    bg_seconds: f64,
    topmost: bool,
}

struct St {
    db: Mutex<Connection>,
    log: Mutex<File>,
    args: Args,
    shutdowns: AtomicU32,
}

impl St {
    fn log(&self, msg: &str) {
        let now = chrono::Local::now().format("%Y-%m-%dT%H:%M:%S%.3f");
        let mut f = self.log.lock().unwrap();
        writeln!(f, "{now} {msg}").unwrap();
        f.flush().unwrap();
    }
    fn persist(&self, role: &str, text: &str) -> i64 {
        let db = self.db.lock().unwrap();
        db.execute(
            "INSERT INTO messages(role, text, ts) VALUES(?1, ?2, ?3)",
            (role, text, chrono::Local::now().to_rfc3339()),
        )
        .unwrap();
        db.last_insert_rowid()
    }
}

fn parse_args() -> Args {
    let exe_dir = std::env::current_exe().unwrap().parent().unwrap().to_path_buf();
    let mut a = Args { run_dir: exe_dir.join("run").to_string_lossy().into(), auto_send: None, bg_seconds: 3.0, topmost: false };
    let v: Vec<String> = std::env::args().collect();
    let mut i = 1;
    while i < v.len() {
        match v[i].as_str() {
            "--run-dir" => { a.run_dir = v[i + 1].clone(); i += 1; }
            "--auto-send" => { a.auto_send = Some(v[i + 1].clone()); i += 1; }
            "--bg-seconds" => { a.bg_seconds = v[i + 1].parse().unwrap(); i += 1; }
            "--topmost" => a.topmost = true,
            _ => {}
        }
        i += 1;
    }
    a
}

#[derive(Serialize)]
struct Boot {
    rows: Vec<(String, String)>,
    auto_send: Option<String>,
}

#[tauri::command]
fn boot(st: State<St>) -> Boot {
    let db = st.db.lock().unwrap();
    let mut q = db.prepare("SELECT role, text FROM messages ORDER BY id").unwrap();
    let rows = q.query_map([], |r| Ok((r.get(0)?, r.get(1)?))).unwrap().map(|r| r.unwrap()).collect();
    Boot { rows, auto_send: st.args.auto_send.clone() }
}

#[tauri::command]
fn log_event(st: State<St>, msg: String) {
    st.log(&msg);
}

#[tauri::command]
fn persist_send(app: AppHandle, st: State<St>, text: String) -> i64 {
    let id = st.persist("user", &text);
    st.log(&format!("send id={id}"));
    st.log("bg start");
    let secs = st.args.bg_seconds;
    std::thread::spawn(move || {
        // LLM 呼び出しの代わりの待ち
        std::thread::sleep(std::time::Duration::from_secs_f64(secs));
        app.emit("bg-done", ()).unwrap();
    });
    id
}

#[tauri::command]
fn bg_end(st: State<St>, maxgap: u32, input: String) {
    let id = st.persist("assistant", "（返事）");
    st.log(&format!("bg end maxgap={maxgap}ms input_during_bg=\"{input}\""));
    st.log(&format!("reply id={id}"));
}

#[tauri::command]
fn hide_window(app: AppHandle, st: State<St>) {
    app.get_webview_window("main").unwrap().hide().unwrap();
    st.log("hide");
}

fn show(app: &AppHandle) {
    let w = app.get_webview_window("main").unwrap();
    w.show().unwrap();
    w.set_focus().unwrap();
    app.state::<St>().log("show");
}

fn main() {
    let args = parse_args();
    std::fs::create_dir_all(&args.run_dir).unwrap();
    let log = OpenOptions::new().create(true).append(true).open(format!("{}/spike.log", args.run_dir)).unwrap();
    let db = Connection::open(format!("{}/spike.db", args.run_dir)).unwrap();
    db.pragma_update(None, "journal_mode", "WAL").unwrap();
    db.pragma_update(None, "synchronous", "FULL").unwrap();
    db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, text TEXT, ts TEXT)", ()).unwrap();
    let loaded: i64 = db.query_row("SELECT count(*) FROM messages", [], |r| r.get(0)).unwrap();
    let topmost = args.topmost;

    let app = tauri::Builder::default()
        .manage(St { db: Mutex::new(db), log: Mutex::new(log), args, shutdowns: AtomicU32::new(0) })
        .invoke_handler(tauri::generate_handler![boot, log_event, persist_send, bg_end, hide_window])
        .setup(move |app| {
            let show_i = MenuItem::with_id(app, "show", "表示", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "終了", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &quit_i])?;
            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("utsushimi-spike-tauri")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, e| match e.id.as_ref() {
                    "show" => show(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, e| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = e {
                        show(tray.app_handle());
                    }
                })
                .build(app)?;
            let w = app.get_webview_window("main").unwrap();
            if topmost {
                w.set_always_on_top(true)?;
            }
            let st = app.state::<St>();
            let console = if unsafe { GetConsoleWindow() }.is_null() { "none" } else { "present" };
            st.log(&format!("start pid={} console={console} loaded={loaded} tray=true", std::process::id()));
            let p = w.outer_position()?;
            let s = w.outer_size()?;
            st.log(&format!("rect {} {} {} {}", p.x, p.y, s.width, s.height));
            Ok(())
        })
        .build(tauri::generate_context!())
        .unwrap();

    app.run(|app, e| match e {
        RunEvent::WindowEvent { event: WindowEvent::CloseRequested { api, .. }, .. } => {
            api.prevent_close(); // Alt+F4 もトレイへ
            app.get_webview_window("main").unwrap().hide().unwrap();
            app.state::<St>().log("hide");
        }
        RunEvent::WindowEvent { event: WindowEvent::Moved(p), .. } => {
            app.state::<St>().log(&format!("rect {} {}", p.x, p.y));
        }
        RunEvent::Exit => {
            let st = app.state::<St>();
            let n = st.shutdowns.fetch_add(1, Ordering::SeqCst) + 1;
            st.log(&format!("shutdown count={n}"));
        }
        _ => {}
    });
}
