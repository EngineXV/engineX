# Engine Browser Bridge

Chrome extension for GCU browser automation. Connects to the Python bridge at `ws://127.0.0.1:9229`.

## Distribution package

```bash
cd tools/browser-extension
bash scripts/package.sh
```

This writes `dist/engine-browser-bridge-<version>.zip` for sharing or manual install.
Reload unpacked from `tools/browser-extension` during development; use the zip for updates.

## Install (unpacked)

1. Start the Engine server or GCU MCP server so the bridge is listening.
2. Open `chrome://extensions`
3. Enable **Developer mode**
4. Click **Load unpacked**
5. Select this directory: `tools/browser-extension`

The popup should show **Connected to Engine bridge** when the Python side is running.

## Playwright fallback (optional)

If you cannot use the extension, install the optional browser extra:

```bash
uv sync --extra browser
uv run playwright install chromium
```

Some headless flows can use Playwright via the chart/GCU optional path; the extension remains the primary GCU driver.
