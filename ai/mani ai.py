import os
import sys
import re
import json
import time
import math
import sqlite3
import threading
import queue
import socket
import subprocess
import webbrowser
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import filedialog

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKDND_OK = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    TKDND_OK = False
from tkinter import font as tkfont

from datetime import datetime

import hashlib
import hmac
import base64
import uuid
import platform
import ctypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import random
import shutil
import glob
import html
import difflib
import io
from contextlib import closing
from html.parser import HTMLParser

try:
    import cv2
    CV2_OK = True
except Exception:
    cv2 = None
    CV2_OK = False

# Optional local math engine.  SHASTRA still runs if SymPy is not installed.
try:
    import sympy as sp
    SYMPY_OK = True
except Exception:
    sp = None
    SYMPY_OK = False

try:
    import psutil
    PSUTIL_OK = True
except Exception:
    psutil = None
    PSUTIL_OK = False


# ============================================================

# SHASTRA FUTURE CORE

# Single-file Windows voice/computer assistant

#

# Optional packages:

#   pip install SpeechRecognition pyttsx3 pyautogui pillow pytesseract AppOpener pywinauto opencv-python
#   Voice input: pip install -r requirements.txt
#   Run with: .venv\Scripts\python.exe ai_fixed.py
#

# Notes:

# - Login selects either Gemini API + Google Search or Wikipedia + Google Search.

# - App launching supports common Windows apps + AppOpener.

# - "click <text>" and "type <text>" use OCR when Tesseract is installed.

# - Keyboard/mouse/window controls use PyAutoGUI / PyGetWindow.

# - Learned aliases are stored in shastra_memory.db.

# ============================================================



# ---------------- Optional imports ----------------



try:

    import speech_recognition as sr

    SPEECH_OK = True

except Exception:

    sr = None

    SPEECH_OK = False



# Free local voice recognition fallback.
try:
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer
    VOSK_OK = True
except Exception:
    sd = None
    Model = None
    KaldiRecognizer = None
    VOSK_OK = False


try:

    import pyttsx3

    TTS_OK = True

except Exception:

    pyttsx3 = None

    TTS_OK = False

try:
    import win32com.client
    WIN32_SAPI_OK = True
except Exception:
    win32com = None
    WIN32_SAPI_OK = False

try:
    import pythoncom
    PYTHONCOM_OK = True
except Exception:
    pythoncom = None
    PYTHONCOM_OK = False



try:

    import pyautogui

    PYAUTO_OK = True

    pyautogui.PAUSE = 0.08

    pyautogui.FAILSAFE = True

except Exception:

    pyautogui = None

    PYAUTO_OK = False



try:

    import pytesseract

    from PIL import Image

    OCR_LIB_OK = True

except Exception:

    pytesseract = None

    Image = None

    OCR_LIB_OK = False



try:

    from AppOpener import open as app_open

    APPOPENER_OK = True

except Exception:

    app_open = None

    APPOPENER_OK = False



try:

    import pygetwindow as gw

    WINDOW_OK = True

except Exception:

    gw = None

    WINDOW_OK = False



try:
    import warnings
    warnings.filterwarnings(
        "ignore",
        message="Revert to STA COM threading mode",
        category=UserWarning,
        module=r"pywinauto.*",
    )
    import pywinauto
    UIA_OK = True
except Exception:
    pywinauto = None
    UIA_OK = False





# ---------------- Configuration ----------------



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "shastra_memory.db")
LOCAL_USERS_DB = os.path.join(BASE_DIR, "shastra_local_users.db")
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "shastra_3d_models")
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

MODEL_EXTENSIONS = {".obj", ".stl", ".ply"}
MODEL_SEARCH_DIRS = [
    MODEL_OUTPUT_DIR,
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]

# Optional free local Vosk model folder.
VOSK_MODEL_DIR = next(
    (
        os.path.join(BASE_DIR, name)
        for name in os.listdir(BASE_DIR)
        if name.lower().startswith("vosk-model")
        and os.path.isdir(os.path.join(BASE_DIR, name))
    ),
    None
)



TESSERACT_CANDIDATES = [

    r"C:\Program Files\Tesseract-OCR\tesseract.exe",

    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",

    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),

]



TESSERACT_PATH = next(

    (p for p in TESSERACT_CANDIDATES if os.path.exists(p)),

    None

)



TESSERACT_OK = bool(TESSERACT_PATH and OCR_LIB_OK)

if TESSERACT_OK:

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH





# ============================================================

# MEMORY

# ============================================================



# ============================================================
# SECURITY MODE (Windows)
# ============================================================
SECURITY_FIREWALL_IN = "SHASTRA_SECURITY_BLOCK_IN"
SECURITY_FIREWALL_OUT = "SHASTRA_SECURITY_BLOCK_OUT"
SECURITY_STATE_FILE = os.path.join(BASE_DIR, "shastra_security_state.json")

def _is_admin():
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: return False

def _run_hidden(cmd):
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    except Exception: return None

def _security_adapters():
    wifi=[]; bt=[]
    ps=("Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Select-Object Name,InterfaceDescription | ConvertTo-Json -Compress")
    r=_run_hidden(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps])
    if r and r.returncode==0:
        try:
            data=json.loads(r.stdout); data=[data] if isinstance(data,dict) else data
            for x in data:
                name=str(x.get("Name","")); desc=str(x.get("InterfaceDescription","")); t=(name+" "+desc).lower()
                if any(k in t for k in ("wi-fi","wifi","wireless")) and name: wifi.append(name)
                if "bluetooth" in t and name: bt.append(name)
        except Exception: pass
    return wifi,bt

def _security_save(wifi,bt):
    try:
        with open(SECURITY_STATE_FILE,"w",encoding="utf-8") as f: json.dump({"wifi":wifi,"bt":bt},f)
    except Exception: pass

def _security_load():
    try:
        with open(SECURITY_STATE_FILE,encoding="utf-8") as f:
            d=json.load(f); return d.get("wifi",[]),d.get("bt",[])
    except Exception: return [],[]

def security_mode_on():
    if os.name!="nt": return False,"Security Mode is supported on Windows only."
    if not _is_admin(): return False,"Administrator permission is required. Restart SHASTRA as Administrator."
    wifi,bt=_security_adapters(); _security_save(wifi,bt)
    for name in wifi: _run_hidden(["netsh","interface","set","interface",f"name={name}","admin=disabled"])
    # Disable Bluetooth adapter through PowerShell.
    for name in bt:
        cmd=f"Disable-NetAdapter -Name '{name.replace(chr(39),chr(39)*2)}' -Confirm:$false -ErrorAction SilentlyContinue"
        _run_hidden(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",cmd])
    _run_hidden(["netsh","advfirewall","firewall","add","rule",f"name={SECURITY_FIREWALL_IN}","dir=in","action=block","profile=any","enable=yes"])
    _run_hidden(["netsh","advfirewall","firewall","add","rule",f"name={SECURITY_FIREWALL_OUT}","dir=out","action=block","profile=any","enable=yes"])
    return True,"Security Mode ON: Wi-Fi and Bluetooth disabled; inbound and outbound firewall traffic blocked."

def security_mode_off():
    if os.name!="nt": return False,"Security Mode is supported on Windows only."
    if not _is_admin(): return False,"Administrator permission is required. Restart SHASTRA as Administrator."
    _run_hidden(["netsh","advfirewall","firewall","delete","rule",f"name={SECURITY_FIREWALL_IN}"])
    _run_hidden(["netsh","advfirewall","firewall","delete","rule",f"name={SECURITY_FIREWALL_OUT}"])
    wifi,bt=_security_load()
    for name in wifi: _run_hidden(["netsh","interface","set","interface",f"name={name}","admin=enabled"])
    for name in bt:
        cmd=f"Enable-NetAdapter -Name '{name.replace(chr(39),chr(39)*2)}' -Confirm:$false -ErrorAction SilentlyContinue"
        _run_hidden(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",cmd])
    try: os.remove(SECURITY_STATE_FILE)
    except Exception: pass
    return True,"Security Mode OFF: Wi-Fi and Bluetooth enabled; firewall rules restored."

def security_mode_status():
    r=_run_hidden(["netsh","advfirewall","firewall","show","rule",f"name={SECURITY_FIREWALL_IN}"])
    return bool(r and SECURITY_FIREWALL_IN.lower() in r.stdout.lower())

class Memory:

    def __init__(self):
        global DB_FILE
        self.lock = threading.Lock()
        self.db = None

        def connect_and_initialize(db_path):
            db = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
            # Force SQLite to read/check the database before using it.
            db.execute("PRAGMA quick_check").fetchall()
            db.execute("""
                CREATE TABLE IF NOT EXISTS learned_commands (
                    phrase TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    target TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    used_count INTEGER DEFAULT 0
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_text TEXT,
                    assistant_text TEXT
                )
            """)
            db.commit()
            return db

        try:
            self.db = connect_and_initialize(DB_FILE)
        except sqlite3.DatabaseError as exc:
            # Close the failed connection, preserve the damaged file, and start
            # with a clean database. The backup may contain recoverable history.
            try:
                if self.db is not None:
                    self.db.close()
            except Exception:
                pass
            self.db = None

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = DB_FILE + f".corrupt_{stamp}.bak"
            recovery_path = DB_FILE + f".recovery_{stamp}.db"
            try:
                if os.path.exists(DB_FILE):
                    os.replace(DB_FILE, backup)
                    print(f"[MEMORY] Corrupt database backed up to: {backup}", flush=True)
            except PermissionError:
                # Another SHASTRA instance may still hold the file open or the
                # OS may have a transient lock on the database file. Start a fresh
                # recovery database so the app can continue without crashing.
                print(
                    f"[MEMORY] Database file is locked; switching to recovery database: {recovery_path}",
                    flush=True,
                )
                DB_FILE = recovery_path
                self.db = connect_and_initialize(DB_FILE)
                return
            except OSError as move_exc:
                print(
                    f"[MEMORY] Unable to back up the corrupt memory database; creating a fresh recovery database instead: {move_exc}",
                    flush=True,
                )
                DB_FILE = recovery_path
                self.db = connect_and_initialize(DB_FILE)
                return

            print(f"[MEMORY] Recreating database after corruption: {exc}", flush=True)
            self.db = connect_and_initialize(DB_FILE)


    def learn(self, phrase, action, target=""):

        phrase = phrase.lower().strip()

        if not phrase:

            return

        with self.lock:

            self.db.execute("""

                INSERT INTO learned_commands

                    (phrase, action, target, created_at)

                VALUES (?, ?, ?, ?)

                ON CONFLICT(phrase) DO UPDATE SET

                    action=excluded.action,

                    target=excluded.target

            """, (phrase, action, target, datetime.now().isoformat()))

            self.db.commit()



    def lookup(self, phrase):

        phrase = phrase.lower().strip()

        with self.lock:

            row = self.db.execute("""

                SELECT action, target

                FROM learned_commands

                WHERE phrase = ?

            """, (phrase,)).fetchone()

        if row:

            return {"action": row[0], "target": row[1]}

        return None



    def log_interaction(self, user_text, assistant_text):

        with self.lock:

            self.db.execute("""

                INSERT INTO interactions(timestamp, user_text, assistant_text)

                VALUES (?, ?, ?)

            """, (

                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                user_text,

                assistant_text

            ))

            self.db.commit()





# ============================================================

# VOICE

# ============================================================



class Voice:
    """Reliable Windows voice core using sounddevice; PyAudio is not required."""
    MARATHI_PHRASES = {
        "hello": "नमस्कार",
        "hi": "नमस्कार",
        "good morning": "शुभ प्रभात",
        "good evening": "शुभ संध्याकाळ",
        "good night": "शुभ रात्र",
        "how are you": "तू कसा आहेस?",
        "i am fine": "मी चांगला आहे",
        "thank you": "धन्यवाद",
        "thanks": "धन्यवाद",
        "please": "कृपया",
        "wait": "प्रतीक्षा करा",
        "done": "संपले",
        "ready": "तयार",
        "open": "उघडा",
        "close": "बंद करा",
        "search": "शोधा",
        "start": "सुरू करा",
        "stop": "थांबवा",
        "listen": "ऐका",
        "help": "मदत",
        "yes": "होय",
        "no": "नाही",
        "ok": "ठीक आहे",
        "okay": "ठीक आहे",
        "computer": "संगणक",
        "voice": "आवाज",
        "language": "भाषा",
        "english": "इंग्रजी",
        "marathi": "मराठी",
    }

    def __init__(self):
        self.recognizer=None; self.engine=None; self.vosk_model=None
        self.tts_backend = None
        self.win32_voice = None
        self.process_launcher = None
        self.status_callback = None
        self.listen_lock=threading.Lock(); self.tts_lock=threading.Lock()
        self.sd=None; self.audio_available=False; self.input_device=None; self.sample_rate=16000
        self.speaking=threading.Event()
        self.current_language = "en"
        self.voice_language = "en-IN"
        if SPEECH_OK:
            try:
                self.recognizer=sr.Recognizer(); self.recognizer.dynamic_energy_threshold=False
                self.recognizer.energy_threshold=180; self.recognizer.pause_threshold=.65
                self.recognizer.phrase_threshold=.10; self.recognizer.non_speaking_duration=.30
                self.recognizer.operation_timeout=6
                print('[MIC] SpeechRecognition engine: ONLINE',flush=True)
            except Exception as e: print(f'[MIC ERROR] SpeechRecognition init: {e}',flush=True)
        try:
            import sounddevice as sd
            self.sd=sd; devices=sd.query_devices(); inputs=[]
            print('[MIC] Searching for audio input devices...',flush=True)
            for i,d in enumerate(devices):
                try:
                    ch=int(d.get('max_input_channels',0))
                    if ch>0:
                        name=str(d.get('name','Unknown')); inputs.append((i,name,ch)); print(f'[MIC] [{i}] {name} (inputs={ch})',flush=True)
                except Exception: pass
            if inputs:
                try: default=int(sd.default.device[0])
                except Exception: default=None
                candidates=[x for x in inputs if x[0]==default]+[x for x in inputs if x[0]!=default]
                for i,name,ch in candidates:
                    for rate in (16000,48000,44100):
                        try:
                            sd.check_input_settings(device=i,samplerate=rate,channels=1,dtype='int16')
                            test=sd.rec(int(rate*.15),samplerate=rate,channels=1,dtype='int16',device=i,blocking=True); sd.stop()
                            if test is not None:
                                self.input_device=i; self.sample_rate=rate; self.audio_available=True
                                print(f'[MIC] Selected device [{i}] {name} @ {rate} Hz',flush=True); print('[MIC] MICROPHONE ONLINE',flush=True); break
                        except Exception: pass
                    if self.audio_available: break
            else: print('[MIC ERROR] No Windows input device found.',flush=True)
            if not self.audio_available: print('[MIC ERROR] No working sounddevice microphone.',flush=True)
        except ImportError: print('[MIC ERROR] Install sounddevice and numpy: python -m pip install sounddevice numpy',flush=True)
        except Exception as e: print(f'[MIC ERROR] sounddevice initialization failed: {e}',flush=True)
        if VOSK_OK and VOSK_MODEL_DIR:
            try: self.vosk_model=Model(VOSK_MODEL_DIR); print('[MIC] Vosk offline model: ONLINE',flush=True)
            except Exception as e: print(f'[MIC] Vosk unavailable: {e}',flush=True)

    def _set_listening_status(self, status):
        if self.status_callback is not None:
            self.status_callback(status)

    def set_language(self, language):
        value = str(language or "").strip().lower()
        if value in ("mr", "marathi", "mr-in", "marathi language") or "मराठी" in value:
            self.current_language = "mr"
            self.voice_language = "mr-IN"
        else:
            self.current_language = "en"
            self.voice_language = "en-IN"
        self._apply_voice_language()
        return self.current_language

    def _apply_voice_language(self):
        if self.current_language == "mr":
            if self.engine is not None:
                try:
                    voices = self.engine.getProperty("voices")
                    for voice in voices:
                        name = str(voice.name).lower()
                        if any(token in name for token in ("heera", "kalpana", "marathi", "hindi", "india")):
                            self.engine.setProperty("voice", voice.id)
                            break
                except Exception:
                    pass
            if self.win32_voice is not None:
                try:
                    voices = self.win32_voice.GetVoices()
                    for voice in voices:
                        name = str(voice.GetDescription()).lower()
                        if any(token in name for token in ("heera", "kalpana", "marathi", "hindi", "india")):
                            self.win32_voice.Voice = voice
                            break
                except Exception:
                    pass

    def detect_language_from_text(self, text):
        value = str(text or "").strip()
        if not value:
            return self.current_language
        lower = value.lower()
        if re.search(r"[\u0900-\u097F]", value) or any(token in lower for token in (
            "मराठी", "मराठीत", "मराठीत बोल", "मराठीत बोला", "मराठी भाषा", "marathi",
            "switch to marathi", "change language to marathi", "in marathi", "speak in marathi")):
            return self.set_language("mr")
        if any(token in lower for token in (
            "switch to english", "change language to english", "in english", "english language")):
            return self.set_language("en")
        return self.current_language

    def _translate_to_marathi(self, text):
        if not text or re.search(r"[\u0900-\u097F]", text):
            return text
        translated = text
        for english, marathi in self.MARATHI_PHRASES.items():
            pattern = re.compile(rf"\b{re.escape(english)}\b", re.IGNORECASE)
            translated = pattern.sub(marathi, translated)
        if translated == text:
            return text
        return translated

    def _init_tts(self):
        if self.engine is not None:
            return self.engine
        if TTS_OK:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 175)
                self.engine.setProperty('volume', 1.0)
                self.tts_backend = 'pyttsx3'
                print('[TTS] Voice engine: ONLINE', flush=True)
                return self.engine
            except Exception as e:
                print(f'[TTS ERROR] {e}', flush=True)
                self.engine = None
        if os.name == 'nt' and WIN32_SAPI_OK:
            try:
                voice = win32com.client.Dispatch('SAPI.SpVoice')
                self.win32_voice = voice
                self.tts_backend = 'sapi'
                print('[TTS] Windows SAPI fallback: ONLINE', flush=True)
                return voice
            except Exception as e:
                print(f'[TTS ERROR] Windows SAPI fallback failed: {e}', flush=True)
        return None

    def _refresh_microphone(self):
        """Recover a Windows/PortAudio input device after a temporary failure."""
        if self.sd is None: return False
        try:
            devices=self.sd.query_devices()
            for i,d in enumerate(devices):
                try:
                    if int(d.get("max_input_channels",0)) <= 0: continue
                    name=str(d.get("name","Unknown"))
                except Exception: continue
                for rate in (16000,48000,44100):
                    try:
                        self.sd.check_input_settings(device=i,samplerate=rate,channels=1,dtype="int16")
                        test=self.sd.rec(int(rate*.12),samplerate=rate,channels=1,dtype="int16",device=i,blocking=True)
                        self.sd.stop()
                        if test is not None and len(test):
                            self.input_device=i; self.sample_rate=rate; self.audio_available=True
                            print(f"[MIC] Recovered input device [{i}] {name} @ {rate} Hz",flush=True)
                            return True
                    except Exception:
                        try: self.sd.stop()
                        except Exception: pass
            self.audio_available=False
        except Exception as e:
            print(f"[MIC] Device recovery failed: {e}",flush=True); self.audio_available=False
        return False

    def _speak_with_system_speech(self, text):
        """Speak through Windows' built-in synthesizer when Python TTS is absent."""
        if os.name != "nt":
            return False
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            print("[TTS ERROR] Windows PowerShell was not found.", flush=True)
            return False

        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        script = (
            "$ErrorActionPreference='Stop'; "
            "Add-Type -AssemblyName System.Speech; "
            f"$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}')); "
            "$speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$speaker.Volume=100; $speaker.Rate=0; "
            "$speaker.Speak($text); $speaker.Dispose()"
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        command = [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
        ]
        process = None
        try:
            launch = self.process_launcher or subprocess.Popen
            process = launch(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired as exc:
            if process is not None:
                process.kill()
                process.communicate()
            print(f"[TTS ERROR] Windows speech timed out: {exc}", flush=True)
            return False
        except (OSError, RuntimeError) as exc:
            print(f"[TTS ERROR] Windows System.Speech could not run: {exc}", flush=True)
            return False

        if process.returncode:
            detail = (stderr or stdout or "unknown PowerShell error").strip()
            print(f"[TTS ERROR] Windows System.Speech failed: {detail}", flush=True)
            return False
        self.tts_backend = "System.Speech"
        print("[TTS] Answer spoken using Windows System.Speech.", flush=True)
        return True

    def speak(self,text):
        if not text: return False
        cleaned=re.sub(r'[\*\_\#\`\~]','',str(text)); cleaned=re.sub(r'https?://\S+','',cleaned); cleaned=re.sub(r'\s+',' ',cleaned).strip()
        if not cleaned: return False
        if self.current_language == "mr":
            cleaned = self._translate_to_marathi(cleaned)
        with self.tts_lock:
            self.speaking.set()
            try:
                speech_text = cleaned[:2200]
                if self._speak_with_system_speech(speech_text):
                    return True
                for attempt in range(2):
                    try:
                        engine = self._init_tts()
                        if engine is None:
                            break
                        if self.current_language == "mr":
                            self._apply_voice_language()
                        if self.tts_backend == 'sapi':
                            self.win32_voice.Speak(speech_text)
                        else:
                            engine.say(speech_text)
                            engine.runAndWait()
                        return True
                    except Exception as exc:
                        print(f'[TTS ERROR] Speech attempt {attempt + 1}/2 failed: {exc}', flush=True)
                        self.engine = None
                        self.win32_voice = None
                        self.tts_backend = None

                print('[TTS ERROR] No text-to-speech backend could speak this answer.', flush=True)
                return False
            finally:
                time.sleep(.15)
                self.speaking.clear()
    def _record_audio(self,max_seconds=18.0,wait_seconds=8.0):
        """Capture one spoken command from sounddevice.

        This version deliberately uses a low adaptive speech gate.  The previous
        gate could sit above normal laptop-microphone speech, which made SHASTRA
        display LISTENING while never producing a command.
        """
        if not self.audio_available or self.sd is None:
            print('[MIC] Audio input is not available.', flush=True)
            return None
        try:
            import numpy as np
            self._set_listening_status('PREPARING MICROPHONE - PLEASE WAIT')
            block_sec = 0.08
            block = max(256, int(self.sample_rate * block_sec))

            # Measure room/mic noise without requiring the user to be silent for long.
            ambient = self.sd.rec(
                int(self.sample_rate * 0.45),
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                device=self.input_device,
                blocking=True,
            )
            self.sd.stop()
            if ambient is None or len(ambient) == 0:
                ambient_rms = 0.0
                ambient_peak = 0.0
            else:
                a = ambient.astype(np.float32).reshape(-1)
                ambient_rms = float(np.sqrt(np.mean(a * a)))
                ambient_peak = float(np.percentile(np.abs(a), 95))

            # Low adaptive gate.  RMS alone is unreliable on laptop microphones,
            # so speech can also cross the gate through its peak level.
            rms_gate = max(45.0, min(260.0, ambient_rms * 1.22 + 28.0))
            peak_gate = max(110.0, min(900.0, ambient_peak * 1.18 + 55.0))
            print(
                f'[MIC] READY - speak now | device={self.input_device} '
                f'rate={self.sample_rate}Hz noise_rms={ambient_rms:.0f} '
                f'rms_gate={rms_gate:.0f} peak_gate={peak_gate:.0f}',
                flush=True,
            )

            chunks = []
            started = False
            silence = 0.0
            voice_run = 0
            processed = 0
            speech_start_index = 0
            lock = threading.Lock()

            def callback(indata, frames, time_info, status):
                if status:
                    print(f'[MIC] {status}', flush=True)
                with lock:
                    chunks.append(indata.copy())

            t0 = time.time()
            finished = False
            with self.sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=block,
                dtype='int16',
                channels=1,
                device=self.input_device,
                callback=callback,
            ):
                self._set_listening_status('LISTENING - SPEAK NOW')
                while time.time() - t0 < max_seconds:
                    if self.speaking.is_set():
                        break
                    time.sleep(0.025)
                    with lock:
                        new = chunks[processed:]
                        old_processed = processed
                        processed = len(chunks)

                    for offset, data in enumerate(new):
                        x = data.astype(np.float32).reshape(-1)
                        rms = float(np.sqrt(np.mean(x * x))) if len(x) else 0.0
                        peak = float(np.percentile(np.abs(x), 95)) if len(x) else 0.0
                        is_voice = (rms >= rms_gate) or (peak >= peak_gate)

                        if not started:
                            if is_voice:
                                voice_run += 1
                                if voice_run >= 2:
                                    started = True
                                    # Keep 0.4 seconds before the confirmed onset.
                                    speech_start_index = max(
                                        0, old_processed + offset - voice_run - 4
                                    )
                                    self._set_listening_status(
                                        'SPEECH DETECTED - FINISH SPEAKING'
                                    )
                                    print(
                                        f'[MIC] SPEECH DETECTED rms={rms:.0f} '
                                        f'peak={peak:.0f}',
                                        flush=True,
                                    )
                                    silence = 0.0
                            else:
                                voice_run = 0
                        else:
                            if is_voice:
                                silence = 0.0
                            else:
                                silence += block_sec
                                if silence >= 1.35:
                                    print('[MIC] Speech finished.', flush=True)
                                    finished = True
                                    break

                    if finished:
                        break
                    if not started and time.time() - t0 >= wait_seconds:
                        print('[MIC] No speech detected; returning to listening.', flush=True)
                        self._set_listening_status('NO SPEECH DETECTED - LISTENING AGAIN')
                        break

            with lock:
                final = list(chunks)

            if not started or not final:
                return None

            audio_chunks = final[max(0, speech_start_index):]
            if not audio_chunks:
                return None
            audio = np.concatenate(audio_chunks, axis=0)
            print(f'[MIC] Captured {len(audio)/self.sample_rate:.2f}s of speech.', flush=True)
            return audio
        except Exception as e:
            print(f'[MIC ERROR] Recording failed: {e}', flush=True)
            self._set_listening_status('MIC ERROR - RETRYING')
            try: self.sd.stop()
            except Exception: pass
            self._refresh_microphone()
            return None


    def _recognition_language_candidates(self):
        if self.current_language == 'mr':
            return ['mr-IN', 'en-IN']
        return ['en-IN', 'mr-IN']

    def _listen_speech_recognition(self):
        if not self.recognizer: return ''
        data=self._record_audio()
        if data is None: return ''
        try:
            self._set_listening_status('TRANSCRIBING SPEECH')
            import numpy as np
            audio=sr.AudioData(np.asarray(data,dtype=np.int16).reshape(-1).tobytes(),self.sample_rate,2)
            print('[MIC] Processing speech with Google recognition...',flush=True)
            text = ''
            for lang in self._recognition_language_candidates():
                try:
                    candidate = self.recognizer.recognize_google(audio, language=lang).strip()
                    if candidate:
                        text = candidate
                        print(f'[MIC] Recognized in {lang}: {text}', flush=True)
                        break
                except sr.UnknownValueError:
                    print(f'[MIC] {lang} did not understand speech; trying next language...',flush=True)
                except Exception as e:
                    print(f'[MIC] Google recognition for {lang} failed: {e}',flush=True)

            if text:
                self.detect_language_from_text(text)
                print(f'[YOU] {text}',flush=True)
                return text

            if self.vosk_model:
                print('[MIC] Google recognition unavailable; switching to offline Vosk...',flush=True)
                try:
                    text=self._recognize_vosk_audio(data)
                    if text: return text
                except Exception as ve:
                    print(f'[VOSK ERROR] {ve}',flush=True)
            self._set_listening_status('SPEECH NOT RECOGNIZED - LISTENING AGAIN')
            print('[MIC] No speech transcription returned. Listening again.',flush=True)
            return ''
        except Exception as e:
            print(f'[MIC ERROR] Speech recognition pipeline failed: {e}',flush=True)
            self._set_listening_status('SPEECH RECOGNITION ERROR - RETRYING')
            if self.vosk_model:
                try: return self._recognize_vosk_audio(data)
                except Exception as ve: print(f'[VOSK ERROR] {ve}',flush=True)
            return ''

    def _recognize_vosk_audio(self, data):
        if not self.vosk_model or not VOSK_OK:
            return ''
        import numpy as np
        rec=KaldiRecognizer(self.vosk_model,self.sample_rate)
        rec.SetWords(False)
        rec.AcceptWaveform(np.asarray(data,dtype=np.int16).reshape(-1).tobytes())
        text=json.loads(rec.FinalResult()).get('text','').strip()
        if text:
            print(f'[YOU] {text}',flush=True)
        return text

    def _listen_vosk(self):
        if not self.vosk_model or not VOSK_OK or self.sd is None or not self.audio_available: return ''
        try:
            rec=KaldiRecognizer(self.vosk_model,self.sample_rate); rec.SetWords(False)
            def callback(indata,frames,time_info,status):
                try: rec.AcceptWaveform(bytes(indata))
                except Exception: pass
            with self.sd.RawInputStream(samplerate=self.sample_rate,blocksize=4000,dtype='int16',channels=1,device=self.input_device,callback=callback):
                t=time.time()
                while time.time()-t<7: time.sleep(.05)
            text=json.loads(rec.FinalResult()).get('text','').strip()
            if text: print(f'[YOU] {text}',flush=True)
            return text
        except Exception as e: print(f'[VOSK ERROR] {e}',flush=True); return ''

    def listen(self):
        if self.speaking.is_set(): return ''
        if not self.audio_available or not self.listen_lock.acquire(blocking=False): return ''
        try:
            if self.speaking.is_set(): return ''
            text=self._listen_speech_recognition()
            if text:
                self.detect_language_from_text(text)
            return text
        finally: self.listen_lock.release()


# SCREEN / OCR

# ============================================================



class ScreenAgent:

    def __init__(self, hud=None):

        self.hud = hud



    def screenshot(self):

        if not PYAUTO_OK:

            return None

        try:

            return pyautogui.screenshot()

        except Exception:

            return None



    def ocr(self, image=None):

        if not TESSERACT_OK:

            return ""



        try:

            if image is None:

                image = self.screenshot()

            if image is None:

                return ""



            return pytesseract.image_to_string(

                image,

                config="--psm 6"

            )

        except Exception:

            return ""



    def find_text(self, target):

        """

        Find the center of an OCR word/phrase on the current screen.

        Returns (x, y) or None.

        """

        if not TESSERACT_OK or not PYAUTO_OK:

            return None



        try:

            image = self.screenshot()

            if image is None:

                return None



            data = pytesseract.image_to_data(

                image,

                output_type=pytesseract.Output.DICT,

                config="--psm 6"

            )



            target_words = re.findall(

                r"[a-z0-9]+",

                target.lower()

            )



            if not target_words:

                return None



            words = []

            for i, raw in enumerate(data["text"]):

                word = raw.strip().lower()

                if not word:

                    continue

                word = re.sub(r"[^a-z0-9]+", "", word)

                if not word:

                    continue

                words.append({

                    "word": word,

                    "x": data["left"][i],

                    "y": data["top"][i],

                    "w": data["width"][i],

                    "h": data["height"][i]

                })



            # Single-word exact match

            for item in words:

                if item["word"] == target.lower().strip():

                    return (

                        item["x"] + item["w"] // 2,

                        item["y"] + item["h"] // 2

                    )



            # Multi-word consecutive match

            n = len(target_words)

            for i in range(len(words) - n + 1):

                candidate = [w["word"] for w in words[i:i+n]]

                if candidate == target_words:

                    x1 = min(w["x"] for w in words[i:i+n])

                    y1 = min(w["y"] for w in words[i:i+n])

                    x2 = max(w["x"] + w["w"] for w in words[i:i+n])

                    y2 = max(w["y"] + w["h"] for w in words[i:i+n])

                    return ((x1 + x2) // 2, (y1 + y2) // 2)



            # Loose contains match

            needle = " ".join(target_words)

            for i in range(len(words)):

                joined = " ".join(w["word"] for w in words[i:i+n])

                if needle in joined:

                    group = words[i:i+n]

                    x1 = min(w["x"] for w in group)

                    y1 = min(w["y"] for w in group)

                    x2 = max(w["x"] + w["w"] for w in group)

                    y2 = max(w["y"] + w["h"] for w in group)

                    return ((x1 + x2) // 2, (y1 + y2) // 2)



        except Exception:

            return None



        return None





# ============================================================

# LAUNCHER

# ============================================================



class Launcher:

    APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "settings": "start ms-settings:",
        "camera": "start microsoft.windows.camera:",
        "snipping tool": "start snippingtool:",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "firefox": "firefox.exe",
        "vs code": "code.exe",
        "visual studio code": "code.exe",
        "vscode": "code.exe",
    }

    # Extra launch names. These are tried in order if the direct command
    # is not found, making application launching much more reliable.
    APP_ALIASES = {
        "jupyter": [
            [sys.executable, "-m", "jupyter", "notebook"],
            [sys.executable, "-m", "jupyterlab"],
        ],
        "jupyter notebook": [
            [sys.executable, "-m", "jupyter", "notebook"],
        ],
        "jupyter lab": [
            [sys.executable, "-m", "jupyter", "lab"],
        ],
        "chrome": [["chrome.exe"], ["start", "chrome", "https://www.google.com"]],
        "google chrome": [["chrome.exe"]],
        "edge": [["msedge.exe"]],
        "microsoft edge": [["msedge.exe"]],
        "firefox": [["firefox.exe"]],
        "vs code": [["code.exe"]],
        "visual studio code": [["code.exe"]],
        "vscode": [["code.exe"]],
    }

    def _start_executable(self, command):
        try:
            subprocess.Popen(command, shell=False)
            return True
        except Exception:
            return False

    def _start_windows_command(self, command):
        try:
            subprocess.Popen(command, shell=True)
            return True
        except Exception:
            return False



    SITES = {

        "google": "https://www.google.com",

        "youtube": "https://www.youtube.com",

        "gmail": "https://mail.google.com",

        "github": "https://github.com",

        "chatgpt": "https://chatgpt.com",

        "wikipedia": "https://www.wikipedia.org",

        "maps": "https://maps.google.com",

        "whatsapp": "https://web.whatsapp.com",

        "instagram": "https://www.instagram.com",

        "facebook": "https://www.facebook.com",

    }



    def _windows_start(self, target):
        """Reliable Windows launcher for names/paths/URLs."""
        target = str(target).strip().strip('"')
        if not target:
            return False
        try:
            if os.path.exists(target):
                os.startfile(target)
                return True
        except Exception as exc:
            print(f"[LAUNCH] os.startfile failed: {exc}", flush=True)
        # Try PATH resolution first.
        try:
            exe = shutil.which(target)
            if exe:
                subprocess.Popen([exe], shell=False)
                return True
        except Exception as exc:
            print(f"[LAUNCH] PATH launch failed: {exc}", flush=True)
        # Windows shell START.  Use a string because START has special syntax.
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "start", "", target],
                capture_output=True, text=True, timeout=8, shell=False
            )
            if result.returncode == 0:
                return True
            print(f"[LAUNCH] START failed rc={result.returncode} stderr={result.stderr.strip()}", flush=True)
        except Exception as exc:
            print(f"[LAUNCH] cmd START failed: {exc}", flush=True)
        return False

    def _resolve_executable(self, target):
        """Find a real executable for a known app name or a local path."""
        candidate = str(target).strip().strip('"')
        if not candidate:
            return None

        # Direct path or existing executable.
        if os.path.exists(candidate):
            if os.path.isdir(candidate):
                try:
                    os.startfile(candidate)
                    return candidate
                except Exception:
                    pass
            return candidate

        # Normalized variants.
        variants = []
        base = candidate.lower().strip()
        variants.append(candidate)
        variants.append(candidate + ".exe")
        variants.append(base)
        variants.append(base + ".exe")
        variants.append(base.replace(" ", ""))
        variants.append(base.replace(" ", "") + ".exe")
        variants.append(base.replace("-", " "))
        variants.append(base.replace("-", " ") + ".exe")

        seen = set()
        for v in variants:
            if not v or v in seen:
                continue
            seen.add(v)
            resolved = shutil.which(v)
            if resolved:
                return resolved

        if os.name == "nt":
            root_dirs = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local"), "Programs"),
            ]
            for root in root_dirs:
                try:
                    for pattern in (candidate, candidate + ".exe", candidate.replace(" ", ""), candidate.replace(" ", "") + ".exe"):
                        found = glob.glob(os.path.join(root, "**", pattern), recursive=True)
                        if found:
                            return found[0]
                except Exception:
                    pass

        return None

    def open_target(self, target):
        target = target.strip()
        low = target.lower()

        if not target:
            return False, "application"

        # Websites
        if low in self.SITES:
            url = self.SITES[low]
            try:
                if os.name == "nt":
                    subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
                else:
                    webbrowser.open(url)
                print(f"[LAUNCH] website -> {url}", flush=True)
                return True, "website"
            except Exception as exc:
                print(f"[LAUNCH ERROR] website {url}: {exc}", flush=True)
                try:
                    webbrowser.open(url)
                    return True, "website"
                except Exception:
                    return False, "website"

        if re.match(r"^(https?://|www\\.)", low) or re.search(
            r"\\.(com|org|net|in|io|gov|edu)(/.*)?$",
            low
        ):
            url = (
                target
                if re.match(r"^https?://", target, re.I)
                else "https://" + target
            )
            try:
                webbrowser.open(url)
                return True, "website"
            except Exception:
                return False, "website"

        # Direct known applications -- use real executable lookup and Windows START.
        command = self.APPS.get(low)
        if command:
            try:
                if command.startswith("start "):
                    ok = self._windows_start(command[6:].strip())
                else:
                    exe = self._resolve_executable(command) or command
                    subprocess.Popen(exe, shell=False)
                    ok = True
                if ok:
                    print(f"[LAUNCH] application -> {target}", flush=True)
                    return True, "application"
            except Exception as exc:
                print(f"[LAUNCH ERROR] direct {target}: {exc}", flush=True)

        # Special application aliases
        aliases = self.APP_ALIASES.get(low, [])
        for command in aliases:
            try:
                if command == ["start", "chrome", "https://www.google.com"]:
                    if self._start_windows_command(command):
                        print(f"[LAUNCH] alias -> {target}", flush=True)
                        return True, "application"
                elif command and command[0] == sys.executable:
                    if self._start_executable(command):
                        print(f"[LAUNCH] alias -> {target}", flush=True)
                        return True, "application"
                elif command and command[0] in ("chrome.exe", "msedge.exe", "firefox.exe", "code.exe"):
                    exe = self._resolve_executable(command[0]) or command[0]
                    if self._windows_start(exe):
                        print(f"[LAUNCH] alias -> {target}", flush=True)
                        return True, "application"
                elif command and self._start_executable(command):
                    print(f"[LAUNCH] alias -> {target}", flush=True)
                    return True, "application"
            except Exception as exc:
                print(f"[LAUNCH] alias failed {target}: {exc}", flush=True)

        # AppOpener
        if APPOPENER_OK:
            try:
                app_open(target, match_closest=True)
                return True, "application"
            except Exception:
                pass

        # Final Windows START attempt.  Do not report success unless START itself succeeds.
        resolved = self._resolve_executable(target)
        if resolved and os.name == "nt":
            try:
                subprocess.Popen([resolved], shell=False)
                print(f"[LAUNCH] resolved executable -> {resolved}", flush=True)
                return True, "application"
            except Exception:
                pass
        if os.name == "nt" and self._windows_start(target):
            print(f"[LAUNCH] Windows START -> {target}", flush=True)
            return True, "application"
        print(f"[LAUNCH] FAILED -> {target}", flush=True)
        return False, "application"



