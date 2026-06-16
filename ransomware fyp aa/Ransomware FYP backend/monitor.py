# --------------------------------------------------------------
# monitor.py – continuous ransomware scanner & notifier
# --------------------------------------------------------------
# This file is independent of the Flask API (api.py). It
#   • Loads the same AppSettings configuration
#   • Keeps a persistent set of already‑seen files
#   • Scans every `settings.scan_interval_seconds` (default 5 s)
#   • Fires a Windows toast notification for any newly‑detected file
#   • Writes alerts to the same SQLite DB & legacy JSON store
# --------------------------------------------------------------

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Configuration constants – keep them in sync with api.py
# ------------------------------------------------------------------
STATUS_FILE = "status.txt"
SETTINGS_FILE = "settings.json"
ALERTS_FILE = "alerts.json"          # legacy JSON store (kept for compatibility)
DB_FILE = "ransomware.db"            # SQLite DB used by api.py
SCAN_INTERVAL_SECONDS = 5            # How often to poll the file system

# ------------------------------------------------------------------
# Helper utilities (copy‑paste from api.py to stay consistent)
# ------------------------------------------------------------------
def now_iso() -> str:
    """Current UTC timestamp in ISO‑8601 format."""
    return datetime.now(timezone.utc).isoformat()


def read_json_file(path: str, default: Any) -> Any:
    """Read a JSON file, return `default` on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json_file(path: str, data: Any) -> None:
    """Atomically write JSON data to `path`."""
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        # If writing fails we simply give up – the monitor will try again later
        pass

def write_text_file(path: str, content: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with row‑factory for dict‑like access."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def append_alert(kind: str, message: str, meta: dict[str, Any] | None = None,
                 username: str | None = None) -> dict[str, Any]:
    """Persist an alert to SQLite and the legacy JSON file."""
    alert_time = now_iso()
    payload_meta = meta or {}

    # ---------- SQLite ----------
    db_id = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO alerts (time_utc, kind, message, meta_json, username)
            VALUES (?, ?, ?, ?, ?)
            """,
            (alert_time, kind, message,
             json.dumps(payload_meta, ensure_ascii=False), username),
        )
        conn.commit()
        db_id = cur.lastrowid
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # ---------- Legacy JSON ----------
    alert = {
        "id": f"alert_{db_id or int(time.time() * 1000)}",
        "time": alert_time,
        "kind": kind,
        "message": message,
        "meta": payload_meta,
        "username": username,
    }
    alerts = read_json_file(ALERTS_FILE, default=[])
    if not isinstance(alerts, list):
        alerts = []
    alerts.insert(0, alert)
    alerts = alerts[:200]                     # keep recent 200 only
    write_json_file(ALERTS_FILE, alerts)

    return alert


