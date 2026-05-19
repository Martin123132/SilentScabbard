import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_MANIFEST = ASSETS_DIR / "skin_manifest.json"
DEFAULT_FALLBACK = "ronin_skin.png"


def safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_manifest(value):
    if not value:
        return DEFAULT_MANIFEST
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def resolve_asset_path(file_name):
    return (ASSETS_DIR / file_name).resolve()


def path_is_inside(path, root):
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def load_manifest(path):
    errors = []
    warnings = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"Manifest could not be read: {exc}"], warnings

    if not isinstance(raw, dict):
        return None, ["Manifest root must be a JSON object."], warnings

    layers = raw.get("layers", [])
    if not isinstance(layers, list) or not layers:
        errors.append("Manifest has no layers.")
        layers = []

    manifest = {
        "width": safe_int(raw.get("width"), 1668),
        "height": safe_int(raw.get("height"), 936),
        "fallback_file": str(raw.get("fallback_file", DEFAULT_FALLBACK)).strip() or DEFAULT_FALLBACK,
        "layers": [],
    }
    if manifest["width"] <= 0 or manifest["height"] <= 0:
        errors.append("Manifest width and height must be positive.")

    for layer in layers:
        if not isinstance(layer, dict):
            warnings.append("Skipped a non-object layer entry.")
            continue
        file_name = str(layer.get("file", "")).strip()
        manifest["layers"].append(
            {
                "name": str(layer.get("name", file_name)).strip() or file_name or "unnamed",
                "file": file_name,
                "x": safe_int(layer.get("x"), 0),
                "y": safe_int(layer.get("y"), 0),
                "enabled": bool(layer.get("enabled", True)),
                "required": bool(layer.get("required", True)),
            }
        )

    return manifest, errors, warnings


def inspect_layers(manifest):
    statuses = []
    errors = []
    loaded = []

    fallback_path = resolve_asset_path(manifest["fallback_file"])
    fallback_ok = path_is_inside(fallback_path, ASSETS_DIR) and fallback_path.exists()
    if not path_is_inside(fallback_path, ASSETS_DIR):
        errors.append(f"Fallback escapes assets folder: {manifest['fallback_file']}")
        fallback_path = None

    for layer in manifest["layers"]:
        status = {
            "name": layer["name"],
            "file": layer["file"],
            "x": layer["x"],
            "y": layer["y"],
            "enabled": layer["enabled"],
            "required": layer["required"],
            "state": "disabled",
            "message": "",
            "path": None,
        }
        if not layer["enabled"]:
            status["message"] = "disabled"
            statuses.append(status)
            continue

        if not layer["file"]:
            status["state"] = "missing-required" if layer["required"] else "missing-optional"
            status["message"] = "no file set"
            statuses.append(status)
            if layer["required"]:
                errors.append(f"Required layer has no file: {layer['name']}")
            continue

        path = resolve_asset_path(layer["file"])
        status["path"] = path
        if not path_is_inside(path, ASSETS_DIR):
            status["state"] = "missing-required" if layer["required"] else "missing-optional"
            status["message"] = "escapes assets folder"
            statuses.append(status)
            if layer["required"]:
                errors.append(f"Required layer escapes assets folder: {layer['file']}")
            continue

        if not path.exists():
            status["state"] = "missing-required" if layer["required"] else "missing-optional"
            status["message"] = "file missing"
            statuses.append(status)
            if layer["required"]:
                errors.append(f"Required layer missing: {layer['file']}")
            continue

        status["state"] = "ok"
        status["message"] = "ready"
        statuses.append(status)
        loaded.append((layer, path))

    return statuses, loaded, fallback_path, fallback_ok, errors


def analyze_manifest(manifest_path):
    manifest, manifest_errors, manifest_warnings = load_manifest(manifest_path)
    if manifest is None:
        manifest = {"width": 1200, "height": 760, "fallback_file": DEFAULT_FALLBACK, "layers": []}
    statuses, loaded, fallback_path, fallback_ok, layer_errors = inspect_layers(manifest)
    return {
        "manifest": manifest,
        "statuses": statuses,
        "loaded_layers": loaded,
        "fallback_path": fallback_path,
        "fallback_ok": fallback_ok,
        "errors": manifest_errors + layer_errors,
        "warnings": manifest_warnings,
    }


def print_report(manifest_path, analysis):
    manifest = analysis["manifest"]
    print(f"Manifest: {manifest_path}")
    print(f"Canvas: {manifest['width']} x {manifest['height']}")
    print(f"Fallback: {manifest['fallback_file']}")
    print(f"Fallback ready: {'yes' if analysis['fallback_ok'] else 'no'}")
    print("Layers:")
    for status in analysis["statuses"]:
        marker = {
            "ok": "ok",
            "missing-required": "missing required",
            "missing-optional": "missing optional",
            "disabled": "disabled",
        }.get(status["state"], status["state"])
        req = "required" if status["required"] else "optional"
        print(f"- {marker}: {status['name']} ({req}) -> {status['file']} @ {status['x']},{status['y']}")

    if analysis["warnings"]:
        print("Warnings:")
        for warning in analysis["warnings"]:
            print(f"- {warning}")
    if analysis["errors"]:
        print("Errors:")
        for error in analysis["errors"]:
            print(f"- {error}")