# ============================================================

# COMPUTER CONTROL

# ============================================================



class ComputerAgent:

    def __init__(self, screen_agent):

        self.screen = screen_agent



    def click(self):

        if PYAUTO_OK:

            pyautogui.click()

            return True

        return False



    def right_click(self):

        if PYAUTO_OK:

            pyautogui.rightClick()

            return True

        return False



    def double_click(self):

        if PYAUTO_OK:

            pyautogui.doubleClick()

            return True

        return False



    def click_text(self, text, right=False, double=False):

        point = self.screen.find_text(text)

        if point is None:

            return False



        if right:

            pyautogui.rightClick(*point)

        elif double:

            pyautogui.doubleClick(*point)

        else:

            pyautogui.click(*point)

        return True



    def type_text(self, text):

        if PYAUTO_OK:

            pyautogui.write(text, interval=0.02)

            return True

        return False



    def press(self, key):

        if PYAUTO_OK:

            pyautogui.press(key)

            return True

        return False



    def hotkey(self, *keys):

        if PYAUTO_OK:

            pyautogui.hotkey(*keys)

            return True

        return False



    def minimize(self):

        if WINDOW_OK:

            try:

                w = gw.getActiveWindow()

                if w:

                    w.minimize()

                    return True

            except Exception:

                pass

        return False



    def maximize(self):

        if WINDOW_OK:

            try:

                w = gw.getActiveWindow()

                if w:

                    w.maximize()

                    return True

            except Exception:

                pass

        return False



    def close(self):

        if WINDOW_OK:

            try:

                w = gw.getActiveWindow()

                if w:

                    w.close()

                    return True

            except Exception:

                pass

        return False



    def switch_window(self):

        return self.hotkey("alt", "tab")

    def switch_window(self):

        return self.hotkey("alt", "f4")



# ============================================================
# FREE WEB RESEARCH + PROCEDURAL 3D MODEL GENERATOR
# ============================================================

def _clean_html_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def web_search_snippets(query, limit=6):
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SHASTRA"})
        with urllib.request.urlopen(req, timeout=2.0) as response:
            page = response.read().decode("utf-8", errors="ignore")
        snippets=[]
        for raw in re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', page, re.S):
            text=_clean_html_text(raw)
            if text and text not in snippets: snippets.append(text[:700])
            if len(snippets)>=limit: break
        return snippets
    except Exception as exc:
        return [f"Web research unavailable: {exc}"]


def research_object(query):
    """Research-first pipeline: collect public web information before any geometry is created."""
    queries = (
        f'"{query}" dimensions design parts features',
    )
    results=[]
    sources=[]
    for q in queries:
        snippets=web_search_snippets(q,3)
        results.extend(snippets)
        sources.append({"query":q,"snippets":snippets})
    unique=[]; seen=set()
    for item in results:
        key=item.lower().strip()
        if key and key not in seen and not key.startswith('web research unavailable'):
            seen.add(key); unique.append(item)
    return unique[:12]


def build_research_profile(query, research):
    """Turn free public-web snippets into conservative geometry hints.
    This never invents manufacturer dimensions when the web did not provide them.
    """
    text=' '.join(research).lower()
    profile={
        'source_count':len(research), 'length':None, 'width':None, 'height':None,
        'wheel_count':4, 'rotor_count':4, 'parts':[], 'features':[]
    }
    # Extract common metric dimensions from snippets. Values are only used as ratios.
    patterns={
        'length':r'(?:length|overall length|l)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)',
        'width':r'(?:width|overall width|w)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)',
        'height':r'(?:height|overall height|h)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)',
    }
    def meters(v,u):
        v=float(v); u=u.lower()
        return v/1000 if u=='mm' else v/100 if u=='cm' else v if u=='m' else v*0.0254 if u in ('in','inch','inches') else v*0.3048
    for key,pat in patterns.items():
        m=re.search(pat,text,re.I)
        if m:
            try: profile[key]=meters(m.group(1),m.group(2))
            except Exception: pass
    wm=re.search(r'\b(\d+)\s*(?:wheels?|tires?)\b',text)
    if wm:
        try: profile['wheel_count']=max(1,min(16,int(wm.group(1))))
        except Exception: pass
    rm=re.search(r'\b(\d+)\s*(?:rotors?|propellers?)\b',text)
    if rm:
        try: profile['rotor_count']=max(1,min(16,int(rm.group(1))))
        except Exception: pass
    keywords=(
        'door','doors','window','windows','wheel','wheels','wing','wings','tail','engine','motor',
        'camera','sensor','arm','arms','leg','legs','antenna','screen','keyboard','handle','seat',
        'roof','hood','trunk','headlight','lights','propeller','rotor','fin','fuselage','cockpit'
    )
    profile['features']=[k for k in keywords if re.search(r'\b'+re.escape(k)+r'\b',text)]
    return profile


def detect_model_kind(request):
    t=request.lower()
    profiles={
        'car':['car','vehicle','sedan','suv','sports car','bmw','tesla','ford','toyota','lamborghini'],
        'robot':['robot','android','humanoid','rover','robotic'],
        'airplane':['airplane','aircraft','jet','plane','boeing','airbus'],
        'drone':['drone','quadcopter','uav','quad copter'],
        'house':['house','home','building','villa','cottage'],
        'phone':['phone','smartphone','iphone','mobile'],
        'laptop':['laptop','notebook computer','notebook'],
        'chair':['chair','office chair','gaming chair'],
        'table':['table','desk','workbench'],
        'tree':['tree','plant'],
        'rocket':['rocket','spaceship','space ship'],
        'watch':['watch','smartwatch','wristwatch'],
    }
    for kind,words in profiles.items():
        if any(w in t for w in words): return kind
    return 'generic'


def _safe_model_name(text):
    return re.sub(r'[^a-zA-Z0-9_-]+','_',text.strip()).strip('_')[:60] or 'shastra_model'


def _append_uv_sphere(v, f, cx, cy, cz, rx, ry, rz, rings=8, segments=16):
    """Fast low/medium-poly sphere used for smooth-looking details."""
    start = len(v) + 1
    for r in range(rings + 1):
        phi = math.pi * r / rings
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(segments):
            a = 2 * math.pi * j / segments
            v.append([cx + rx * sp * math.cos(a), cy + ry * sp * math.sin(a), cz + rz * cp])
    for r in range(rings):
        for j in range(segments):
            nj = (j + 1) % segments
            a = start + r * segments + j
            b = start + r * segments + nj
            c = start + (r + 1) * segments + nj
            d = start + (r + 1) * segments + j
            f.extend([(a,b,c),(a,c,d)])


def _append_box(v, f, cx, cy, cz, sx, sy, sz):
    """Convenience wrapper using half-extents."""
    _append_cube_mesh(v, f, cx, cy, cz, sx, sy, sz)


def _append_torus(v, f, cx, cy, cz, major, minor, axis='y', rings=12, sides=8):
    start = len(v) + 1
    for i in range(rings):
        u = 2 * math.pi * i / rings
        cu, su = math.cos(u), math.sin(u)
        for j in range(sides):
            w = 2 * math.pi * j / sides
            cw, sw = math.cos(w), math.sin(w)
            rr = major + minor * cw
            if axis == 'y':
                v.append([cx + rr * cu, cy + minor * sw, cz + rr * su])
            elif axis == 'x':
                v.append([cx + minor * sw, cy + rr * cu, cz + rr * su])
            else:
                v.append([cx + rr * cu, cy + rr * su, cz + minor * sw])
    for i in range(rings):
        ni = (i + 1) % rings
        for j in range(sides):
            nj = (j + 1) % sides
            a = start + i*sides+j
            b = start + ni*sides+j
            c = start + ni*sides+nj
            d = start + i*sides+nj
            f.extend([(a,b,c),(a,c,d)])


def _write_obj_generic(path,kind='generic',profile=None):
    """Create dependency-free OBJ geometry using the requested object type and research profile."""
    profile=profile or {}
    verts=[]; faces=[]
    def cube(cx,cy,cz,sx,sy,sz):
        b=len(verts)+1
        verts.extend([(cx-sx,cy-sy,cz-sz),(cx+sx,cy-sy,cz-sz),(cx+sx,cy+sy,cz-sz),(cx-sx,cy+sy,cz-sz),(cx-sx,cy-sy,cz+sz),(cx+sx,cy-sy,cz+sz),(cx+sx,cy+sy,cz+sz),(cx-sx,cy+sy,cz+sz)])
        faces.extend([(b,b+1,b+2,b+3),(b+4,b+7,b+6,b+5),(b,b+4,b+5,b+1),(b+1,b+5,b+6,b+2),(b+2,b+6,b+7,b+3),(b+4,b,b+3,b+7)])
    def cyl(cx,cy,cz,r,depth,segments=20,axis='z'):
        a=len(verts)+1
        for z in (-depth/2,depth/2):
            for i in range(segments):
                ang=2*math.pi*i/segments
                if axis=='x': verts.append((cx+z,cy+r*math.cos(ang),cz+r*math.sin(ang)))
                elif axis=='y': verts.append((cx+r*math.cos(ang),cy+z,cz+r*math.sin(ang)))
                else: verts.append((cx+r*math.cos(ang),cy+r*math.sin(ang),cz+z))
        for i in range(segments):
            j=(i+1)%segments; faces.append((a+i,a+j,a+segments+j,a+segments+i))
        faces.append(tuple(a+i for i in range(segments))); faces.append(tuple(a+segments+i for i in reversed(range(segments))))
    # Research-derived aspect ratio. If the web returned dimensions, preserve their proportions.
    L,W,H=profile.get('length'),profile.get('width'),profile.get('height')
    if L and W and H:
        scale=2.5/max(L,W,H); sx,sy,sz=L*scale/2,W*scale/2,H*scale/2
    else:
        sx,sy,sz=2.5,1.0,1.0
    if kind=='car':
        # Detailed but fast automotive silhouette: lower body, cabin, windows,
        # four wheels/tires, rims, lights, grille, mirrors, handles and spoiler.
        body_z = sz * 0.72
        _append_box(verts, faces, 0, 0, body_z, sx, sy, sz*.32)
        _append_box(verts, faces, -sx*.05, 0, sz*1.20, sx*.52, sy*.82, sz*.34)
        # Hood and trunk give the roof/cabin a more realistic stepped profile.
        _append_box(verts, faces, sx*.58, 0, sz*.93, sx*.34, sy*.91, sz*.13)
        _append_box(verts, faces, -sx*.64, 0, sz*.93, sx*.27, sy*.91, sz*.13)
        # Windows: four dark geometry panels, slightly outside each side.
        for side in (-1, 1):
            y = side * (sy*.835)
            _append_box(verts, faces, -sx*.28, y, sz*1.28, sx*.22, .025, sz*.22)
            _append_box(verts, faces,  sx*.25, y, sz*1.28, sx*.22, .025, sz*.22)
            # door seams / handles
            for x in (-sx*.28, sx*.25):
                _append_box(verts, faces, x, y*1.006, sz*.91, sx*.015, .012, sz*.025)
        # Wheels + rims + hubs. Torus gives a tire ring rather than a solid cylinder.
        wheel_x = (-sx*.62, sx*.62)
        wheel_y = (-(sy*1.03), sy*1.03)
        wheel_r = max(sz*.30, min(sx,sy)*.20)
        for x in wheel_x:
            for y in wheel_y:
                _append_torus(verts, faces, x, y, wheel_r, wheel_r*.72, wheel_r*.22, 'y', 16, 8)
                _append_cylinder_mesh(verts, faces, x, y, wheel_r, wheel_r*.58, wheel_r*.20, 'y', 16)
                _append_cylinder_mesh(verts, faces, x, y*1.01, wheel_r, wheel_r*.23, wheel_r*.24, 'y', 12)
        # Headlights / tail lights and front grille.
        for y in (-sy*.58, sy*.58):
            _append_uv_sphere(verts, faces, sx*.91, y, sz*.78, sz*.13, sz*.10, sz*.08, 6, 12)
            _append_box(verts, faces, -sx*.91, y, sz*.78, sz*.10, sz*.08, sz*.07)
        _append_box(verts, faces, sx*1.005, 0, sz*.64, sz*.045, sy*.32, sz*.10)
        # Side mirrors.
        for y in (-sy*.98, sy*.98):
            _append_uv_sphere(verts, faces, sx*.20, y, sz*1.18, sz*.09, sz*.055, sz*.07, 6, 10)
        # Spoiler for sports/super cars.
        if any(k in profile.get('_request','').lower() for k in ('sports','sport','super','racing','race','lamborghini')):
            _append_box(verts, faces, -sx*.86, 0, sz*1.18, sx*.10, sy*.72, sz*.045)
            _append_box(verts, faces, -sx*.86, -sy*.58, sz*1.02, sx*.045, sy*.045, sz*.18)
            _append_box(verts, faces, -sx*.86, sy*.58, sz*1.02, sx*.045, sy*.045, sz*.18)
        # Exhaust tips.
        for y in (-sy*.38, sy*.38):
            _append_cylinder_mesh(verts, faces, -sx*1.01, y, sz*.55, sz*.075, sz*.12, 'x', 12)
    elif kind=='robot':
        cube(0,0,sz, sx*.35,sy*.55,sz*.65); cube(0,0,sz*2.0,sx*.28,sy*.45,sz*.28)
        for x in (-sx*.55,sx*.55): cube(x,0,sz, sx*.12,sy*.30,sz*.5); cube(x,0,sz*.2,sx*.15,sy*.35,sz*.12)
        if 'antenna' in profile.get('features',[]): cyl(0,0,sz*2.55,sz*.05,sz*.45,16,'z')
    elif kind=='airplane':
        cube(0,0,sz*.7,sx,sy*.28,sz*.28); cube(0,0,sz*.72,sx*.25,sy*1.8,sz*.08); cube(-sx*.65,0,sz*1.2,sx*.2,sy*.7,sz*.08)
        if 'engine' in profile.get('features',[]):
            for y in (-sy*.65,sy*.65): cyl(sx*.1,y,sz*.55,sz*.16,sz*.55,20,'x')
    elif kind=='drone':
        cube(0,0,sz*.8,sx*.3,sy*.3,sz*.08)
        count=profile.get('rotor_count',4); count=4 if count<4 else min(count,8)
        pts=[(-1,-1),(1,-1),(-1,1),(1,1),(-2,0),(2,0),(0,-2),(0,2)][:count]
        for px,py in pts:
            x=px*sx*.65; y=py*sy*.65; cube(x,y,sz*.8,sx*.28,sy*.04,sz*.04); cyl(x,y,sz,sz*.12,sz*.04,20,'z')
    elif kind=='house':
        cube(0,0,sz*.65,sx,sy,sz*.65); cube(0,0,sz*1.7,sx*1.05,sy*1.05,sz*.08); cube(0,-sy*1.02,sz*.55,sx*.18,.04,sz*.5)
        if 'window' in profile.get('features',[]):
            for x in (-sx*.45,sx*.45): cube(x,-sy*1.03,sz*.9,sx*.16,.03,sz*.16)
    elif kind=='phone':
        cube(0,0,0,sx*.55,sy*.10,sz); cube(0,-sy*.12,0,sx*.43,.03,sz*.78)
    elif kind=='laptop':
        cube(0,0,0,sx*.9,sy*.65,sz*.06); cube(0,sy*.58,sz*.55,sx*.9,.05,sz*.5)
    elif kind=='chair':
        cube(0,0,sz*.8,sx*.4,.08,sz*.7); cube(0,0,sz*.18,sx*.4,sy*.35,.08)
        for x in (-sx*.3,sx*.3):
            for y in (-sy*.3,sy*.3): cyl(x,y,-sz*.25,.08,sz*.7,12,'z')
    elif kind=='table':
        cube(0,0,sz,sx,sy,.08)
        for x in (-sx*.75,sx*.75):
            for y in (-sy*.7,sy*.7): cyl(x,y,0,.10,sz*2,12,'z')
    elif kind=='tree':
        cyl(0,0,sz*.7,.25,sz*1.4,20,'z'); cyl(0,0,sz*1.8,sx*.5,sz*.9,24,'z')
    elif kind=='rocket':
        cyl(0,0,sz,sx*.28,sz*2.2,24,'z'); cyl(0,0,sz*2.2,sx*.3,sz*.45,24,'z')
        for x in (-sx*.35,sx*.35): cube(x,0,sz*.5,.08,sy*.25,sz*.35)
    elif kind=='watch':
        cyl(0,0,0,sx*.35,sz*.15,32,'z'); cube(0,0,-sz*.35,sx*.14,sy*.6,.05); cube(0,0,sz*.35,sx*.14,sy*.6,.05)
    else:
        cube(0,0,sz*.5,sx*.6,sy*.6,sz*.5); cyl(0,0,sz*1.2,min(sx,sy)*.35,sz*.45,24,'z')
    with open(path,'w',encoding='utf-8') as f:
        f.write('# SHASTRA FREE RESEARCH-DRIVEN 3D MODEL\n')
        for vx,vy,vz in verts: f.write('v %.5f %.5f %.5f\n'%(vx,vy,vz))
        for face in faces: f.write('f '+' '.join(map(str,face))+'\n')


def find_blender():
    """Return a local Blender executable when installed; never downloads anything."""
    candidates = [
        shutil.which("blender"),
        r"C:\Program Files\Blender Foundation\Blender\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None



def search_reference_image(query, out_dir):
    """Find and download one public web image as a visual reference for the requested model."""
    os.makedirs(out_dir, exist_ok=True)
    try:
        q = urllib.parse.quote_plus(query + " 3d model reference")
        url = "https://www.bing.com/images/search?q=" + q
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SHASTRA"})
        with urllib.request.urlopen(req, timeout=8) as response:
            html_text = response.read().decode("utf-8", errors="ignore")
        urls=[]
        for m in re.finditer(r'"murl"\s*:\s*"(.*?)"', html_text):
            u=m.group(1).replace('\\/','/')
            if u.startswith(('http://','https://')) and u not in urls:
                urls.append(u)
            if len(urls)>=12: break
        for idx,u in enumerate(urls):
            try:
                req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0 SHASTRA"})
                with urllib.request.urlopen(req,timeout=6) as r:
                    data=r.read(4_000_000)
                ext='.jpg'
                ctype=(r.headers.get('Content-Type') or '').lower()
                if 'png' in ctype: ext='.png'
                elif 'webp' in ctype: ext='.webp'
                path=os.path.join(out_dir,'reference'+ext)
                with open(path,'wb') as f: f.write(data)
                if os.path.getsize(path)>1500:
                    return path,u
            except Exception:
                continue
    except Exception as exc:
        return None, str(exc)
    return None, "No downloadable public image found"


def _image_to_relief_obj(image_path, obj_path, max_size=72):
    """Create a fast image-derived 3D relief mesh from any dropped image."""
    if Image is None:
        raise RuntimeError("Pillow is required for image-to-3D mode.")
    im=Image.open(image_path).convert('L')
    w,h=im.size
    scale=max(w,h)/float(max_size)
    nw=max(8,min(max_size,int(w/scale)))
    nh=max(8,min(max_size,int(h/scale)))
    im=im.resize((nw,nh))
    px=list(im.getdata())
    verts=[]; faces=[]
    zmin=-0.12; zmax=0.85
    for y in range(nh):
        for x in range(nw):
            val=px[y*nw+x]/255.0
            xx=(x/(nw-1)-0.5)*5.0
            yy=(0.5-y/(nh-1))*5.0*(nh/max(nw,1))
            zz=zmin+(val**1.35)*(zmax-zmin)
            verts.append((xx,yy,zz))
    for y in range(nh-1):
        for x in range(nw-1):
            a=y*nw+x; b=a+1; c=a+nw+1; d=a+nw
            faces.extend([(a+1,b+1,c+1),(a+1,c+1,d+1)])
    # Solid base underneath the relief for a printable-looking object.
    base_start=len(verts)
    for y in range(nh):
        for x in range(nw):
            xx=(x/(nw-1)-0.5)*5.0
            yy=(0.5-y/(nh-1))*5.0*(nh/max(nw,1))
            verts.append((xx,yy,zmin-0.18))
    for y in range(nh-1):
        for x in range(nw-1):
            a=base_start+y*nw+x; b=a+1; c=a+nw+1; d=a+nw
            faces.extend([(a+1,d+1,c+1),(a+1,c+1,b+1)])
    with open(obj_path,'w',encoding='utf-8') as f:
        f.write('# SHASTRA image-derived 3D relief\n')
        for v in verts: f.write('v %.6f %.6f %.6f\n'%v)
        for face in faces: f.write('f '+' '.join(map(str,face))+'\n')
    return nw,nh,len(verts),len(faces)


def generate_3d_from_image(image_path):
    """Turn a user-provided image into a 3D relief OBJ and preview it."""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)
    name=_safe_model_name(os.path.splitext(os.path.basename(image_path))[0]) + '_image3d'
    folder=os.path.join(MODEL_OUTPUT_DIR,name+'_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(folder,exist_ok=True)
    ref=os.path.join(folder,os.path.basename(image_path))
    if os.path.abspath(image_path)!=os.path.abspath(ref):
        try: shutil.copy2(image_path,ref)
        except Exception: ref=image_path
    obj_path=os.path.join(folder,name+'.obj')
    nw,nh,nv,nf=_image_to_relief_obj(ref,obj_path)
    with open(os.path.join(folder,'image_to_3d.txt'),'w',encoding='utf-8') as f:
        f.write('SHASTRA IMAGE-TO-3D MODE\n')
        f.write('SOURCE IMAGE: '+ref+'\n')
        f.write(f'GRID: {nw} x {nh}\nVERTICES: {nv}\nFACES: {nf}\n')
        f.write('METHOD: grayscale height-map relief extrusion\n')
    return folder,obj_path,ref,nv,nf


def generate_3d_model(request):
    """Strict research-first model pipeline.
    1) Search public web information.
    2) Build a research profile.
    3) Generate geometry from the requested object + researched facts.
    4) Save the research alongside the model for traceability.
    """
    model_name=_safe_model_name(request)
    folder=os.path.join(MODEL_OUTPUT_DIR,model_name+'_'+datetime.now().strftime('%Y%m%d_%H%M%S')); os.makedirs(folder,exist_ok=True)
    kind=detect_model_kind(request)
    # 3D Maker always performs a lightweight web research pass and downloads
    # one public reference image. Geometry is still generated locally so it is fast.
    research = research_object(request)
    if not research:
        research = ["No web snippets returned; used SHASTRA local geometry profile."]
    reference_path, reference_url = search_reference_image(request, folder)
    if reference_path:
        research.append("Reference image: " + reference_url)
    profile=build_research_profile(request,research)
    profile['_request'] = request
    research_file=os.path.join(folder,'web_research.txt')
    with open(research_file,'w',encoding='utf-8') as f:
        f.write('SHASTRA FAST + ACCURATE PROCEDURAL 3D MODEL\n\nREQUEST: '+request+'\nOBJECT TYPE: '+kind+'\n\nRESEARCHED FACTS / SNIPPETS:\n')
        for i,item in enumerate(research,1): f.write(f'[{i}] {item}\n\n')
        f.write('\nDERIVED GEOMETRY PROFILE:\n'+json.dumps(profile,indent=2))
    obj_path=os.path.join(folder,model_name+'.obj'); blend_path=os.path.join(folder,model_name+'.blend'); script_path=os.path.join(folder,'build_model.py')
    blender=find_blender()
    # Blender path remains free, but the dependency-free OBJ always uses the researched profile.
    _write_obj_generic(obj_path,kind,profile)
    if blender:
        # Do NOT regenerate a second hard-coded model in Blender. Import the
        # research-driven OBJ we just created, then save the same geometry as .blend.
        import_script = f'''import bpy\nOBJ={obj_path!r}\nBLEND={blend_path!r}\nbpy.ops.object.select_all(action=\"SELECT\")\nbpy.ops.object.delete(use_global=False)\ntry:\n    bpy.ops.wm.obj_import(filepath=OBJ)\nexcept Exception:\n    bpy.ops.import_scene.obj(filepath=OBJ)\nbpy.ops.wm.save_as_mainfile(filepath=BLEND)\nprint(\"SHASTRA_RESEARCH_MODEL_IMPORTED\")\n'''
        try:
            with open(script_path,'w',encoding='utf-8') as sf: sf.write(import_script)
            proc=subprocess.run([blender,'-b','--python',script_path],capture_output=True,text=True,timeout=180)
            if proc.returncode==0 and os.path.exists(blend_path):
                return True,folder,research,'BLENDER_RESEARCH_DRIVEN',proc.stdout[-1200:]
        except Exception:
            pass
    return True,folder,research,'OBJ_RESEARCH_DRIVEN',json.dumps(profile)

def _model_file_candidates(root_dirs=None):
    """Find locally saved free 3D files. No paid service or external API is used."""
    roots = root_dirs or MODEL_SEARCH_DIRS
    found=[]
    seen=set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        try:
            for base, dirs, files in os.walk(root):
                # Keep scanning reasonably fast and avoid hidden/system folders.
                dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in {"node_modules", "__pycache__"}]
                for name in files:
                    ext=os.path.splitext(name)[1].lower()
                    if ext in MODEL_EXTENSIONS:
                        path=os.path.abspath(os.path.join(base,name))
                        if path not in seen:
                            seen.add(path); found.append(path)
        except Exception:
            continue
    return sorted(found, key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)


