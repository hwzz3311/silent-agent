# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install Puppeteer dependencies (optional, for real accessibility tree)
pip install puppeteer-extra puppeteer-extra-plugin-stealth

# Start Relay server (required for extension mode)
python src/relay_server.py
python src/relay_server.py --port 18792  # with custom port

# Start REST API service
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload

# Run tests
pytest tests_api.py
pytest tests_xiaohongshu.py
python test_simple.py
python test_a11y_tree.py

# Test browser client (with different modes)
BROWSER_MODE=extension python test_browser_client.py
BROWSER_MODE=puppeteer python test_browser_client.py
BROWSER_MODE=hybrid python test_browser_client.py
```

## Browser Modes

The system supports three browser client modes:

| Mode | Description | Start Requirements |
|------|-------------|-------------------|
| `extension` | Chrome Extension (default) | Relay server + Extension loaded |
| `puppeteer` | Puppeteer controlled | Chrome browser (auto-started) |
| `hybrid` | Puppeteer + Extension | Both above |

### Environment Variables Configuration

```bash
# Browser mode
BROWSER_MODE=extension|puppeteer|hybrid

# Puppeteer settings (for puppeteer/hybrid mode)
PUPPETEER_HEADLESS=true|false
PUPPETEER_ARGS=--arg1,--arg2
STEALTH_ENABLED=true|false

# Extension settings (for extension/hybrid mode)
RELAY_HOST=127.0.0.1
RELAY_PORT=18792
SECRET_KEY=your_key

# Server settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
```

## Architecture Overview

**SilentAgent** is a browser automation system supporting multiple control modes:
- Chrome extension + Python controller (legacy)
- Puppeteer based control (new)
- Hybrid mode combining both

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Chrome Extension | `extension/` | Runs in browser, executes scripts via `chrome.scripting` |
| Relay Server | `src/relay_server.py` | WebSocket relay between extension and Python client |
| Python Client | `src/client/client.py` | `SilentAgentClient` for controlling the browser |
| Browser Module | `src/browser/` | Unified browser client (Puppeteer/Extension/Hybrid) |
| Tool Framework | `src/tools/` | `Tool` abstract base class, tool registry |
| Site Adapters | `src/tools/business/sites/` | `Site` abstract class for site-specific automation |
| REST API | `src/api/` | FastAPI endpoints for tool execution |
| Flow Engine | `src/flow/` | JSON-based workflow execution engine |
| Config | `src/config.py` | Application configuration |

### Browser Client Module (`src/browser/`)

| File | Description |
|------|-------------|
| `base.py` | `BrowserClient` abstract base class |
| `client_factory.py` | Factory for creating clients by mode |
| `extension_client.py` | Wrapper for extension-based control |
| `puppeteer_client.py` | Puppeteer-based control with stealth |
| `hybrid_client.py` | Combined mode for best results |

### Multi-Plugin Key System

Each Chrome extension instance generates a unique `secret_key` based on machine info. The Relay server maintains a dictionary of extension connections by key, allowing a single Python client to control multiple browser instances:

```python
client_a = SilentAgentClient(secret_key="KEY_A")
client_b = SilentAgentClient(secret_key="KEY_B")
```

### Communication Flow

**Extension Mode:**
1. Extension connects to Relay with `{type: "hello", secretKey, tools}`
2. Python client sends `{method: "executeTool", params: {name, args, secretKey}}`
3. Relay routes to correct extension and returns tool result

**Puppeteer Mode:**
1. Python client creates Puppeteer browser via `BrowserClientFactory`
2. Direct CDP communication with browser
3. `page.accessibility.snapshot()` returns real accessibility tree

**Hybrid Mode:**
1. Uses Puppeteer for navigation and accessibility tree
2. Falls back to extension for complex interactions
3. Best of both worlds

## Accessibility Tree

The system supports multiple ways to get accessibility tree:

| Mode | Tree Type | How |
|------|-----------|-----|
| extension | Simulated | DOM-based simulation |
| puppeteer | Real | `page.accessibility.snapshot()` |
| hybrid | Real | Puppeteer CDP `Accessibility.getFullAXTree` |

To force real tree in extension mode:
```python
result = await get_a11y_tree(use_real_tree=True)
```

## Testing Notes

- Extension mode tests require Chrome extension loaded and connected to Relay server
- Extension must have target sites authorized in settings
- Puppeteer mode requires `puppeteer-extra` package
- See `test_a11y_tree.py` and `test_browser_client.py` for examples