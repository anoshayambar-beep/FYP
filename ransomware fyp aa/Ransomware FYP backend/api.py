from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from functools import wraps

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import subprocess

import random
import smtplib
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from blockchain_logger import Blockchain

APP_VERSION = "1.0"
SECRET_KEY = "comsats_fyp_super_secret_key"  # Better to load from env in prod

STATUS_FILE = "status.txt"
SETTINGS_FILE = "settings.json"
ALERTS_FILE = "alerts.json"  # legacy JSON store (kept for compatibility)
DB_FILE = "ransomware.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text_file(path: str, default: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or default
    except Exception:
        return default


def write_text_file(path: str, content: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def read_json_file(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json_file(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def send_welcome_email(receiver_email, username, password):
    """
    Sends a welcome email with login details upon registration.
    """
    sender_email = "alishbazainab1@gmail.com"  # Personal Gmail for Sending
    password_env = "hicp tdwx vppy azlv"    # Gmail App Password (alishbazainab1)

    subject = "Ransomware System - Registration Successful"
    body = f"Welcome to the Ransomware Detection System!\n\nYour account has been created successfully.\n\nUsername: {username}\nEmail: {receiver_email}\nPassword: {password}\n\nPlease keep your login details safe."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password_env)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def init_db() -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_utc TEXT NOT NULL,
                ransomware_detected INTEGER NOT NULL,
                scanned_files INTEGER,
                suspicious_count INTEGER,
                username TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_utc TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                meta_json TEXT,
                username TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT
            )
            """
        )
        
        # Add phone and email columns if they don't exist
        for col in [("phone", "TEXT"), ("email", "TEXT")]:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col[0]} {col[1]}")
            except sqlite3.OperationalError:
                pass
            
        # Add username column if it doesn't exist for legacy tables
        try:
            cur.execute("ALTER TABLE scan_events ADD COLUMN username TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cur.execute("ALTER TABLE alerts ADD COLUMN username TEXT")
        except sqlite3.OperationalError:
            pass
            
        conn.commit()
    finally:
        conn.close()


def default_scan_paths() -> list[str]:
    # Keep default reasonably safe/performance-friendly.
    # User can override via /settings.
    user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or "C:\\Users\\Administrator"
    return [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads"),
    ]


def normalize_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        try:
            p2 = os.path.abspath(os.path.expandvars(p))
            if p2 not in out:
                out.append(p2)
        except Exception:
            continue
    return out


@dataclass(frozen=True)
class AppSettings:
    scan_paths: list[str]
    ransomware_extensions: list[str]
    max_files: int
    time_limit_seconds: int

    @staticmethod
    def load() -> "AppSettings":
        raw = read_json_file(SETTINGS_FILE, default={})
        scan_paths = raw.get("scan_paths") or default_scan_paths()
        ransomware_extensions = raw.get("ransomware_extensions") or [
            ".locked",
            ".encrypted",
            ".crypt",
            ".crypto",
            ".enc",
            ".locky",
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


def append_alert(kind: str, message: str, meta: dict[str, Any] | None = None, username: str = None) -> dict[str, Any]:
    alert_time = now_iso()
    payload_meta = meta or {}

    # Write to SQLite
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO alerts (time_utc, kind, message, meta_json, username)
            VALUES (?, ?, ?, ?, ?)
            """,
            (alert_time, kind, message, json.dumps(payload_meta, ensure_ascii=False), username),
        )
        conn.commit()
        db_id = cur.lastrowid
    except Exception:
        db_id = None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Legacy JSON list (for backward compatibility / offline inspection)
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
    alerts = alerts[:200]
    write_json_file(ALERTS_FILE, alerts)
    return alert