def find_saved_3d_model(query=""):
    """Resolve a user's saved model by path, filename, or latest model."""
    q=(query or "").strip().strip('"')
    if q:
        expanded=os.path.abspath(os.path.expandvars(os.path.expanduser(q)))
        if os.path.isfile(expanded) and os.path.splitext(expanded)[1].lower() in MODEL_EXTENSIONS:
            return expanded
    files=_model_file_candidates()
    if not files:
        return None
    if q:
        qlow=q.lower()
        scored=[]
        for path in files:
            name=os.path.basename(path).lower()
            stem=os.path.splitext(name)[0]
            score=(100 if qlow in name else 0)+(60 if qlow in stem else 0)
            score += sum(1 for token in re.findall(r"[a-z0-9]+", qlow) if token in stem)
            scored.append((score,path))
        scored.sort(key=lambda x:(x[0], os.path.getmtime(x[1])), reverse=True)
        if scored and scored[0][0] > 0:
            return scored[0][1]
    return files[0]


def _load_obj_wireframe(path):
    verts=[]; faces=[]
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        for line in f:
            line=line.strip()
            if line.startswith("v "):
                parts=line.split()
                if len(parts)>=4:
                    try: verts.append((float(parts[1]),float(parts[2]),float(parts[3])))
                    except ValueError: pass
            elif line.startswith("f "):
                idx=[]
                for token in line.split()[1:]:
                    try: idx.append(int(token.split('/')[0]))
                    except ValueError: pass
                if len(idx)>=3:
                    # OBJ face indices are 1-based; the Tk renderer uses 0-based Python indices.
                    idx=[i-1 if i>0 else len(verts)+i for i in idx]
                    # Convert polygons to triangles for stable mesh rendering.
                    for i in range(1,len(idx)-1):
                        faces.append((idx[0],idx[i],idx[i+1]))
    return verts,faces


def _load_ascii_stl(path):
    verts=[]; faces=[]; index={}
    def get(v):
        key=tuple(round(x,6) for x in v)
        if key not in index: index[key]=len(verts); verts.append(key)
        return index[key]
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        tri=[]
        for line in f:
            if line.strip().lower().startswith("vertex "):
                p=line.split()
                if len(p)>=4:
                    try: tri.append((float(p[1]),float(p[2]),float(p[3])))
                    except ValueError: pass
                    if len(tri)==3:
                        faces.append(tuple(get(v) for v in tri)); tri=[]
    return verts,faces


def _load_binary_or_ascii_stl(path):
    # First try ASCII; if it has no triangles, parse standard binary STL.
    try:
        verts,faces=_load_ascii_stl(path)
        if faces: return verts,faces
    except Exception: pass
    import struct
    verts=[]; faces=[]; index={}
    with open(path,"rb") as f:
        data=f.read()
    if len(data)<84: return [],[]
    try: count=struct.unpack_from("<I",data,80)[0]
    except Exception: return [],[]
    def get(v):
        key=tuple(round(x,6) for x in v)
        if key not in index: index[key]=len(verts); verts.append(key)
        return index[key]
    offset=84
    for _ in range(min(count,(len(data)-84)//50)):
        if offset+50>len(data): break
        vals=struct.unpack_from("<12f",data,offset)
        tri=[vals[3:6],vals[6:9],vals[9:12]]
        faces.append(tuple(get(v) for v in tri)); offset+=50
    return verts,faces


def _load_ply(path):
    verts=[]; faces=[]
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        header=[]; line=f.readline()
        if line.strip()!="ply": return [],[]
        vertex_count=face_count=0; ascii_mode=False
        while True:
            line=f.readline()
            if not line: return [],[]
            t=line.strip(); header.append(t)
            if t.startswith("format ascii"): ascii_mode=True
            if t.startswith("element vertex "): vertex_count=int(t.split()[-1])
            if t.startswith("element face "): face_count=int(t.split()[-1])
            if t=="end_header": break
        if not ascii_mode: return [],[]
        for _ in range(vertex_count):
            p=f.readline().split()
            if len(p)>=3:
                try: verts.append((float(p[0]),float(p[1]),float(p[2])))
                except ValueError: verts.append((0,0,0))
        for _ in range(face_count):
            p=f.readline().split()
            try:
                n=int(p[0]); ids=[int(x) for x in p[1:n+1]]
                for i in range(1,len(ids)-1): faces.append((ids[0],ids[i],ids[i+1]))
            except Exception: pass
    return verts,faces


def load_3d_wireframe(path):
    ext=os.path.splitext(path)[1].lower()
    if ext==".obj": return _load_obj_wireframe(path)
    if ext==".stl": return _load_binary_or_ascii_stl(path)
    if ext==".ply": return _load_ply(path)
    return [],[]

# NATURAL LANGUAGE COMMAND ROUTER

# ============================================================



class DeviceNetwork:
    """Secure same-ID/password LAN discovery and bidirectional command link."""
    DISCOVERY_PORT = 39271
    API_PORT = 39272
    MAGIC = "SHASTRA_DISCOVERY_V1"

    def __init__(self, user_id, password, hud=None):
        self.user_id = user_id.strip()
        self.secret = hashlib.sha256((self.user_id + "\0" + password).encode()).digest()
        self.hud = hud
        self.device_id = str(uuid.uuid4())
        self.device_name = platform.node() or "SHASTRA DEVICE"
        self.devices = {}
        self.sessions = {}
        self.lock = threading.RLock()
        self.running = False
        self.http = None
        self.preferred_peer = None
        self.score = self.hardware_score()

    @staticmethod
    def ram_gb():
        try:
            class M(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = M(); m.dwLength = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullTotalPhys / (1024**3), 1)
        except Exception:
            return 0.0

    def hardware_score(self):
        cores = os.cpu_count() or 1
        ram = self.ram_gb()
        gpu = 0
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "(Get-CimInstance Win32_VideoController | Measure-Object).Count"],
                               capture_output=True, text=True, timeout=2,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            gpu = min(int(r.stdout.strip() or "0"), 4)
        except Exception:
            pass
        return round(cores*10 + ram*4 + gpu*35, 1)

    def info(self):
        return {"id": self.device_id, "name": self.device_name, "user_id": self.user_id,
                "score": self.score, "cores": os.cpu_count() or 1, "ram_gb": self.ram_gb(),
                "port": self.API_PORT}

    def _proof(self, nonce):
        return hmac.new(self.secret, f"{self.user_id}|{nonce}".encode(), hashlib.sha256).hexdigest()

    def start(self):
        if self.running: return
        self.running = True
        net = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): return
            def send_json(self, code, obj):
                raw = json.dumps(obj).encode(); self.send_response(code)
                self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
            def body(self):
                n = int(self.headers.get("Content-Length", "0")); return json.loads(self.rfile.read(n).decode())
            def do_GET(self):
                if self.path == "/shastra/info": self.send_json(200, net.info())
                else: self.send_json(404, {"ok":False})
            def do_POST(self):
                try: data = self.body()
                except Exception: self.send_json(400, {"ok":False}); return
                if self.path == "/shastra/handshake":
                    nonce = str(data.get("nonce", ""))
                    good = data.get("user_id") == net.user_id and hmac.compare_digest(str(data.get("proof", "")), net._proof(nonce))
                    if not good: self.send_json(401, {"ok":False, "error":"authentication failed"}); return
                    token = uuid.uuid4().hex
                    with net.lock: net.sessions[token] = time.time() + 3600
                    self.send_json(200, {"ok":True, "token":token, "device":net.info()}); return
                if self.path == "/shastra/execute":
                    token = str(data.get("token", ""))
                    with net.lock: valid = net.sessions.get(token, 0) > time.time()
                    command = str(data.get("command", "")).strip()
                    if not valid or not command or len(command) > 1000:
                        self.send_json(401, {"ok":False, "error":"unauthorized or invalid command"}); return
                    threading.Thread(target=net.remote_command_callback, args=(command,), daemon=True).start()
                    self.send_json(200, {"ok":True, "accepted":True}); return
                self.send_json(404, {"ok":False})
        try:
            self.http = ThreadingHTTPServer(("0.0.0.0", self.API_PORT), Handler)
            threading.Thread(target=self.http.serve_forever, daemon=True).start()
            threading.Thread(target=self._listen, daemon=True).start()
            threading.Thread(target=self._broadcast, daemon=True).start()
            if self.hud: self.hud.log_event("MULTI-DEVICE CORE: ONLINE")
        except Exception as e:
            if self.hud: self.hud.log_event("MULTI-DEVICE ERROR: " + str(e))

    def stop(self):
        self.running = False
        try: self.http.shutdown(); self.http.server_close()
        except Exception: pass

    def _broadcast(self):
        while self.running:
            try:
                data = json.dumps({"magic":self.MAGIC, **self.info()}).encode()
                sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
                sock.sendto(data,("255.255.255.255",self.DISCOVERY_PORT)); sock.close()
            except Exception: pass
            time.sleep(2)

    def _listen(self):
        try:
            sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(("0.0.0.0",self.DISCOVERY_PORT)); sock.settimeout(1)
        except Exception as e:
            if self.hud: self.hud.log_event("DISCOVERY ERROR: " + str(e))
            return
        while self.running:
            try:
                raw, addr=sock.recvfrom(8192); d=json.loads(raw.decode())
                if d.get("magic") != self.MAGIC or d.get("id") == self.device_id or d.get("user_id") != self.user_id: continue
                d["ip"]=addr[0]; d["last_seen"]=time.time()
                with self.lock: self.devices[d["id"]]=d
                self._select_powerful()
            except socket.timeout: pass
            except Exception: pass
        sock.close()

    def snapshot(self):
        with self.lock:
            now=time.time(); out=[d.copy() for d in self.devices.values() if now-d.get("last_seen",0)<8]
        out.sort(key=lambda d: float(d.get("score",0)), reverse=True); return out

    def _select_powerful(self):
        d=self.snapshot(); self.preferred_peer=d[0]["id"] if d else None

    def strongest(self):
        d=self.snapshot(); return d[0] if d else None

    def connect(self, device_id=None):
        d=self.snapshot(); target=next((x for x in d if x["id"]==device_id),None) if device_id else self.strongest()
        if not target: return False, "No other SHASTRA device found on this network."
        nonce=uuid.uuid4().hex; url=f"http://{target['ip']}:{target.get('port',self.API_PORT)}/shastra/handshake"
        try:
            body=json.dumps({"user_id":self.user_id,"nonce":nonce,"proof":self._proof(nonce)}).encode()
            req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=4) as r: result=json.loads(r.read().decode())
            if not result.get("ok"): return False,"Authentication failed."
            with self.lock: self.devices[target["id"]]["token"]=result["token"]
            self.preferred_peer=target["id"]; return True,f"Connected to {target['name']}."
        except Exception as e: return False,f"Connection failed: {e}"

    def send_command(self, command, device_id=None):
        d=self.snapshot(); target=next((x for x in d if x["id"]==device_id),None) if device_id else None
        if target is None and self.preferred_peer: target=next((x for x in d if x["id"]==self.preferred_peer),None)
        if target is None: target=self.strongest()
        if not target: return False,"No linked SHASTRA device is online."
        if not target.get("token"):
            ok,msg=self.connect(target["id"]);
            if not ok: return False,msg
            target=next((x for x in self.snapshot() if x["id"]==target["id"]),target)
        try:
            url=f"http://{target['ip']}:{target.get('port',self.API_PORT)}/shastra/execute"
            body=json.dumps({"token":target["token"],"command":command}).encode()
            req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=4) as r: result=json.loads(r.read().decode())
            return (True,f"Command sent to {target['name']}.") if result.get("ok") else (False,result.get("error","Remote command rejected."))
        except Exception as e: return False,f"Remote command failed: {e}"

    def remote_command_callback(self, command):
        if self.hud: self.hud.log_event("REMOTE COMMAND: " + command)
        if self.hud and getattr(self.hud, "engine", None): self.hud.engine.submit_command(command)


# ============================================================
# FREE CURRENT-MESH 3D EDITOR
# ============================================================
def _read_obj_mesh(path):
    verts=[]; faces=[]
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        for line in f:
            p=line.strip().split()
            if not p: continue
            if p[0]=="v" and len(p)>=4:
                try: verts.append([float(p[1]),float(p[2]),float(p[3])])
                except: pass
            elif p[0]=="f" and len(p)>=4:
                ids=[]
                for q in p[1:]:
                    try: ids.append(int(q.split('/')[0]))
                    except: pass
                for i in range(1,len(ids)-1): faces.append((ids[0],ids[i],ids[i+1]))
    return verts,faces

def _append_cube_mesh(v,f,cx,cy,cz,sx,sy,sz):
    b=len(v)+1; v.extend([[cx-sx,cy-sy,cz-sz],[cx+sx,cy-sy,cz-sz],[cx+sx,cy+sy,cz-sz],[cx-sx,cy+sy,cz-sz],[cx-sx,cy-sy,cz+sz],[cx+sx,cy-sy,cz+sz],[cx+sx,cy+sy,cz+sz],[cx-sx,cy+sy,cz+sz]])
    f.extend([(b,b+1,b+2),(b,b+2,b+3),(b+4,b+7,b+6),(b+4,b+6,b+5),(b,b+4,b+5),(b,b+5,b+1),(b+1,b+5,b+6),(b+1,b+6,b+2),(b+2,b+6,b+7),(b+2,b+7,b+3),(b+4,b,b+3),(b+4,b+3,b+7)])

def _append_cylinder_mesh(v,f,cx,cy,cz,r,d,axis="z",n=20):
    b=len(v)+1
    for z in (-d/2,d/2):
        for i in range(n):
            a=2*math.pi*i/n
            if axis=="y": v.append([cx+r*math.cos(a),cy+z,cz+r*math.sin(a)])
            else: v.append([cx+r*math.cos(a),cy+r*math.sin(a),cz+z])
    for i in range(n):
        j=(i+1)%n; f.extend([(b+i,b+j,b+n+j),(b+i,b+n+j,b+n+i)])

def _save_obj_mesh(path,v,f):
    with open(path,"w",encoding="utf-8") as out:
        out.write("# SHASTRA MODIFIED MODEL\n")
        for x,y,z in v: out.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for a,b,c in f: out.write(f"f {a} {b} {c}\n")

def modify_current_3d_model(path,command):
    v,f=_read_obj_mesh(path)
    if not v: return False,"The current OBJ model cannot be edited."
    c=command.lower(); xs=[x[0] for x in v]; ys=[x[1] for x in v]; zs=[x[2] for x in v]
    cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2; sx=max(xs)-min(xs); sy=max(ys)-min(ys); sz=max(zs)-min(zs)
    desc=""
    if any(k in c for k in ("bigger","larger","increase size","enlarge","scale up")):
        for x in v: x[0]=cx+(x[0]-cx)*1.2; x[1]=cy+(x[1]-cy)*1.2; x[2]=cz+(x[2]-cz)*1.2
        desc="scaled larger"
    elif any(k in c for k in ("smaller","shrink","decrease size","scale down")):
        for x in v: x[0]=cx+(x[0]-cx)*.8; x[1]=cy+(x[1]-cy)*.8; x[2]=cz+(x[2]-cz)*.8
        desc="scaled smaller"
    elif "rotate" in c:
        a=math.radians(-20 if "left" in c else 20); ca,sa=math.cos(a),math.sin(a)
        for x in v: dx=x[0]-cx; dy=x[1]-cy; x[0]=cx+dx*ca-dy*sa; x[1]=cy+dx*sa+dy*ca
        desc="rotated"
    elif "move" in c or "shift" in c:
        dx=(-.35 if "left" in c else .35 if "right" in c else 0); dy=(.35 if "forward" in c else -.35 if "back" in c else 0); dz=(.35 if "up" in c else -.35 if "down" in c else 0)
        for x in v: x[0]+=dx; x[1]+=dy; x[2]+=dz
        desc="moved"
    elif "add" in c and "wheel" in c:
        r=max(.12,sx*.08)
        for x in (min(xs)+r,max(xs)-r):
            for y in (min(ys)-r,max(ys)+r): _append_cylinder_mesh(v,f,x,y,min(zs)+r,r,r*.6,"y",24)
        desc="added four wheels"
    elif "add" in c and "arm" in c:
        _append_cube_mesh(v,f,cx-sx*.7,cy,cz,sx*.08,sy*.12,sz*.25); _append_cube_mesh(v,f,cx+sx*.7,cy,cz,sx*.08,sy*.12,sz*.25); desc="added two arms"
    elif "add" in c and "wing" in c:
        _append_cube_mesh(v,f,cx,cy-sy*.8,cz,sx*.45,sy*.18,.08); _append_cube_mesh(v,f,cx,cy+sy*.8,cz,sx*.45,sy*.18,.08); desc="added two wings"
    elif "add" in c and "antenna" in c:
        _append_cylinder_mesh(v,f,cx,cy,max(zs)+.4,.06,.8,"z",12); desc="added an antenna"
    elif "add" in c and "roof" in c:
        _append_cube_mesh(v,f,cx,cy,cz+sz*.55,sx*.42,sy*.42,.08); desc="added a roof"
    elif "add" in c and "cube" in c:
        _append_cube_mesh(v,f,cx,cy,cz+sz*.4,sx*.15,sy*.15,sz*.15); desc="added a cube"
    elif "add" in c and "cylinder" in c:
        _append_cylinder_mesh(v,f,cx,cy,max(zs)+.3,max(.08,sx*.12),max(.2,sz*.4)); desc="added a cylinder"
    else:
        return False,"Tell me what to change, for example: make it bigger, rotate left, move up, add wheels, add arms, add wings, add antenna, add roof."
    try: shutil.copy2(path,path+".bak")
    except: pass
    _save_obj_mesh(path,v,f); return True,desc

class CommandRouter:

    KEY_MAP = {

        "enter": "enter",

        "return": "enter",

        "backspace": "backspace",

        "delete": "delete",

        "tab": "tab",

        "escape": "esc",

        "esc": "esc",

        "space": "space",

        "up": "up",

        "down": "down",

        "left": "left",

        "right": "right",

        "home": "home",

        "end": "end",

        "page up": "pageup",

        "page down": "pagedown",

    }

    MARATHI_REPLACEMENTS = [
        ("गुगल", "google"),
        ("क्रोम", "chrome"),
        ("क्रॉम", "chrome"),
        ("च्रॉम", "chrome"),
        ("chromogad", "chrome"),
        ("चोम", "chrome"),
        ("यूट्यूब", "youtube"),
        ("नोटपॅड", "notepad"),
        ("नोटपड", "notepad"),
        ("व्हीएस कोड", "vs code"),
        ("व्हिज्युअल स्टुडिओ कोड", "visual studio code"),
        ("क्लिक", "click"),
        ("लिखा", "type"),
        ("टाइप", "type"),
        ("उघडा", "open"),
        ("उघड", "open"),
        ("उघडून", "open"),
        ("सुरू", "start"),
        ("सुरू करा", "start"),
        ("शोध", "search"),
        ("शोधा", "search"),
        ("बंद करा", "close"),
        ("बंद", "close"),
        ("मराठी", "marathi"),
        ("इंग्रजी", "english"),
        ("मदत", "help"),
        ("ठीक आहे", "ok"),
        ("नमस्कार", "hello"),
        ("३d", "3d"),
        ("थ्री डी", "3d"),
    ]

    def normalize(self, text):

        text = str(text or "").lower().strip()
        text = text.replace("’", "'")
        text = re.sub(r"[^a-z0-9\u0900-\u097F:/._ -]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        for prefix in (
            "hey shastra ",
            "shastra ",
            "please ",
            "could you ",
            "can you ",
            "would you ",
        ):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # Marathi commands are translated to English before the router parses them.
        if re.search(r"[\u0900-\u097F]", text):
            normalized = text
            for marathi, english in self.MARATHI_REPLACEMENTS:
                normalized = re.sub(r"\b" + re.escape(marathi) + r"\b", english, normalized)
            text = normalized

        # Common speech-recognition variants. These are intentionally limited
        # to command/application words so normal questions are not rewritten.
        replacements = {
            "you tube": "youtube",
            "you-tube": "youtube",
            "google tube": "youtube",
            "chrom": "chrome",
            "crome": "chrome",
            "google chrom": "google chrome",
            "vs code": "vs code",
            "visual studio code": "visual studio code",
            "three d": "3d",
            "3 d": "3d",
            "three dimensional": "3d",
            "chrome gad": "chrome",
            "chrome gadd": "chrome",
            "chromogad": "chrome",
            "google chromogad": "google chrome",
        }
        for a, b in replacements.items():
            text = re.sub(r"\b" + re.escape(a) + r"\b", b, text)

        # Speech recognition often adds a small trailing phrase to activation
        # commands. Normalize those variants to one canonical command.
        text = re.sub(r"\b(is|please)\s+(activate|activated|active)\b", "activate", text)
        text = re.sub(r"\b(is|please)\s+(deactivate|deactivated|inactive|off)\b", "deactivate", text)
        return text



    def parse(self, raw):

        text = self.normalize(raw)



        # Learned exact command is checked outside this class.



        # 3D model generation
        if re.match(r"^(make|create|generate|build)\s+.+\b(3d|three[- ]?d)\b.*", text):
            return "generate_3d", text

        # Natural application wording: "open the application chrome", etc.
        text = re.sub(r"^(open|launch|start|run)\s+(?:the\s+)?(?:application|app)\s+(.+)$", r"\1 \2", text)
        text = re.sub(r"^(open|launch|start|run)\s+(?:the\s+)?browser\s+(.+)$", r"\1 \2", text)

        # Support target-first speech patterns such as "chrome open" and "youtube start".
        if not text.startswith(("open ", "launch ", "start ", "run ")):
            m = re.match(r"^(?P<target>[a-z0-9\u0900-\u097F ._:-]+?)\s+(?:open|launch|start|run|go to)$", text)
            if m:
                return "open", m.group("target").strip()

        # Explicit open / launch / start commands.
        m = re.match(
            r"^(open|launch|start|run)\s+(.+)$",
            text,
        )
        if m:
            return "open", m.group(2).strip()

        # Bare application names should also open directly.
        bare_apps = {
            "chrome", "google chrome", "youtube", "notepad", "calculator",
            "paint", "vs code", "visual studio code", "cmd", "command prompt",
            "powershell", "file explorer", "explorer", "google", "gmail",
            "github", "wikipedia", "maps", "whatsapp", "instagram", "facebook",
        }
        if text in bare_apps:
            return "open", text



        # Close an application/window

        if re.match(r"^(close|exit)\s+(this|the)?\s*(window|app|application)$", text):

            return "close", ""



        # Minimize / maximize / switch

        if text in ("minimize", "minimize window", "minimize this window"):

            return "minimize", ""

        if text in ("maximize", "maximize window", "maximize this window"):

            return "maximize", ""

        if text in ("switch window", "switch windows", "next window"):

            return "switch", ""



        # Mouse at current cursor

        if text in ("click", "left click", "left-click"):

            return "click", ""

        if text in ("right click", "right-click"):

            return "right_click", ""

        if text in ("double click", "double-click"):

            return "double_click", ""



        # OCR-targeted mouse

        m = re.match(r"^(click|press)\s+(?:on\s+)?(.+)$", text)

        if m and m.group(2).strip() not in self.KEY_MAP:

            return "click_text", m.group(2).strip()



        m = re.match(r"^right click\s+(?:on\s+)?(.+)$", text)

        if m:

            return "right_click_text", m.group(1).strip()



        m = re.match(r"^double click\s+(?:on\s+)?(.+)$", text)

        if m:

            return "double_click_text", m.group(1).strip()



        # Type / write

        m = re.match(

            r"^(type|write|enter text|input)\s+(.+)$",

            text

        )

        if m:

            return "type", m.group(2)



        # Screen scan / OCR

        if text in (

            "scan screen",

            "scan the screen",

            "read screen",

            "read the screen",

            "screen scan",

            "what is on screen",

            "what's on screen",

        ):

            return "scan", ""



        # Press key

        if text.startswith("press "):

            key = text[6:].strip()

            return "key", self.KEY_MAP.get(key, key)



        if text in self.KEY_MAP:

            return "key", self.KEY_MAP[text]



        # Special shortcuts

        shortcuts = {

            "copy": ("hotkey", ("ctrl", "c")),

            "paste": ("hotkey", ("ctrl", "v")),

            "cut": ("hotkey", ("ctrl", "x")),

            "select all": ("hotkey", ("ctrl", "a")),

            "save": ("hotkey", ("ctrl", "s")),

            "undo": ("hotkey", ("ctrl", "z")),

            "redo": ("hotkey", ("ctrl", "y")),

            "new tab": ("hotkey", ("ctrl", "t")),

            "close tab": ("hotkey", ("ctrl", "w")),

            "refresh": ("key", "f5"),

            "shut down pc": ("key", "f4"),

            "go back": ("hotkey", ("alt", "left")),

            "go forward": ("hotkey", ("alt", "right")),

        }

        if text in shortcuts:

            return shortcuts[text]



        # Questions

        return "question", text





# ============================================================

# WEB ANSWER

# ============================================================



def check_internet(timeout=3):
    """Check whether an external internet connection is available."""
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
    finally:
        socket.setdefaulttimeout(old_timeout)


