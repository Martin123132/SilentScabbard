import json
import os
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import font as tkfont
from urllib import error, request


def _first_existing_path(values):
    for value in values:
        if not value:
            continue
        path = Path(value)
        if path.exists():
            return path
    return None


def _resolve_ollama_exe():
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.environ.get("RONIN_OLLAMA_EXE"),
        r"D:\AI\Ollama\app\ollama.exe",
        str(Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe") if local_appdata else None,
        shutil.which("ollama"),
    ]
    return _first_existing_path(candidates)


def _resolve_ollama_models():
    configured = os.environ.get("RONIN_OLLAMA_MODELS") or os.environ.get("OLLAMA_MODELS")
    if configured:
        return configured
    d_models = Path(r"D:\AI\Ollama\models")
    if d_models.exists() or Path("D:/").exists():
        return str(d_models)
    return str(Path.home() / "SilentScabbard" / "ollama-models")


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SKIN_IMAGE = ASSETS_DIR / "ronin_skin.png"
SKIN_MANIFEST = ASSETS_DIR / "skin_manifest.json"
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
MEMORY_FILE = DATA_DIR / "memory.json"
VAULT_FILE = DATA_DIR / "vault.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_OLLAMA_EXE = _resolve_ollama_exe()
DEFAULT_OLLAMA_MODELS = _resolve_ollama_models()
DEFAULT_OLLAMA_API = "http://127.0.0.1:11434"
DEFAULT_MODEL_NAME = os.environ.get("RONIN_MODEL_NAME") or "ronin"

HIT_RECTS = {
    "model": (1202, 24, 1414, 62),
    "settings": (1432, 0, 1489, 75),
    "minimize": (1490, 0, 1545, 75),
    "close": (1592, 0, 1668, 75),
    "memory": (168, 873, 294, 914),
    "whisper": (306, 873, 441, 914),
    "session": (452, 873, 575, 914),
    "riddle": (626, 837, 928, 895),
    "plain": (952, 837, 1254, 895),
}


class RoninApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.configure(bg="#080806")
        self.resizable(False, False)

        self.messages = []
        self.last_answer = ""
        self.last_user_prompt = ""
        self.last_meaning = ""
        self.is_waiting = False
        self.drag_offset = None
        self.hover_target = None
        self.status_base = "LOCAL - WAKING OLLAMA"
        self.status_dots = 0
        self.lantern_step = 0
        self.ollama_ready = False
        self.typing_job = None
        self.meaning_job = None
        self.quote_full_text = ""
        self.meaning_full_text = ""
        self.quote_index = 0
        self.meaning_index = 0
        self.riddle_mode = True
        self.whisper_mode = False
        self.memory_enabled = True
        self.memory = []
        self.vault = []
        self.settings = {}
        self.ollama_exe = DEFAULT_OLLAMA_EXE
        self.ollama_models = DEFAULT_OLLAMA_MODELS
        self.ollama_api = DEFAULT_OLLAMA_API
        self.model_name = DEFAULT_MODEL_NAME
        self.data_lock = threading.Lock()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_jsonl = SESSIONS_DIR / f"{self.session_id}.jsonl"
        self.session_txt = SESSIONS_DIR / f"{self.session_id}.txt"

        self._prepare_local_data()
        self._build_fonts()
        self._load_skin()
        self._place_window()
        self._build_ui()
        self._start_ollama_in_background()
        self._start_animations()

    def _prepare_local_data(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text('{"memories": []}\n', encoding="utf-8")
        if not VAULT_FILE.exists():
            VAULT_FILE.write_text('{"items": []}\n', encoding="utf-8")
        if not SETTINGS_FILE.exists():
            self._save_settings(self._default_settings(), write_local_override=False)
        self.settings = self._load_settings()
        self._apply_settings(self.settings)
        self.memory = self._load_memory()
        self.vault = self._load_vault()
        self._append_session_event("system", "Session opened.")

    def _default_settings(self):
        return {
            "model_name": DEFAULT_MODEL_NAME,
            "ollama_exe": str(DEFAULT_OLLAMA_EXE) if DEFAULT_OLLAMA_EXE else "",
            "ollama_models": DEFAULT_OLLAMA_MODELS,
            "ollama_api": DEFAULT_OLLAMA_API,
        }

    def _current_settings(self):
        return {
            "model_name": self.model_name,
            "ollama_exe": str(self.ollama_exe) if self.ollama_exe else "",
            "ollama_models": self.ollama_models,
            "ollama_api": self.ollama_api,
        }

    def _load_settings(self):
        settings = self._default_settings()
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        if isinstance(raw, dict):
            for key in settings:
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    settings[key] = value.strip()
        return settings

    def _save_settings(self, settings, write_local_override=True):
        clean = self._clean_settings(settings)
        tmp_file = SETTINGS_FILE.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(clean, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        tmp_file.replace(SETTINGS_FILE)
        if write_local_override:
            self._write_local_override(clean)
        return clean

    def _clean_settings(self, settings):
        defaults = self._default_settings()
        clean = {}
        for key, default in defaults.items():
            value = settings.get(key, default) if isinstance(settings, dict) else default
            value = str(value).strip() if value is not None else ""
            clean[key] = value or default
        clean["ollama_api"] = clean["ollama_api"].rstrip("/")
        clean["model_name"] = re.sub(r"\s+", "-", clean["model_name"])
        return clean

    def _apply_settings(self, settings):
        clean = self._clean_settings(settings)
        self.settings = clean
        self.model_name = clean["model_name"]
        self.ollama_exe = Path(clean["ollama_exe"]) if clean["ollama_exe"] else None
        self.ollama_models = clean["ollama_models"]
        self.ollama_api = clean["ollama_api"]
        os.environ["OLLAMA_MODELS"] = self.ollama_models
        os.environ["RONIN_MODEL_NAME"] = self.model_name
        if self.ollama_exe:
            os.environ["RONIN_OLLAMA_EXE"] = str(self.ollama_exe)
        os.environ["RONIN_OLLAMA_MODELS"] = self.ollama_models

    def _write_local_override(self, settings):
        config_file = BASE_DIR / "ronin.local.ps1"
        lines = [
            f"$env:RONIN_OLLAMA_EXE = '{self._ps_escape(settings.get('ollama_exe', ''))}'",
            f"$env:RONIN_OLLAMA_MODELS = '{self._ps_escape(settings.get('ollama_models', ''))}'",
            f"$env:OLLAMA_MODELS = '{self._ps_escape(settings.get('ollama_models', ''))}'",
            f"$env:RONIN_MODEL_NAME = '{self._ps_escape(settings.get('model_name', DEFAULT_MODEL_NAME))}'",
            "",
        ]
        config_file.write_text("\n".join(lines), encoding="utf-8")

    def _ps_escape(self, value):
        return str(value).replace("'", "''")

    def _load_memory(self):
        try:
            raw = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        memories = raw.get("memories", raw if isinstance(raw, list) else [])
        if not isinstance(memories, list):
            return []
        clean = []
        for item in memories:
            if isinstance(item, dict) and item.get("text"):
                clean.append(item)
        return clean

    def _save_memory(self):
        payload = {"memories": self.memory}
        tmp_file = MEMORY_FILE.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp_file.replace(MEMORY_FILE)

    def _load_vault(self):
        try:
            raw = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        items = raw.get("items", raw if isinstance(raw, list) else [])
        if not isinstance(items, list):
            return []
        clean = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("answer"):
                continue
            tags = item.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            item["tags"] = [str(tag) for tag in tags if str(tag).strip()]
            item.setdefault("title", self._make_vault_title(item.get("prompt", ""), item.get("answer", "")))
            item.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
            clean.append(item)
        return clean

    def _save_vault(self):
        payload = {"items": self.vault}
        tmp_file = VAULT_FILE.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        tmp_file.replace(VAULT_FILE)

    def _append_session_event(self, role, content):
        event = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "role": role,
            "content": content,
        }
        with self.data_lock:
            with self.session_jsonl.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=True) + "\n")
            with self.session_txt.open("a", encoding="utf-8") as handle:
                handle.write(f"[{event['ts']}] {role.upper()}\n{content}\n\n")

    def _build_fonts(self):
        self.font_input = tkfont.Font(family="Georgia", size=16)
        self.font_button = tkfont.Font(family="Georgia", size=12)
        self.font_quote = tkfont.Font(family="Georgia", size=24)
        self.font_meaning = tkfont.Font(family="Georgia", size=14)
        self.font_status = tkfont.Font(family="Georgia", size=10)

    def _load_skin(self):
        self.skin = None
        self.skin_layers = []
        self.skin_manifest = None

        manifest = self._load_skin_manifest()
        if manifest:
            self.skin_manifest = manifest
            self.window_width = manifest["width"]
            self.window_height = manifest["height"]
            self.skin_layers = self._load_skin_layers(manifest)
            if self.skin_layers:
                return

        fallback_image = self._skin_fallback_path(manifest)
        if fallback_image and fallback_image.exists():
            self.skin = tk.PhotoImage(file=str(fallback_image))
            self.window_width = self.skin.width()
            self.window_height = self.skin.height()
        else:
            self.window_width = 1200
            self.window_height = 760

    def _load_skin_manifest(self):
        if not SKIN_MANIFEST.exists():
            return None
        try:
            raw = json.loads(SKIN_MANIFEST.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(raw, dict):
            return None
        layers = raw.get("layers", [])
        if not isinstance(layers, list):
            return None

        width = self._safe_int(raw.get("width"), 1668)
        height = self._safe_int(raw.get("height"), 936)
        fallback_file = str(raw.get("fallback_file", "ronin_skin.png")).strip() or "ronin_skin.png"
        clean_layers = []
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            file_name = str(layer.get("file", "")).strip()
            if not file_name:
                continue
            clean_layers.append(
                {
                    "name": str(layer.get("name", file_name)).strip() or file_name,
                    "file": file_name,
                    "x": self._safe_int(layer.get("x"), 0),
                    "y": self._safe_int(layer.get("y"), 0),
                    "enabled": bool(layer.get("enabled", True)),
                    "required": bool(layer.get("required", True)),
                }
            )

        if not clean_layers:
            return None
        return {"width": width, "height": height, "fallback_file": fallback_file, "layers": clean_layers}

    def _safe_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _load_skin_layers(self, manifest):
        layers = []
        for layer in manifest["layers"]:
            if not layer.get("enabled", True):
                continue
            image_path = (ASSETS_DIR / layer["file"]).resolve()
            try:
                image_path.relative_to(ASSETS_DIR.resolve())
            except ValueError:
                if layer.get("required", True):
                    return []
                continue
            if not image_path.exists():
                if layer.get("required", True):
                    return []
                continue
            try:
                image = tk.PhotoImage(file=str(image_path))
            except tk.TclError:
                if layer.get("required", True):
                    return []
                continue
            layers.append({"image": image, "x": layer["x"], "y": layer["y"], "name": layer["name"]})
        return layers

    def _skin_fallback_path(self, manifest):
        fallback_file = "ronin_skin.png"
        if manifest:
            fallback_file = manifest.get("fallback_file") or fallback_file
        fallback_path = (ASSETS_DIR / fallback_file).resolve()
        try:
            fallback_path.relative_to(ASSETS_DIR.resolve())
        except ValueError:
            return SKIN_IMAGE
        return fallback_path

    def _place_window(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max((screen_w - self.window_width) // 2, 0)
        y = max((screen_h - self.window_height) // 2, 0)
        self.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self,
            width=self.window_width,
            height=self.window_height,
            bg="#080806",
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        if self.skin_layers:
            for layer in self.skin_layers:
                self.canvas.create_image(layer["x"], layer["y"], image=layer["image"], anchor="nw")
        elif self.skin:
            self.canvas.create_image(0, 0, image=self.skin, anchor="nw")
        else:
            self._draw_fallback_background()

        self._create_lighting()
        self._create_dynamic_text()
        self._create_input()
        self._create_interaction_overlays()

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _event: setattr(self, "drag_offset", None))
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(200, self.entry.focus_set)

    def _draw_fallback_background(self):
        self.canvas.create_rectangle(0, 0, self.window_width, self.window_height, fill="#0c0b09", outline="")
        self.canvas.create_text(
            self.window_width / 2,
            72,
            text="Ronin",
            fill="#c8a96b",
            font=("Georgia", 32),
        )
        self.canvas.create_text(
            self.window_width / 2,
            self.window_height / 2,
            text="The room waits for its skin.",
            fill="#8a7b5d",
            font=("Georgia", 18),
        )

    def _create_lighting(self):
        self.hanging_glow = self.canvas.create_oval(
            1470,
            132,
            1596,
            322,
            fill="#211207",
            outline="",
            stipple="gray25",
        )
        self.floor_glow = self.canvas.create_oval(
            1376,
            516,
            1482,
            668,
            fill="#1c1007",
            outline="",
            stipple="gray25",
        )

    def _create_dynamic_text(self):
        self.quote_patch = None
        self.quote_item = None
        self.meaning_patch = None
        self.meaning_item = None
        self.status_patch = self.canvas.create_rectangle(698, 31, 996, 60, fill="#090907", outline="")
        self.status_dot = self.canvas.create_oval(709, 40, 719, 50, fill="#53bd76", outline="")
        self.status_item = self.canvas.create_text(
            850,
            45,
            text=self.status_base,
            fill="#d2c3a0",
            font=self.font_status,
            anchor="center",
        )

    def _create_input(self):
        self.entry = tk.Text(
            self,
            height=2,
            bg="#141414",
            fg="#d7c6a1",
            insertbackground="#d7c6a1",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            wrap="word",
            font=self.font_input,
        )
        self.entry_window = self.canvas.create_window(
            582,
            747,
            anchor="nw",
            width=620,
            height=68,
            window=self.entry,
        )
        self.entry.bind("<Return>", self._return_to_send)
        self.entry.bind("<Shift-Return>", lambda _event: None)
        self.entry.bind("<Control-Return>", self._send_from_event)

        self.send_button = tk.Button(
            self,
            text="SEND",
            command=self.send_message,
            bg="#141414",
            fg="#cdb477",
            activebackground="#1f1d19",
            activeforeground="#e1ca8b",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            font=self.font_button,
            cursor="hand2",
        )
        self.send_button.bind("<Enter>", lambda _event: self._style_send_button(True))
        self.send_button.bind("<Leave>", lambda _event: self._style_send_button(False))
        self.canvas.create_window(
            1220,
            760,
            anchor="nw",
            width=92,
            height=48,
            window=self.send_button,
        )

    def _create_interaction_overlays(self):
        self.riddle_select = self.canvas.create_rectangle(
            *HIT_RECTS["riddle"],
            outline="#d4b978",
            width=2,
        )
        self.memory_select = self.canvas.create_rectangle(
            *HIT_RECTS["memory"],
            outline="#d4b978",
            width=2,
        )
        self.whisper_select = self.canvas.create_rectangle(
            *HIT_RECTS["whisper"],
            outline="#d4b978",
            width=2,
            state="hidden",
        )
        self.hover_outline = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            outline="#e0c981",
            width=2,
            state="hidden",
        )
        self.close_hover = self.canvas.create_rectangle(
            *HIT_RECTS["close"],
            outline="#8d3f33",
            width=2,
            state="hidden",
        )

    def _style_send_button(self, hover):
        if self.is_waiting:
            return
        if hover:
            self.send_button.configure(bg="#1f1d19", fg="#e1ca8b")
        else:
            self.send_button.configure(bg="#141414", fg="#cdb477")

    def _return_to_send(self, event):
        if event.state & 0x0001:
            return None
        self.send_message()
        return "break"

    def _send_from_event(self, _event):
        self.send_message()
        return "break"

    def _on_mouse_move(self, event):
        target = self._hit_test(event)
        if target == self.hover_target:
            return

        self.hover_target = target
        self.canvas.configure(cursor="hand2" if target else "")
        self.canvas.itemconfigure(self.hover_outline, state="hidden")
        self.canvas.itemconfigure(self.close_hover, state="hidden")

        if not target:
            return

        if target == "close":
            self.canvas.itemconfigure(self.close_hover, state="normal")
            return

        if target in HIT_RECTS:
            self.canvas.coords(self.hover_outline, *HIT_RECTS[target])
            self.canvas.itemconfigure(self.hover_outline, state="normal")
            self.canvas.tag_raise(self.hover_outline)

    def _on_mouse_leave(self, _event):
        self.hover_target = None
        self.canvas.configure(cursor="")
        self.canvas.itemconfigure(self.hover_outline, state="hidden")
        self.canvas.itemconfigure(self.close_hover, state="hidden")

    def _on_mouse_down(self, event):
        target = self._hit_test(event)

        if target == "close":
            self.destroy()
            return

        if target == "minimize":
            self.iconify()
            return

        if target == "model":
            self._show_meaning(f"Model: {self.model_name}. The blade is local.")
            self._set_status("MODEL READY")
            return

        if target == "settings":
            self._show_meaning("Settings open. The forge has handles now.")
            self.open_settings_viewer()
            return

        if target == "memory":
            self.memory_enabled = not self.memory_enabled
            self.canvas.itemconfigure(self.memory_select, state="normal" if self.memory_enabled else "hidden")
            state = "ON" if self.memory_enabled else "OFF"
            count = len(self.memory)
            self._show_meaning(f"Memory {state}. {count} local memor{'y' if count == 1 else 'ies'} carved.")
            self._set_status(f"MEMORY {state}")
            self.open_memory_viewer()
            return

        if target == "whisper":
            self.whisper_mode = not self.whisper_mode
            self.canvas.itemconfigure(self.whisper_select, state="normal" if self.whisper_mode else "hidden")
            self._set_status("WHISPER MODE ON" if self.whisper_mode else "WHISPER MODE OFF")
            self.entry.focus_set()
            return

        if target == "session":
            count = len([m for m in self.messages if m["role"] == "user"])
            self._show_meaning(f"Session has {count} question{'s' if count != 1 else ''}. Logs are on D.")
            self._set_status("SESSION LOGGING")
            self.open_session_viewer()
            return

        if target == "riddle":
            self.riddle_mode = True
            self.canvas.itemconfigure(self.riddle_select, state="normal")
            self._set_status("RIDDLE MODE")
            self.entry.focus_set()
            return

        if target == "plain":
            self.explain_plainly()
            return

        if event.y <= 76:
            self.drag_offset = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _on_mouse_drag(self, event):
        if not self.drag_offset:
            return
        dx, dy = self.drag_offset
        self.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    def _hit_test(self, event):
        for name, rect in HIT_RECTS.items():
            if self._inside(event, *rect):
                return name
        return None

    def _inside(self, event, left, top, right, bottom):
        return left <= event.x <= right and top <= event.y <= bottom

    def _make_modal(self, title, width=760, height=560):
        modal = tk.Toplevel(self)
        modal.title(title)
        modal.configure(bg="#11100d")
        modal.transient(self)
        modal.geometry(self._centered_geometry(width, height))
        modal.minsize(520, 360)

        header = tk.Frame(modal, bg="#171511", padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text=title,
            bg="#171511",
            fg="#d4b978",
            font=self.font_button,
            anchor="w",
        ).pack(side="left")
        tk.Button(
            header,
            text="Close",
            command=modal.destroy,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="right")
        body = tk.Frame(modal, bg="#11100d", padx=16, pady=16)
        body.pack(fill="both", expand=True)
        return modal, body

    def _centered_geometry(self, width, height):
        x = self.winfo_x() + max((self.window_width - width) // 2, 0)
        y = self.winfo_y() + max((self.window_height - height) // 2, 0)
        return f"{width}x{height}+{x}+{y}"

    def _make_text_view(self, parent, text):
        view = tk.Text(
            parent,
            bg="#15130f",
            fg="#e1d6c0",
            insertbackground="#e1d6c0",
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            wrap="word",
            font=self.font_meaning,
        )
        scrollbar = tk.Scrollbar(parent, command=view.yview)
        view.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        view.pack(side="left", fill="both", expand=True)
        view.insert("1.0", text)
        view.configure(state="disabled")
        return view

    def open_settings_viewer(self):
        self._set_status("SETTINGS OPEN")
        modal, body = self._make_modal("Settings", width=920, height=650)

        fields = {}

        def add_field(label_text, key, browse_kind=None):
            row = tk.Frame(body, bg="#11100d")
            row.pack(fill="x", pady=(0, 10))
            tk.Label(
                row,
                text=label_text,
                bg="#11100d",
                fg="#d4b978",
                font=self.font_status,
                anchor="w",
                width=18,
            ).pack(side="left")
            entry = tk.Entry(
                row,
                bg="#15130f",
                fg="#e1d6c0",
                insertbackground="#e1d6c0",
                relief="flat",
                bd=0,
                font=self.font_meaning,
            )
            entry.insert(0, self._current_settings().get(key, ""))
            entry.pack(side="left", fill="x", expand=True, ipady=7)
            fields[key] = entry

            if browse_kind:
                def browse():
                    if browse_kind == "file":
                        path = filedialog.askopenfilename(
                            parent=modal,
                            title="Choose ollama.exe",
                            filetypes=[("Ollama executable", "ollama.exe"), ("Executable", "*.exe"), ("All files", "*.*")],
                        )
                    else:
                        path = filedialog.askdirectory(parent=modal, title="Choose model storage folder")
                    if path:
                        entry.delete(0, "end")
                        entry.insert(0, path)

                self._modal_button(row, "Browse", browse).pack(side="left", padx=(10, 0))

        add_field("Model name", "model_name")
        add_field("Ollama executable", "ollama_exe", "file")
        add_field("Model storage", "ollama_models", "directory")
        add_field("Ollama API", "ollama_api")

        output_frame = tk.Frame(body, bg="#11100d")
        output_frame.pack(fill="both", expand=True, pady=(8, 0))
        output = tk.Text(
            output_frame,
            bg="#15130f",
            fg="#e1d6c0",
            insertbackground="#e1d6c0",
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            wrap="word",
            font=self.font_status,
            height=12,
        )
        output_scroll = tk.Scrollbar(output_frame, command=output.yview)
        output.configure(yscrollcommand=output_scroll.set)
        output.pack(side="left", fill="both", expand=True)
        output_scroll.pack(side="right", fill="y")

        def set_output(text):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", text)
            output.configure(state="disabled")

        def settings_from_fields():
            return {
                "model_name": fields["model_name"].get().strip(),
                "ollama_exe": fields["ollama_exe"].get().strip(),
                "ollama_models": fields["ollama_models"].get().strip(),
                "ollama_api": fields["ollama_api"].get().strip(),
            }

        def save_settings():
            settings = self._save_settings(settings_from_fields())
            self._apply_settings(settings)
            self._append_session_event("system", "Settings saved.")
            warning = self._settings_warning(settings)
            message = "Settings saved to data/settings.json and ronin.local.ps1."
            if warning:
                message += "\n\n" + warning
            set_output(message)
            self._show_meaning("Settings saved locally.", typed=True)
            self._set_status("SETTINGS SAVED")

        def reset_defaults():
            defaults = self._default_settings()
            for key, entry in fields.items():
                entry.delete(0, "end")
                entry.insert(0, defaults.get(key, ""))
            set_output("Defaults restored in the form. Press Save to keep them.")
            self._set_status("SETTINGS DEFAULTS")

        def run_health_check():
            set_output("Checking local paths and model state...")
            self._set_status("HEALTH CHECK")
            settings = self._clean_settings(settings_from_fields())

            def work():
                text = self._settings_health_text(settings)
                self.after(0, lambda: set_output(text))

            threading.Thread(target=work, daemon=True).start()

        def rebuild_model():
            settings = self._save_settings(settings_from_fields())
            self._apply_settings(settings)
            set_output("Rebuilding the local model. This may take a while if the base model is missing...")
            self._set_status("MODEL REBUILDING")

            def work():
                text = self._rebuild_model_text(settings)
                self.after(0, lambda: set_output(text))
                self.after(0, lambda: self._set_status("MODEL READY" if "success" in text.lower() else "MODEL REBUILD CHECK"))

            threading.Thread(target=work, daemon=True).start()

        def open_data_folder():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(str(DATA_DIR))
            self._set_status("DATA FOLDER")

        buttons = tk.Frame(body, bg="#11100d")
        buttons.pack(fill="x", pady=(12, 0))
        self._modal_button(buttons, "Save", save_settings).pack(side="left")
        self._modal_button(buttons, "Health Check", run_health_check).pack(side="left", padx=(10, 0))
        self._modal_button(buttons, "Open Vault", self.open_vault_viewer).pack(side="left", padx=(10, 0))
        self._modal_button(buttons, "Data Folder", open_data_folder).pack(side="left", padx=(10, 0))
        self._modal_button(buttons, "Rebuild Model", rebuild_model, danger=True).pack(side="left", padx=(10, 0))
        self._modal_button(buttons, "Reset Defaults", reset_defaults).pack(side="right")

        set_output(
            "Settings are local to this folder.\n\n"
            "Press Save after changing paths or model name.\n"
            "Press Health Check to verify Ollama, model storage, and the current model."
        )
        modal.focus_set()

    def _modal_button(self, parent, text, command, danger=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#3a211b" if danger else "#252119",
            fg="#e0b9a8" if danger else "#d7c6a1",
            activebackground="#4a2b23" if danger else "#322b20",
            activeforeground="#f0d0c1" if danger else "#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        )

    def _settings_warning(self, settings):
        model_dir = settings.get("ollama_models", "")
        if re.match(r"^[cC]:\\", model_dir):
            return "Warning: model storage is on C:. Use a larger drive for model files if possible."
        if Path("D:/").exists() and not re.match(r"^[dD]:\\", model_dir):
            return "D: exists, but model storage is not on D:."
        return ""

    def _settings_health_text(self, settings):
        settings = self._clean_settings(settings)
        ollama_exe = Path(settings["ollama_exe"]) if settings.get("ollama_exe") else None
        model_dir = settings["ollama_models"]
        model_name = settings["model_name"]
        api = settings["ollama_api"]

        lines = [
            "SilentScabbard settings",
            "",
            f"App folder:       {BASE_DIR}",
            f"Model name:       {model_name}",
            f"Ollama exe:       {ollama_exe if ollama_exe else 'missing'}",
            f"Model directory:  {model_dir}",
            f"Ollama API:       {api}",
            "",
        ]

        warning = self._settings_warning(settings)
        if warning:
            lines.extend([warning, ""])

        api_ready = False
        try:
            with request.urlopen(f"{api}/api/version", timeout=2) as response:
                api_ready = response.status == 200
        except (OSError, error.URLError):
            api_ready = False

        lines.append(f"API ready:        {'yes' if api_ready else 'no'}")
        lines.append(f"Ollama exe found: {'yes' if ollama_exe and ollama_exe.exists() else 'no'}")
        lines.append(f"Model dir exists: {'yes' if Path(model_dir).exists() else 'no'}")

        model_present = False
        if ollama_exe and ollama_exe.exists():
            env = os.environ.copy()
            env["OLLAMA_MODELS"] = model_dir
            try:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    [str(ollama_exe), "list"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=flags,
                )
                model_present = bool(re.search(rf"(?m)^{re.escape(model_name)}(?::latest)?\s", result.stdout))
            except (OSError, subprocess.SubprocessError):
                model_present = False

        lines.append(f"Model present:    {'yes' if model_present else 'no'}")
        lines.append(f"C model cache:    {self._directory_size_gb(Path.home() / '.ollama' / 'models')} GB")

        for drive in ("C:/", "D:/"):
            drive_path = Path(drive)
            if drive_path.exists():
                usage = shutil.disk_usage(drive_path)
                lines.append(f"{drive_path.drive} free:          {round(usage.free / 1024 / 1024 / 1024, 2)} GB")

        if model_present and api_ready:
            lines.extend(["", "Health: ready."])
        else:
            lines.extend(["", "Health: needs setup or repair."])
        return "\n".join(lines)

    def _directory_size_gb(self, path):
        if not path.exists():
            return 0
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except OSError:
                    pass
        return round(total / 1024 / 1024 / 1024, 4)

    def _rebuild_model_text(self, settings):
        settings = self._clean_settings(settings)
        ollama_exe = Path(settings["ollama_exe"]) if settings.get("ollama_exe") else None
        if not ollama_exe or not ollama_exe.exists():
            return "Cannot rebuild. Ollama executable was not found."

        model_dir = Path(settings["ollama_models"])
        model_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = str(model_dir)

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                [str(ollama_exe), "create", settings["model_name"], "-f", str(BASE_DIR / "Modelfile")],
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
                creationflags=flags,
            )
        except Exception as exc:
            return f"Model rebuild failed:\n{exc}"

        output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
        if result.returncode == 0:
            return "Model rebuild success.\n\n" + (output or "Ollama completed without extra output.")
        return f"Model rebuild failed with exit code {result.returncode}.\n\n{output}"

    def open_session_viewer(self):
        self._set_status("SESSION LOG OPEN")
        modal, body = self._make_modal("Session Log")
        path_label = tk.Label(
            body,
            text=str(self.session_txt),
            bg="#11100d",
            fg="#8f8263",
            font=self.font_status,
            anchor="w",
        )
        path_label.pack(fill="x", pady=(0, 10))
        try:
            text = self.session_txt.read_text(encoding="utf-8")
        except OSError as exc:
            text = f"Could not read session log:\n{exc}"
        if not text.strip():
            text = "The page is still blank."
        self._make_text_view(body, text)
        modal.focus_set()

    def open_vault_viewer(self):
        self.vault = self._load_vault()
        self._set_status("VAULT OPEN")
        modal, body = self._make_modal("Ronin Vault", width=940, height=620)

        summary = tk.Label(
            body,
            text=self._vault_summary_text(),
            bg="#11100d",
            fg="#d7c6a1",
            font=self.font_meaning,
            anchor="w",
        )
        summary.pack(fill="x", pady=(0, 10))

        search_frame = tk.Frame(body, bg="#11100d")
        search_frame.pack(fill="x", pady=(0, 12))
        search_entry = tk.Entry(
            search_frame,
            bg="#15130f",
            fg="#e1d6c0",
            insertbackground="#e1d6c0",
            relief="flat",
            bd=0,
            font=self.font_meaning,
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=7)

        content = tk.Frame(body, bg="#11100d")
        content.pack(fill="both", expand=True)

        list_frame = tk.Frame(content, bg="#11100d")
        list_frame.pack(side="left", fill="both", expand=True)
        item_list = tk.Listbox(
            list_frame,
            bg="#15130f",
            fg="#e1d6c0",
            selectbackground="#5c4828",
            selectforeground="#fff3cf",
            relief="flat",
            bd=0,
            activestyle="none",
            font=self.font_status,
        )
        list_scroll = tk.Scrollbar(list_frame, command=item_list.yview)
        item_list.configure(yscrollcommand=list_scroll.set)
        item_list.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")

        detail_frame = tk.Frame(content, bg="#11100d")
        detail_frame.pack(side="right", fill="both", expand=True, padx=(14, 0))
        detail = tk.Text(
            detail_frame,
            bg="#15130f",
            fg="#e1d6c0",
            insertbackground="#e1d6c0",
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            wrap="word",
            font=self.font_meaning,
            width=42,
        )
        detail_scroll = tk.Scrollbar(detail_frame, command=detail.yview)
        detail.configure(yscrollcommand=detail_scroll.set)
        detail.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        visible_items = []

        def set_detail(text):
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("1.0", text)
            detail.configure(state="disabled")

        def selected_item():
            selection = item_list.curselection()
            if not selection:
                return None
            index = selection[0]
            if 0 <= index < len(visible_items):
                return visible_items[index]
            return None

        def refresh(query=None):
            nonlocal visible_items
            self.vault = self._load_vault()
            query = (query or "").strip()
            if query:
                visible_items = self._search_vault(query, limit=None)
            else:
                visible_items = sorted(
                    self.vault,
                    key=lambda item: item.get("created_at", ""),
                    reverse=True,
                )

            item_list.delete(0, "end")
            for item in visible_items:
                title = item.get("title", "Untitled")
                created = item.get("created_at", "")[:10]
                tags = ", ".join(item.get("tags", []))
                suffix = f"  [{tags}]" if tags else ""
                item_list.insert("end", f"{created}  {title}{suffix}")

            summary.configure(text=self._vault_summary_text(query=query, visible=len(visible_items)))
            if visible_items:
                item_list.selection_set(0)
                item_list.activate(0)
                set_detail(self._vault_detail_text(visible_items[0]))
            else:
                set_detail("No saved scrolls match this search.")

        def on_select(_event=None):
            item = selected_item()
            if item:
                set_detail(self._vault_detail_text(item))

        def search():
            refresh(search_entry.get())
            self._set_status("VAULT SEARCH")

        def clear_search():
            search_entry.delete(0, "end")
            refresh()
            self._set_status("VAULT OPEN")

        def save_last():
            result, item = self._save_current_exchange_to_vault()
            if result == "missing":
                self._set_status("NOTHING TO VAULT")
                set_detail("Ask Ronin something first, then use Save Last Exchange.")
                return
            self._append_session_event("system", f"Vault {result}: {item.get('title', 'Untitled')}")
            self._show_meaning(f"Vault {result}. {len(self.vault)} saved scroll{'s' if len(self.vault) != 1 else ''}.", typed=True)
            self._set_status("VAULT SAVED" if result == "saved" else "VAULT UPDATED")
            refresh(search_entry.get())

        def remember_selected():
            item = selected_item()
            if not item:
                self._set_status("SELECT A SCROLL")
                return
            memory_text = f"User saved a vault scroll named {item.get('title', 'Untitled')}."
            saved = self._add_memory(memory_text, f"vault:{item.get('id', '')}")
            self._append_session_event("system", f"Vault promoted to memory: {item.get('title', 'Untitled')}")
            self._set_status("MEMORY CARVED" if saved else "MEMORY UNCHANGED")
            self._show_meaning("Vault title remembered." if saved else "That vault title was already remembered.", typed=True)

        def delete_selected():
            item = selected_item()
            if not item:
                self._set_status("SELECT A SCROLL")
                return
            item_id = item.get("id")
            self.vault = [saved for saved in self._load_vault() if saved.get("id") != item_id]
            self._save_vault()
            self._append_session_event("system", f"Deleted vault item: {item.get('title', 'Untitled')}")
            self._set_status("VAULT DELETED")
            refresh(search_entry.get())

        item_list.bind("<<ListboxSelect>>", on_select)
        search_entry.bind("<Return>", lambda _event: (search(), "break")[1])

        tk.Button(
            search_frame,
            text="Search",
            command=search,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))
        tk.Button(
            search_frame,
            text="Clear",
            command=clear_search,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        buttons = tk.Frame(body, bg="#11100d")
        buttons.pack(fill="x", pady=(12, 0))
        tk.Button(
            buttons,
            text="Save Last Exchange",
            command=save_last,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            buttons,
            text="Remember Selected",
            command=remember_selected,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))
        tk.Button(
            buttons,
            text="Delete Selected",
            command=delete_selected,
            bg="#3a211b",
            fg="#e0b9a8",
            activebackground="#4a2b23",
            activeforeground="#f0d0c1",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))
        tk.Button(
            buttons,
            text="Refresh",
            command=lambda: refresh(search_entry.get()),
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="right")

        refresh()
        modal.focus_set()

    def open_memory_viewer(self):
        self.memory = self._load_memory()
        self._set_status("MEMORY OPEN")
        modal, body = self._make_modal("Local Memory")

        summary = tk.Label(
            body,
            text=self._memory_summary_text(),
            bg="#11100d",
            fg="#d7c6a1",
            font=self.font_meaning,
            anchor="w",
        )
        summary.pack(fill="x", pady=(0, 10))

        list_frame = tk.Frame(body, bg="#11100d")
        list_frame.pack(fill="both", expand=True)
        memory_list = tk.Listbox(
            list_frame,
            bg="#15130f",
            fg="#e1d6c0",
            selectbackground="#5c4828",
            selectforeground="#fff3cf",
            relief="flat",
            bd=0,
            activestyle="none",
            font=self.font_meaning,
        )
        scrollbar = tk.Scrollbar(list_frame, command=memory_list.yview)
        memory_list.configure(yscrollcommand=scrollbar.set)
        memory_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def refresh():
            self.memory = self._load_memory()
            memory_list.delete(0, "end")
            for index, item in enumerate(self.memory, start=1):
                memory_list.insert("end", f"{index}. {item.get('text', '')}")
            summary.configure(text=self._memory_summary_text())
            state = "ON" if self.memory_enabled else "OFF"
            self.canvas.itemconfigure(self.memory_select, state="normal" if self.memory_enabled else "hidden")
            self._show_meaning(f"Memory {state}. {len(self.memory)} local memor{'y' if len(self.memory) == 1 else 'ies'} carved.")

        def forget_selected():
            selection = memory_list.curselection()
            if not selection:
                self._set_status("SELECT A MEMORY")
                return
            index = selection[0]
            if 0 <= index < len(self.memory):
                removed = self.memory.pop(index)
                self._save_memory()
                self._append_session_event("system", f"Forgot memory: {removed.get('text', '')}")
                self._set_status("MEMORY FORGOTTEN")
                refresh()

        def forget_all():
            self._clear_memory()
            self._append_session_event("system", "Forgot all memories from memory viewer.")
            self._set_status("MEMORY CLEARED")
            refresh()

        buttons = tk.Frame(body, bg="#11100d")
        buttons.pack(fill="x", pady=(12, 0))
        tk.Button(
            buttons,
            text="Forget Selected",
            command=forget_selected,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            buttons,
            text="Forget Everything",
            command=forget_all,
            bg="#3a211b",
            fg="#e0b9a8",
            activebackground="#4a2b23",
            activeforeground="#f0d0c1",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))
        tk.Button(
            buttons,
            text="Refresh",
            command=refresh,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=self.font_status,
            cursor="hand2",
        ).pack(side="right")

        refresh()
        modal.focus_set()

    def _memory_summary_text(self):
        state = "on" if self.memory_enabled else "off"
        count = len(self.memory)
        return f"Memory is {state}. {count} local memor{'y' if count == 1 else 'ies'} stored on D."

    def _vault_summary_text(self, query=None, visible=None):
        count = len(self.vault)
        if query:
            shown = visible if visible is not None else 0
            return f"Vault search: {shown} of {count} saved scroll{'s' if count != 1 else ''} matched."
        return f"Vault holds {count} saved scroll{'s' if count != 1 else ''} on D."

    def _shorten_text(self, text, limit=72):
        text = re.sub(r"\s+", " ", (text or "").strip())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _make_vault_title(self, prompt, answer):
        base = self._shorten_text(prompt, 64) or self._shorten_text(answer, 64)
        return base or "Untitled scroll"

    def _vault_signature(self, prompt, answer):
        joined = f"{prompt}\n---\n{answer}".lower()
        return re.sub(r"\s+", " ", joined).strip()

    def _parse_vault_details(self, raw):
        raw = (raw or "").strip()
        if not raw:
            return None, []

        title_text = raw
        tag_text = ""
        if "|" in raw:
            title_text, tag_text = raw.split("|", 1)

        hash_tags = re.findall(r"#([A-Za-z0-9 _-]+)", raw)
        title_text = re.sub(r"#[A-Za-z0-9 _-]+", "", title_text).strip()
        tags = self._parse_tags(tag_text)
        tags.extend(self._clean_tag(tag) for tag in hash_tags)
        tags = [tag for tag in dict.fromkeys(tags) if tag]
        return title_text or None, tags

    def _parse_tags(self, raw):
        tags = []
        for part in re.split(r"[,#]", raw or ""):
            tag = self._clean_tag(part)
            if tag:
                tags.append(tag)
        return tags

    def _clean_tag(self, value):
        value = re.sub(r"[^A-Za-z0-9 _-]", "", (value or "")).strip().lower()
        value = re.sub(r"\s+", "-", value)
        return value[:32]

    def _save_current_exchange_to_vault(self, title=None, tags=None):
        prompt = (self.last_user_prompt or "").strip()
        answer = (self.last_answer or "").strip()
        if not prompt or not answer:
            return "missing", {}

        self.vault = self._load_vault()
        signature = self._vault_signature(prompt, answer)
        tags = [tag for tag in (tags or []) if tag]
        now = datetime.now().isoformat(timespec="seconds")

        for item in self.vault:
            existing_signature = item.get("signature") or self._vault_signature(
                item.get("prompt", ""),
                item.get("answer", ""),
            )
            if existing_signature != signature:
                continue
            item["signature"] = signature
            if title:
                item["title"] = title
            existing_tags = item.get("tags", [])
            item["tags"] = [tag for tag in dict.fromkeys(existing_tags + tags) if tag]
            if self.last_meaning and not item.get("meaning"):
                item["meaning"] = self.last_meaning
            item["updated_at"] = now
            self._save_vault()
            return "updated", item

        item = {
            "id": f"vault-{int(time.time() * 1000)}-{len(self.vault) + 1:03d}",
            "title": title or self._make_vault_title(prompt, answer),
            "prompt": prompt,
            "answer": answer,
            "meaning": self.last_meaning,
            "tags": tags,
            "created_at": now,
            "source_session": self.session_id,
            "signature": signature,
        }
        self.vault.append(item)
        self._save_vault()
        return "saved", item

    def _search_vault(self, query, limit=6):
        self.vault = self._load_vault()
        terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_-]+", query or "")]
        if not terms:
            return []

        scored = []
        for item in self.vault:
            title = item.get("title", "")
            tags = " ".join(item.get("tags", []))
            prompt = item.get("prompt", "")
            answer = item.get("answer", "")
            meaning = item.get("meaning", "")
            blob = f"{title} {tags} {prompt} {answer} {meaning}".lower()
            if not all(term in blob for term in terms):
                continue

            score = 0
            title_lower = title.lower()
            tags_lower = tags.lower()
            for term in terms:
                if term in title_lower:
                    score += 5
                if term in tags_lower:
                    score += 3
                if term in prompt.lower():
                    score += 2
                if term in answer.lower() or term in meaning.lower():
                    score += 1
            scored.append((score, item.get("created_at", ""), item))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        results = [item for _score, _created, item in scored]
        if limit is None:
            return results
        return results[:limit]

    def _vault_detail_text(self, item):
        tags = ", ".join(item.get("tags", [])) or "none"
        lines = [
            item.get("title", "Untitled scroll"),
            f"Saved: {item.get('created_at', 'unknown')}",
            f"Session: {item.get('source_session', 'unknown')}",
            f"Tags: {tags}",
            "",
            "Prompt:",
            item.get("prompt", ""),
            "",
            "Answer:",
            item.get("answer", ""),
        ]
        meaning = item.get("meaning", "").strip()
        if meaning:
            lines.extend(["", "Plain meaning:", meaning])
        return "\n".join(lines)

    def _handle_local_vault_command(self, prompt):
        text = prompt.strip()
        compact = re.sub(r"\s+", " ", text.lower())

        if compact in {"vault", "open vault", "show vault", "vault open"}:
            self.open_vault_viewer()
            self.vault = self._load_vault()
            count = len(self.vault)
            return "The vault door slides open.", f"Vault holds {count} saved scroll{'s' if count != 1 else ''} on D."

        search_match = re.match(r"^(?:search vault|vault search|find vault)\s*:?\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
        if search_match:
            query = self._clean_memory_value(search_match.group(1))
            results = self._search_vault(query)
            if not results:
                return "No scroll answers.", f"No vault matches for: {query}"
            lines = ["The vault answers:"]
            for index, item in enumerate(results[:3], start=1):
                lines.append(f"{index}. {item.get('title', 'Untitled scroll')}")
            return "\n".join(lines), f"Vault search found {len(results)} match{'es' if len(results) != 1 else ''}. Open the gear to browse."

        tag_match = re.match(r"^tag\s+(?:this|last|answer)\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
        save_match = re.match(r"^(?:save|vault)\s+(?:this|that|last|answer)(?:\s*:?\s*(.*))?$", text, flags=re.IGNORECASE | re.DOTALL)
        if not tag_match and not save_match:
            return None

        if tag_match:
            raw_details = tag_match.group(1)
            title = None
            tags = self._parse_tags(raw_details)
        else:
            raw_details = save_match.group(1)
            title, tags = self._parse_vault_details(raw_details)
        result, item = self._save_current_exchange_to_vault(title=title, tags=tags)
        if result == "missing":
            return "The vault waits empty-handed.", "Ask Ronin first, then use `save this`."
        if result == "updated":
            return "The old scroll gains a sharper knot.", f"Vault updated: {item.get('title', 'Untitled scroll')}"
        return "The scroll enters the vault.", f"Vault saved: {item.get('title', 'Untitled scroll')}"

    def _start_animations(self):
        self._animate_lantern()
        self._animate_status()

    def _animate_lantern(self):
        if not self.winfo_exists():
            return

        idle = ["#1b1007", "#231307", "#2b1809", "#201207"]
        active = ["#2d1808", "#3b210d", "#4b2c12", "#34200d"]
        palette = active if self.is_waiting else idle
        color = palette[self.lantern_step % len(palette)]
        floor_color = active[(self.lantern_step + 2) % len(active)] if self.is_waiting else idle[(self.lantern_step + 1) % len(idle)]
        self.canvas.itemconfigure(self.hanging_glow, fill=color)
        self.canvas.itemconfigure(self.floor_glow, fill=floor_color)
        self.canvas.itemconfigure(self.status_dot, fill="#76d18d" if self.ollama_ready else "#9f7b42")
        self.lantern_step += 1
        self.after(520, self._animate_lantern)

    def _animate_status(self):
        if not self.winfo_exists():
            return

        animated = self.is_waiting or "WAKING" in self.status_base or "UNFOLDS" in self.status_base
        dots = "." * (self.status_dots % 4) if animated else ""
        self.canvas.itemconfigure(self.status_item, text=f"{self.status_base}{dots}")
        self.status_dots += 1
        self.after(420, self._animate_status)

    def _start_ollama_in_background(self):
        thread = threading.Thread(target=self._ensure_ollama_ready, daemon=True)
        thread.start()

    def _ensure_ollama_ready(self):
        if self._api_ready():
            self.ollama_ready = True
            self._set_status("LOCAL - OLLAMA CONNECTED")
            return

        if not self.ollama_exe:
            self.ollama_ready = False
            self._set_status("OLLAMA NOT FOUND")
            return

        env = os.environ.copy()
        env["OLLAMA_MODELS"] = self.ollama_models

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                [str(self.ollama_exe), "serve"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        except OSError as exc:
            self.ollama_ready = False
            self._set_status(f"OLLAMA FAILED: {exc}")
            return

        for _ in range(30):
            if self._api_ready():
                self.ollama_ready = True
                self._set_status("LOCAL - OLLAMA CONNECTED")
                return
            time.sleep(0.5)

        self.ollama_ready = False
        self._set_status("OLLAMA STILL WAKING")

    def _api_ready(self):
        try:
            with request.urlopen(f"{self.ollama_api}/api/version", timeout=2) as response:
                return response.status == 200
        except (OSError, error.URLError):
            return False

    def _extract_memory_text(self, prompt):
        text = prompt.strip()
        patterns = [
            (r"^remember this\s*:\s*(.+)$", "{value}"),
            (r"^remember\s*:\s*(.+)$", "{value}"),
            (r"^remember\s+(.+)$", "{value}"),
            (r"^my name is\s+(.+)$", "User's name is {value}."),
            (r"^call me\s+(.+)$", "User wants to be called {value}."),
        ]
        for pattern, template in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            value = self._clean_memory_value(match.group(1))
            if value:
                return template.format(value=value)
        return None

    def _clean_memory_value(self, value):
        value = value.strip().strip('"').strip("'").strip()
        value = re.sub(r"\s+", " ", value)
        return value

    def _add_memory(self, text, source):
        existing = {item.get("text", "").lower() for item in self.memory}
        if text.lower() in existing:
            return False
        item = {
            "id": f"mem-{int(time.time() * 1000)}-{len(self.memory) + 1:03d}",
            "text": text,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": source,
        }
        self.memory.append(item)
        self._save_memory()
        return True

    def _clear_memory(self):
        self.memory = []
        self._save_memory()

    def _memory_prompt_message(self):
        if not self.memory_enabled or not self.memory:
            return None
        lines = [f"- {item['text']}" for item in self.memory[-12:]]
        return {
            "role": "system",
            "content": "Known local memory:\n" + "\n".join(lines),
        }

    def _handle_local_memory_command(self, prompt):
        if prompt.strip().lower() == "forget everything":
            self._clear_memory()
            return "The slate is ash. Nothing remains.", "Memory cleared. 0 local memories."

        memory_text = self._extract_memory_text(prompt)
        if not memory_text:
            return None

        saved = self._add_memory(memory_text, prompt)
        if saved:
            count = len(self.memory)
            return "Carved into the quiet wood.", f"Memory saved. {count} local memor{'y' if count == 1 else 'ies'}."
        return "The mark was already carved.", f"Memory unchanged. {len(self.memory)} local memories."

    def send_message(self):
        if self.is_waiting:
            return

        prompt = self.entry.get("1.0", "end").strip()
        if not prompt:
            self._set_status("EMPTY SCABBARD")
            return

        self.entry.delete("1.0", "end")
        self.messages.append({"role": "user", "content": prompt})
        self._append_session_event("user", prompt)

        local_result = self._handle_local_memory_command(prompt)
        if not local_result:
            local_result = self._handle_local_vault_command(prompt)
        if local_result:
            answer, meaning = local_result
            self.messages.append({"role": "assistant", "content": answer})
            self._append_session_event("assistant", answer)
            self._show_quote(answer, typed=True)
            self._show_meaning(meaning, typed=True)
            meaning_lower = meaning.lower()
            if "vault" in meaning_lower:
                self._set_status("VAULT UPDATED")
            elif "saved" in meaning_lower:
                self._set_status("MEMORY CARVED")
            elif "cleared" in meaning_lower:
                self._set_status("MEMORY CLEARED")
            else:
                self._set_status("MEMORY UNCHANGED")
            return

        self.last_user_prompt = prompt
        self.last_meaning = ""
        self._set_waiting(True, "THE BLADE IS THINKING")

        thread = threading.Thread(target=self._ask_ronin, daemon=True)
        thread.start()

    def _ask_ronin(self):
        mode_prompt = (
            "You are Kage inside a local desktop app. Reply in plain English. "
            "Give useful counsel through restrained riddle language. "
            "Use one to three short lines unless the user clearly asks for detail. "
            "Do not explain the riddle unless asked."
        )
        if self.whisper_mode:
            mode_prompt += " Whisper mode is on: answer in one quiet line."

        messages = [{"role": "system", "content": mode_prompt}]
        memory_message = self._memory_prompt_message()
        if memory_message:
            messages.append(memory_message)
        messages.extend(self.messages[-16:])

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.78,
                "top_p": 0.9,
                "num_predict": 120 if self.whisper_mode else 160,
            },
        }
        answer = self._post_chat(payload)
        self.messages.append({"role": "assistant", "content": answer})
        self.last_answer = answer
        self.after(0, lambda: self._receive_answer(answer))

    def explain_plainly(self):
        if self.is_waiting:
            return
        if not self.last_answer:
            self._show_meaning("Ask first. Meaning follows the riddle.")
            return

        self._set_waiting(True, "MEANING UNFOLDS")
        thread = threading.Thread(target=self._ask_meaning, daemon=True)
        thread.start()

    def _ask_meaning(self):
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "Explain the previous riddle plainly in one short practical sentence. Use no samurai voice.",
                },
                {"role": "user", "content": self.last_answer},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 80,
            },
        }
        meaning = self._post_chat(payload)
        self.after(0, lambda: self._receive_meaning(meaning))

    def _post_chat(self, payload):
        try:
            data = json.dumps(payload).encode("utf-8")
            req = request.Request(
                f"{self.ollama_api}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = result.get("message", {}).get("content", "").strip()
            return answer or "The lantern is lit, but gives no answer."
        except Exception as exc:
            return f"The gate sticks: {exc}"

    def _receive_answer(self, answer):
        self.last_answer = answer
        self.last_meaning = ""
        self._append_session_event("assistant", answer)
        self._show_quote(answer, typed=True)
        self._show_meaning("Plain meaning waits beneath the paper.", typed=True)
        self._set_waiting(False, "LOCAL - OLLAMA CONNECTED")

    def _receive_meaning(self, meaning):
        self.last_meaning = meaning
        self._append_session_event("meaning", meaning)
        self._show_meaning(meaning, typed=True)
        self._set_waiting(False, "LOCAL - OLLAMA CONNECTED")

    def _show_quote(self, text, typed=False):
        self._cancel_typing("quote")
        if self.quote_patch:
            self.canvas.delete(self.quote_patch)
        if self.quote_item:
            self.canvas.delete(self.quote_item)

        self.quote_patch = self.canvas.create_rectangle(145, 220, 558, 390, fill="#b8a581", outline="")
        self.quote_item = self.canvas.create_text(
            352,
            305,
            text="",
            fill="#1d1a14",
            font=self.font_quote,
            width=440,
            justify="center",
            anchor="center",
        )
        if typed:
            self.quote_full_text = text
            self.quote_index = 0
            self._type_quote()
        else:
            self.canvas.itemconfigure(self.quote_item, text=text)

    def _show_meaning(self, text, typed=False):
        self._cancel_typing("meaning")
        if self.meaning_patch:
            self.canvas.delete(self.meaning_patch)
        if self.meaning_item:
            self.canvas.delete(self.meaning_item)

        self.meaning_patch = self.canvas.create_rectangle(95, 620, 510, 670, fill="#211d17", outline="")
        self.meaning_item = self.canvas.create_text(
            115,
            642,
            text="",
            fill="#e1d6c0",
            font=self.font_meaning,
            width=390,
            justify="left",
            anchor="w",
        )
        if typed:
            self.meaning_full_text = text
            self.meaning_index = 0
            self._type_meaning()
        else:
            self.canvas.itemconfigure(self.meaning_item, text=text)

    def _type_quote(self):
        if not self.quote_item:
            return
        step = 2 if len(self.quote_full_text) > 110 else 1
        self.quote_index = min(self.quote_index + step, len(self.quote_full_text))
        self.canvas.itemconfigure(self.quote_item, text=self.quote_full_text[: self.quote_index])
        if self.quote_index < len(self.quote_full_text):
            delay = 24 if self.whisper_mode else 16
            self.typing_job = self.after(delay, self._type_quote)

    def _type_meaning(self):
        if not self.meaning_item:
            return
        self.meaning_index = min(self.meaning_index + 2, len(self.meaning_full_text))
        self.canvas.itemconfigure(self.meaning_item, text=self.meaning_full_text[: self.meaning_index])
        if self.meaning_index < len(self.meaning_full_text):
            self.meaning_job = self.after(12, self._type_meaning)

    def _cancel_typing(self, target):
        if target == "quote" and self.typing_job:
            self.after_cancel(self.typing_job)
            self.typing_job = None
        if target == "meaning" and self.meaning_job:
            self.after_cancel(self.meaning_job)
            self.meaning_job = None

    def _set_waiting(self, waiting, status_text):
        self.is_waiting = waiting
        state = "disabled" if waiting else "normal"
        self.send_button.configure(state=state)
        self.entry.configure(state=state)
        self._set_status(status_text)
        self._style_send_button(False)
        if not waiting:
            self.entry.focus_set()

    def _set_status(self, text):
        def update():
            self.status_base = text
            self.status_dots = 0
            self.canvas.itemconfigure(self.status_item, text=text)

        self.after(0, update)


if __name__ == "__main__":
    app = RoninApp()
    app.mainloop()
