# Skin Assets

SilentScabbard can use either a single full-window skin or layered artwork.

The current public build ships with:

- `ronin_skin.png`: the complete current UI skin
- `skin_manifest.json`: layer instructions

## Current Fallback

The manifest currently draws `ronin_skin.png` as one layer. This keeps the app stable while new art is developed.

## Layered Skin Workflow

To split the UI into replaceable pieces, add PNG files to this folder and update `skin_manifest.json`.

Example:

```json
{
  "width": 1668,
  "height": 936,
  "layers": [
    { "name": "room", "file": "room.png", "x": 0, "y": 0, "enabled": true },
    { "name": "samurai", "file": "samurai.png", "x": 760, "y": 82, "enabled": true },
    { "name": "foreground", "file": "foreground.png", "x": 0, "y": 0, "enabled": true }
  ]
}
```

Keep the canvas size at `1668 x 936` unless the UI hit rectangles are also updated.

If the manifest is missing or invalid, the app falls back to `ronin_skin.png`. If that is also missing, it draws a plain fallback screen.