class _VisualSearchHTMLParser(HTMLParser):
    """Collect readable text and outbound result links from a visual search page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.links = []
        self._skip_depth = 0
        self._anchor_url = None
        self._anchor_text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        if tag == "a":
            self._anchor_url = dict(attrs).get("href")
            self._anchor_text = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and self._anchor_url:
            label = re.sub(r"\s+", " ", " ".join(self._anchor_text)).strip()
            if label:
                self.links.append((label, self._anchor_url))
            self._anchor_url = None
            self._anchor_text = []

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.text_parts.append(text)
            if self._anchor_url is not None:
                self._anchor_text.append(text)


def capture_camera_image():
    """Capture one bounded-size still from the default PC camera."""
    if not CV2_OK or cv2 is None:
        raise RuntimeError(
            "Camera search needs OpenCV. Install it in SHASTRA's Python environment "
            "with: python -m pip install opencv-python"
        )

    backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
    camera = cv2.VideoCapture(0, backend)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            "Could not open camera input 0. Check Windows Camera permission and "
            "close any other app currently using this camera."
        )
    try:
        frame = None
        for _ in range(12):
            ok, current = camera.read()
            if ok and current is not None and current.size:
                frame = current
            time.sleep(0.04)
        if frame is None:
            raise RuntimeError("The camera opened, but it did not provide an image.")

        height, width = frame.shape[:2]
        longest_side = max(width, height)
        if longest_side > 1280:
            scale = 1280 / longest_side
            frame = cv2.resize(
                frame,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        encoded, image = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
        )
        if not encoded:
            raise RuntimeError("The camera image could not be encoded for visual search.")
        return image.tobytes()
    finally:
        camera.release()


def search_camera_image(image_bytes, max_results=6):
    """Upload one user-requested camera still to Google image search."""
    if not image_bytes:
        raise ValueError("The camera did not provide an image to search.")
    if len(image_bytes) > 5 * 1024 * 1024:
        raise ValueError("The camera image is larger than the 5 MB upload limit.")

    boundary = "----SHASTRAVisualSearch" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="encoded_image"; filename="shastra-camera.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("ascii") + image_bytes + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(
        "https://www.google.com/searchbyimage/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            search_url = response.geturl()
            page = response.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RuntimeError(
                "Google visual search temporarily rate-limited the image upload. "
                "Wait a minute and try again."
            ) from exc
        raise RuntimeError(
            f"Google visual search rejected the image upload (HTTP {exc.code})."
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach Google visual search: {exc}") from exc

    parser = _VisualSearchHTMLParser()
    parser.feed(page)
    results = []
    seen_urls = set()
    for label, href in parser.links:
        url = urllib.parse.urljoin(search_url, html.unescape(href))
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.lower().endswith("google.com") and parsed.path == "/url":
            query = urllib.parse.parse_qs(parsed.query)
            url = query.get("q", query.get("url", [url]))[0]
            parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        if parsed.netloc.lower().endswith("google.com") or url in seen_urls:
            continue
        if len(label) < 3:
            continue
        seen_urls.add(url)
        results.append((label[:240], url))
        if len(results) >= max_results:
            break

    visible_text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return search_url, results, visible_text[:6000]


def summarize_camera_search(search_url, results, visible_text, image_text=""):
    """Turn reverse-image matches into a concise, source-linked explanation."""
    answer = ["CAMERA IMAGE SEARCH — SHASTRA"]
    if image_text:
        answer.append("Text read from the image: " + image_text[:900])
    if not results:
        if image_text:
            answer.append(
                "Google did not return readable visual matches. I searched the "
                "text visible in the image instead."
            )
            research = web_research(image_text, max_results=5)
            if research:
                answer.append("Web information based on the visible text:")
                for index, (title, snippet) in enumerate(research, 1):
                    answer.append(
                        f"{index}. {title}: {(snippet or 'No summary available.')[:420]}\n"
                        f"   Search/source: https://www.google.com/search?q="
                        f"{urllib.parse.quote_plus(title)}"
                    )
            else:
                answer.append("I could not find web information for the visible text.")
        else:
            answer.append(
                "Google did not return readable visual matches and I could not "
                "read text from the image, so I cannot identify it reliably."
            )
        answer.append("Open the visual-search page: " + search_url)
        if visible_text:
            answer.append("Search page text: " + visible_text[:900])
        return "\n\n".join(answer)

    answer.append("Visual matches found:")
    for index, (title, url) in enumerate(results[:5], 1):
        answer.append(f"{index}. {title}\n   Source: {url}")

    research_titles = [title for title, _url in results[:2] if len(title) >= 5]
    if research_titles:
        answer.append("\nMORE INFORMATION FROM THE MATCHING WEB RESULTS:")
        for title in research_titles:
            research = web_research(title, max_results=3)
            answer.append("\nAbout " + title + ":")
            if research:
                for result_title, snippet in research[:3]:
                    detail = (snippet or "").strip()
                    research_url = (
                        "https://www.google.com/search?q="
                        + urllib.parse.quote_plus(result_title)
                    )
                    answer.append(
                        f"- {result_title}: {detail[:360]}\n  Source: "
                        + research_url
                    )
            else:
                answer.append("I found no additional readable web summary.")
    answer.append("\nFull visual-search page: " + search_url)
    answer.append(
        "These are visual matches, not a guaranteed identification; check the "
        "linked sources to confirm the match."
    )
    return "\n".join(answer)


def extract_camera_image_text(image_bytes):
    """Read visible text from the still so labels can provide a searchable clue."""
    if not TESSERACT_OK or Image is None or pytesseract is None:
        return ""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, timeout=8)
        return re.sub(r"\s+", " ", text).strip()[:1200]
    except Exception as exc:
        print(f"[CAMERA OCR] Text extraction failed: {exc}", flush=True)
        return ""



# ============================================================
# AI WEB MODE / FREE WEB MODE
# ============================================================

# Session-only authentication choice. The API key is never written to disk.
SHASTRA_AI_SESSION = {
    "use_api": False,
    "api_key": "",
    "username": "",
}

def _http_json(url, payload, headers=None, timeout=30):
    """POST JSON and return decoded JSON with useful errors."""
    data = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "SHASTRA-Future-Core/1.0",
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {detail[:900]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(str(exc)) from exc


def _extract_gemini_text(data):
    """Extract text from a Gemini generateContent response."""
    parts = []
    for candidate in data.get("candidates", []) or []:
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                parts.append(str(text).strip())
    return "\n".join(x for x in parts if x).strip()


def gemini_web_answer(query, api_key):
    """
    Gemini API answer with Google Search grounding.

    The API key is supplied only for the current process/session. It is not
    saved into SQLite, source code, or a settings file.
    """
    key = str(api_key or "").strip()
    if not key:
        raise RuntimeError("No Gemini API key was supplied.")

    model = os.environ.get("SHASTRA_GEMINI_MODEL", "gemini-3.8-flash")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + urllib.parse.quote(model, safe="")
        + ":generateContent?key="
        + urllib.parse.quote(key, safe="")
    )

    prompt = (
        "You are SHASTRA, a Windows personal AI assistant. "
        "Answer the user's question clearly and accurately. "
        "Use Google Search grounding to check current information when useful. "
        "Prefer current, factual information. If sources disagree, say so. "
        "Do not invent facts. Keep the answer concise unless the question needs detail.\n\n"
        "USER QUESTION:\n" + query
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1800,
        },
    }

    data = _http_json(endpoint, payload, timeout=45)
    text = _extract_gemini_text(data)
    if not text:
        raise RuntimeError(
            "Gemini returned no readable answer. "
            + json.dumps(data, ensure_ascii=False)[:1000]
        )

    # Add grounding/source information when Gemini returned it.
    grounding = []
    for candidate in data.get("candidates", []) or []:
        gm = candidate.get("groundingMetadata") or {}
        chunks = gm.get("groundingChunks") or []
        for chunk in chunks:
            web = chunk.get("web") or {}
            uri = web.get("uri")
            title = web.get("title")
            if uri and uri not in [u for _, u in grounding]:
                grounding.append((title or uri, uri))

    if grounding:
        source_lines = ["\n\nSources checked by Gemini:"]
        for title, uri in grounding[:6]:
            source_lines.append(f"- {title}: {uri}")
        text += "\n".join(source_lines)

    return text


def google_search_results(query, limit=5):
    """
    Lightweight Google web search reader.

    Google may change its HTML layout, so this function is deliberately
    tolerant and returns an empty list rather than crashing SHASTRA.
    """
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/154 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        page = response.read().decode("utf-8", errors="ignore")

    results = []

    # Common Google result form: <h3>title</h3> inside an anchor.
    title_matches = re.findall(
        r'<a[^>]+href="([^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?</a>',
        page,
        flags=re.I | re.S,
    )
    for raw_url, raw_title in title_matches:
        title = _clean_html_text(raw_title)
        result_url = html.unescape(raw_url)
        if result_url.startswith("/url?"):
            parsed = urllib.parse.urlparse(result_url)
            target = urllib.parse.parse_qs(parsed.query).get("q")
            if target:
                result_url = target[0]
        if not result_url.startswith("http"):
            continue

        # Find a nearby readable snippet after the title. This is best-effort.
        pos = page.find(raw_title)
        nearby = page[pos:pos + 5000] if pos >= 0 else ""
        snippets = re.findall(
            r'<div[^>]+class="[^"]*(?:VwiC3b|yXK7lf)[^"]*"[^>]*>(.*?)</div>',
            nearby,
            flags=re.I | re.S,
        )
        snippet = _clean_html_text(snippets[0]) if snippets else ""

        item = (title, snippet, result_url)
        if item not in results:
            results.append(item)
        if len(results) >= limit:
            break

    # Fallback parser for layouts where the h3 pattern changed.
    if not results:
        for raw_title, raw_snippet in re.findall(
            r'<h3[^>]*>(.*?)</h3>.*?'
            r'<div[^>]+class="[^"]*(?:VwiC3b|yXK7lf)[^"]*"[^>]*>(.*?)</div>',
            page,
            flags=re.I | re.S,
        )[:limit]:
            title = _clean_html_text(raw_title)
            snippet = _clean_html_text(raw_snippet)
            if title:
                results.append((title, snippet, url))

    return results


def wikipedia_answer(query):
    """Get a readable Wikipedia summary for the user's question."""
    api_url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(query.replace(" ", "_"), safe="")
    )
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "SHASTRA-Future-Core/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8", errors="ignore"))
        extract = str(data.get("extract") or "").strip()
        title = str(data.get("title") or "").strip()
        page_url = (
            (data.get("content_urls") or {})
            .get("desktop", {})
            .get("page")
        )
        if extract:
            answer = f"Wikipedia — {title}\n{extract}"
            if page_url:
                answer += f"\n\nSource: {page_url}"
            return answer
    except Exception:
        pass

    # Search Wikipedia when the direct summary endpoint does not match.
    try:
        search_url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search"
            "&format=json&srnamespace=0&srlimit=1&srsearch="
            + urllib.parse.quote(query)
        )
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "SHASTRA-Future-Core/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8", errors="ignore"))
        pages = data.get("query", {}).get("search", [])
        if pages:
            title = pages[0].get("title", "")
            source = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_")
            )
            return (
                f"Wikipedia result: {title}\n"
                f"{_clean_html_text(pages[0].get('snippet', ''))}\n\n"
                f"Source: {source}"
            )
    except Exception:
        pass
    return ""


def answer_free_google_wikipedia(query):
    """
    No-API mode:
    1. Read Wikipedia.
    2. Read Google web results.
    3. Combine the readable evidence without requiring an AI API key.
    """
    query = str(query or "").strip()
    if not query:
        return "I did not receive a question."

    sections = []
    wiki = wikipedia_answer(query)
    if wiki:
        sections.append(wiki)

    try:
        google_results = google_search_results(query, limit=5)
    except Exception as exc:
        google_results = []
        google_error = str(exc)
    else:
        google_error = ""

    if google_results:
        lines = ["Google Search results:"]
        for number, (title, snippet, url) in enumerate(google_results, 1):
            lines.append(f"{number}. {title}")
            if snippet:
                lines.append(f"   {snippet[:500]}")
            lines.append(f"   Source: {url}")
        sections.append("\n".join(lines))
    else:
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        sections.append(
            "Google Search could not be read automatically.\n"
            f"Open Google Search: {search_url}"
            + (f"\nReason: {google_error[:250]}" if google_error else "")
        )

    if not sections:
        return "I could not retrieve Wikipedia or Google results. Check your internet connection."

    return "\n\n".join(sections)


# ============================================================
# LOCAL LEARNING / CONNECTED KNOWLEDGE
# ============================================================
# SHASTRA keeps exact questions and also groups different questions
# that belong to the same topic. A new related question can therefore
# use older local knowledge as context before API/Web research.
# API keys are NEVER stored here.
KNOWLEDGE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shastra_knowledge.db")

_KNOWLEDGE_STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "to", "in", "on", "for",
    "why", "how", "when", "where", "which", "who", "can", "could", "would",
    "should", "do", "does", "did", "explain", "tell", "me", "about", "please",
    "give", "show", "with", "and", "or", "this", "that", "these", "those",
    "use", "used", "using", "means", "mean", "does", "it", "its", "from",
    "into", "your", "you", "i", "my", "we", "they", "be", "being", "than",
}


def normalize_knowledge_question(question):
    """Normalize a question so harmless formatting differences match."""
    text = str(question or "").strip().casefold()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def knowledge_terms(text):
    """Return useful topic/content words from a question or knowledge item."""
    normalized = normalize_knowledge_question(text)
    words = re.findall(r"[a-z0-9_]{2,}|[\u0900-\u097F]{2,}", normalized)
    return {w for w in words if w not in _KNOWLEDGE_STOPWORDS and len(w) > 1}


def infer_knowledge_topic(question, fallback="general"):
    """Pick a stable topic label from the strongest content words."""
    terms = knowledge_terms(question)
    if not terms:
        return fallback
    # Preserve the question's first useful term; this makes HTML questions
    # naturally group under HTML, Python questions under Python, etc.
    normalized = normalize_knowledge_question(question)
    ordered = [w for w in normalized.split() if w in terms]
    if ordered:
        return " ".join(ordered[:2])
    return sorted(terms, key=lambda x: (-len(x), x))[0]