class SkinPreview(tk.Tk):
    def __init__(self, manifest_path):
        super().__init__()
        self.title("SilentScabbard Skin Preview")
        self.configure(bg="#11100d")
        self.images = []
        self.manifest_path = manifest_path

        analysis = analyze_manifest(manifest_path)
        manifest = analysis["manifest"]
        self.manifest = manifest
        self.statuses = analysis["statuses"]
        self.errors = analysis["errors"]
        self.warnings = analysis["warnings"]
        self.fallback_path = analysis["fallback_path"]
        self.fallback_ok = analysis["fallback_ok"]
        self.loaded_layers = analysis["loaded_layers"]

        self._build_fonts()
        self._build_ui()

    def _build_fonts(self):
        self.font_title = tkfont.Font(family="Georgia", size=14, weight="bold")
        self.font_body = tkfont.Font(family="Georgia", size=10)
        self.font_small = tkfont.Font(family="Consolas", size=9)

    def _build_ui(self):
        self.geometry("1180x760")
        header = tk.Frame(self, bg="#171511", padx=14, pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="SilentScabbard Skin Preview",
            bg="#171511",
            fg="#d4b978",
            font=self.font_title,
            anchor="w",
        ).pack(side="left")
        tk.Button(
            header,
            text="Close",
            command=self.destroy,
            bg="#252119",
            fg="#d7c6a1",
            activebackground="#322b20",
            activeforeground="#e6d7b8",
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            font=self.font_body,
            cursor="hand2",
        ).pack(side="right")

        body = tk.PanedWindow(self, orient="horizontal", sashwidth=6, bg="#11100d", bd=0)
        body.pack(fill="both", expand=True)

        preview_frame = tk.Frame(body, bg="#080806")
        body.add(preview_frame, minsize=640, stretch="always")
        self._build_preview_canvas(preview_frame)

        info_frame = tk.Frame(body, bg="#11100d", padx=12, pady=12)
        body.add(info_frame, minsize=360)
        self._build_info_panel(info_frame)

    def _build_preview_canvas(self, parent):
        canvas = tk.Canvas(parent, bg="#080806", highlightthickness=0)
        x_scroll = tk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        y_scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        width = self.manifest["width"]
        height = self.manifest["height"]
        canvas.configure(scrollregion=(0, 0, width, height))
        canvas.create_rectangle(0, 0, width, height, fill="#0c0b09", outline="")

        used_fallback = False
        if self.errors and self.fallback_ok:
            self._draw_image(canvas, self.fallback_path, 0, 0)
            used_fallback = True
        elif self.loaded_layers:
            for layer, path in self.loaded_layers:
                self._draw_image(canvas, path, layer["x"], layer["y"])
        elif self.fallback_ok:
            self._draw_image(canvas, self.fallback_path, 0, 0)
            used_fallback = True
        else:
            canvas.create_text(
                width / 2,
                height / 2,
                text="No usable skin assets found.",
                fill="#d4b978",
                font=self.font_title,
            )

        if used_fallback:
            canvas.create_rectangle(16, 16, 270, 48, fill="#171511", outline="#5c4828")
            canvas.create_text(28, 32, text="fallback preview", fill="#d4b978", font=self.font_body, anchor="w")

    def _draw_image(self, canvas, path, x, y):
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return
        self.images.append(image)
        canvas.create_image(x, y, image=image, anchor="nw")

    def _build_info_panel(self, parent):
        summary = [
            f"Manifest: {self.manifest_path}",
            f"Canvas: {self.manifest['width']} x {self.manifest['height']}",
            f"Fallback: {self.manifest['fallback_file']}",
            f"Fallback ready: {'yes' if self.fallback_ok else 'no'}",
            "",
            "Layers:",
        ]
        text = tk.Text(
            parent,
            bg="#15130f",
            fg="#e1d6c0",
            insertbackground="#e1d6c0",
            relief="flat",
            bd=0,
            padx=10,
            pady=10,
            wrap="word",
            font=self.font_small,
        )
        text.pack(fill="both", expand=True)
        for line in summary:
            text.insert("end", line + "\n")
        for status in self.statuses:
            text.insert("end", self._status_line(status) + "\n")

        if self.warnings:
            text.insert("end", "\nWarnings:\n")
            for warning in self.warnings:
                text.insert("end", f"- {warning}\n")
        if self.errors:
            text.insert("end", "\nErrors:\n")
            for error in self.errors:
                text.insert("end", f"- {error}\n")
            text.insert("end", "\nPreview is using fallback where possible.\n")
        else:
            text.insert("end", "\nSkin preview ready.\n")
        text.configure(state="disabled")

    def _status_line(self, status):
        marker = {
            "ok": "ok",
            "missing-required": "missing required",
            "missing-optional": "missing optional",
            "disabled": "disabled",
        }.get(status["state"], status["state"])
        req = "required" if status["required"] else "optional"
        return f"- {marker}: {status['name']} ({req}) -> {status['file']} @ {status['x']},{status['y']}"


def main():
    parser = argparse.ArgumentParser(description="Preview SilentScabbard skin manifests.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Manifest path, absolute or relative to repo root.")
    parser.add_argument("--check-only", action="store_true", help="Print manifest status and exit without opening a window.")
    parser.add_argument("--close-after", type=float, default=0.0, help="Auto-close the preview window after this many seconds.")
    args = parser.parse_args()

    manifest_path = resolve_manifest(args.manifest)
    analysis = analyze_manifest(manifest_path)
    if args.check_only:
        print_report(manifest_path, analysis)
        return 1 if analysis["errors"] else 0

    app = SkinPreview(manifest_path)
    if args.close_after > 0:
        app.after(max(1, int(args.close_after * 1000)), app.destroy)
    app.mainloop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Skin preview failed: {exc}", file=sys.stderr)
        raise
