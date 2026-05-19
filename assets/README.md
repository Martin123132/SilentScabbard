# Skin Assets

SilentScabbard can use either a single full-window skin or layered artwork.

The current public build ships with:

- `ronin_skin.png`: the complete current UI skin
- `skin_manifest.json`: layer instructions
- `skin_manifest.full.json`: the stable full-skin profile
- `skin_manifest.layered.example.json`: the future room/samurai/foreground profile

## Current Fallback

The active manifest currently draws `ronin_skin.png` as one layer. This keeps the app stable while new art is developed.

## Layered Skin Workflow

To split the UI into replaceable pieces:

1. Put `room.png`, `foreground.png`, and optional `samurai.png` in one source folder.
2. Run the importer:

```powershell
.\import-layered-skin.ps1 -SourceFolder D:\Path\To\LayerPngs
```

The importer validates the PNGs, backs up replaced layer files to `data\skin_backups`, copies valid layers into `assets\layers`, activates the layered profile, and opens the preview.

You can still switch profiles manually with:

```powershell
.\set-skin-profile.ps1 -SkinProfile layered
```

If required layer files are missing, the switch refuses and restores the full-skin profile. The importer does not resize artwork; `room.png` and `foreground.png` must be `1668 x 936`.

Double-click helpers:

- `CHECK_SKIN_WINDOWS.bat`
- `IMPORT_LAYERED_SKIN_WINDOWS.bat`
- `PREVIEW_SKIN_WINDOWS.bat`
- `USE_FULL_SKIN_WINDOWS.bat`
- `USE_LAYERED_SKIN_WINDOWS.bat`

Terminal preview commands:

```powershell
.\preview-skin.ps1
.\preview-skin.ps1 -Manifest assets\skin_manifest.layered.example.json
```

Previewing the layered example is safe even before layer files exist. It reports missing required files and renders the fallback where possible without changing the active manifest.

Example:

```json
{
  "width": 1668,
  "height": 936,
  "fallback_file": "ronin_skin.png",
  "layers": [
    { "name": "room", "file": "layers/room.png", "x": 0, "y": 0, "enabled": true, "required": true },
    { "name": "samurai", "file": "layers/samurai.png", "x": 760, "y": 82, "enabled": true, "required": false },
    { "name": "foreground", "file": "layers/foreground.png", "x": 0, "y": 0, "enabled": true, "required": true }
  ]
}
```

Keep the canvas size at `1668 x 936` unless the UI hit rectangles are also updated.

If the manifest is missing, invalid, or missing a required layer, the app falls back to `ronin_skin.png`. If that is also missing, it draws a plain fallback screen.