def init_knowledge_database():
    """Create/migrate the local connected-knowledge database."""
    with closing(sqlite3.connect(KNOWLEDGE_DB, timeout=10)) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS learned_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_question TEXT NOT NULL UNIQUE,
                original_question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic TEXT NOT NULL DEFAULT 'general',
                keywords TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                use_count INTEGER NOT NULL DEFAULT 1
            )"""
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(learned_answers)").fetchall()}
        if "topic" not in columns:
            db.execute("ALTER TABLE learned_answers ADD COLUMN topic TEXT NOT NULL DEFAULT 'general'")
        if "keywords" not in columns:
            db.execute("ALTER TABLE learned_answers ADD COLUMN keywords TEXT NOT NULL DEFAULT ''")
        db.commit()


def knowledge_lookup(question):
    """Return (answer, row_id, topic) for an exact normalized question."""
    normalized = normalize_knowledge_question(question)
    if not normalized:
        return None, None, None
    init_knowledge_database()
    with closing(sqlite3.connect(KNOWLEDGE_DB, timeout=10)) as db:
        row = db.execute(
            "SELECT id, answer, topic FROM learned_answers WHERE normalized_question = ? LIMIT 1",
            (normalized,),
        ).fetchone()
        if not row:
            return None, None, None
        db.execute(
            "UPDATE learned_answers SET last_used_at = ?, use_count = use_count + 1 WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), row[0]),
        )
        db.commit()
        return str(row[1]), int(row[0]), str(row[2] or "general")


def knowledge_find_related(question, limit=5):
    """Find older knowledge that is probably about the same topic.

    This intentionally uses a conservative lexical score instead of fuzzy
    matching the whole answer, so unrelated questions are not accidentally
    treated as the same question.
    """
    terms = knowledge_terms(question)
    if not terms:
        return []
    init_knowledge_database()
    with closing(sqlite3.connect(KNOWLEDGE_DB, timeout=10)) as db:
        rows = db.execute(
            "SELECT id, original_question, answer, topic, keywords, use_count FROM learned_answers"
        ).fetchall()

    candidates = []
    for row in rows:
        row_id, original, answer, topic, keywords, use_count = row
        row_terms = set(filter(None, str(keywords or "").split())) or knowledge_terms(original)
        if not row_terms:
            continue
        overlap = terms & row_terms
        if not overlap:
            continue
        union = terms | row_terms
        jaccard = len(overlap) / max(1, len(union))
        coverage = len(overlap) / max(1, len(terms))
        # Coverage matters most: "HTML" should strongly connect to
        # "what are HTML tags?" even if the rest of the words differ.
        score = (coverage * 0.70) + (jaccard * 0.30)
        if str(topic or "general").casefold() in terms:
            score += 0.18
        if score >= 0.28:
            candidates.append((score, row_id, original, answer, topic or "general", use_count))

    candidates.sort(key=lambda item: (item[0], item[5]), reverse=True)
    return candidates[:max(1, int(limit))]


def knowledge_save(question, answer, topic=None):
    """Save/update one question while keeping it connected to a topic."""
    normalized = normalize_knowledge_question(question)
    answer_text = str(answer or "").strip()
    if not normalized or not answer_text:
        return False
    init_knowledge_database()
    topic = str(topic or infer_knowledge_topic(question)).strip() or "general"
    keywords = " ".join(sorted(knowledge_terms(question) | knowledge_terms(topic)))
    now = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(KNOWLEDGE_DB, timeout=10)) as db:
        with db:
            db.execute(
                """INSERT INTO learned_answers
                   (normalized_question, original_question, answer, topic, keywords, created_at, last_used_at, use_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(normalized_question) DO UPDATE SET
                       answer = excluded.answer,
                       topic = excluded.topic,
                       keywords = excluded.keywords,
                       last_used_at = excluded.last_used_at""",
                (normalized, str(question).strip(), answer_text, topic, keywords, now, now),
            )
    return True


def _connected_knowledge_context(question, related_rows):
    """Build compact context that can be supplied to the online answer engine."""
    if not related_rows:
        return ""
    lines = [
        "LOCAL SHASTRA KNOWLEDGE CONTEXT",
        "Use this older knowledge as context. Do not blindly repeat it; improve or correct it when current research provides better information.",
    ]
    for _, _, original, answer, topic, _ in related_rows[:5]:
        lines.append(f"\nTopic: {topic}\nEarlier question: {original}\nEarlier answer: {answer[:1800]}")
    return "\n".join(lines)


try:
    init_knowledge_database()
except Exception as exc:
    print(f"[KNOWLEDGE DB] Initialization warning: {exc}", flush=True)


def answer_with_selected_mode(query):
    """Connected-learning question router.

    1. Normalize + exact lookup.
    2. If exact match exists, return its saved answer immediately.
    3. Otherwise find related topic knowledge.
    4. Use that older knowledge + fresh API/Web research.
    5. Save the new question under the related topic.

    Returns: (answer, source).
    """
    query = str(query or "").strip()
    if not query:
        return "I did not receive a question.", "LOCAL DATABASE"

    cached_answer, row_id, cached_topic = knowledge_lookup(query)
    if cached_answer:
        print(
            f"[KNOWLEDGE DB] EXACT HIT id={row_id} topic={cached_topic}: {query}",
            flush=True,
        )
        return cached_answer, "LOCAL DATABASE - EXACT MATCH"

    print(f"[KNOWLEDGE DB] EXACT MISS: {query}", flush=True)
    related = knowledge_find_related(query, limit=5)
    topic = related[0][4] if related else infer_knowledge_topic(query)

    if related:
        print(
            f"[KNOWLEDGE DB] RELATED TOPIC: {topic} | matched {len(related)} item(s)",
            flush=True,
        )
    else:
        print(f"[KNOWLEDGE DB] NO RELATED TOPIC: creating '{topic}'", flush=True)

    use_api = bool(SHASTRA_AI_SESSION.get("use_api"))
    api_key = SHASTRA_AI_SESSION.get("api_key", "")
    context = _connected_knowledge_context(query, related)

    if use_api:
        try:
            research_query = query
            if context:
                research_query = (
                    query
                    + "\n\n"
                    + context
                    + "\n\nAnswer the user's new question using the relevant local knowledge above "
                      "and current Google Search research. Keep the new answer focused, and "
                      "connect it naturally to the existing topic."
                )
            answer = gemini_web_answer(research_query, api_key)
        except Exception as exc:
            return (
                "AI API mode is enabled, but the API request failed.\n\n"
                f"Error: {str(exc)[:700]}\n\n"
                "Check your Gemini API key, internet connection, and "
                "SHASTRA_GEMINI_MODEL if you changed it.",
                "WEB/API ERROR",
            )
    else:
        # Free mode still gets fresh web/Wikipedia data. When related local
        # knowledge exists, put it first so the new answer stays connected.
        fresh = answer_free_google_wikipedia(query)
        if context:
            answer = (
                f"CONNECTED KNOWLEDGE — {topic.upper()}\n\n"
                + context.replace("LOCAL SHASTRA KNOWLEDGE CONTEXT\n", "", 1).strip()
                + "\n\nFRESH WEB RESEARCH\n\n"
                + fresh
            )
        else:
            answer = fresh

    if answer and not str(answer).startswith("I could not retrieve"):
        try:
            if knowledge_save(query, answer, topic=topic):
                print(
                    f"[KNOWLEDGE DB] NEW QUESTION SAVED id/topic={topic}",
                    flush=True,
                )
        except Exception as exc:
            print(f"[KNOWLEDGE DB] Save warning: {exc}", flush=True)

    return answer, "WEB/API + RELATED KNOWLEDGE" if related else "WEB/API - NEW TOPIC"

# ============================================================
# SHASTRA ADVISOR / DECISION SUPPORT
# ============================================================

def recent_memory_context(limit=8):
    """Return recent user/assistant interactions for project continuity."""
    try:
        db = sqlite3.connect(DB_FILE, check_same_thread=False)
        rows = db.execute(
            "SELECT user_text, assistant_text, timestamp FROM interactions "
            "ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        db.close()
        rows.reverse()
        return rows
    except Exception:
        return []


def web_research(query, max_results=5):
    """Free web research using DuckDuckGo HTML plus the Instant Answer API."""
    results = []
    try:
        q = urllib.parse.quote_plus(query)
        url = "https://html.duckduckgo.com/html/?q=" + q
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 SHASTRA-Future-Core/1.0",
                "Accept": "text/html,application/xhtml+xml"
            },
        )
        with urllib.request.urlopen(req, timeout=2.0) as response:
            html = response.read().decode("utf-8", errors="ignore")
        # Lightweight extraction; avoids requiring BeautifulSoup.
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html, flags=re.I | re.S
        )
        for title, snippet in blocks[:max_results]:
            clean = lambda x: re.sub(r"<[^>]+>", " ", x)
            title = re.sub(r"\s+", " ", clean(title)).strip()
            snippet = re.sub(r"\s+", " ", clean(snippet)).strip()
            if title:
                results.append((title, snippet))
    except Exception as exc:
        results.append(("Web search unavailable", str(exc)))

    # Add a compact knowledge result as a second free source when available.
    try:
        encoded = urllib.parse.quote(query)
        url = "https://api.duckduckgo.com/?q=" + encoded + "&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SHASTRA"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            results.insert(0, (data.get("Heading") or "DuckDuckGo knowledge result", abstract))
    except Exception:
        pass
    return results[:max_results]


def advisor_response(goal):
    """Research a goal and produce neutral, practical decision-support suggestions."""
    goal = goal.strip()
    memory = recent_memory_context(8)
    online = check_internet()
    research_query = goal
    if online:
        research_query = (
            goal +
            " current best practices examples technologies features risks 2026"
        )
    research = web_research(research_query, 5) if online else []

    lines = []
    lines.append("ADVISOR ANALYSIS")
    lines.append("Goal: " + goal)
    if online:
        lines.append("Research: current web information checked.")
    else:
        lines.append("Research: internet unavailable; using local context only.")

    if memory:
        related = []
        goal_words = set(re.findall(r"[a-zA-Z]{4,}", goal.lower()))
        for user_text, assistant_text, _ts in memory:
            words = set(re.findall(r"[a-zA-Z]{4,}", (user_text or "").lower()))
            if goal_words & words:
                related.append(user_text)
        if related:
            lines.append("Earlier related idea: " + related[-1][:240])

    if research:
        lines.append("\nONLINE RESEARCH:")
        for idx, (title, snippet) in enumerate(research[:5], 1):
            lines.append(f"{idx}. {title}: {snippet[:260]}")

    # Practical framework rather than choosing for the user.
    lines.append("\nSUGGESTED APPROACH:")
    lines.append("1. Define the exact result you want before starting implementation.")
    lines.append("2. Build a small working version first, then add advanced features.")
    lines.append("3. Choose technology based on the project's requirements, your current skills, time and budget.")
    lines.append("4. Validate the idea with current information before spending money or committing to a large build.")
    lines.append("5. Compare at least two reasonable approaches and choose the one that fits your priorities.")
    lines.append("\nNEXT STEP:")
    lines.append("Tell me the project goal, and I can break it into features, technology, research findings, risks and a step-by-step build plan.")
    lines.append("\nYou make the final decision; I provide the research and trade-offs.")
    return "\n".join(lines)


def recent_friend_context(limit=6):
    """Small recent conversation window used only for natural continuity."""
    rows = recent_memory_context(limit)
    if not rows:
        return ""
    parts = []
    for user_text, assistant_text, _ts in rows[-limit:]:
        if user_text:
            parts.append("You: " + str(user_text)[:180])
        if assistant_text:
            parts.append("SHASTRA: " + str(assistant_text)[:220])
    return "\n".join(parts[-10:])


def friend_response(text):
    """Free local friend-style conversation. No paid AI API is required."""
    t = text.lower().strip()
    name = "SHASTRA"

    if any(x in t for x in ("hello", "hi", "hey", "namaste", "good morning", "good evening", "good night")):
        return "Hey! 😄 I’m right here. What are you working on today?"
    if any(x in t for x in ("how are you", "how are u", "what's up", "whats up", "what are you doing")):
        return "I’m good and fully online. 😄 Tell me what’s on your mind. We can chat, plan something, research an idea, or work on your project."
    if any(x in t for x in ("thank you", "thanks", "thx")):
        return "Anytime, bro. 😄"
    if any(x in t for x in ("good job", "nice", "great", "awesome")):
        return "Thanks! 😄 Let’s keep building."
    if any(x in t for x in ("i am tired", "i'm tired", "i feel tired", "i am bored", "i'm bored")):
        return "Take it easy for a moment. 😄 If you want, we can just talk, or I can suggest something useful that doesn’t require heavy work."
    if any(x in t for x in ("i am confused", "i'm confused", "i feel confused", "i don't know")):
        return "No problem. Tell me what you’re deciding between, and I’ll help you break it down into clear options and trade-offs. You’ll make the final call."
    if any(x in t for x in ("motivate me", "give me motivation", "i need motivation")):
        return "Keep it simple: pick one useful thing, start for ten minutes, and finish the first small step. Momentum comes after starting."
    if "who are you" in t or "what are you" in t or "tell me about yourself" in t:
        return "I’m SHASTRA — your local computer assistant. You can talk to me normally, ask me to research an idea, or give me a computer command.My owner name is Ayush Jagtap."

    # Natural conversational statements that should not trigger web research.
    conversational_starts = (
        "i feel ", "i think ", "i like ", "i don't like ", "i love ",
        "today i ", "yesterday i ", "my day ", "bro ", "dude ",
        "i was ", "i am ", "i'm ", "just wanted to talk", "let's talk",
        "can we talk", "talk with me", "stay with me"
    )
    if t.startswith(conversational_starts) or t in ("talk to me", "chat with me", "let's chat"):
        ctx = recent_friend_context(4)
        if ctx and any(w in t for w in ("yesterday", "earlier", "before", "we talked")):
            return "Yeah, I’m following the recent conversation context. Tell me what you want to continue with, and we’ll take it one step at a time."
        return "I’m listening. Tell me more. 😄"

    return "I’m listening. Tell me a little more about that. If it becomes a project or decision, I can research it and help you compare the options."


def looks_like_friend_request(text):
    """Detect casual conversation before generic web-question handling."""
    t = text.lower().strip()
    exact = {
        "hi", "hello", "hey", "hey shastra", "good morning", "good evening",
        "good night", "talk to me", "chat with me", "let's talk", "lets talk",
        "how are you", "what's up", "whats up", "who are you", "thank you", "thanks"
    }
    if t in exact:
        return True
    if any(p in t for p in (
        "i am tired", "i'm tired", "i am bored", "i'm bored", "i am confused",
        "i'm confused", "motivate me", "give me motivation", "can we talk",
        "just wanted to talk", "talk with me", "stay with me"
    )):
        return True
    return any(t.startswith(p) for p in (
        "i feel ", "i think ", "i like ", "i don't like ", "i love ",
        "today i ", "yesterday i ", "my day ", "bro ", "dude ",
        "i was ", "i am ", "i'm "
    ))


def looks_like_advisor_request(text):
    """Detect planning/advice intent before treating the input as a simple question."""
    t = text.lower().strip()
    patterns = (
        "i want to", "i need to", "i am planning", "i'm planning",
        "i plan to", "i decided to", "i want", "suggest me",
        "give me suggestion", "what should i", "which should i",
        "how should i", "help me plan", "make a project",
        "build a project", "start a project", "start business",
        "make a website", "make a web page", "make webpage",
        "what project", "idea for", "recommend a project",
        "should i make", "help me decide", "research this idea",
        "analyze this idea", "what can i do today", "what should i do now"
    )
    return any(p in t for p in patterns)


# FUTURISTIC HUD

# ============================================================




# ============================================================
# MATHS TEACHER MODE
# ============================================================

def _math_clean_question(text):
    q = str(text or "").strip()
    q = re.sub(r"^(?:hey\s+)?shastra[\s,:-]*", "", q, flags=re.I).strip()
    q = re.sub(r"^(?:solve|calculate|find|evaluate|work\s+out|what\s+is)\s+", "", q, flags=re.I).strip()
    return q

def _math_basic_eval(expr):
    """Safe arithmetic fallback. No eval() and no arbitrary Python execution."""
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    expr = re.sub(r"\bpercent\b", "%", expr, flags=re.I)
    if not re.fullmatch(r"[0-9+\-*/().%\s*]+", expr):
        return None
    # Handle simple percentages such as 20% of 500.
    m = re.fullmatch(r"\s*([0-9.]+)\s*%\s*(?:of\s*)?([0-9.]+)\s*", expr, re.I)
    if m:
        return float(m.group(1)) * float(m.group(2)) / 100.0
    try:
        return float(sp.sympify(expr, evaluate=True)) if SYMPY_OK else None
    except Exception:
        return None

def solve_math_step_by_step(question):
    """
    Return a teacher-style solution, not just the final number.
    SymPy is used only for mathematical parsing/solving; no arbitrary code
    is executed from the user's expression.
    """
    q = _math_clean_question(question)
    if not q:
        return "Please give me a maths problem."

    # Normalize common spoken/typed forms.
    q = q.replace("×", "*").replace("÷", "/").replace("−", "-").replace("=", " = ")
    q = re.sub(r"\s+", " ", q).strip()

    # Linear / polynomial equations.
    if SYMPY_OK and "=" in q:
        try:
            left, right = q.split("=", 1)
            # Convert spoken x forms and common multiplication notation.
            left = left.replace("^", "**")
            right = right.replace("^", "**")
            x = sp.Symbol("x")
            eq = sp.Eq(sp.sympify(left, locals={"x": x}), sp.sympify(right, locals={"x": x}))
            sols = sp.solve(eq, x)
            if sols:
                lhs = sp.simplify(eq.lhs)
                rhs = sp.simplify(eq.rhs)
                lines = [
                    "MATHS TEACHER MODE",
                    "",
                    f"Question: {question}",
                    "",
                    "Step 1 — Write the equation:",
                    f"  {sp.sstr(lhs)} = {sp.sstr(rhs)}",
                    "",
                    "Step 2 — Move terms and simplify:",
                ]
                if len(sols) == 1:
                    sol = sp.simplify(sols[0])
                    lines += [
                        f"  Solve for x.",
                        f"  x = {sp.sstr(sol)}",
                        "",
                        "Step 3 — Check:",
                        f"  Substitute x = {sp.sstr(sol)} into the original equation.",
                        f"  Left side = {sp.sstr(lhs.subs(x, sol))}",
                        f"  Right side = {sp.sstr(rhs.subs(x, sol))}",
                        "",
                        f"Final answer: x = {sp.sstr(sol)}",
                    ]
                else:
                    lines += [f"  The equation has {len(sols)} solutions."]
                    for idx, sol in enumerate(sols, 1):
                        lines.append(f"  Solution {idx}: x = {sp.sstr(sp.simplify(sol))}")
                    lines += ["", "Final answer: " + ", ".join("x = " + sp.sstr(sp.simplify(v)) for v in sols)]
                return "\n".join(lines)
        except Exception:
            pass

    # Arithmetic / simple expression.
    if SYMPY_OK:
        try:
            expr = q
            # Avoid interpreting ordinary prose as a math expression.
            if re.fullmatch(r"[0-9+\-*/().%\s*xX^]+", expr):
                expr = expr.replace("^", "**")
                value = sp.simplify(sp.sympify(expr))
                if value.is_number:
                    return (
                        "MATHS TEACHER MODE\n\n"
                        f"Question: {question}\n\n"
                        "Step 1 — Write the expression:\n"
                        f"  {sp.sstr(sp.sympify(expr))}\n\n"
                        "Step 2 — Apply the operation rules:\n"
                        "  Work through multiplication/division before addition/subtraction.\n\n"
                        "Step 3 — Simplify:\n"
                        f"  = {sp.sstr(value)}\n\n"
                        f"Final answer: {sp.sstr(value)}"
                    )
        except Exception:
            pass

    # Word-problem helper: percentage.
    m = re.search(r"([0-9.]+)\s*%\s*(?:of)\s*([0-9.]+)", q, re.I)
    if m:
        pct, base = map(float, m.groups())
        result = pct * base / 100
        return (
            "MATHS TEACHER MODE\n\n"
            f"Question: {question}\n\n"
            "Step 1 — Convert the percentage to a fraction:\n"
            f"  {pct:g}% = {pct:g}/100\n\n"
            "Step 2 — Multiply by the whole amount:\n"
            f"  ({pct:g}/100) × {base:g}\n\n"
            "Step 3 — Calculate:\n"
            f"  = {result:g}\n\n"
            f"Final answer: {result:g}"
        )

    return (
        "MATHS TEACHER MODE\n\n"
        f"Question: {question}\n\n"
        "I need a clearer mathematical expression to solve it step by step. "
        "For example: 2x + 5 = 17, 25 × 16, or 20% of 500."
    )

class HUD:

    # ------------------------------------------------------------
    # SHASTRA FUTURE HUD
    # Canvas-first interface inspired by the supplied SHASTRA UI
    # image.  No external image assets are required.
    # ------------------------------------------------------------

    BG = "#040b12"
    PANEL = "#0a1723"
    PANEL2 = "#0f2334"
    CYAN = "#67e4ff"
    CYAN2 = "#dfeefb"
    BLUE = "#2ea1ff"
    DIM = "#6a8ea1"
    TEXT = "#edf7ff"
    GREEN = "#63f7c7"
    ORANGE = "#ffbf7e"
    RED = "#ff5f7e"
    GRID = "#132b38"

    def __init__(self, root):
        self.root = root
        self.ui_thread_id = threading.get_ident()
        self.root.title("SHASTRA // JARVIS INTERFACE")
        self.root.geometry("1720x980")
        self.root.minsize(1366, 820)
        self.root.maxsize(1920, 1080)
        self.root.configure(bg=self.BG)
        try:
            self.root.attributes("-alpha", 0.99)
        except Exception:
            pass

        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self.angle = 0.0
        self.pulse = 0.0
        self.wave = 0.0
        self.scan = 0.0
        self.running = True
        self.engine = None
        self.device_network = None
        self.mobile_server = None

        self.last_command = "SYSTEM STANDBY"
        self.last_status = "INITIALIZING"
        self.log_lines = []
        self.messages = [
            ("SHASTRA", "Core online. Ask me anything or give me a computer command.", False)
        ]
        self.vision_text = "MODEL: READY\nSOFTWARE: SHASTRA CORE\nSTATUS: ONLINE"
        self.mode = "ADVISOR MODE"
        self.mode_detail = "Researching & Suggesting..."
        self.voice_level = 0.55
        self.cpu = 18
        self.ram = 42
        self.gpu = 12
        self.battery = 78
        self.temp_cpu = 45
        self.temp_gpu = 42
        self.temp_system = 38
        self.model_path = None
        self.model_name = "No saved model"
        self.model_vertices = []
        self.model_faces = []
        self.model_zoom = 1.0
        self.model_rotation = 0.0
        self.model_error = ""
        self.model_showcase = False
        self.last_answer = ""
        self.security_mode = security_mode_status()
        self.reference_image_path = None
        self.camera_preview_window = None
        self.camera_preview_photo = None
        self.camera_preview_bytes = None
        self.camera_preview_status = None
        self.image_drop_ready = True
        self.math_teacher_mode = False
        self.voice_control_enabled = True
        self.chat_scroll_user = False

        self.canvas = tk.Canvas(
            self.root, bg=self.BG, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.command_label = tk.Label(
            self.root, text="COMMAND / TYPE HERE", bg=self.BG, fg="#9feaff",
            font=("Consolas", 8, "bold")
        )
        self.chat_entry = tk.Entry(
            self.root,
            bg="#071e2d",
            fg=self.TEXT,
            insertbackground=self.CYAN,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#0d5a76",
            highlightcolor="#5fe6ff",
            font=("Segoe UI", 11),
        )
        self.chat_entry.insert(0, "")
        self.chat_entry.bind("<Return>", lambda e: self.submit_text())
        self.chat_entry.bind("<FocusIn>", lambda e: self._entry_focus(True))
        self.chat_entry.bind("<FocusOut>", lambda e: self._entry_focus(False))

        self.send_btn = tk.Button(
            self.root,
            text="EXECUTE",
            command=self.submit_text,
            bg="#0a3252",
            fg="#dffcff",
            activebackground="#0d5d7d",
            activeforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#0d5a76",
            font=("Consolas", 9, "bold"),
            cursor="hand2",
        )

        # Real scrollable conversation widget.  The old canvas-only message
        # renderer could clip the second/follow-up answer when several bubbles
        # arrived quickly.  This widget keeps the newest answer visible and lets
        # the user scroll through the complete answer history.
        self.chat_text = tk.Text(
            self.root,
            bg="#061a2a",
            fg=self.TEXT,
            insertbackground=self.CYAN,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#123d5b",
            highlightcolor="#5fe6ff",
            wrap="word",
            font=("Segoe UI", 9),
            padx=10,
            pady=8,
            spacing1=2,
            spacing3=7,
            state="disabled",
        )
        self.chat_scroll = tk.Scrollbar(
            self.root, orient="vertical", command=self.chat_text.yview,
            bg="#07384d", activebackground="#16d9ff",
            troughcolor="#03131f", relief="flat", bd=0, width=10
        )
        self.chat_text.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_text.tag_configure("YOU", foreground=self.TEXT, font=("Segoe UI", 9, "bold"))
        self.chat_text.tag_configure("SHASTRA", foreground=self.CYAN2, font=("Segoe UI", 9, "bold"))
        self.chat_text.tag_configure("BODY", foreground=self.TEXT, font=("Segoe UI", 9))
        self.chat_text.tag_configure("SEPARATOR", foreground="#0a4e67")
        self.chat_text.bind("<MouseWheel>", self._chat_mousewheel)
        self.chat_text.bind("<Button-4>", lambda e: self._chat_mousewheel(e, 1))
        self.chat_text.bind("<Button-5>", lambda e: self._chat_mousewheel(e, -1))

        self.voice_btn = tk.Button(
            self.root,
            text="MIC",
            command=self.start_voice,
            bg="#0a2e4a",
            fg="#dffcff",
            activebackground="#0d5d7d",
            activeforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#0d5a76",
            font=("Segoe UI", 13, "bold"),
            cursor="hand2",
        )

        self.camera_btn = tk.Button(
            self.root,
            text="CAMERA",
            command=self.start_camera_search,
            bg="#0a2e4a",
            fg="#dffcff",
            activebackground="#0d5d7d",
            activeforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#0d5a76",
            font=("Consolas", 8, "bold"),
            cursor="hand2",
        )

        self.drop_image_btn = tk.Button(
            self.root, text="▣  DROP IMAGE → 3D", command=self.pick_image_for_3d,
            bg="#0a2d43", fg="#dffcff", activebackground="#0b5a73",
            activeforeground="white", relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#0d5a76",
            font=("Consolas", 8, "bold"), cursor="hand2"
        )

        self.quick_buttons = []
        for text in ("YES, SHOW ROADMAP", "PROJECT IDEAS", "BLENDER BASICS", "MAKE 3D CAR"):
            b = tk.Button(
                self.root,
                text=text,
                command=lambda t=text: self.quick_command(t),
                bg="#0a2338",
                fg="#dffcff",
                activebackground="#0d5d7d",
                activeforeground="white",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#103f5f",
                font=("Consolas", 8, "bold"),
                cursor="hand2",
            )
            self.quick_buttons.append(b)

        for button in [self.send_btn, self.voice_btn, self.camera_btn, self.drop_image_btn, *self.quick_buttons]:
            self._bind_button_glow(button, button.cget("bg"), button.cget("fg"), "#0f6b8a", "#ffffff")

        self.canvas.bind("<Configure>", lambda e: self._place_widgets())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.build()
        self.register_image_drop()
        self.animate()

    def _bind_button_glow(self, widget, base_bg, base_fg, hover_bg, hover_fg):
        def _enter(event):
            widget.configure(bg=hover_bg, fg=hover_fg)

        def _leave(event):
            widget.configure(bg=base_bg, fg=base_fg)

        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)

    # --------------------------- geometry helpers ---------------------------

    def _w(self):
        return max(1180, self.canvas.winfo_width())

    def _h(self):
        return max(720, self.canvas.winfo_height())

    def _place_widgets(self):
        """Place real Tk widgets above the canvas without create_window duplication.

        The previous implementation recreated Canvas window items every animation
        frame.  Because animate() clears the canvas, those embedded widgets could
        become duplicated/misaligned and appear as white blocks.  Direct `place()`
        keeps the controls as normal Tk widgets and they stay stable while the
        canvas is redrawn.
        """
        w, h = self._w(), self._h()
        right_x = w - 410
        panel_w = 392

        # Keep controls inside the right SHASTRA panel.
        self.command_label.place(x=right_x + 14, y=h - 157, width=360, height=18)
        self.voice_btn.place(x=right_x + 12, y=h - 132, width=42, height=34)
        self.camera_btn.place(x=right_x + 60, y=h - 132, width=72, height=34)
        self.chat_entry.place(x=right_x + 138, y=h - 132, width=150, height=34)
        self.send_btn.place(x=right_x + 294, y=h - 132, width=84, height=34)

        # Full scrollable answer area.  It ends above the command strip.
        chat_top = 370
        chat_bottom = h - 170
        chat_x = right_x + 12
        chat_y = chat_top + 38
        chat_w = panel_w - 34
        chat_h = max(70, chat_bottom - chat_y - 10)
        self.chat_text.place(x=chat_x, y=chat_y, width=chat_w - 10, height=chat_h)
        self.chat_scroll.place(x=chat_x + chat_w - 8, y=chat_y, width=10, height=chat_h)
        self._refresh_chat_widget()

        # Image-to-3D button and quick actions share one compact row.
        self.drop_image_btn.place(x=right_x + 12, y=h - 91, width=142, height=28)
        quick_x = right_x + 160
        for i, b in enumerate(self.quick_buttons):
            b.place(x=quick_x + i * 57, y=h - 91, width=54, height=28)

        # Circular image-drop target is canvas artwork, so redraw only that part.
        self.canvas.delete("image_drop_ring")
        cx, cy, r = right_x + panel_w / 2, 172, 58
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=self.CYAN, width=2,
                                tags=("image_drop_ring",))
        self.canvas.create_oval(cx-r+10, cy-r+10, cx+r-10, cy+r-10, outline=self.CYAN2, width=1,
                                tags=("image_drop_ring",))
        self.canvas.create_line(cx-26, cy, cx+26, cy, fill=self.CYAN2, width=2,
                                tags=("image_drop_ring",))
        self.canvas.create_text(cx, cy+76, text="DROP IMAGE HERE", fill=self.CYAN,
                                font=("Consolas", 9, "bold"), tags=("image_drop_ring",))

    def _chat_mousewheel(self, event, direction=None):
        try:
            delta = direction if direction is not None else (1 if event.delta > 0 else -1)
            self.chat_text.yview_scroll(delta * 3, "units")
            self.chat_scroll_user = True
        except Exception:
            pass
        return "break"

    def _refresh_chat_widget(self, autoscroll=True):
        """Render the complete conversation in a real scrollable text widget."""
        if not hasattr(self, "chat_text"):
            return
        try:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("1.0", "end")
            for idx, (speaker, text, is_user) in enumerate(self.messages[-30:]):
                tag = "YOU" if is_user else "SHASTRA"
                self.chat_text.insert("end", speaker + "\n", tag)
                self.chat_text.insert("end", str(text).strip() + "\n", "BODY")
                if idx < len(self.messages[-30:]) - 1:
                    self.chat_text.insert("end", "────────────────────────\n", "SEPARATOR")
            self.chat_text.configure(state="disabled")
            if autoscroll and not self.chat_scroll_user:
                self.chat_text.see("end")
            elif autoscroll:
                # New answers should always land on screen; the user can scroll
                # upward again after the newest answer has appeared.
                self.chat_text.see("end")
                self.chat_scroll_user = False
        except Exception:
            pass

    def pick_image_for_3d(self):
        path=filedialog.askopenfilename(title="Choose image for 3D model",filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if path: self.handle_image_to_3d(path)

    def handle_image_to_3d(self, path):
        path=path.strip().strip('{}').strip('"')
        if not os.path.isfile(path): return
        self.model_showcase=True; self.mode="3D IMAGE MAKER"; self.mode_detail="Image-derived 3D relief"
        self.set_status("IMAGE → 3D PROCESSING")
        self.set_vision("◉ SHASTRA IMAGE-TO-3D\n\nLoading image...\nBuilding depth mesh...")
        self.set_answer("Creating a 3D model from the selected image...")
        self.log_event("IMAGE TO 3D: "+path)
        def work():
            try:
                folder,obj,ref,nv,nf=generate_3d_from_image(path)
                self.reference_image_path=ref
                self.show_3d_model(obj)
                self.set_status("IMAGE 3D MODEL READY")
                self.set_vision(f"✓ IMAGE → 3D COMPLETE\n\n{os.path.basename(path)[:48]}\nVertices: {nv}\nFaces: {nf}\nMethod: depth relief mesh")
                self.set_answer("3D model created from the image and loaded into the live preview.\nOutput: "+obj)
                if self.engine: self.engine.speak("The image has been converted into a 3D model and loaded into the preview.")
            except Exception as exc:
                self.set_status("IMAGE 3D ERROR"); self.set_vision("× IMAGE → 3D ERROR\n\n"+str(exc)[:500]); self.set_answer(str(exc))
                if self.engine: self.engine.speak("I could not create the image based 3D model.")
        threading.Thread(target=work,daemon=True).start()

    def _parse_dnd_paths(self, data):
        """Parse Windows TkDND paths safely, including paths containing spaces."""
        if not data:
            return []
        try:
            if hasattr(self.root, "tk"):
                parts = self.root.tk.splitlist(data)
            else:
                parts = [data]
        except Exception:
            parts = [data]
        out = []
        for item in parts:
            item = str(item).strip().strip('\"')
            if item.startswith("{") and item.endswith("}"):
                item = item[1:-1]
            if item.lower().startswith("file:///"):
                item = urllib.parse.unquote(item[8:])
            elif item.lower().startswith("file://"):
                item = urllib.parse.unquote(item[7:])
            else:
                item = urllib.parse.unquote(item)
            item = os.path.normpath(item)
            if os.path.isfile(item):
                out.append(item)
        return out

    def _on_image_drop(self, event):
        paths = self._parse_dnd_paths(getattr(event, "data", ""))
        image_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
        for path in paths:
            if os.path.splitext(path)[1].lower() in image_ext:
                self.log_event("IMAGE DROP ACCEPTED: " + path)
                self.handle_image_to_3d(path)
                return "break"
        self.set_status("DROP AN IMAGE FILE")
        self.set_answer("Please drop a PNG, JPG, JPEG, WEBP, BMP, GIF, or TIFF image.")
        return "break"

    def register_image_drop(self):
        if not TKDND_OK:
            self.log_event("DRAG AND DROP OFF: tkinterdnd2 is not installed")
            self.set_status("INSTALL tkinterdnd2 FOR DRAG/DROP")
            print("[3D DROP] Install with: python -m pip install tkinterdnd2",flush=True)
            return
        try:
            targets=[self.root,self.canvas,self.drop_image_btn]
            for target in targets:
                if not hasattr(target,"drop_target_register"):
                    continue
                # Some Windows installations report tkinterdnd2 as available but do
                # not actually expose the TkDND command set. Guard against that so
                # the app stays usable even when drag/drop is unavailable.
                try:
                    target.tk.call("info", "commands")
                except Exception:
                    continue
                try:
                    target.drop_target_register(DND_FILES)
                    target.dnd_bind("<<Drop>>", self._on_image_drop)
                    target.dnd_bind("<<DragEnter>>", lambda e: self.set_status("DROP IMAGE → 3D"))
                    target.dnd_bind("<<DragLeave>>", lambda e: self.set_status("3D IMAGE MAKER READY"))
                except Exception as exc:
                    print(f"[3D DROP] drag/drop binding skipped: {exc}", flush=True)
            self.log_event("DRAG AND DROP IMAGE INPUT: ONLINE")
            print("[3D DROP] Drag/drop input ONLINE",flush=True)
        except Exception as exc:
            self.log_event("DRAG AND DROP SETUP FAILED: "+str(exc))
            self.set_status("USE DROP IMAGE BUTTON")
            print(f"[3D DROP ERROR] {exc}",flush=True)

    def _entry_focus(self, focused):
        if focused and not self.chat_entry.get():
            self.set_status("TEXT INPUT READY")
        elif not focused and not self.chat_entry.get():
            self.set_status("READY")

    # --------------------------- drawing primitives --------------------------

    def panel(self, x1, y1, x2, y2, title=None, accent=None, fill=None):
        accent = accent or self.CYAN
        fill = fill or self.PANEL
        cut = 14
        pts = [
            x1 + cut, y1, x2 - cut, y1,
            x2, y1 + cut, x2, y2 - cut,
            x2 - cut, y2, x1 + cut, y2,
            x1, y2 - cut, x1, y1 + cut,
        ]
        # layered neon edge
        self.canvas.create_polygon(pts, fill=fill, outline="#06384c", width=1)
        self.canvas.create_line(
            x1 + 10, y1 + 3, x2 - 20, y1 + 3,
            fill=accent, width=1
        )
        self.canvas.create_line(
            x1 + 3, y1 + 18, x1 + 3, y2 - 18,
            fill="#0b6680", width=1
        )
        self.canvas.create_line(
            x2 - 3, y1 + 18, x2 - 3, y2 - 18,
            fill="#0b6680", width=1
        )
        if title:
            self.canvas.create_text(
                x1 + 14, y1 + 13, text=title,
                anchor="w", fill=accent,
                font=("Consolas", 9, "bold")
            )

    def txt(self, x, y, text, fill=None, size=9, bold=False,
            anchor="w", family="Consolas"):
        self.canvas.create_text(
            x, y, text=text, fill=fill or self.TEXT,
            anchor=anchor,
            font=(family, size, "bold" if bold else "normal")
        )

    def bar(self, x, y, width, value, label, color=None):
        color = color or self.CYAN
        self.txt(x, y, label, self.TEXT, 8)
        self.txt(x + width, y, f"{int(value)}%", self.TEXT, 8, True, "e")
        self.canvas.create_rectangle(
            x, y + 8, x + width, y + 13,
            fill="#0b2b39", outline=""
        )
        self.canvas.create_rectangle(
            x, y + 8, x + width * max(0, min(1, value / 100)),
            y + 13, fill=color, outline=""
        )

    def hex_icon(self, cx, cy, r, symbol, color=None):
        color = color or self.CYAN
        pts = []
        for i in range(6):
            a = math.radians(i * 60 - 30)
            pts.extend((cx + math.cos(a) * r, cy + math.sin(a) * r))
        self.canvas.create_polygon(
            pts, fill="#06283a", outline=color, width=2
        )
        self.canvas.create_text(
            cx, cy, text=symbol, fill=color,
            font=("Segoe UI Symbol", max(9, int(r * 0.65)), "bold")
        )

    # --------------------------- UI build -----------------------------------

    def build(self):
        self._draw_static_shell()
        self._place_widgets()

    def _draw_static_shell(self):
        # The shell is redrawn by animate so it remains responsive on resize.
        pass

    def draw_header(self, w):
        self.canvas.create_rectangle(0, 0, w, 78, fill="#071722", outline="")
        self.canvas.create_line(18, 76, w - 18, 76, fill="#173d53", width=1)
        self.canvas.create_line(18, 12, w - 18, 12, fill="#0f6288", width=1)

        # Clean premium brand block
        self.hex_icon(34, 39, 23, "S", self.CYAN2)
        self.txt(68, 30, "SHASTRA", self.CYAN2, 22, True, "w", "Segoe UI")
        self.txt(70, 52, "FUTURE INTELLIGENCE CORE", "#8db5c7", 8, True)

        # Minimal nav with stronger spacing
        nav = ["THINK", "ANALYZE", "CREATE", "EXECUTE"]
        start = w * 0.42
        for i, n in enumerate(nav):
            self.txt(start + i * 110, 33, n, self.TEXT, 8, True, "center")
            if i < len(nav) - 1:
                self.txt(start + 52 + i * 110, 33, "•", self.CYAN, 9, True, "center")

        # Centered status cluster
        self.canvas.create_oval(w - 410, 27, w - 398, 39, fill=self.GREEN, outline="")
        self.txt(w - 388, 34, "ONLINE", self.GREEN, 9, True)
        now = datetime.now()
        self.txt(w - 290, 28, now.strftime("%H:%M:%S"), self.TEXT, 14, True)
        self.txt(w - 290, 48, now.strftime("%d %b %Y").upper(), "#7aa9ba", 7)
        if self.security_mode:
            self.canvas.create_rectangle(w - 410, 50, w - 218, 68, outline=self.RED, fill="#2b0b16")
            self.txt(w - 314, 59, "SECURITY MODE ON", self.RED, 7, True, "center")
        for i, icon in enumerate(("⌁", "♩", "◎", "⚙")):
            self.txt(w - 190 + i * 42, 38, icon, self.CYAN, 17, True, "center")

    def draw_left(self, w, h):
        x1, x2 = 18, 445
        y = 88

        # SYSTEM STATUS
        self.panel(x1, y, x2, y + 260, "SYSTEM STATUS")
        stats = [
            ("CPU", self.cpu, "⚙"),
            ("RAM", self.ram, "▣"),
            ("GPU", self.gpu, "◈"),
            ("DISK", 28, "▤"),
            ("NETWORK", 68, "⌁"),
            ("BATTERY", self.battery, "▰"),
        ]
        for i, (name, value, icon) in enumerate(stats):
            yy = y + 43 + i * 34
            self.txt(x1 + 20, yy, icon, self.CYAN, 15, True)
            self.txt(x1 + 52, yy, name, self.TEXT, 9, True)
            self.bar(x1 + 52, yy + 1, 190, value, "", self.CYAN if name != "BATTERY" else self.GREEN)
        self.txt(x2 - 18, y + 225, "0.8 Mbps ↑  0.6 Mbps ↓", "#6ba5b8", 8, False, "e")

        # TEMPERATURE + NETWORK
        self.panel(x1, y + 270, x1 + 205, y + 405, "TEMPERATURE")
        self.txt(x1 + 18, y + 315, f"CPU       {self.temp_cpu}°C", self.TEXT, 9)
        self.txt(x1 + 18, y + 340, f"GPU       {self.temp_gpu}°C", self.TEXT, 9)
        self.txt(x1 + 18, y + 365, f"System    {self.temp_system}°C", self.TEXT, 9)

        self.panel(x1 + 220, y + 270, x2, y + 405, "NETWORK")
        self.txt(x1 + 238, y + 315, "Wi-Fi", self.TEXT, 9)
        self.txt(x1 + 238, y + 335, "Connected", self.GREEN, 9, True)
        self.txt(x1 + 238, y + 358, "IP", "#7fa8b8", 8)
        self.txt(x1 + 275, y + 358, "192.168.1.104", self.TEXT, 8)
        self.txt(x1 + 238, y + 380, "Speed", "#7fa8b8", 8)
        self.txt(x1 + 275, y + 380, "0.8 / 0.6 Mbps", self.TEXT, 8)

        # APPLICATIONS
        ay = y + 415
        self.panel(x1, ay, x2, ay + 190, "APPLICATIONS")
        apps = [
            ("●", "Chrome"), ("⌁", "VS Code"), ("▣", "Files"),
            ("▶", "Web"), ("N", "Notes"), ("◉", "Chat"),
            ("S", "Music"), ("◈", "Comm"),
        ]
        for i, (ico, name) in enumerate(apps):
            col, row = i % 4, i // 4
            bx = x1 + 15 + col * 102
            by = ay + 42 + row * 68
            self.canvas.create_rectangle(
                bx, by, bx + 88, by + 55,
                fill="#081d2c", outline="#0d5573", width=1
            )
            self.canvas.create_oval(
                bx + 27, by + 8, bx + 61, by + 42,
                fill="#0a2738", outline=self.CYAN, width=1
            )
            self.txt(bx + 44, by + 24, ico, self.CYAN2, 14, True, "center", "Segoe UI")
            self.txt(bx + 44, by + 48, name, self.TEXT, 6, False, "center", "Segoe UI")

        # DEVICES
        dy = ay + 200
        self.panel(x1, dy, x2, dy + 150, "DEVICES")
        devices = []
        if self.device_network:
            devices = self.device_network.snapshot()
        self.txt(x1 + 25, dy + 40, "▣", self.CYAN, 15)
        self.txt(x1 + 52, dy + 40, "PC - 01", self.TEXT, 9, True)
        self.txt(x1 + 175, dy + 40, "● ONLINE", self.GREEN, 8, True)
        self.txt(x1 + 245, dy + 40, "(This Device)", "#79aabb", 8)
        for i, d in enumerate(devices[:2]):
            yy = dy + 70 + i * 26
            self.txt(x1 + 25, yy, "▣", self.CYAN, 12)
            self.txt(x1 + 52, yy, str(d.get("name", "DEVICE"))[:15], self.TEXT, 8)
            self.txt(x1 + 175, yy, "● ONLINE", self.GREEN, 8)
            self.txt(x1 + 245, yy, str(d.get("ip", "")), "#79aabb", 8)

        # 3D MODEL PREVIEW — shows the user's actual saved/generated mesh.
        py = dy + 160
        self.panel(x1, py, x2, h - 90, "3D MODEL PREVIEW")
        self._draw_saved_model(x1 + 12, py + 28, x1 + 292, h - 108)
        self.txt(x1 + 305, py + 82, "Model:", self.DIM, 7, True)
        self.txt(x1 + 305, py + 98, self.model_name[:22], self.TEXT, 8, True)
        self.txt(x1 + 305, py + 122, "Format:", self.DIM, 7, True)
        self.txt(x1 + 350, py + 122, (os.path.splitext(self.model_name)[1].upper().replace(".","") or "—"), self.CYAN2, 7, True)
        self.txt(x1 + 305, py + 144, "Status:", self.DIM, 7, True)
        self.txt(x1 + 350, py + 144, "LIVE" if self.model_vertices else "WAITING", self.GREEN, 7, True)
        if self.model_error:
            self.txt(x1 + 305, py + 164, "LOAD ERROR", self.RED, 7, True)

    def _draw_car_wireframe(self, cx, cy, sx, sy):
        c = "#19cfff"
        c2 = "#0b718f"
        body = [
            (cx - sx, cy + 12), (cx - 92, cy - 10), (cx - 46, cy - sy + 5),
            (cx + 44, cy - sy + 8), (cx + 92, cy - 8), (cx + sx, cy + 15),
            (cx + 112, cy + 34), (cx - 112, cy + 34),
        ]
        pts = [v for p in body for v in p]
        self.canvas.create_polygon(pts, fill="", outline=c, width=2)
        self.canvas.create_line(cx - 46, cy - sy + 5, cx - 20, cy + 3, fill=c, width=1)
        self.canvas.create_line(cx + 44, cy - sy + 8, cx + 18, cy + 3, fill=c, width=1)
        self.canvas.create_line(cx - 20, cy + 3, cx + 18, cy + 3, fill=c, width=1)
        for dx in (-82, 82):
            self.canvas.create_oval(cx + dx - 23, cy + 18, cx + dx + 23, cy + 64,
                                    outline=c, width=2)
            self.canvas.create_oval(cx + dx - 10, cy + 31, cx + dx + 10, cy + 51,
                                    outline=c2, width=1)
        for i in range(5):
            self.canvas.create_line(cx - 90 + i * 45, cy + 8,
                                    cx - 75 + i * 45, cy + 38,
                                    fill=c2, width=1)

    def draw_model_showcase(self, w, h, left, right, top, bottom, cx, cy):
        """Full central 3D showcase: hide the normal core animation and show only the real mesh."""
        self.panel(left, top, right, bottom, fill="#020c15")
        self.txt(cx, top + 24, "3D MODEL SHOWCASE", self.CYAN2, 20, True, "center", "Segoe UI")
        self.txt(cx, top + 45, self.model_name[:64], "#8ec8d8", 8, False, "center")

        # Large live mesh viewport
        vx1, vy1 = left + 35, top + 70
        vx2, vy2 = right - 35, bottom - 65
        self.canvas.create_rectangle(vx1, vy1, vx2, vy2,
                                     fill="#010910", outline="#0a5872", width=1)
        # perspective grid
        for gy in range(int(vy1 + 20), int(vy2), 35):
            self.canvas.create_line(vx1, gy, vx2, gy, fill="#06202c")
        for gx in range(int(vx1), int(vx2), 45):
            self.canvas.create_line(gx, vy1, gx, vy2, fill="#06202c")

        if self.model_vertices and self.model_faces:
            cx2 = (vx1 + vx2) / 2
            cy2 = (vy1 + vy2) / 2 + 8

            # Auto-fit the actual projected mesh to the viewport.  This prevents
            # small OBJ/STL models from appearing tiny and prevents large models
            # from being clipped at the edges.
            base_scale = min(vx2-vx1, vy2-vy1) * 0.72 * self.model_zoom
            raw_pts = [self._project_model(v[0], v[1], v[2], cx2, cy2, base_scale)
                       for v in self.model_vertices]
            min_px = min(p[0] for p in raw_pts); max_px = max(p[0] for p in raw_pts)
            min_py = min(p[1] for p in raw_pts); max_py = max(p[1] for p in raw_pts)
            raw_w = max(1.0, max_px - min_px)
            raw_h = max(1.0, max_py - min_py)
            fit = min((vx2-vx1) * 0.72 / raw_w, (vy2-vy1) * 0.62 / raw_h)
            fit = max(0.35, min(2.8, fit))
            scale = base_scale * fit
            pts = [self._project_model(v[0], v[1], v[2], cx2, cy2, scale)
                   for v in self.model_vertices]
            # Render a real filled mesh, back-to-front, then add a subtle edge overlay.
            render_faces=[]
            a=math.radians(self.model_rotation)
            ca,sa=math.cos(a),math.sin(a)
            for face in self.model_faces[:18000]:
                if len(face) < 3: continue
                try:
                    ids=(face[0],face[1],face[2])
                    p3=[self.model_vertices[i] for i in ids]
                except (IndexError,TypeError):
                    continue
                depth=sum((v[0]*sa+v[2]*ca) for v in p3)/3.0
                render_faces.append((depth, ids))
            render_faces.sort(key=lambda item:item[0])
            for depth, ids in render_faces:
                p0,p1,p2=[pts[i] for i in ids]
                shade="#08465a" if depth < 0 else "#0d86a8"
                self.canvas.create_polygon(
                    [p0[0],p0[1],p1[0],p1[1],p2[0],p2[1]],
                    fill=shade, outline="", width=0
                )
            # A light edge pass makes the geometry readable without turning the
            # entire object into a wireframe.
            for depth, ids in render_faces[::max(1, len(render_faces)//900)]:
                p0,p1,p2=[pts[i] for i in ids]
                self.canvas.create_line(p0[0],p0[1],p1[0],p1[1], fill="#19cfff", width=1)
                self.canvas.create_line(p1[0],p1[1],p2[0],p2[1], fill="#19cfff", width=1)
            self.txt(cx2, vy2-15, "● SOLID MESH • LIVE ROTATION", self.GREEN, 8, True, "center")
        else:
            self.txt(cx, cy-15, "3D MODEL MAKER ACTIVE", self.CYAN2, 18, True, "center")
            self.txt(cx, cy+12, "No model loaded yet", self.TEXT, 10, False, "center")
            self.txt(cx, cy+35, "Type: make a 3D model of a drone", self.DIM, 9, False, "center")

        # Minimal model telemetry; no normal core animation in this mode.
        self.panel(left + 18, bottom - 50, right - 18, bottom - 12, fill="#04131d")
        self.txt(left + 35, bottom - 31, "● LIVE MESH", self.GREEN, 8, True)
        self.txt(left + 155, bottom - 31, f"VERTICES {len(self.model_vertices):,}", self.CYAN2, 8, True)
        self.txt(left + 320, bottom - 31, f"FACES {len(self.model_faces):,}", self.CYAN2, 8, True)
        self.txt(right - 35, bottom - 31, "ROTATING", "#83afbd", 8, True, "e")

    def draw_mini_core(self, w, h):
        """Always-visible compact SHASTRA core, pinned bottom-left."""
        cx, cy = 92, h - 92
        pulse = math.sin(self.pulse) * 3
        self.canvas.create_oval(cx-48-pulse, cy-48-pulse, cx+48+pulse, cy+48+pulse,
                                outline="#073c56", width=1)
        self.canvas.create_oval(cx-39, cy-39, cx+39, cy+39,
                                outline="#0c9dc6", width=2)
        self.canvas.create_oval(cx-29, cy-29, cx+29, cy+29,
                                outline="#49e7ff", width=1)
        for i in range(10):
            a = math.radians(self.angle * (1 if i % 2 == 0 else -1) + i * 36)
            x = cx + math.cos(a) * 38
            y = cy + math.sin(a) * 38
            self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=self.CYAN2, outline="")
        self.canvas.create_oval(cx-12, cy-12, cx+12, cy+12,
                                fill="#06141f", outline="#16d9ff", width=2)
        self.txt(cx, cy+1, "F", self.CYAN2, 11, True, "center")
        self.txt(cx, cy+58, "SHASTRA CORE", self.CYAN2, 7, True, "center")

    def draw_center(self, w, h):
        left = 458
        right = w - 425
        top = 88
        bottom = h - 92
        cx = (left + right) / 2
        cy = (top + bottom) / 2 + 5
        self.core_cx, self.core_cy = cx, cy

        # Center title
        self.panel(cx - 200, top, cx + 200, top + 55, fill="#041521")
        self.txt(cx, top + 22, "SHASTRA CORE", self.CYAN2, 20, True, "center", "Segoe UI")
        self.txt(cx, top + 43, "AI ASSISTANT  •  MULTI DEVICE  •  ALWAYS WITH YOU",
                 "#b6dce7", 7, False, "center")

        if self.model_showcase:
            # In 3D showcase mode the normal SHASTRA core animation is hidden.
            # The showcase is also visible immediately after activation, before a mesh exists.
            self.draw_model_showcase(w, h, left, right, top + 58, bottom, cx, cy)
            return

        # Central animated energy field
        pulse = math.sin(self.pulse) * 5
        for radius, color, width in [
            (245, "#073c56", 1), (215, "#07516d", 2),
            (185, "#0b7392", 1), (155, "#0c9dc6", 2),
            (125, "#20d5fa", 1), (92, "#49e7ff", 2)
        ]:
            r = radius + pulse * (1 if radius < 160 else 0.4)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                    outline=color, width=width)

        # Segmented rotating rings
        for idx, radius in enumerate((232, 198, 165, 135)):
            direction = 1 if idx % 2 == 0 else -1
            for seg in range(18):
                start = self.angle * direction + seg * 20
                extent = 7 + (seg % 3) * 4
                self.canvas.create_arc(
                    cx-radius, cy-radius, cx+radius, cy+radius,
                    start=start, extent=extent, style="arc",
                    outline=self.CYAN if seg % 4 == 0 else "#0b7594",
                    width=2 if seg % 4 == 0 else 1
                )

        # Orbiting nodes
        for i in range(26):
            a = math.radians(self.angle * (0.55 + (i % 2) * 0.25) + i * 360 / 26)
            r = 105 + 65 * math.sin(self.pulse * 1.5 + i * 0.7)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r
            s = 2 if i % 3 else 4
            self.canvas.create_oval(x-s, y-s, x+s, y+s,
                                    fill=self.CYAN2, outline="")

        # Radial beams
        for i in range(16):
            a = math.radians(self.angle + i * 22.5)
            inner = 65
            outer = 250 + 15 * math.sin(self.pulse + i)
            x1, y1 = cx + math.cos(a)*inner, cy + math.sin(a)*inner
            x2, y2 = cx + math.cos(a)*outer, cy + math.sin(a)*outer
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill="#0a5570", width=1)

        # Core glow
        for r, outline, width in [(74, "#0b5d7a", 2), (58, "#1ccfff", 3), (42, "#b5f9ff", 2)]:
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                    fill="#031d2b", outline=outline, width=width)
        self.canvas.create_oval(cx-30, cy-30, cx+30, cy+30,
                                fill="#0a77a4", outline="#d6fbff", width=2)
        self.txt(cx, cy - 5, "S", "white", 22, True, "center", "Segoe UI")
        self.txt(cx, cy + 19, "CORE", self.CYAN2, 7, True, "center")

        # Labels around the core
        for label, deg in (("VOICE", -90), ("VISION", 0),
                           ("AUTOMATION", 90), ("WEB", 180)):
            a = math.radians(deg)
            rr = 280
            self.txt(cx + math.cos(a)*rr, cy + math.sin(a)*rr,
                     label, "#3f9eb9", 8, True, "center")

        # Waveform
        pts = []
        for xx in range(int(cx-175), int(cx+176), 5):
            val = (math.sin(xx * 0.13 + self.wave) * 8 +
                   math.sin(xx * 0.037 + self.wave * .6) * 5)
            pts.extend((xx, cy + 160 + val))
        self.canvas.create_line(*pts, fill=self.CYAN, width=2)

        # Center mode rail
        self.panel(left, h - 210, right, h - 105, fill="#04131d")
        modes = [
            ("◉", "LISTENING"), ("◎", "UNDERSTANDING"),
            ("◌", "RESEARCHING"), ("◇", "THINKING"),
            ("◆", "SUGGESTING"), ("▶", "EXECUTING"), ("●", "READY")
        ]
        for i, (ico, name) in enumerate(modes):
            x = left + 75 + i * ((right-left-150) / 6)
            col = self.CYAN2 if name == "READY" else "#74a9ba"
            self.txt(x, h - 157, ico, col, 12, True, "center")
            self.txt(x, h - 135, name, col, 7, True, "center")

        # Listening panel
        self.panel(cx - 240, h - 100, cx + 145, h - 18, fill="#04131d")
        self.hex_icon(cx - 195, h - 59, 27, "♩")
        self.txt(cx - 155, h - 78, "LISTENING...", self.CYAN2, 11, True)
        wave_pts = []
        for xx in range(int(cx-145), int(cx+115), 4):
            yy = h - 56 + math.sin(xx*.12 + self.wave)*7 * (0.7 + self.voice_level)
            wave_pts.extend((xx, yy))
        self.canvas.create_line(*wave_pts, fill=self.CYAN, width=2)
        self.txt(cx - 155, h - 33, "“Hey Shastra, I want to make a 3D model project...”",
                 "#b5dbe4", 7)

    def draw_right(self, w, h):
        x1 = w - 410
        x2 = w - 18

        # Advisor mode
        self.panel(x1, 88, x2, 220, "CURRENT MODE")
        self.hex_icon(x1 + 43, 145, 29, "✦")
        self.txt(x1 + 82, 132, self.mode, self.CYAN2, 11, True)
        self.txt(x1 + 82, 153, self.mode_detail, "#82afbe", 8)
        # mini waveform
        pts = []
        for xx in range(x1 + 82, x2 - 20, 5):
            yy = 191 + math.sin(xx*.22 + self.wave)*7
            pts.extend((xx, yy))
        self.canvas.create_line(*pts, fill=self.CYAN, width=2)

        # Conversation memory
        self.panel(x1, 230, x2, 360, "CONVERSATION MEMORY")
        memories = [
            ("Webpage project plan", "2h ago"),
            ("3D model project", "4h ago"),
            ("Business ideas", "6h ago"),
            ("Study plan", "1d ago"),
            ("General chat", "1d ago"),
        ]
        for i, (a, b) in enumerate(memories):
            yy = 263 + i * 18
            self.txt(x1 + 15, yy, "◉", self.CYAN, 7)
            self.txt(x1 + 30, yy, a, self.TEXT, 7)
            self.txt(x2 - 14, yy, b, "#78a2b1", 7, False, "e")

        # Chat. Keep the panel clean and readable.
        chat_top = 370
        chat_bottom = h - 170
        self.panel(x1, chat_top, x2, chat_bottom, "SHASTRA")
        self.txt(x2 - 35, chat_top + 13, "×", self.CYAN, 17, True, "center")
        self.txt(x2 - 17, chat_top + 13, "⌃", self.CYAN, 13, True, "center")

        # Dedicated control strip behind the Tk widgets.
        self.canvas.create_rectangle(x1 + 8, h - 166, x2 - 8, h - 62,
                                     fill="#081c2a", outline="#123d57", width=1)
        self.txt(x1 + 12, h - 64, "VOICE • TYPE • EXECUTE • IMAGE → 3D", "#7ab9c9", 7, True)

    def draw_footer(self, w, h):
        self.txt(28, h - 23, "BIGGER DREAMS  •  SMARTER SOLUTIONS  •  SHASTRA",
                 self.CYAN, 8, True)
        self.panel(w - 405, h - 57, w - 18, h - 10, fill="#04131d")
        self.txt(w - 380, h - 34, "DREAM", self.CYAN2, 9, True)
        self.txt(w - 327, h - 34, "›", self.CYAN, 12, True)
        self.txt(w - 307, h - 34, "PLAN", self.CYAN2, 9, True)
        self.txt(w - 254, h - 34, "›", self.CYAN, 12, True)
        self.txt(w - 234, h - 34, "BUILD", self.CYAN2, 9, True)
        self.txt(w - 178, h - 34, "›", self.CYAN, 12, True)
        self.txt(w - 158, h - 34, "ACHIEVE", self.CYAN2, 9, True)
        self.txt(w - 64, h - 34, "— SHASTRA", self.CYAN, 8, True)

    # --------------------------- animation ---------------------------------

    def _update_stats(self):
        if PSUTIL_OK:
            try:
                self.cpu = max(0, min(100, psutil.cpu_percent(interval=None)))
                self.ram = max(0, min(100, psutil.virtual_memory().percent))
                self.battery = int(psutil.sensors_battery().percent) if psutil.sensors_battery() else self.battery
                self.temp_cpu = int(self.cpu / 2.2 + 36)
                self.temp_gpu = int(40 + self.gpu * .12)
                self.temp_system = int(35 + self.ram * .08)
            except Exception:
                pass
        else:
            # Smooth demo telemetry keeps the HUD alive without dependencies.
            self.cpu = 18 + int(8 * (math.sin(self.wave * .4) + 1))
            self.ram = 42 + int(5 * math.sin(self.wave * .23))
            self.gpu = 12 + int(4 * math.sin(self.wave * .31))

    def animate(self):
        if not self.running:
            return

        w, h = self._w(), self._h()
        self.angle = (self.angle + 1.8) % 360
        if self.model_vertices:
            self.model_rotation = (self.model_rotation + 0.65) % 360
        self.pulse += 0.075
        self.wave += 0.42
        self.scan = (self.scan + 4) % max(1, h)

        self._update_stats()

        self.canvas.delete("all")

        # Background grid
        self.canvas.create_rectangle(0, 0, w, h, fill=self.BG, outline="")
        for x in range(0, w, 45):
            self.canvas.create_line(x, 76, x, h, fill=self.GRID)
        for y in range(80, h, 45):
            self.canvas.create_line(0, y, w, y, fill=self.GRID)

        # Moving scan beam
        self.canvas.create_line(0, self.scan, w, self.scan,
                                fill="#06394e", width=1)

        self.draw_header(w)
        self.draw_left(w, h)
        self.draw_center(w, h)
        self.draw_mini_core(w, h)
        self.draw_right(w, h)
        self.draw_footer(w, h)

        self._place_widgets()
        self.clock_update()
        self.root.after(45, self.animate)

    def clock_update(self):
        # Clock is drawn in the header, so this method intentionally remains tiny.
        pass

    # --------------------------- engine callbacks --------------------------

    def _ui(self, callback):
        if threading.get_ident() == self.ui_thread_id:
            callback()
        else:
            try:
                self.root.after(0, callback)
            except Exception:
                pass

    def set_devices(self, network):
        self._ui(lambda: setattr(self, "device_network", network))

    def log_event(self, text):
        def update():
            self.log_lines.append(str(text))
            self.log_lines = self.log_lines[-20:]
        self._ui(update)

    def set_command(self, text):
        def update():
            self.last_command = str(text)
            if text and self.mode not in ("LISTENING", "READY"):
                self.mode_detail = str(text)[:42]
        self._ui(update)

    def set_status(self, text):
        def update():
            self.last_status = str(text)
            status = str(text).upper()
            if "FRIEND" in status:
                self.mode = "FRIEND MODE"; self.mode_detail = "Conversation & continuity"
            elif "RESEARCH" in status or "ADVISOR" in status:
                self.mode = "ADVISOR MODE"; self.mode_detail = "Researching & Suggesting..."
            elif "TRANSCRIB" in status or "UNDERSTAND" in status:
                self.mode = "UNDERSTANDING MODE"; self.mode_detail = status[:36]
            elif "SPEECH DETECTED" in status:
                self.mode = "LISTENING"; self.mode_detail = "Command detected — keep speaking..."
            elif "PREPARING MICROPHONE" in status:
                self.mode = "LISTENING"; self.mode_detail = "Starting microphone..."
            elif "LISTENING - SPEAK NOW" in status:
                self.mode = "LISTENING"; self.mode_detail = "Microphone active — speak now..."
            elif (
                status.endswith(("READY", "COMPLETE", "OFF"))
                or status in ("ERROR", "VOICE ERROR", "NOT FOUND")
            ):
                self.mode = "READY"; self.mode_detail = status[:36]
            elif "PROCESSING" in status or "COMMAND RECEIVED" in status:
                self.mode = "EXECUTING"; self.mode_detail = status[:36]
            elif "EXEC" in status or "TASK" in status or "3D" in status:
                self.mode = "EXECUTING"; self.mode_detail = status[:36]
            elif "LISTEN" in status or "NO SPEECH" in status:
                self.mode = "LISTENING"; self.mode_detail = status[:36]
            else:
                self.mode = "READY"; self.mode_detail = status[:36]
        self._ui(update)

    def set_vision(self, text):
        self._ui(lambda: setattr(self, "vision_text", str(text)))

    def show_camera_preview(self, image_bytes):
        """Show the exact still SHASTRA is about to submit for visual search."""
        def update():
            try:
                import numpy as np

                frame = cv2.imdecode(
                    np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if frame is None:
                    raise RuntimeError("The captured camera JPEG could not be decoded.")

                height, width = frame.shape[:2]
                scale = min(1.0, 960 / width, 640 / height)
                if scale < 1.0:
                    frame = cv2.resize(
                        frame,
                        (max(1, int(width * scale)), max(1, int(height * scale))),
                        interpolation=cv2.INTER_AREA,
                    )
                encoded, preview = cv2.imencode(".png", frame)
                if not encoded:
                    raise RuntimeError("The captured camera still could not be previewed.")

                if (
                    self.camera_preview_window is not None
                    and self.camera_preview_window.winfo_exists()
                ):
                    self.camera_preview_window.destroy()
                window = tk.Toplevel(self.root)
                window.title("SHASTRA — Captured Camera Still")
                window.configure(bg=self.BG)
                photo = tk.PhotoImage(
                    data=base64.b64encode(preview.tobytes()).decode("ascii")
                )
                image_label = tk.Label(window, image=photo, bg=self.BG)
                image_label.pack(padx=12, pady=(12, 6))
                tk.Label(
                    window,
                    text=(
                        f"Captured still: {width} × {height} pixels — "
                        "this exact image is being searched"
                    ),
                    bg=self.BG,
                    fg=self.CYAN2,
                    font=("Segoe UI", 10),
                ).pack(padx=12, pady=(0, 12))
                tk.Button(
                    window,
                    text="SAVE STILL AS...",
                    command=self.save_camera_preview,
                    bg="#07384d",
                    fg=self.CYAN2,
                    activebackground="#0b5a73",
                    activeforeground="white",
                    relief="flat",
                    bd=0,
                    font=("Consolas", 9, "bold"),
                    cursor="hand2",
                ).pack(padx=12, pady=(0, 8))
                self.camera_preview_status = tk.Label(
                    window, text="", bg=self.BG, fg=self.GREEN,
                    font=("Segoe UI", 9)
                )
                self.camera_preview_status.pack(padx=12, pady=(0, 10))
                window.camera_preview_photo = photo
                self.camera_preview_photo = photo
                self.camera_preview_bytes = image_bytes
                self.camera_preview_window = window
                window.protocol("WM_DELETE_WINDOW", window.destroy)
            except Exception as exc:
                message = "Could not display the captured camera preview: " + str(exc)
                self.log_event(message)
                self.set_status("CAMERA PREVIEW ERROR")
                print("[CAMERA PREVIEW ERROR]", repr(exc), flush=True)

        self._ui(update)

    def save_camera_preview(self):
        """Save the requested camera still only when the user chooses a location."""
        if not self.camera_preview_bytes:
            self.set_status("NO CAMERA STILL TO SAVE")
            return
        path = filedialog.asksaveasfilename(
            title="Save SHASTRA camera still",
            defaultextension=".jpg",
            filetypes=[("JPEG image", "*.jpg"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "wb") as image_file:
                image_file.write(self.camera_preview_bytes)
        except OSError as exc:
            message = "Could not save the camera still: " + str(exc)
            self.log_event(message)
            self.set_status("CAMERA IMAGE SAVE ERROR")
            print("[CAMERA SAVE ERROR]", repr(exc), flush=True)
            return
        if self.camera_preview_status is not None:
            self.camera_preview_status.configure(text="Saved: " + path)
        self.log_event("CAMERA STILL SAVED: " + path)
        self.set_status("CAMERA STILL SAVED")

    def set_answer(self, text):
        """Store a complete SHASTRA answer and refresh the scrollable chat."""
        def update():
            answer = str(text).strip()
            if not answer:
                return
            self.last_answer = answer
            self.messages.append(("SHASTRA", answer, False))
            self.messages = self.messages[-30:]
            self.chat_scroll_user = False
            self._refresh_chat_widget(autoscroll=True)
            if self.engine and getattr(self.engine, "running", False):
                # Every SHASTRA answer is spoken. Engine.speak() deduplicates
                # explicit speak() calls already present in command handlers.
                self.engine.speak(answer)
        self._ui(update)

    def add_user_message(self, text):
        def update():
            msg = str(text).strip()
            if not msg:
                return
            self.messages.append(("YOU", msg, True))
            self.messages = self.messages[-30:]
            self.chat_scroll_user = False
            self._refresh_chat_widget(autoscroll=True)
        self._ui(update)

    # --------------------------- 3D model preview --------------------------

    def set_security_mode(self, enabled, message=""):
        def update():
            self.security_mode=bool(enabled)
            self.mode="SECURITY MODE" if enabled else "READY"
            self.mode_detail="Wireless + network locked" if enabled else "All systems available"
            self.last_status="SECURITY MODE ON" if enabled else "SECURITY MODE OFF"
            if message:
                self.messages.append(("SHASTRA",message,False)); self.messages=self.messages[-30:]; self._refresh_chat_widget(autoscroll=True)
        self._ui(update)

    def show_3d_model(self, path):
        """Load a local OBJ/STL/PLY into the built-in dependency-free preview."""
        def work():
            try:
                verts, faces = load_3d_wireframe(path)
                if not verts or not faces:
                    raise ValueError("No supported mesh geometry was found in the file.")
                # Normalize once; rendering then stays fast even for large files.
                if len(verts) > 12000:
                    step=max(1, len(verts)//12000)
                    keep=verts[::step]
                    # A sampled vertex set cannot safely preserve faces, so fall back
                    # to a bounded face list while retaining original indices.
                    faces=faces[:18000]
                xs=[v[0] for v in verts]; ys=[v[1] for v in verts]; zs=[v[2] for v in verts]
                cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
                scale=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs),1e-6)
                norm=[((x-cx)/scale,(y-cy)/scale,(z-cz)/scale) for x,y,z in verts]
                name=os.path.basename(path)
                def apply():
                    self.model_path=path
                    self.model_name=name
                    self.model_vertices=norm
                    self.model_faces=faces[:18000]
                    self.model_zoom=1.0
                    self.model_rotation=0.0
                    self.model_error=""
                    self.model_showcase = True
                    self.vision_text=f"✓  3D MODEL LOADED\n\n{name[:50]}\n\nVertices: {len(norm)}\nFaces: {len(faces)}\nPreview: LIVE"
                    self.last_status="3D MODEL LOADED"
                    self.mode="3D SHOWCASE"; self.mode_detail="Model preview active"
                self._ui(apply)
            except Exception as exc:
                self._ui(lambda: setattr(self,"model_error",str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def show_latest_3d_model(self, query=""):
        path=find_saved_3d_model(query)
        if not path:
            self.set_status("NO 3D MODEL")
            self.set_vision("×  NO SAVED 3D MODEL FOUND\n\nSave an OBJ, STL, or ASCII PLY in:\n"+MODEL_OUTPUT_DIR)
            return None
        self.show_3d_model(path)
        self.log_event("3D PREVIEW: "+path)
        return path

    def _project_model(self, x, y, z, cx, cy, scale):
        # Simple isometric projection with automatic animated rotation.
        a=math.radians(self.model_rotation)
        ca,sa=math.cos(a),math.sin(a)
        rx=x*ca-z*sa; rz=x*sa+z*ca
        px=cx + (rx- y)*0.78*scale
        py=cy + (rx+y)*0.30*scale - rz*0.92*scale
        return px,py

    def _draw_saved_model(self, x1, y1, x2, y2):
        cx=(x1+x2)/2; cy=(y1+y2)/2+8
        if not self.model_vertices or not self.model_faces:
            self._draw_car_wireframe(cx,cy,min(145,(x2-x1)*.35),55)
            self.txt(cx, y2-17, "SAVE / GENERATE A MODEL", self.DIM, 7, True, "center")
            return
        scale=min(x2-x1,y2-y1)*0.92*self.model_zoom
        pts=[]
        for v in self.model_vertices:
            pts.append(self._project_model(v[0],v[1],v[2],cx,cy,scale))
        # Draw far-to-near approximately using average transformed z.
        for face in self.model_faces[:18000]:
            try:
                p0,p1,p2=[pts[i] for i in face]
            except (IndexError,TypeError): continue
            self.canvas.create_polygon([p0[0],p0[1],p1[0],p1[1],p2[0],p2[1]], fill="#0b718f", outline="#19cfff", width=1)
        self.txt(x1+12,y2-18,"● LIVE MESH PREVIEW",self.GREEN,7,True)

    # --------------------------- controls ----------------------------------

    def submit_text(self):
        text = self.chat_entry.get().strip()
        if not text:
            return
        self.chat_entry.delete(0, "end")
        self.add_user_message(text)
        if self.engine:
            self.engine.submit_command(text)

    def start_camera_search(self):
        if not self.engine:
            self.set_status("CORE OFFLINE")
            return
        command = "analyze camera"
        self.add_user_message(command)
        self.engine.submit_command(command)

    def quick_command(self, text):
        mapping = {
            "YES, SHOW ROADMAP": "show me the roadmap",
            "PROJECT IDEAS": "give me project ideas",
            "BLENDER BASICS": "explain blender basics",
            "MAKE 3D CAR": "make a generic sports car 3d model",
        }
        cmd = mapping.get(text, text)
        self.add_user_message(cmd)
        if self.engine:
            self.engine.submit_command(cmd)

    def start_voice(self):
        if not self.engine:
            return
        if not self.voice_control_enabled:
            self.set_status("VOICE CONTROL OFF")
            return
        self.set_status("LISTENING")
        # Engine.voice_loop is the sole microphone owner. Starting a second
        # listener here races the same non-blocking listen lock and loses input.
        self.log_event("MIC button pressed; speak now to the active SHASTRA listener.")
        self.engine.request_voice_capture()

    def _voice_result(self, text):
        self.add_user_message(text)
        if self.engine:
            self.engine.submit_command(text)

    def shutdown(self):
        self.running = False
        try:
            if self.engine:
                self.engine.running = False
            if self.device_network:
                self.device_network.stop()
            if self.mobile_server:
                self.mobile_server.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


class Engine:

    def __init__(self, hud, session=None):

        self.hud = hud
        self.session = dict(session or SHASTRA_AI_SESSION)

        self.voice = Voice()
        self.voice.process_launcher = self._launch_process_on_ui
        self.voice.status_callback = self.hud.set_status

        self.memory = Memory()

        self.router = CommandRouter()

        self.screen = ScreenAgent(hud)

        self.computer = ComputerAgent(self.screen)

        self.launcher = Launcher()

        self.device_network = None
        self.running = True
        self.hud.engine = self

        # Ordered command execution: only one command may mutate the UI/core at a time.
        self.command_queue = queue.Queue()
        self.command_busy = threading.Event()
        self.voice_capture_requested = threading.Event()
        self.command_thread = threading.Thread(target=self._command_worker, daemon=True)
        self.command_thread.start()

        # Ordered speech execution: never start one TTS thread per answer.
        self.speech_queue = queue.Queue()
        self.last_voice_command = ""
        self.last_voice_command_time = 0.0
        self._last_spoken_text = ""
        self._last_spoken_time = 0.0
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()

    def request_voice_capture(self):
        self.voice_capture_requested.set()

    def _launch_process_on_ui(self, command, **kwargs):
        if threading.get_ident() == self.hud.ui_thread_id:
            return subprocess.Popen(command, **kwargs)

        completed = threading.Event()
        result = {}

        def launch():
            try:
                result["process"] = subprocess.Popen(command, **kwargs)
            except Exception as exc:
                result["error"] = exc
            finally:
                completed.set()

        self.hud._ui(launch)
        if not completed.wait(timeout=15):
            raise RuntimeError("Timed out waiting for the Windows UI thread to start speech.")
        if "error" in result:
            raise RuntimeError(f"Could not start the Windows speech process: {result['error']}") from result["error"]
        return result["process"]

    def submit_command(self, text):
        if not text or not self.running:
            return
        cleaned = str(text).strip()
        if not cleaned:
            return
        # The command thread is normally responsible for serializing execution, but
        # if it is not alive yet (or has died) a typed/voice command must still be
        # accepted immediately instead of silently being dropped.
        if getattr(self, "command_thread", None) is not None and self.command_thread.is_alive():
            self.command_busy.set()
            self.command_queue.put(cleaned)
            return
        self.command_busy.set()
        try:
            self.execute(cleaned)
        except Exception as exc:
            try:
                self.hud.log_event("COMMAND FALLBACK ERROR: " + str(exc))
                self.hud.set_status("COMMAND ERROR")
            except Exception:
                pass
        finally:
            self.command_busy.clear()

    def _is_math_teacher_activation(self, normalized):
        # Full commands plus short natural triggers.  The user can simply say/type
        # "math", "maths", or "math teaching mode" to enter the teaching mode.
        aliases = (
            "math teacher mode activate", "maths teacher mode activate",
            "activate math teacher mode", "activate maths teacher mode",
            "activate math teaching mode", "activate maths teaching mode",
            "start math teacher mode", "start maths teacher mode",
            "start math teaching mode", "start maths teaching mode",
            "math teacher mode on", "maths teacher mode on",
            "math teaching mode on", "maths teaching mode on",
            "enable math teacher mode", "enable maths teacher mode",
            "enable math teaching mode", "enable maths teaching mode",
            "maths mode activate", "math mode activate",
            "math teacher activate", "maths teacher activate",
            "activate math", "activate maths",
            "start math", "start maths",
        )
        if normalized in aliases:
            return True
        return normalized in (
            "math", "maths", "math teacher", "maths teacher",
            "math teaching", "maths teaching",
            "math teaching mode", "maths teaching mode",
        )

    def _is_math_teacher_deactivation(self, normalized):
        return normalized in (
            "math teacher mode deactivate", "maths teacher mode deactivate",
            "deactivate math teacher mode", "deactivate maths teacher mode",
            "deactivate math teaching mode", "deactivate maths teaching mode",
            "stop math teacher mode", "stop maths teacher mode",
            "stop math teaching mode", "stop maths teaching mode",
            "math teacher mode off", "maths teacher mode off",
            "math teaching mode off", "maths teaching mode off",
            "disable math teacher mode", "disable maths teacher mode",
            "disable math teaching mode", "disable maths teaching mode",
            "maths mode deactivate", "math mode deactivate",
            "math teacher off", "maths teacher off",
            "math teaching off", "maths teaching off",
        )

    def _is_obvious_computer_command(self, normalized):
        prefixes = (
            "open ", "launch ", "start ", "run ", "type ", "write ",
            "click", "right click", "double click", "press ", "scan ",
            "minimize", "maximize", "switch window", "close ",
            "make a 3d", "create a 3d", "generate a 3d", "build a 3d",
            "3d model maker", "activate 3d", "start 3d", "enable 3d",
            "security mode", "send to ", "control ",
        )
        return normalized in ("click", "right click", "double click", "exit", "quit") or normalized.startswith(prefixes)

    def _execute_math_teacher(self, question):
        self.hud.set_status("MATHS TEACHER")
        self.hud.mode = "MATHS TEACHER MODE"
        self.hud.mode_detail = "Step-by-step teaching"
        self.hud.set_vision(
            "◉ MATHS TEACHER\n\n"
            "MODE: ACTIVE\n"
            "STEP 1 → Understand the problem\n"
            "STEP 2 → Show the method\n"
            "STEP 3 → Calculate\n"
            "STEP 4 → Check\n"
            "STEP 5 → Final answer"
        )
        answer = solve_math_step_by_step(question)
        self.hud.set_answer(answer)
        self.hud.log_event("MATHS TEACHER SOLVED: " + question)
        self.speak(answer)
        self.hud.set_status("MATH LESSON READY")

    def _analyze_camera_image(self):
        self.hud.set_status("CAMERA CAPTURE")
        self.hud.set_vision(
            "◉ SHASTRA CAMERA SEARCH\n\n"
            "Capturing one still image...\n"
            "The still will be uploaded to Google visual search."
        )
        self.hud.log_event("CAMERA SEARCH: capturing one requested still")
        image_bytes = None
        image_text = ""
        try:
            image_bytes = capture_camera_image()
            self.hud.show_camera_preview(image_bytes)
            image_text = extract_camera_image_text(image_bytes)
            self.hud.set_status("SEARCHING IMAGE")
            self.hud.set_vision(
                "◉ SHASTRA CAMERA SEARCH\n\n"
                "Still captured and shown in the preview window.\n"
                + ("Reading visible text and " if image_text else "")
                + "uploading this same still for visual search..."
            )
            search_url, results, visible_text = search_camera_image(image_bytes)
            answer = summarize_camera_search(
                search_url, results, visible_text, image_text
            )
            if not results:
                webbrowser.open(search_url)
            self.hud.set_answer(answer)
            self.hud.set_status("CAMERA SEARCH READY")
            self.hud.log_event(
                f"CAMERA SEARCH COMPLETE: {len(results)} visual matches"
            )
            print("\n===== SHASTRA CAMERA SEARCH =====\n" + answer + "\n===============================\n")
            self.speak(answer)
        except Exception as exc:
            if image_bytes:
                lens_url = "https://lens.google.com/"
                answer = summarize_camera_search(
                    lens_url,
                    [],
                    "Automatic visual search was unavailable: " + str(exc),
                    image_text,
                )
                answer += (
                    "\n\nThe camera still was captured and is shown in the preview "
                    "window. Automatic visual search failed: "
                    f"{str(exc)[:300]}. Google Lens is open, but it did not receive "
                    "the still automatically. Use SAVE STILL AS... in the preview "
                    "window, then upload that saved image in Lens to retry."
                )
                try:
                    webbrowser.open(lens_url)
                except Exception as browser_exc:
                    self.hud.log_event(
                        "Could not open Google Lens: " + str(browser_exc)
                    )
                self.hud.set_answer(answer)
                self.hud.set_vision(
                    "◉ CAMERA STILL CAPTURED\n\n"
                    "The captured still is shown in its preview window.\n"
                    "Automatic visual search was unavailable.\n"
                    + ("Visible text was sent to web research." if image_text
                       else "Google Lens opened; the image must be selected manually.")
                )
                self.hud.set_status("CAMERA SEARCH FALLBACK")
                self.hud.log_event(
                    "CAMERA IMAGE CAPTURED; automatic visual search unavailable: "
                    + str(exc)
                )
                self.speak(answer)
            else:
                message = "Camera search failed: " + str(exc)
                self.hud.set_answer(message)
                self.hud.set_vision("× SHASTRA CAMERA SEARCH\n\n" + str(exc)[:500])
                self.hud.set_status("CAMERA SEARCH ERROR")
                self.hud.log_event(message)
                print("[CAMERA SEARCH ERROR]", repr(exc), flush=True)
                self.speak(message)

    def _command_worker(self):
        while self.running:
            try:
                command = self.command_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if command is None:
                self.command_queue.task_done()
                break
            self.command_busy.set()
            try:
                self.execute(command)
            except Exception as exc:
                message = f"Command failed: {exc}"
                self.hud.log_event("COMMAND ERROR: " + repr(exc))
                self.hud.set_status("COMMAND ERROR")
                self.hud.set_answer(message)
            finally:
                self.command_queue.task_done()
                if self.command_queue.empty():
                    self.command_busy.clear()

    def _speech_worker(self):
        com_initialized = False
        try:
            if os.name == "nt" and PYTHONCOM_OK:
                pythoncom.CoInitialize()
                com_initialized = True
            while self.running or not self.speech_queue.empty():
                try:
                    text = self.speech_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if text is None:
                    self.speech_queue.task_done()
                    break
                try:
                    if not self.voice.speak(text):
                        self.hud.log_event("TTS ERROR: No speech backend could speak the answer.")
                        self.hud.set_status("VOICE ERROR")
                except Exception as exc:
                    try:
                        self.hud.log_event("TTS ERROR: " + str(exc))
                        # Recreate pyttsx3 once after an unexpected backend failure.
                        if TTS_OK:
                            try:
                                self.voice.engine = pyttsx3.init()
                                self.voice.engine.setProperty("rate", 175)
                                self.voice.engine.setProperty("volume", 1.0)
                                if self.voice.speak(text):
                                    self.hud.log_event("TTS RECOVERED")
                            except Exception as retry_exc:
                                self.hud.log_event("TTS RETRY ERROR: " + str(retry_exc))
                    except Exception:
                        pass
                finally:
                    self.speech_queue.task_done()
        except Exception as exc:
            self.hud.log_event("TTS THREAD ERROR: " + str(exc))
            self.hud.set_status("VOICE ERROR")
        finally:
            if com_initialized:
                pythoncom.CoUninitialize()

    def speak(self, text):
        if not text or not self.running:
            return
        text = str(text).strip()
        if not text:
            return
        # Prevent duplicate speech when a command path explicitly calls speak()
        # after set_answer().  Prefix/equivalent answers within a few seconds are
        # treated as the same answer.
        now = time.time()
        clean = re.sub(r"\s+", " ", text).strip().lower()
        previous = re.sub(r"\s+", " ", self._last_spoken_text).strip().lower()
        if previous and (clean == previous or clean.startswith(previous) or previous.startswith(clean)) and now - self._last_spoken_time < 4.0:
            return
        self._last_spoken_text = text
        self._last_spoken_time = now
        self.hud.log_event("SHASTRA SPEAK: " + text)
        try:
            self.memory.log_interaction(self.hud.last_command, text)
        except Exception:
            pass
        self.voice.speaking.set()
        self.speech_queue.put(text)



    def execute(self, raw):

        if not raw:

            return



        raw = raw.strip()

        if not raw:

            return

        if re.search(r"[\u0900-\u097F]", raw):
            self.voice.set_language("mr")
            self.hud.set_status("MARATHI MODE")

        self.hud.set_command(raw)
        self.hud.set_status("EXECUTING")
        self.hud.log_event("INPUT: " + raw)
        print(f"[EXECUTE] Starting command: {raw!r}", flush=True)



        normalized = self.router.normalize(raw)

        # Always print the final transcript and normalized command. This makes
        # it clear whether a failure is speech recognition or command routing.
        print(f"[COMMAND RECEIVED] raw={raw!r} | normalized={normalized!r}", flush=True)

        camera_question = normalized in (
            "analyze camera",
            "analyze the camera",
            "camera search",
            "search camera",
            "search camera image",
            "search what the camera sees",
            "identify camera image",
            "analyze my camera",
            "what am i looking at",
            "look through camera",
            "look through the camera",
            "what do you see",
            "what do you see through the camera",
            "what do you see here",
            "what is in the camera",
            "what s in the camera",
            "what is this",
            "what is that",
            "what's this",
            "what's that",
            "what s this",
            "what s that",
            "what is this thing",
            "what is that thing",
            "identify this",
            "identify that",
            "identify this object",
            "identify that object",
            "describe this",
            "describe that",
            "describe this image",
            "describe this picture",
            "tell me about this",
            "tell me about that",
            "look at this",
            "look at that",
            "analyze this",
            "analyze that",
            "analyze this image",
            "what is in this image",
            "what s in this image",
            "what is in this picture",
            "what s in this picture",
            "what is in the image",
            "what s in the image",
            "what is in the photo",
            "what s in the photo",
            "what is in front of me",
            "what s in front of me",
            "what am i showing you",
        )
        if camera_question or re.match(
            r"^(?:what is|what's|identify|describe|analyze|analyse|look at|tell me about)\s+"
            r"(?:this|that|the)\s+(?:image|picture|photo|object|thing|item)$",
            normalized,
        ):
            self._analyze_camera_image()
            return

        # ---------------- VOICE CONTROL ----------------
        if normalized in ("voice control on", "activate voice control", "turn on voice control", "enable voice control"):
            self.hud.voice_control_enabled = True
            self.hud.set_status("VOICE CONTROL ON")
            self.hud.set_answer("Voice Control is ON. Speak a command or use the command box.")
            self.hud.log_event("VOICE CONTROL ENABLED")
            self.speak("Voice Control is on.")
            return
        if normalized in ("voice control off", "deactivate voice control", "turn off voice control", "disable voice control"):
            self.hud.voice_control_enabled = False
            self.hud.set_status("VOICE CONTROL OFF")
            self.hud.set_answer("Voice Control is OFF. Use the typed command box and Execute button.")
            self.hud.log_event("VOICE CONTROL DISABLED")
            self.speak("Voice Control is off.")
            return

# ---------------- UNIVERSAL STOP / MODE OFF ----------------
        # "stop" always stops the currently active teaching/model mode.
        # A model name may also follow it, e.g. "stop drone" or "stop sports car".
        # This is deliberately checked before mode activation and before the
        # generic question/computer routing.
        stop_mode_command = normalized in (
            "stop", "stop mode", "stop current mode", "stop current model",
            "stop model", "stop 3d", "stop 3d model", "stop 3d model maker",
            "stop maths", "stop math", "stop teaching",
        )
        # If a 3D model/mode is active, any "stop <model name>" command also
        # stops it, e.g. "stop drone", "stop sports car", or "stop robot".
        if (self.hud.model_showcase or str(getattr(self.hud, "mode", "")).upper().startswith("3D")) and normalized.startswith("stop "):
            if not normalized.startswith(("stop shastra", "stop security mode")):
                stop_mode_command = True
        if stop_mode_command:
            if self.hud.math_teacher_mode:
                self.hud.math_teacher_mode = False
                self.hud.mode = "SHASTRA CORE"
                self.hud.mode_detail = "Normal code animation"
                self.hud.set_status("READY")
                self.hud.set_vision("SHASTRA CORE\n\nMaths Teacher Mode stopped.\nNormal SHASTRA mode restored.")
                self.hud.set_answer("Maths Teacher Mode stopped. Normal SHASTRA mode restored.")
                self.hud.log_event("MATHS TEACHER MODE STOPPED")
                self.speak("Maths Teacher Mode stopped.")
                return
            if self.hud.model_showcase or str(getattr(self.hud, "mode", "")).upper().startswith("3D"):
                self.hud.model_showcase = False
                self.hud.mode = "SHASTRA CORE"
                self.hud.mode_detail = "Normal code animation"
                self.hud.set_status("READY")
                self.hud.set_vision("SHASTRA CORE\n\n3D Model Maker stopped.\nNormal SHASTRA mode restored.")
                self.hud.set_answer("3D Model Maker stopped. The current model is no longer active.")
                self.hud.log_event("3D MODEL / CURRENT MODEL STOPPED")
                self.speak("The active 3D model has been stopped.")
                return
            self.hud.set_status("READY")
            self.hud.set_answer("Nothing is currently active to stop.")
            self.hud.log_event("STOP COMMAND: NOTHING ACTIVE")
            self.speak("Nothing is currently active to stop.")
            return

# ---------------- 3D MODEL MAKER MODE ----------------
        activate_3d = normalized in (
            "3d model maker activate",
            "activate 3d model maker",
            "start 3d model maker",
            "turn on 3d model maker",
            "enable 3d model maker",
            "3d model maker",
            "3d maker activate",
            "3d mode activate",
            "activate 3d mode",
            "start 3d mode",
            "turn on 3d mode",
            "enable 3d mode",
            "3d mode on",
            "3d model mode on",
            "3d maker on",
            "3d model maker activity",
            "3d model maker activated",
            "activate 3d model maker mode",
            "3d model maker mode on",
            "3d maker activated",
            # Short natural triggers: saying/typing just "3D" or "3D model"
            # activates the 3D Model Maker.
            "3d",
            "3d model",
            "3d maker",
            "3d model mode",
            "activate 3d",
            "activate 3d model",
        )
        deactivate_3d = normalized in (
            "3d model maker deactivate",
            "deactivate 3d model maker",
            "stop 3d model maker",
            "turn off 3d model maker",
            "disable 3d model maker",
            "3d maker off",
            "3d model deactivate",
            "3d mode deactivate",
            "deactivate 3d mode",
            "stop 3d mode",
            "turn off 3d mode",
            "disable 3d mode",
            "3d mode off",
            "3d model mode off",
            "stop 3d",
            "stop 3d model",
            "stop 3d model maker",
            "3d model maker off",
        )
        # Handle common speech-recognition variants such as "activity" or
        # "activated", while never treating an explicit OFF command as ON.
        if not activate_3d:
            activate_3d = (
                normalized in ("3d", "3d model", "3d maker", "3d model maker", "3d model mode")
                or (
                    "3d" in normalized and "model" in normalized and "maker" in normalized
                    and any(word in normalized for word in ("activate", "activated", "activity", "start", "enable", "turn on", "on"))
                    and not any(word in normalized for word in ("deactivate", "disable", "turn off", "stop", " off"))
                )
            )
        if activate_3d:
            self.hud.math_teacher_mode = False
            self.hud.model_showcase = True
            self.hud.mode = "3D MODEL MAKER"
            self.hud.mode_detail = "Model creation mode active"
            self.hud.set_status("3D MODEL MAKER ACTIVE")
            self.hud.set_vision(
                "◉  SHASTRA 3D MODEL MAKER\n\n"
                "MODE: ACTIVE\n"
                "Say: make a 3D model of a drone\n"
                "Or drag and drop an image here to make an image-derived 3D model."
            )
            self.hud.set_answer("3D Model Maker is ACTIVE. Now tell me what 3D model to create.")
            self.hud.log_event("3D MODEL MAKER ACTIVATED")
            self.speak("3D Model Maker is now active. Tell me what model to create.")
            return
        if deactivate_3d:
            self.hud.math_teacher_mode = False
            self.hud.model_showcase = False
            self.hud.mode = "SHASTRA CORE"
            self.hud.mode_detail = "Normal code animation"
            self.hud.set_status("READY")
            self.hud.set_vision("SHASTRA CORE\n\nNormal code animation restored.\n3D Model Maker is off.")
            self.hud.set_answer("3D Model Maker is off. Normal SHASTRA code animation restored.")
            self.hud.log_event("3D MODEL MAKER DEACTIVATED")
            self.speak("3D Model Maker is off. Normal SHASTRA mode restored.")
            return

        # ---------------- MATHS TEACHER MODE ----------------
        if self._is_math_teacher_activation(normalized):
            self.hud.math_teacher_mode = True
            self.hud.mode = "MATHS TEACHER MODE"
            self.hud.mode_detail = "Step-by-step teaching"
            self.hud.set_status("MATHS TEACHER ACTIVE")
            self.hud.set_vision(
                "◉ SHASTRA MATHS TEACHER\n\n"
                "MODE: ACTIVE\n"
                "I will teach step by step.\n\n"
                "Say/type:\n"
                "• Say: math (or maths)\n"
                "• Solve 2x + 5 = 17\n"
                "• 25 × 16\n"
                "• 20% of 500\n\n"
                "Say: maths teacher mode off"
            )
            self.hud.set_answer(
                "Maths Teacher Mode is active. Give me a maths problem and I will "
                "explain it step by step, then check the answer."
            )
            self.hud.log_event("MATHS TEACHER MODE ACTIVATED")
            self.speak("Maths Teacher Mode is active. Give me a maths problem.")
            return

        if self._is_math_teacher_deactivation(normalized):
            self.hud.math_teacher_mode = False
            self.hud.mode = "ADVISOR MODE"
            self.hud.mode_detail = "Researching & Suggesting..."
            self.hud.set_status("READY")
            self.hud.set_vision("SHASTRA CORE\n\nMaths Teacher Mode is OFF.")
            self.hud.set_answer("Maths Teacher Mode is off. Normal SHASTRA mode restored.")
            self.hud.log_event("MATHS TEACHER MODE DEACTIVATED")
            self.speak("Maths Teacher Mode is off. Normal SHASTRA mode restored.")
            return

        # If teacher mode is active, normal computer commands still work,
        # while mathematical questions go directly to the teaching engine.
        if self.hud.math_teacher_mode and not self._is_obvious_computer_command(normalized):
            self._execute_math_teacher(raw)
            return

                # ---------------- SECURITY MODE ----------------
        if normalized in ("start security mode","enable security mode","security mode on","turn on security mode","activate security mode"):
            ok,msg=security_mode_on(); self.hud.set_security_mode(ok,msg); self.hud.set_status("SECURITY MODE ON" if ok else "SECURITY MODE ERROR"); self.hud.set_vision("✓ SECURITY MODE ACTIVE\n\nWi-Fi: DISABLED\nBluetooth: DISABLED\nFirewall traffic: BLOCKED" if ok else "× SECURITY MODE FAILED\n\n"+msg); self.hud.set_answer(msg); self.speak(msg); return
        if normalized in ("stop security mode","disable security mode","security mode off","turn off security mode","deactivate security mode"):
            ok,msg=security_mode_off(); self.hud.set_security_mode(False if ok else True,msg); self.hud.set_status("SECURITY MODE OFF" if ok else "SECURITY MODE ERROR"); self.hud.set_vision("✓ SECURITY MODE OFF\n\nWi-Fi: ENABLED\nBluetooth: ENABLED\nFirewall traffic: RESTORED" if ok else "× SECURITY MODE OFF FAILED\n\n"+msg); self.hud.set_answer(msg); self.speak(msg); return
        if normalized in ("security status","security mode status"):
            active=security_mode_status(); self.hud.set_security_mode(active,"Security Mode is ON." if active else "Security Mode is OFF."); self.speak("Security Mode is currently on." if active else "Security Mode is currently off."); return
        # ---------------- CURRENT 3D MODEL EDIT ----------------
        edit_prefix=("change 3d model","change the 3d model","modify 3d model","edit 3d model","change this model","modify this model","edit this model","add to 3d model","add to this model")
        if any(normalized.startswith(x) for x in edit_prefix):
            cmd=re.sub(r"^(change|modify|edit)\s+(the\s+)?3d\s+model\s*","",normalized).strip(); cmd=re.sub(r"^(change|modify|edit)\s+(this\s+)?model\s*","",cmd).strip(); cmd=re.sub(r"^add\s+to\s+(the\s+)?(?:3d\s+)?model\s*","add ",cmd).strip()
            if not self.hud.model_path or not self.hud.model_path.lower().endswith(".obj"):
                self.hud.set_answer("Load or generate an OBJ 3D model first."); self.speak("Load or generate a 3D model first."); return
            ok,desc=modify_current_3d_model(self.hud.model_path,cmd)
            if ok:
                self.hud.show_3d_model(self.hud.model_path); self.hud.set_status("3D MODEL CHANGED"); self.hud.set_answer("3D model changed: "+desc); self.hud.log_event("3D EDIT: "+desc); self.speak("3D model changed. "+desc)
            else: self.hud.set_answer(desc); self.speak(desc)
            return



        if normalized in (

            "exit",

            "quit",

            "stop shastra",

            "shutdown shastra",

        ):

            self.running = False

            self.hud.set_status("SHUTTING DOWN")

            self.speak("Shastra is shutting down.")

            return



        # ---------------- MULTI-DEVICE CONTROL ----------------
        if self.device_network:
            if normalized in ("show devices", "find devices", "scan devices"):
                self.hud.set_devices(self.device_network)
                n=len(self.device_network.snapshot())
                self.speak(f"I found {n} other SHASTRA device{'s' if n != 1 else ''}.")
                return
            if normalized in ("connect devices", "pair devices"):
                ok,msg=self.device_network.connect()
                self.hud.set_devices(self.device_network)
                self.hud.set_status("DEVICE LINKED" if ok else "DEVICE LINK FAILED")
                self.speak(msg); return
            if normalized in ("use powerful device", "use strongest device", "select powerful device"):
                d=self.device_network.strongest()
                if d:
                    self.device_network.preferred_peer=d["id"]; self.hud.set_devices(self.device_network)
                    self.speak(f"Powerful device selected: {d['name']}, score {d['score']}.")
                else: self.speak("No other SHASTRA device is available.")
                return
            for prefix in ("send to ", "control ", "run on other device ", "run on powerful device ", "open on other device "):
                if normalized.startswith(prefix):
                    cmd=normalized[len(prefix):].strip()
                    ok,msg=self.device_network.send_command(cmd)
                    self.hud.set_status("REMOTE TASK SENT" if ok else "REMOTE LINK ERROR")
                    self.hud.set_devices(self.device_network); self.speak(msg); return

        # ---------------- RETURN TO NORMAL CORE ANIMATION ----------------
        if normalized in (
            "code animation start",
            "okay code animation start",
            "ok code animation start",
            "start code animation",
            "show code animation",
            "show core animation",
            "normal animation",
            "back to core animation",
            "core animation",
        ):
            self.hud.model_showcase = False
            self.hud.set_status("READY")
            self.hud.set_vision("SHASTRA CORE\n\nNormal code animation restored.\nAll assistant functions remain active.")
            self.hud.log_event("NORMAL CORE ANIMATION STARTED")
            self.hud.set_answer("Normal SHASTRA core animation is running again.")
            self.speak("Normal core animation started.")
            return

        # ---------------- LOCAL 3D MODEL LIBRARY ----------------
        if normalized in ("show 3d model", "show my 3d model", "show saved model", "open 3d preview", "show model", "preview 3d model"):
            self.hud.set_status("LOADING 3D MODEL")
            path=self.hud.show_latest_3d_model("")
            if path:
                self.speak(f"Showing your saved 3D model: {os.path.basename(path)}")
            else:
                self.speak("I could not find a saved OBJ, STL, or PLY model.")
            return

        m=re.match(r"^(?:show|open|load|preview)\s+(?:my\s+)?(?:3d\s+)?model\s+(.+)$", normalized)
        if m:
            query=m.group(1).strip()
            self.hud.set_status("LOADING 3D MODEL")
            path=self.hud.show_latest_3d_model(query)
            if path:
                self.speak(f"Loaded {os.path.basename(path)} into the 3D preview.")
            else:
                self.speak("I could not find that saved 3D model.")
            return

        # ---------------- IMAGE FILE → 3D ----------------
        image_match=re.match(r"^(?:make|create|generate|build)\s+(?:a\s+)?3d\s+model\s+from\s+(.+)$", normalized)
        if image_match:
            candidate=image_match.group(1).strip().strip('"')
            if os.path.isfile(candidate) and os.path.splitext(candidate)[1].lower() in {'.png','.jpg','.jpeg','.webp','.bmp'}:
                self.hud.handle_image_to_3d(candidate)
                return

        # ---------------- FREE 3D MODEL GENERATION ----------------
        model_match = re.match(
            r"^(?:make|create|generate|build)\s+(?:a\s+|an\s+)?(.+?)\s+(?:3d\s+)?model(?:\s+of)?\s*(.*)$",
            normalized,
        )
        simple_3d_match = re.match(
            r"^(?:make|create|generate|build)\s+(?:a\s+|an\s+)?(.+?)\s+(?:3d|three[- ]?d)(?:\s+model)?$",
            normalized,
        )
        if model_match or simple_3d_match:
            if model_match:
                left = model_match.group(1).strip()
                right = model_match.group(2).strip()
                # Handles natural forms such as "make a 3D model of a robot"
                # and "make a model of a robot" without losing the requested object.
                if left.lower() in {"3d", "three d", "model", "object", "a", "an"} and right:
                    request = right
                else:
                    request = (right if right else left).strip()
            else:
                request = simple_3d_match.group(1).strip()
            request = re.sub(r"^(?:a|an)\s+", "", request).strip()
            if not request:
                request = "generic object"
            self.hud.set_status("3D WEB RESEARCH")
            self.hud.set_vision("◉  SHASTRA 3D FABRICATOR\n\nResearching object specifications...\nBuilding object-specific geometry...")
            self.hud.log_event("3D MODEL REQUEST: " + request)
            try:
                ok, folder, research, engine_name, details = generate_3d_model(request)
                answer = (f"3D model generated for {request}.\n\nResearch: {len(research)} public web snippets\nGenerator: free {engine_name} pipeline\nOutput folder: {folder}")
                self.hud.set_answer(answer)
                self.hud.set_vision("✓  MODEL GENERATED\n\n" + request[:55] + "\n\nWeb research: COMPLETE\nGeometry: COMPLETE\nFiles: OBJ" + (" + BLEND" if engine_name == "BLENDER" else ""))
                self.hud.set_status("3D MODEL READY")
                self.hud.log_event("3D MODEL READY: " + folder)
                generated_obj=os.path.join(folder, _safe_model_name(request)+".obj")
                if os.path.exists(generated_obj):
                    self.hud.show_3d_model(generated_obj)
                else:
                    latest=find_saved_3d_model(request)
                    if latest: self.hud.show_3d_model(latest)
                self.speak(f"I generated the free 3D model for {request} and loaded it into the preview.")
            except Exception as exc:
                self.hud.set_status("3D MODEL ERROR")
                self.hud.set_vision("×  3D GENERATION ERROR\n\n" + str(exc)[:500])
                self.hud.log_event("3D ERROR: " + str(exc))
                self.speak("The 3D model generator encountered an error.")
            return

        # Friend mode: natural conversation before advisor or web-question handling.
        if looks_like_friend_request(raw):
            self.hud.set_status("FRIEND MODE")
            self.hud.set_vision(
                "◎  SHASTRA FRIEND MODE\n\n"
                "Listening...\n"
                "Conversation mode active."
            )
            answer = friend_response(raw)
            self.hud.set_answer(answer)
            self.hud.log_event("FRIEND CONVERSATION")
            self.speak(answer[:1000])
            return

        # Advisor / decision-support mode comes before the generic question route.
        # It researches current information when internet is available, uses recent
        # SHASTRA memory for continuity, and gives options/trade-offs instead of
        # silently making the user's decision.
        if looks_like_advisor_request(raw):
            self.hud.set_status("ADVISOR RESEARCH")
            self.hud.set_vision(
                "◎  SHASTRA ADVISOR\n\n"
                "Analyzing your goal...\n"
                "Checking current web information...\n"
                "Preparing options and next steps..."
            )
            answer = advisor_response(raw)
            self.hud.set_answer(answer)
            self.hud.set_status("ADVICE READY")
            self.hud.log_event("ADVISOR ANALYSIS COMPLETE")
            print("\n===== SHASTRA ADVISOR =====\n" + answer + "\n===========================\n")
            self.speak(answer[:1200])
            return

        # Exact learned command first

        learned = self.memory.lookup(normalized)

        if learned:

            action = learned["action"]

            target = learned["target"]

            self.hud.log_event("MEMORY MATCH: " + action)

        else:

            # Canonicalize the most important voice commands before the generic
            # router. This handles small STT mistakes without changing questions.
            command_text = normalized
            exact_voice_aliases = {
                "open chrome browser": "open chrome",
                "open google chrome browser": "open chrome",
                "launch chrome browser": "open chrome",
                "start chrome browser": "open chrome",
                "open google": "open google",
                "open you tube": "open youtube",
                "launch youtube": "open youtube",
                "start youtube": "open youtube",
            }
            command_text = exact_voice_aliases.get(command_text, command_text)
            if command_text != normalized:
                print(f"[COMMAND FIX] {normalized!r} -> {command_text!r}", flush=True)
            action, target = self.router.parse(command_text)

        print(f"[ROUTER] action={action!r} target={target!r}", flush=True)

        try:

            # ---------------- OPEN ----------------

            if action == "open":

                self.hud.set_status("LAUNCHING")

                ok, kind = self.launcher.open_target(target)
                print(f"[EXECUTE] OPEN target={target!r} ok={ok} kind={kind}", flush=True)
                self.hud.log_event(f"OPEN RESULT: {target} -> {'SUCCESS' if ok else 'FAILED'}")

                if ok:

                    self.memory.learn(normalized, action, target)

                    self.hud.set_status("TASK COMPLETE")

                    self.speak(f"Opening {target}.")

                else:

                    self.hud.set_status("NOT FOUND")

                    self.speak(f"I could not open {target}.")

                return



            # ---------------- TYPE ----------------

            if action == "type":

                self.hud.set_status("VISION CHECK")

                self.hud.set_vision(

                    "●  OCR CHECK\n\n"

                    "Preparing typing target..."

                )



                # If a text field is already focused, type directly.

                # The screen is captured first so the command remains

                # compatible with future vision targeting.

                if not self.screen.screenshot():

                    self.hud.log_event("Screen capture unavailable.")



                self.hud.set_status("TYPING")

                self.computer.type_text(target)

                self.hud.set_status("TASK COMPLETE")

                self.memory.learn(normalized, action, target)

                return



            # ---------------- CLICK ----------------

            if action == "click":

                self.hud.set_status("LEFT CLICK")

                self.computer.click()

                self.hud.set_status("TASK COMPLETE")

                return



            if action == "right_click":

                self.hud.set_status("RIGHT CLICK")

                self.computer.right_click()

                self.hud.set_status("TASK COMPLETE")

                return



            if action == "double_click":

                self.hud.set_status("DOUBLE CLICK")

                self.computer.double_click()

                self.hud.set_status("TASK COMPLETE")

                return



            # ---------------- OCR TARGET CLICK ----------------

            if action in (

                "click_text",

                "right_click_text",

                "double_click_text",

            ):

                self.hud.set_status("VISION SEARCH")

                self.hud.set_vision(

                    "◉  SEARCHING SCREEN\n\n"

                    f'TARGET: "{target}"'

                )

                self.hud.log_event(

                    f"OCR target search: {target}"

                )



                if not TESSERACT_OK:

                    self.hud.set_status("OCR OFFLINE")

                    self.speak(

                        "I need Tesseract OCR installed "

                        "to find that text on the screen."

                    )

                    return



                if action == "click_text":

                    ok = self.computer.click_text(target)

                elif action == "right_click_text":

                    ok = self.computer.click_text(

                        target,

                        right=True

                    )

                else:

                    ok = self.computer.click_text(

                        target,

                        double=True

                    )



                if ok:

                    self.hud.set_status("TARGET FOUND")

                    self.hud.set_vision(

                        f"✓  TARGET FOUND\n\n{target}"

                    )

                else:

                    self.hud.set_status("TARGET NOT FOUND")

                    self.hud.set_vision(

                        f"×  TARGET NOT FOUND\n\n{target}"

                    )

                    self.speak(

                        f"I could not find {target} on the screen."

                    )

                return



            # ---------------- KEY ----------------

            if action == "key":

                self.hud.set_status("KEYBOARD")

                self.computer.press(target)

                self.hud.set_status("TASK COMPLETE")

                return



            # ---------------- HOTKEY ----------------

            if action == "hotkey":

                self.hud.set_status("KEYBOARD")

                self.computer.hotkey(*target)

                self.hud.set_status("TASK COMPLETE")

                return



            # ---------------- WINDOW ----------------

            if action == "minimize":

                self.hud.set_status("MINIMIZING")

                self.computer.minimize()

                return



            if action == "maximize":

                self.hud.set_status("MAXIMIZING")

                self.computer.maximize()

                return



            if action == "switch":

                self.hud.set_status("SWITCHING")

                self.computer.switch_window()

                return



            if action == "close":

                self.hud.set_status("CLOSING")

                self.computer.close()

                return



            # ---------------- SCAN ----------------

            if action == "scan":

                self.hud.set_status("SCREEN SCAN")

                self.hud.set_vision(

                    "◉  CAPTURING SCREEN\n\n"

                    "Running OCR..."

                )



                if not TESSERACT_OK:

                    self.hud.set_status("OCR OFFLINE")

                    self.speak(

                        "Screen capture is available, "

                        "but Tesseract OCR is not installed."

                    )

                    return



                image = self.screen.screenshot()

                text = self.screen.ocr(image)



                if text.strip():

                    print("\n===== SCREEN TEXT =====")

                    print(text)

                    print("=======================\n")



                    self.hud.log_event(

                        "OCR detected screen text."

                    )

                    self.hud.set_vision(

                        "✓  SCREEN READ\n\n"

                        + text[:220]

                    )

                    self.speak(

                        "I read the screen successfully."

                    )

                else:

                    self.hud.set_vision(

                        "○  NO READABLE TEXT"

                    )

                    self.speak(

                        "I could not find readable text."

                    )



                self.hud.set_status("READY")

                return



            # ---------------- QUESTION ----------------

            if action == "question":

                self.hud.set_status("CHECKING INTERNET")

                self.hud.set_vision(
                    "◎  CONNECTION CHECK\n\n"
                    "Checking internet connection..."
                )

                self.hud.log_event(
                    "CHECKING INTERNET FOR QUESTION"
                )

                online = check_internet()

                if online:
                    self.hud.set_status("INTERNET ONLINE")

                    selected_mode = (
                        "GEMINI AI + GOOGLE SEARCH"
                        if self.session.get("use_api")
                        else "WIKIPEDIA + GOOGLE SEARCH"
                    )
                    self.hud.set_vision(
                        "◎  WEB REASONER\n\n"
                        f"MODE: {selected_mode}\n"
                        "Internet connection detected.\n"
                        "Searching current information..."
                    )

                    self.hud.log_event(
                        "INTERNET ONLINE"
                    )
                    self.hud.log_event(
                        "ANSWER MODE: "
                        + (
                            "GEMINI API + GOOGLE SEARCH"
                            if self.session.get("use_api")
                            else "WIKIPEDIA + GOOGLE SEARCH"
                        )
                    )

                    answer, answer_source = answer_with_selected_mode(target)
                    self.hud.log_event("ANSWER SOURCE: " + answer_source)
                    if answer_source.startswith("LOCAL DATABASE"):
                        self.hud.set_vision(
                            "✓  LOCAL KNOWLEDGE\n\n"
                            "Question found in SHASTRA database.\n"
                            "No API / Google / Wikipedia request needed.\n"
                            "Returning the saved answer..."
                        )
                        self.hud.set_status("LOCAL ANSWER FOUND")
                    elif answer_source.startswith("WEB/API"):
                        self.hud.log_event("NEW ANSWER: SAVING TO CONNECTED LOCAL KNOWLEDGE DB")

                else:
                    self.hud.set_status("INTERNET OFFLINE")

                    self.hud.set_vision(
                        "○  OFFLINE MODE\n\n"
                        "Internet connection unavailable."
                    )

                    self.hud.log_event(
                        "INTERNET OFFLINE"
                    )

                    # The local knowledge database works even when the internet is offline.
                    cached_answer, row_id, cached_topic = knowledge_lookup(target)
                    if cached_answer:
                        answer = cached_answer
                        answer_source = "LOCAL DATABASE"
                        self.hud.log_event(f"KNOWLEDGE DB EXACT HIT OFFLINE id={row_id} topic={cached_topic}")
                        self.hud.set_vision(
                            "✓  OFFLINE LOCAL KNOWLEDGE\n\n"
                            "Question found in SHASTRA database.\n"
                            "No internet request needed.\n"
                            "Returning the saved answer..."
                        )
                        self.hud.set_status("LOCAL ANSWER FOUND")
                    else:
                        answer = (
                            "I cannot access current online information "
                            "because the internet connection is unavailable, "
                            "and this question is not in my local knowledge database."
                        )
                        answer_source = "OFFLINE - NOT LEARNED"

                self.hud.set_answer(answer)
                self.hud.log_event("ANSWER BOX UPDATED")


                print("\n===== SHASTRA =====")

                print(answer)

                print("===================\n")



                self.hud.set_status("ANSWER READY")

                self.speak(answer[:700])

                return



        except Exception as exc:

            self.hud.set_status("ERROR")

            self.hud.log_event(

                "ERROR: " + str(exc)

            )

            self.speak(

                "I encountered an error while performing that task."

            )



    def voice_loop(self):

        time.sleep(1)



        self.hud.set_status("READY")

        self.hud.log_event(
            "SHASTRA core initialized."
        )

        self.speak(

            "Shastra is online."

        )



        while self.running:
            while self.running and (
                self.voice.speaking.is_set() or self.command_busy.is_set()
            ):
                if self.command_busy.is_set() and not self.voice.speaking.is_set():
                    self.hud.set_status("PROCESSING COMMAND")
                time.sleep(0.12)
            if not self.running:
                break

            if not self.hud.voice_control_enabled:
                self.hud.set_status("VOICE CONTROL OFF")
                time.sleep(0.25)
                continue
            if not SPEECH_OK or self.voice.sd is None:
                self.hud.set_status(
                    "VOICE UNAVAILABLE - SELECT PROJECT .VENV PYTHON"
                )
                self.hud.log_event(
                    "Voice input needs SpeechRecognition, sounddevice, and numpy. "
                    "Run SHASTRA with ai\\.venv\\Scripts\\python.exe."
                )
                time.sleep(2.0)
                continue
            if not self.voice.audio_available:
                self.hud.set_status("MIC UNAVAILABLE - CHECK PERMISSIONS")
                time.sleep(2.0)
                self.voice._refresh_microphone()
                continue
            manual_request = self.voice_capture_requested.is_set()
            self.voice_capture_requested.clear()
            self.hud.set_status("PREPARING MICROPHONE")
            self.hud.set_command(
                "SPEAK NOW..." if manual_request else "LISTENING FOR COMMAND..."
            )
            if manual_request:
                self.hud.voice_level = 1.0
            try:
                command = self.voice.listen()
            except Exception as exc:
                self.hud.voice_level = 0.55
                self.hud.set_status("VOICE INPUT ERROR - RETRYING")
                self.hud.set_vision(
                    "× VOICE INPUT ERROR\n\n" + str(exc)[:500]
                )
                self.hud.log_event("VOICE INPUT ERROR: " + repr(exc))
                print("[MIC ERROR] Voice listener recovered from error:", repr(exc), flush=True)
                time.sleep(0.5)
                continue
            self.hud.voice_level = 0.55
            if not command:
                if manual_request:
                    self.hud.set_status("VOICE NOT HEARD")
                    self.hud.set_command("Try again; speak clearly near the microphone.")
                    self.hud.log_event("MIC BUTTON: no speech was transcribed.")
                else:
                    self.hud.set_status("NO SPEECH - LISTENING AGAIN")
                    time.sleep(0.35)
                continue

            normalized_command = self.router.normalize(command)
            now = time.time()
            if normalized_command and normalized_command == self.last_voice_command and now - self.last_voice_command_time < 2.5:
                print(f'[MIC] Ignoring duplicate command: {command}', flush=True)
                continue
            self.last_voice_command = normalized_command
            self.last_voice_command_time = now
            print(f"[VOICE->QUEUE] {command!r}", flush=True)
            self.hud.add_user_message(command)
            self.hud.log_event("VOICE COMMAND ACCEPTED: " + command)
            self.hud.set_command("HEARD: " + command)
            self.hud.set_status("COMMAND RECEIVED")
            self.submit_command(command)



        self.hud.running = False





# ============================================================

# MAIN

# ============================================================



class LocalhostLogin:
    """
    Local SHASTRA sign-in.

    Login now asks whether the user wants AI API mode.
    - YES: enter a Gemini API key. Answers use Gemini + Google Search grounding.
    - NO: answers use Wikipedia + Google Search directly.

    The API key exists only in memory for the current SHASTRA process and is
    never stored in the local users database.
    """

    def __init__(self):
        self.result = None
        self.completed = threading.Event()
        self.lock = threading.Lock()
        with closing(sqlite3.connect(LOCAL_USERS_DB)) as db:
            with db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS local_users "
                    "(username TEXT PRIMARY KEY COLLATE NOCASE, created_at TEXT NOT NULL)"
                )

    @staticmethod
    def _page(message=""):
        feedback = (
            f'<p class="message">{html.escape(message)}</p>'
            if message else ""
        )
        return (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>SHASTRA Login</title>"
            "<style>"
            "body{margin:0;background:#040b12;color:#edf7ff;font:16px Segoe UI,Arial;"
            "display:grid;min-height:100vh;place-items:center}"
            "main{width:min(460px,calc(100% - 40px));padding:30px;background:#0a1723;"
            "border:1px solid #17617a;border-radius:14px;box-sizing:border-box;"
            "box-shadow:0 18px 55px rgba(0,0,0,.45)}"
            "h1{color:#67e4ff;margin:0 0 8px;font-size:30px}"
            "h2{font-size:17px;margin:24px 0 8px;color:#dff7ff}"
            "p{color:#9bb8c5;line-height:1.45}"
            "label{display:block;margin-top:14px;color:#d9edf5;font-weight:600}"
            "input,button{box-sizing:border-box;width:100%;padding:12px;margin-top:8px;"
            "border-radius:8px;font-size:16px}"
            "input{background:#061a2a;color:#fff;border:1px solid #17617a;outline:none}"
            "input:focus{border-color:#67e4ff}"
            "button{background:#0a5270;color:#fff;border:0;cursor:pointer;font-weight:700}"
            ".choice{display:flex;gap:10px;margin-top:10px}"
            ".choice button{margin-top:0;background:#12384b;border:1px solid #28627a}"
            ".choice button.selected{background:#08764d;border-color:#3ee3a5}"
            ".hidden{display:none!important}"
            ".message{color:#ffbf7e;background:#24170b;padding:10px;border-radius:7px}"
            ".hint{font-size:13px;color:#7fa5b5}"
            "</style><body><main>"
            "<h1>SHASTRA</h1>"
            "<p>Sign in and choose how SHASTRA should answer your questions.</p>"
            f"{feedback}"
            "<form method='post' action='/login' onsubmit='return validateLogin()'>"
            "<label for='username'>Username</label>"
            "<input id='username' name='username' minlength='3' maxlength='32' "
            "pattern='[A-Za-z0-9_.-]+' autocomplete='username' required autofocus>"
            "<h2>Use AI API?</h2>"
            "<div class='choice'>"
            "<button type='button' id='yesBtn' onclick='chooseApi(true)'>YES — AI + Web</button>"
            "<button type='button' id='noBtn' onclick='chooseApi(false)'>NO — Wikipedia + Google</button>"
            "</div>"
            "<input type='hidden' id='use_api' name='use_api' value='no'>"
            "<div id='apiBox' class='hidden'>"
            "<label for='api_key'>Gemini API Key</label>"
            "<input id='api_key' name='api_key' type='password' maxlength='300' "
            "autocomplete='off' placeholder='Paste your Gemini API key'>"
            "<p class='hint'>The key is used only for this SHASTRA session and is not saved to the local database.</p>"
            "</div>"
            "<button type='submit' style='margin-top:22px'>Continue to SHASTRA</button>"
            "</form>"
            "<script>"
            "function chooseApi(yes){"
            "document.getElementById('use_api').value=yes?'yes':'no';"
            "document.getElementById('apiBox').classList.toggle('hidden',!yes);"
            "document.getElementById('yesBtn').classList.toggle('selected',yes);"
            "document.getElementById('noBtn').classList.toggle('selected',!yes);"
            "document.getElementById('api_key').required=yes;"
            "}"
            "function validateLogin(){"
            "const yes=document.getElementById('use_api').value==='yes';"
            "const key=document.getElementById('api_key').value.trim();"
            "if(yes && !key){alert('Please enter your Gemini API key.');return false;}"
            "return true;}"
            "chooseApi(false);"
            "</script>"
            "</main></body></html>"
        )

    def _sign_in(self, username, use_api=False, api_key=""):
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise ValueError(
                "Use 3–32 characters: letters, numbers, dots, underscores, or hyphens."
            )

        use_api = bool(use_api)
        api_key = str(api_key or "").strip()

        if use_api and not api_key:
            raise ValueError("AI API is set to YES, so a Gemini API key is required.")

        with closing(sqlite3.connect(LOCAL_USERS_DB)) as db:
            with db:
                cursor = db.execute(
                    "INSERT OR IGNORE INTO local_users (username, created_at) VALUES (?, ?)",
                    (username, datetime.now().isoformat(timespec="seconds")),
                )
                created = cursor.rowcount == 1
                row = db.execute(
                    "SELECT username FROM local_users WHERE username = ?",
                    (username,),
                ).fetchone()

        if row is None:
            raise RuntimeError("Could not find or create the local user profile.")

        # Store only in memory. Never put api_key in SQLite.
        SHASTRA_AI_SESSION["username"] = row[0]
        SHASTRA_AI_SESSION["use_api"] = use_api
        SHASTRA_AI_SESSION["api_key"] = api_key if use_api else ""

        return row[0], created

    def run(self):
        login = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                print("[LOCAL LOGIN] " + (format % args), flush=True)

            def _send_html(self, status, page):
                body = page.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path != "/":
                    self._send_html(404, "<h1>Not found</h1>")
                    return
                self._send_html(200, login._page())

            def do_POST(self):
                if self.path != "/login":
                    self._send_html(404, "<h1>Not found</h1>")
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 8192:
                        raise ValueError("Invalid login request.")

                    form = urllib.parse.parse_qs(
                        self.rfile.read(length).decode("utf-8", errors="strict"),
                        keep_blank_values=True,
                    )

                    username = form.get("username", [""])[0]
                    use_api = form.get("use_api", ["no"])[0].lower() == "yes"
                    api_key = form.get("api_key", [""])[0]

                    signed_in_name, created = login._sign_in(
                        username,
                        use_api=use_api,
                        api_key=api_key,
                    )

                except (UnicodeDecodeError, ValueError) as exc:
                    self._send_html(400, login._page(str(exc)))
                    return
                except sqlite3.Error as exc:
                    print(
                        f"[LOCAL LOGIN ERROR] Database operation failed: {exc}",
                        flush=True,
                    )
                    self._send_html(
                        500,
                        login._page("Could not save the local profile."),
                    )
                    return

                with login.lock:
                    login.result = {
                        "username": signed_in_name,
                        "use_api": use_api,
                        "api_key": api_key if use_api else "",
                    }
                    login.completed.set()

                if use_api:
                    mode_message = (
                        "AI API mode selected. Gemini + Google Search will answer questions."
                    )
                else:
                    mode_message = (
                        "Free web mode selected. Wikipedia + Google Search will answer questions."
                    )

                message = (
                    "Local profile created. " + mode_message
                    if created
                    else mode_message
                )

                # Do not echo the API key back to the browser.
                self._send_html(
                    200,
                    "<!doctype html><html><meta charset='utf-8'>"
                    "<title>SHASTRA Ready</title>"
                    "<style>body{font:16px Segoe UI;background:#040b12;color:#fff;"
                    "padding:40px}h1{color:#67e4ff}</style>"
                    "<body><h1>SHASTRA READY</h1><p>"
                    + html.escape(message)
                    + "</p><p>You can close this browser tab and use SHASTRA.</p>"
                    "</body></html>",
                )

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        address, port = server.server_address
        server_thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
        )
        server_thread.start()

        login_url = f"http://{address}:{port}/"
        print(f"[LOCAL LOGIN] IP address: {address}:{port}", flush=True)
        print(f"[LOCAL LOGIN] Open {login_url} to sign in.", flush=True)

        try:
            if not webbrowser.open(login_url):
                raise RuntimeError(
                    f"Could not open a browser for local login. Visit {login_url} manually."
                )
            while not self.completed.wait(timeout=0.25):
                pass
            return self.result
        finally:
            server.shutdown()
            server.server_close()


class MobileControlServer:
    """LAN-only mobile command panel authenticated with the active local user ID."""

    PORT = 5000
    PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#06111b"><title>SHASTRA Mobile</title>
<style>
:root{color-scheme:dark;font:16px system-ui,Segoe UI,sans-serif;background:#06111b;color:#e8f5fc}
*{box-sizing:border-box}body{margin:0 auto;max-width:900px;padding:16px;padding-bottom:env(safe-area-inset-bottom,16px)}
h1{color:#67e4ff;font-size:1.35rem;margin:0}.sub{color:#9bb8c5;margin:4px 0 16px}
section{background:#0a1a27;border:1px solid #16445a;border-radius:12px;padding:14px;margin:12px 0}
input,button{font:inherit;border-radius:8px;padding:12px;border:1px solid #28627a}
input{background:#04121d;color:#fff;width:100%;min-width:0}
button{background:#075575;color:#fff;font-weight:700;cursor:pointer}
button:disabled{opacity:.55}#connect{display:flex;gap:8px}#connect button{white-space:nowrap}
#pair label{display:block;margin:12px 0 6px}
#screen{display:block;width:100%;min-height:180px;max-height:58vh;object-fit:contain;background:#02070b;border-radius:8px}
#status{color:#75e5bd;min-height:1.4em;font-size:.9rem}.chat{height:27vh;min-height:150px;overflow:auto;display:flex;flex-direction:column;gap:8px}
.msg{white-space:pre-wrap;overflow-wrap:anywhere;background:#102638;border-radius:8px;padding:9px}
.msg b{color:#67e4ff;display:block;font-size:.8rem;margin-bottom:3px}
form{display:flex;gap:8px}form button{white-space:nowrap}
#voiceButton{width:100%;margin-top:8px;background:#126642}
.hidden{display:none!important}.hint{color:#9bb8c5;font-size:.85rem}
</style></head><body>
<header><h1>SHASTRA</h1><p class="sub">Mobile control panel · commands and screen are shared with your computer</p></header>
<section id="pair"><p>Sign in with the same user ID you used on your computer.</p>
<label for="userId">User ID</label>
<input id="userId" type="text" autocomplete="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_.-]+" placeholder="Computer sign-in user ID" required>
<div id="connect"><button id="connectButton" type="button">Sign in</button></div><p id="pairError" role="alert"></p>
<p class="hint">Use this only on your trusted local Wi-Fi network.</p></section>
<main id="panel" class="hidden">
<section><h2>Computer screen · live</h2><img id="screen" alt="Live computer screen"><p id="status">Connecting…</p></section>
<section><h2>SHASTRA conversation</h2><div id="messages" class="chat" aria-live="polite"></div>
<form id="commandForm"><input id="command" maxlength="1000" autocomplete="off" placeholder="Type a command for SHASTRA" required>
<button id="sendButton">Send to PC</button></form>
<button id="voiceButton" type="button" aria-pressed="false">Speak to PC</button>
<p class="hint">Voice commands are recognized on this phone and executed only on your computer.</p></section>
</main>
<script>
const pair=document.getElementById("pair"),panel=document.getElementById("panel");
const statusLine=document.getElementById("status");
const userIdInput=document.getElementById("userId");
let userId=sessionStorage.getItem("shastraUserId")||"",screenUrl="";
userIdInput.value=userId;
async function api(path,options={}){const response=await fetch(path,{...options,headers:{"X-SHASTRA-USER-ID":userId,...options.headers}});
let body={};if(response.headers.get("content-type")?.includes("json"))body=await response.json();
if(!response.ok)throw Error(body.error||`Request failed (${response.status})`);return {response,body};}
async function connect(){userId=userIdInput.value.trim();try{await api("/api/state");
sessionStorage.setItem("shastraUserId",userId);
pair.classList.add("hidden");panel.classList.remove("hidden");document.getElementById("pairError").textContent="";
refresh();setInterval(refresh,1300);setInterval(refreshScreen,1500);refreshScreen();}
catch(error){sessionStorage.removeItem("shastraUserId");userId="";
userIdInput.value="";document.getElementById("pairError").textContent=error.message;}}
document.getElementById("connectButton").addEventListener("click",connect);
userIdInput.addEventListener("keydown",event=>{if(event.key==="Enter")connect();});
function renderMessages(messages){const box=document.getElementById("messages"),atBottom=box.scrollHeight-box.scrollTop-box.clientHeight<60;
box.replaceChildren();for(const item of messages){const row=document.createElement("div"),name=document.createElement("b"),text=document.createElement("span");
row.className="msg";name.textContent=item[0];text.textContent=item[1];row.append(name,text);box.append(row);}if(atBottom)box.scrollTop=box.scrollHeight;}
let refreshing=false;
async function refresh(){if(refreshing)return;refreshing=true;try{const {body}=await api("/api/state");renderMessages(body.messages);
statusLine.textContent=`${body.status} · ${body.command}`;}catch(error){statusLine.textContent=error.message;
if(error.message.includes("user ID")){sessionStorage.removeItem("shastraUserId");location.reload();}}finally{refreshing=false;}}
async function refreshScreen(){try{const {response}=await api("/api/screen"),url=URL.createObjectURL(await response.blob());
const image=document.getElementById("screen"),previous=screenUrl;screenUrl=url;image.src=url;if(previous)URL.revokeObjectURL(previous);}
catch(error){statusLine.textContent=`Screen unavailable: ${error.message}`;}}
async function sendCommandToPc(command){const field=document.getElementById("command"),button=document.getElementById("sendButton");
button.disabled=true;try{await api("/api/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command})});
field.value="";statusLine.textContent="Command sent to SHASTRA on your computer.";}
catch(error){statusLine.textContent=error.message;}finally{button.disabled=false;}}
document.getElementById("commandForm").addEventListener("submit",event=>{event.preventDefault();
const command=document.getElementById("command").value.trim();if(command)sendCommandToPc(command);});
const voiceButton=document.getElementById("voiceButton");
let mobileRecognition=null;
function resetVoiceButton(){voiceButton.textContent="Speak to PC";voiceButton.setAttribute("aria-pressed","false");}
voiceButton.addEventListener("click",()=>{if(mobileRecognition){mobileRecognition.stop();return;}
const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!Recognition){statusLine.textContent="Phone voice recognition is not supported by this browser. Try typing the command.";return;}
const recognition=new Recognition();mobileRecognition=recognition;
recognition.lang=navigator.language||"en-US";recognition.interimResults=false;recognition.maxAlternatives=1;
let commandSubmitted=false;
voiceButton.textContent="Stop listening";voiceButton.setAttribute("aria-pressed","true");
recognition.onstart=()=>{statusLine.textContent="Listening on this phone. Say an app name to open it on your PC.";};
recognition.onresult=event=>{if(commandSubmitted)return;
const command=Array.from(event.results).filter(result=>result.isFinal)
.map(result=>result[0].transcript).join(" ").trim();if(!command)return;
commandSubmitted=true;mobileRecognition=null;resetVoiceButton();
document.getElementById("command").value=command;statusLine.textContent=`Voice command: "${command}" — sending to PC…`;
sendCommandToPc(command);};
recognition.onerror=event=>{mobileRecognition=null;resetVoiceButton();
if(event.error==="not-allowed"||event.error==="service-not-allowed")statusLine.textContent="Microphone access was denied. Allow microphone access and try again.";
else if(event.error==="no-speech")statusLine.textContent="No speech detected. Tap Speak to PC and try again.";
else statusLine.textContent=`Phone voice input failed: ${event.error}.`;};
recognition.onend=()=>{if(mobileRecognition===recognition){mobileRecognition=null;resetVoiceButton();
if(!commandSubmitted)statusLine.textContent="Voice listening stopped. Tap Speak to PC to try again."; }};
try{recognition.start();}catch(error){mobileRecognition=null;resetVoiceButton();
statusLine.textContent=`Could not start phone voice input: ${error.message}`;}});
if(userId)connect();
</script></body></html>"""

    def __init__(self, hud, engine, user_id):
        self.hud = hud
        self.engine = engine
        self.user_id = user_id
        self.http = None
        self.lock = threading.Lock()
        self.failed_attempts = {}

    @staticmethod
    def lan_addresses():
        addresses = set()
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as route:
                route.connect(("8.8.8.8", 80))
                address = route.getsockname()[0]
                if not address.startswith("127."):
                    addresses.add(address)
        except OSError:
            pass
        try:
            addresses.update(
                item[4][0]
                for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                if not item[4][0].startswith("127.")
            )
        except OSError:
            pass
        return sorted(addresses)

    def _state(self):
        completed = threading.Event()
        state = {}

        def read():
            state.update(
                status=self.hud.last_status,
                command=self.hud.last_command,
                messages=[list(message[:2]) for message in self.hud.messages[-30:]],
            )
            completed.set()

        self.hud._ui(read)
        if not completed.wait(3):
            raise TimeoutError("Timed out while reading SHASTRA's desktop state.")
        return state

    def start(self):
        mobile = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def send_body(self, status, content_type, body):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(body)

            def send_json(self, status, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_body(status, "application/json; charset=utf-8", body)

            def authorized(self):
                address = self.client_address[0]
                now = time.time()
                supplied_user_id = self.headers.get("X-SHASTRA-USER-ID", "")
                with mobile.lock:
                    failures, blocked_until = mobile.failed_attempts.get(address, (0, 0))
                    if blocked_until > now:
                        self.send_json(429, {"error": "Too many incorrect sign-in attempts. Try again shortly."})
                        return False
                    valid_user_id = bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", supplied_user_id))
                    if valid_user_id and hmac.compare_digest(
                        supplied_user_id.casefold(), mobile.user_id.casefold()
                    ):
                        mobile.failed_attempts.pop(address, None)
                        return True
                    failures += 1
                    blocked_until = now + 60 if failures >= 8 else 0
                    mobile.failed_attempts[address] = (0 if blocked_until else failures, blocked_until)
                self.send_json(401, {"error": "Incorrect or missing user ID."})
                return False

            def do_GET(self):
                path = urllib.parse.urlsplit(self.path).path
                if path == "/":
                    self.send_body(200, "text/html; charset=utf-8", mobile.PAGE.encode("utf-8"))
                    return
                if path not in ("/api/state", "/api/screen"):
                    self.send_json(404, {"error": "Not found."})
                    return
                if not self.authorized():
                    return
                if path == "/api/state":
                    try:
                        self.send_json(200, mobile._state())
                    except TimeoutError as exc:
                        self.send_json(503, {"error": str(exc)})
                    return
                try:
                    image = mobile.engine.screen.screenshot()
                    if image is None:
                        self.send_json(503, {"error": "Desktop screen capture is unavailable."})
                        return
                    image.thumbnail((1280, 800))
                    output = io.BytesIO()
                    image.save(output, format="JPEG", quality=65, optimize=True)
                    self.send_body(200, "image/jpeg", output.getvalue())
                except (OSError, RuntimeError, ValueError) as exc:
                    mobile.hud.log_event("MOBILE SCREEN ERROR: " + str(exc))
                    self.send_json(503, {"error": "Could not capture the desktop screen."})

            def do_POST(self):
                if urllib.parse.urlsplit(self.path).path != "/api/command":
                    self.send_json(404, {"error": "Not found."})
                    return
                if not self.authorized():
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 2048:
                        raise ValueError("Invalid command request.")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    command = payload.get("command", "") if isinstance(payload, dict) else ""
                    if not isinstance(command, str) or not command.strip() or len(command) > 1000:
                        raise ValueError("Enter a command of 1–1000 characters.")
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    self.send_json(400, {"error": str(exc)})
                    return
                if not mobile.engine.running:
                    self.send_json(503, {"error": "SHASTRA is not running."})
                    return
                command = command.strip()
                mobile.hud.add_user_message(command)
                mobile.hud.set_command("MOBILE: " + command)
                mobile.engine.submit_command(command)
                mobile.hud.log_event("MOBILE COMMAND ACCEPTED: " + command)
                self.send_json(202, {"ok": True, "accepted": True})

        server = ThreadingHTTPServer(("0.0.0.0", self.PORT), Handler)
        server.daemon_threads = True
        self.http = server
        threading.Thread(target=server.serve_forever, daemon=True).start()

        addresses = self.lan_addresses()
        if addresses:
            access = ", ".join(f"http://{address}:{self.PORT}/" for address in addresses)
        else:
            access = f"http://<computer-local-IP>:{self.PORT}/"
        message = f"MOBILE CONTROL: {access} | Sign in with your computer user ID."
        print("[SHASTRA] " + message, flush=True)
        self.hud.log_event(message)

    def stop(self):
        if self.http is not None:
            self.http.shutdown()
            self.http.server_close()
            self.http = None


def main():
    print("[SHASTRA] Starting SHASTRA Future Intelligence Core...", flush=True)
    print("[SHASTRA] Login will ask: Use AI API? YES/NO", flush=True)
    try:
        login_session = LocalhostLogin().run()
        if not login_session:
            print("[SHASTRA] Local login did not complete.", flush=True)
            return

        user_id = login_session["username"]
        use_api = bool(login_session.get("use_api"))
        mode_name = "AI API + Google Search" if use_api else "Wikipedia + Google Search"

        root=(TkinterDnD.Tk() if TKDND_OK else tk.Tk())
        hud=HUD(root)
        engine=Engine(hud, login_session)

        hud.log_event(f"LOCAL SESSION: {user_id}")
        hud.log_event(f"QUESTION MODE: {mode_name}")
        hud.log_event("Using shared local assistant data. Remote device linking requires authenticated credentials.")
        mobile_server = MobileControlServer(hud, engine, user_id)
        hud.mobile_server = mobile_server
        try:
            mobile_server.start()
        except OSError as exc:
            message = "MOBILE CONTROL ERROR: Could not start LAN server: " + str(exc)
            hud.log_event(message)
            print("[SHASTRA] " + message, flush=True)
        # Do not automatically open a saved 3D model at startup.
        # Keep the SHASTRA core visible until the user explicitly requests 3D mode.
        threading.Thread(target=engine.voice_loop,daemon=True).start()
        print("[SHASTRA] Voice loop started.", flush=True)
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[SHASTRA] Stopped by user.", flush=True)
    except Exception as exc:
        import traceback
        print("\n[SHASTRA] FATAL ERROR:", repr(exc), flush=True)
        traceback.print_exc()
        try:
            input("\nPress Enter to close...")
        except Exception:
            pass
if __name__ == "__main__":
    main()