def scan_files(settings: AppSettings) -> dict[str, Any]:
    start = time.time()
    scanned = 0
    errors = 0
    suspicious: list[dict[str, Any]] = []
    suspicious_set: set[str] = set()

    paths = [p for p in settings.scan_paths if os.path.exists(p)]
    for root in paths:
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common heavy/system folders inside user dirs
            dirnames[:] = [
                d
                for d in dirnames
                if d.lower() not in {"node_modules", ".git", ".dart_tool", "build", "__pycache__"}
            ]

            for name in filenames:
                if scanned >= settings.max_files:
                    break
                if (time.time() - start) > settings.time_limit_seconds:
                    break

                scanned += 1
                full_path = os.path.join(dirpath, name)
                try:
                    lower = name.lower()
                    if any(lower.endswith(ext) for ext in settings.ransomware_extensions):
                        if full_path not in suspicious_set:
                            suspicious_set.add(full_path)
                            suspicious.append(
                                {
                                    "path": full_path,
                                    "reason": "suspicious_extension",
                                }
                            )
                except Exception:
                    errors += 1

            if scanned >= settings.max_files or (time.time() - start) > settings.time_limit_seconds:
                break

        if scanned >= settings.max_files or (time.time() - start) > settings.time_limit_seconds:
            break

    duration_ms = int((time.time() - start) * 1000)
    ransomware_detected = len(suspicious) > 0
    return {
        "started_at": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        "finished_at": now_iso(),
        "duration_ms": duration_ms,
        "scanned_files": scanned,
        "errors": errors,
        "ransomware_detected": ransomware_detected,
        "suspicious_files": suspicious[:50],
        "scanned_paths": paths,
        "limits": {
            "max_files": settings.max_files,
            "time_limit_seconds": settings.time_limit_seconds,
        },
    }


# =========================
# BACKGROUND MONITORING
# =========================

def trigger_os_notification(title, message):
    try:
        # Path to the custom bottom-right popup script
        script_path = os.path.join(os.getcwd(), "pop_bottom_right.ps1")
        cmd = [
            'powershell', 
            '-ExecutionPolicy', 'Bypass', 
            '-File', script_path, 
            '-title', title, 
            '-message', message
        ]
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"Notification Error: {e}")


def scan_for_realtime_threats(settings: AppSettings, known_threats: set):
    """
    Periodically scans paths for new threats recursively.
    """
    new_threats_found = []
    
    for root_dir in settings.scan_paths:
        if not os.path.exists(root_dir):
            continue
            
        try:
            # Recursive scan using os.walk
            for root, dirs, files in os.walk(root_dir):
                for name in files:
                    full_path = os.path.join(root, name)
                    if full_path not in known_threats:
                        lower = name.lower()
                        if any(lower.endswith(ext) for ext in settings.ransomware_extensions):
                            new_threats_found.append(full_path)
                            known_threats.add(full_path)
        except Exception as e:
            print(f"Scan Error in {root_dir}: {e}")
            continue
            
    return new_threats_found


def start_background_monitor():
    print("SYSTEM: Background Monitor (Polling Mode) Started")
    settings = AppSettings.load()
    
    # Initialize known threats recursively
    known_threats = set()
    for root_dir in settings.scan_paths:
        if os.path.exists(root_dir):
            print(f"SYSTEM: Initial Indexing for {root_dir}...")
            try:
                for root, dirs, files in os.walk(root_dir):
                    for name in files:
                         full_path = os.path.join(root, name)
                         known_threats.add(full_path)
                print(f"SYSTEM: Indexed {root_dir} successfully.")
            except Exception as e:
                print(f"SYSTEM: Error indexing {root_dir}: {e}")
    
    print(f"SYSTEM: Total unique files indexed: {len(known_threats)}")
    
    counter = 0
    try:
        while True:
            counter += 1
            if counter % 10 == 0:
                print(f"SYSTEM: Monitoring heartbeat... ({len(known_threats)} files tracked)")
            current_settings = AppSettings.load()
            new_threats = scan_for_realtime_threats(current_settings, known_threats)
            
            if new_threats:
                for threat in new_threats:
                    print(f"REAL-TIME ALERT: New threat detected: {threat}")
                    
                    # Update status
                    write_text_file(STATUS_FILE, "Ransomware Activity Detected (Real-time)")
                    
                    trigger_os_notification(
                        "Security Alert!", 
                        f"Suspicious activity detected in: {os.path.basename(threat)}"
                    )
                    
                    try:
                        append_alert(
                            kind="realtime_protection",
                            message=f"Real-time protection flagged suspicious file: {threat}",
                            meta={"file": threat}
                        )
                        blockchain.add_block({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "prediction": "Suspicious",
                            "status": "Real-time Detection",
                            "username": "system_monitor"
                        })
                        
                        # Add to scan_events to keep reports synced
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO scan_events (time_utc, ransomware_detected, scanned_files, suspicious_count, username) VALUES (?, ?, ?, ?, ?)",
                            (now_iso(), 1, 1, 1, "system_monitor")
                        )
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print(f"Log Error: {e}")
            
            time.sleep(5)  # Scan every 5 seconds
    except Exception as e:
        print(f"SYSTEM: Monitor stopped due to error: {e}")


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)
blockchain = Blockchain()
init_db()