def trigger_os_notification(title: str, message: str) -> None:
    """
    Show a Custom Pop-up Window (White + Yellow Triangle) in Bottom Right.
    """
    try:
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $form = New-Object System.Windows.Forms.Form
        $form.Text = '{title}'
        $form.Size = New-Object System.Drawing.Size(400,120)
        $form.StartPosition = 'Manual'
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
        $form.Location = New-Object System.Drawing.Point(($screen.Width - 410), ($screen.Height - 130))
        $form.FormBorderStyle = 'FixedDialog'
        $form.TopMost = $true
        $form.BackColor = [System.Drawing.Color]::White
        
        $icon = New-Object System.Windows.Forms.PictureBox
        $icon.Image = [System.Drawing.SystemIcons]::Warning.ToBitmap()
        $icon.Location = New-Object System.Drawing.Point(10, 20)
        $icon.Size = New-Object System.Drawing.Size(50, 50)
        $icon.SizeMode = 'StretchImage'
        $form.Controls.Add($icon)
        
        $label = New-Object System.Windows.Forms.Label
        $label.Text = '{message}'
        $label.Location = New-Object System.Drawing.Point(70, 20)
        $label.Size = New-Object System.Drawing.Size(300, 60)
        $label.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
        $label.TextAlign = 'MiddleLeft'
        $form.Controls.Add($label)
        
        $form.Add_Click({{$form.Close()}})
        $form.ShowDialog()
        """
        import subprocess
        subprocess.Popen(["powershell", "-Command", ps_script], creationflags=0x08000000)
    except Exception:
        pass


# ------------------------------------------------------------------
# Settings handling – matches the AppSettings dataclass from api.py
# ------------------------------------------------------------------
def default_scan_paths() -> list[str]:
    """Default directories (Desktop, Documents, Downloads)."""
    user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or r"C:\Users\Administrator"
    return [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads"),
    ]


def normalize_paths(paths: list[str]) -> list[str]:
    """Resolve env vars, make absolute, deduplicate."""
    out: list[str] = []
    for p in paths:
        try:
            p2 = os.path.abspath(os.path.expandvars(p))
            if p2 not in out:
                out.append(p2)
        except Exception:
            continue
    return out


class AppSettings:
    """Simple settings container – mirrors the dataclass from api.py."""
    def __init__(self, scan_paths: list[str], ransomware_extensions: list[str],
                 max_files: int, time_limit_seconds: int):
        self.scan_paths = scan_paths
        self.ransomware_extensions = ransomware_extensions
        self.max_files = max_files
        self.time_limit_seconds = time_limit_seconds

    @staticmethod
    def load() -> "AppSettings":
        raw = read_json_file(SETTINGS_FILE, default={})
        scan_paths = raw.get("scan_paths") or default_scan_paths()
        ransomware_extensions = raw.get("ransomware_extensions") or [
            ".locked", ".encrypted", ".crypt", ".crypto",
            ".enc", ".locky"
        ]
        max_files = int(raw.get("max_files") or 50_000)
        time_limit_seconds = int(raw.get("time_limit_seconds") or 20)

        return AppSettings(
            scan_paths=normalize_paths(list(scan_paths)),
            ransomware_extensions=[str(x).lower() for x in ransomware_extensions],
            max_files=max(1, max_files),
            time_limit_seconds=max(1, time_limit_seconds),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_paths": self.scan_paths,
            "ransomware_extensions": self.ransomware_extensions,
            "max_files": self.max_files,
            "time_limit_seconds": self.time_limit_seconds,
        }

# ------------------------------------------------------------------
# Advanced Behavioral Monitoring with Watchdog
# ------------------------------------------------------------------
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

RANSOM_NOTE_KEYWORDS = [
    "decrypt", "restore_files", "readme_for_", "recover_your", 
    "how_to_decrypt", "read_it", "attention"
]

class RansomwareBehaviorHandler(FileSystemEventHandler):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.known_threats = set()
        
        # Behavioral tracking for mass modifications
        self.modification_timestamps = []
        self.lock = threading.Lock()
        
    def _check_mass_modification(self) -> bool:
        now = time.time()
        with self.lock:
            # Keep only timestamps from the last 10 seconds
            self.modification_timestamps = [t for t in self.modification_timestamps if now - t <= 10]
            
            if len(self.modification_timestamps) > 10:
                # Mass modification detected! (e.g. >10 files changed in 10s)
                self.modification_timestamps.clear() # reset to avoid spamming
                return True
        return False
        
    def _analyze_file(self, file_path: str, event_type: str):
        # We only care about file names for quick heuristic checks
        filename = os.path.basename(file_path).lower()
        
        # 1. Suspicious Extension Check (Signature-based)
        if any(filename.endswith(ext) for ext in self.settings.ransomware_extensions):
            with self.lock:
                normalized_path = os.path.normpath(file_path).lower()
                if normalized_path not in self.known_threats:
                    self.known_threats.add(normalized_path)
                    self._trigger_threat(".locked file created", file_path)
                
        # 2. Ransom Note Check (Heuristic-based)
        if any(kw in filename for kw in RANSOM_NOTE_KEYWORDS) and filename.endswith(('.txt', '.html', '.hta')):
            with self.lock:
                normalized_path = os.path.normpath(file_path).lower()
                if normalized_path not in self.known_threats:
                    self.known_threats.add(normalized_path)
                    self._trigger_threat("Ransom note / Decrypt file created", file_path)
                
    def _trigger_threat(self, threat_type: str, file_path: str):
        filename = os.path.basename(file_path)
        folder_name = os.path.basename(os.path.dirname(file_path))
        print(f"[Alert] {threat_type} detected: {file_path}")
        
        write_text_file(STATUS_FILE, "Ransomware Activity Detected (Behavioral)")
        
        if ".locked" in threat_type:
            notif_title = "Security Alert!"
            notif_msg = f"Suspicious activity detected: {filename}"
        else:
            notif_title = "Ransomware Activity Detected!"
            notif_msg = f"Behavior Detected: {threat_type}"
            
        trigger_os_notification(notif_title, notif_msg)
        
        # Save to DB exactly like the old scan_files so the UI renders it cleanly
        append_alert(
            kind="ransomware",
            message="Ransomware Activity Detected!",
            meta={"suspicious_files": [{"path": file_path, "reason": threat_type}]},
            username="system_monitor"
        )
        
        try:
            from blockchain_logger import Blockchain
            blockchain = Blockchain()
            if "deletion" in threat_type.lower():
                status_text = f"Real-time Protection: Mass deletion detected in {folder_name}"
            else:
                status_text = f"Real-time Protection: {filename} created in {folder_name}"
                
            blockchain.add_block({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prediction": "Suspicious",
                "status": status_text,
                "username": "system_monitor"
            })
        except Exception as e:
            with open("monitor_errors.log", "a") as f:
                f.write(f"[{datetime.now()}] Blockchain log error: {str(e)}\n")

    def _is_ignored(self, file_path: str) -> bool:
        # Broadly ignore our own project folder to prevent system files from triggering alerts
        lower_path = file_path.lower()
        if "ransomware fyp" in lower_path:
            return True
        if ".db-journal" in lower_path or "blockchain_logs.json" in lower_path:
            return True
        if "alerts.json" in lower_path or "status.txt" in lower_path:
            return True
        return False

    def on_created(self, event):
        if not event.is_directory and not self._is_ignored(event.src_path):
            self._analyze_file(event.src_path, "created")

    def on_moved(self, event):
        if not event.is_directory and not self._is_ignored(event.dest_path):
            self._analyze_file(event.dest_path, "renamed")
                
    def on_deleted(self, event):
        if not event.is_directory and not self._is_ignored(event.src_path):
            with self.lock:
                self.modification_timestamps.append(time.time())
            if self._check_mass_modification():
                self._trigger_threat("Mass files deletion detected", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and not self._is_ignored(event.src_path):
            self._analyze_file(event.src_path, "modified")

lock_file_fp = None

def main() -> None:
    # --- Singleton Check: Prevent multiple instances ---
    global lock_file_fp
    LOCK_FILE = "monitor.lock"
    try:
        import msvcrt
        lock_file_fp = open(LOCK_FILE, "a")
        lock_file_fp.seek(0)
        msvcrt.locking(lock_file_fp.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file_fp.truncate(0)
        lock_file_fp.write(str(os.getpid()))
        lock_file_fp.flush()
    except Exception:
        print("[Monitor] Another instance is already running. Exiting.")
        return

    try:
        print("[Monitor] Starting advanced behavioral ransomware monitor …")
        settings = AppSettings.load()
        
        observer = Observer()
        handler = RansomwareBehaviorHandler(settings)
        
        # Watch all configured paths
        for path in settings.scan_paths:
            if os.path.exists(path):
                observer.schedule(handler, path, recursive=True)
                print(f"[Monitor] Watching {path} recursively.")
                with open("monitor_paths.log", "a") as f:
                    f.write(f"[{datetime.now()}] Watching: {path}\n")
                
        observer.start()
        print("[Monitor] Real-time Behavioral protection is active.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\n[Monitor] Stopped by user.")
        
        observer.join()
    finally:
        if lock_file_fp:
            try:
                lock_file_fp.close()
            except:
                pass
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[Monitor] Unexpected error: {e}")