# =========================
# AUTH DECORATORS
# =========================

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = {"username": data["username"], "role": data["role"]}
        except Exception as e:
            return jsonify({"error": "Token is invalid!", "message": str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if data["role"] != "admin":
                return jsonify({"error": "Requires admin privileges!"}), 403
            current_user = {"username": data["username"], "role": data["role"]}
        except Exception as e:
            return jsonify({"error": "Token is invalid!", "message": str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# =========================
# ENDPOINTS
# =========================

@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "user")  # 'user' or 'admin'
    phone = data.get("phone")
    email = data.get("email")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    hashed_password = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, phone, email) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, role, phone, email)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            conn.close()
        except:
            pass

    # --- Send Welcome Email ---
    email_success = False
    if email:
        email_success = send_welcome_email(email, username, password)

    # --- SYSTEM NOTIFICATION (To simulate SMS on Desktop) ---
    try:
        import subprocess
        notification_title = "Ransomware System Alert"
        notification_msg = f"Email to {email}: Welcome {username}! Registration Successful."
        
        # PowerShell command to show a balloon notification (works widely on Windows)
        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -id $pid).Path)
        $notification.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
        $notification.BalloonTipText = "{notification_msg}"
        $notification.BalloonTipTitle = "{notification_title}"
        $notification.Visible = $true
        $notification.ShowBalloonTip(10000)
        """
        subprocess.Popen(['powershell', '-Command', ps_cmd], shell=True)
    except:
        pass

    return jsonify({
        "message": "User registered successfully", 
        "role": role,
        "email_sent": email_success,
        "msg": f"Registration Successful! Welcome email {'sent' if email_success else 'failed (check credentials)'} to {email}"
    }), 201

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Could not verify"}), 401

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    token = jwt.encode({
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc).timestamp() + 24 * 3600 # 24 hours expiry
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"token": token, "role": user["role"], "username": user["username"]})


# Removed forgot password endpoints as per user request

@app.get("/health")
def health():
    return jsonify({"ok": True, "version": APP_VERSION, "time": now_iso()})


@app.get("/detect")
@require_auth
def detect(current_user):
    status = read_text_file(STATUS_FILE, default="System Safe")
    return jsonify({"status": status, "time": now_iso(), "user": current_user["username"]})


@app.get("/scan")
@require_auth
def scan(current_user):
    settings = AppSettings.load()

    result = scan_files(settings)

    # Persist scan event in SQLite
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO scan_events (time_utc, ransomware_detected, scanned_files, suspicious_count, username)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                result["finished_at"],
                1 if result["ransomware_detected"] else 0,
                int(result.get("scanned_files", 0)),
                len(result.get("suspicious_files") or []),
                current_user["username"],
            ),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if result["ransomware_detected"]:
        write_text_file(STATUS_FILE, "Ransomware Activity Detected")
        alert = append_alert(
            kind="ransomware",
            message="Ransomware indicators found during scan",
            meta={"suspicious_files": result["suspicious_files"]},
            username=current_user["username"]
        )
        blockchain.add_block(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prediction": "Suspicious",
                "status": "Ransomware Detected",
                "username": current_user["username"],
                "role": current_user["role"],
            }
        )
    else:
        write_text_file(STATUS_FILE, "System Safe")
        blockchain.add_block(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prediction": "Safe",
                "status": "System Safe",
                "username": current_user["username"],
                "role": current_user["role"],
            }
        )

    return jsonify(result)


@app.get("/blockchain")
@require_admin
def get_blockchain(current_user):
    blockchain.load_chain()
    return jsonify({"chain": blockchain.chain, "length": len(blockchain.chain)})


@app.get("/alerts")
@require_auth
def get_alerts(current_user):
    # Prefer SQLite alerts (most recent first)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if current_user["role"] == "admin":
            cur.execute(
                """
                SELECT time_utc, kind, message, meta_json, username
                FROM alerts
                ORDER BY id DESC
                LIMIT 200
                """
            )
        else:
            cur.execute(
                """
                SELECT time_utc, kind, message, meta_json, username
                FROM alerts
                WHERE username = ? OR username IS NULL
                ORDER BY id DESC
                LIMIT 200
                """,
                (current_user["username"],)
            )
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    alerts: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        try:
            meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
        except Exception:
            meta = {}
        alerts.append(
            {
                "id": f"alert_db_{idx}",
                "time": row["time_utc"],
                "kind": row["kind"],
                "message": row["message"],
                "meta": meta,
                "username": row["username"] if "username" in row.keys() else None,
            }
        )

    # Fallback to legacy JSON if DB empty
    if not alerts:
        legacy = read_json_file(ALERTS_FILE, default=[])
        if isinstance(legacy, list):
            alerts = legacy

    return jsonify({"alerts": alerts})


@app.get("/reports")
@require_auth
def reports(current_user):
    # Primary aggregation from SQLite (authoritative source for reports).
    scan_events = 0
    ransomware_events = 0
    total_scanned = 0
    last_event_time: str | None = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if current_user["role"] == "admin":
            cur.execute(
                """
                SELECT
                    COUNT(*)                        AS total_scans,
                    SUM(scanned_files)              AS total_scanned_files,
                    SUM(CASE WHEN ransomware_detected = 1 THEN 1 ELSE 0 END) AS ransomware_scans,
                    MAX(time_utc)                   AS last_time
                FROM scan_events
                """
            )
        else:
            cur.execute(
                """
                SELECT
                    COUNT(*)                        AS total_scans,
                    SUM(scanned_files)              AS total_scanned_files,
                    SUM(CASE WHEN ransomware_detected = 1 THEN 1 ELSE 0 END) AS ransomware_scans,
                    MAX(time_utc)                   AS last_time
                FROM scan_events
                WHERE username = ?
                """,
                (current_user["username"],)
            )
        row = cur.fetchone()
        if row:
            scan_events = int(row["total_scans"] or 0)
            total_scanned = int(row["total_scanned_files"] or 0)
            ransomware_events = int(row["ransomware_scans"] or 0)
            last_event_time = row["last_time"]
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return jsonify(
        {
            "scan_events": scan_events,
            "ransomware_events": ransomware_events,
            "total_scanned_files": total_scanned,
            "last_event_time": last_event_time,
        }
    )


@app.get("/settings")
@require_admin
def get_settings(current_user):
    settings = AppSettings.load()
    return jsonify(settings.to_dict())


@app.post("/settings")
@require_admin
def set_settings(current_user):
    payload = request.get_json(silent=True) or {}
    current = AppSettings.load()

    scan_paths = payload.get("scan_paths", current.scan_paths)
    ransomware_extensions = payload.get("ransomware_extensions", current.ransomware_extensions)
    max_files = payload.get("max_files", current.max_files)
    time_limit_seconds = payload.get("time_limit_seconds", current.time_limit_seconds)

    new_settings = AppSettings(
        scan_paths=normalize_paths(list(scan_paths)),
        ransomware_extensions=[str(x).lower() for x in list(ransomware_extensions)],
        max_files=max(1, int(max_files)),
        time_limit_seconds=max(1, int(time_limit_seconds)),
    )
    write_json_file(SETTINGS_FILE, new_settings.to_dict())
    return jsonify(new_settings.to_dict())


@app.get("/test-notify")
def test_notify():
    trigger_os_notification("Test Alert", "This is a test notification from your FYP backend!")
    return jsonify({"message": "Test notification triggered! Check your system tray."})


lock_file_fp = None

def check_singleton():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        return
    global lock_file_fp
    try:
        import msvcrt
        lock_file_fp = open("api.lock", "a")
        lock_file_fp.seek(0)
        msvcrt.locking(lock_file_fp.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file_fp.truncate(0)
        lock_file_fp.write(str(os.getpid()))
        lock_file_fp.flush()
    except Exception:
        print("[API] Another instance is already running. Exiting.")
        import sys
        sys.exit(0)

if __name__ == "__main__":
    check_singleton()
    # Main API for the Flutter frontend
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)  # enable hot‑reload
