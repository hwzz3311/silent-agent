# RPA Development API Reference

## Server API

### Browser Management

#### POST /browser/launch

Launch a new browser instance.

**Request:**
```json
{
  "id": "browser_123",
  "headless": true,
  "args": ["--disable-blink-features=AutomationControlled"],
  "executablePath": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
}
```

**Response:**
```json
{
  "success": true,
  "id": "browser_123",
  "wsEndpoint": "ws://127.0.0.1:9222/devtools/browser/...",
  "pageCount": 1
}
```

#### POST /browser/:id/close

Close browser instance.

**Response:**
```json
{
  "success": true
}
```

### Page Operations

#### POST /browser/:id/page/:pageIndex/goto

Navigate to URL.

**Request:**
```json
{
  "url": "https://example.com",
  "waitUntil": "networkidle2",
  "timeout": 30000,
  "headers": {
    "User-Agent": "Mozilla/5.0..."
  }
}
```

**Response:**
```json
{
  "success": true,
  "status": 200,
  "url": "https://example.com",
  "htmlLength": 15234
}
```

#### POST /browser/:id/page/:pageIndex/a11y

Get accessibility tree.

**Response:**
```json
{
  "success": true,
  "a11y": {
    "role": "RootWebArea",
    "name": "Page Title",
    "url": "https://example.com",
    "children": [
      {
        "role": "link",
        "name": "Click here",
        "url": "https://example.com/page"
      },
      {
        "role": "button",
        "name": "Submit"
      },
      {
        "role": "textbox",
        "name": "Search",
        "focused": true
      }
    ]
  }
}
```

#### POST /browser/:id/page/:pageIndex/click

Click element by CSS selector.

**Request:**
```json
{
  "selector": "#submit"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/type

Input text to element.

**Request:**
```json
{
  "selector": "#search",
  "text": "search term",
  "delay": 50
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/wait

Wait for element to appear.

**Request:**
```json
{
  "selector": "#result",
  "timeout": 30000
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/execute

Execute custom JavaScript.

**Request:**
```json
{
  "script": "() => document.title",
  "scriptType": "function"
}
```

**Response:**
```json
{
  "success": true,
  "result": "Page Title"
}
```

#### POST /browser/:id/page/:pageIndex/screenshot

Take screenshot.

**Request:**
```json
{
  "fullPage": false
}
```

**Response:**
```json
{
  "success": true,
  "format": "png",
  "data": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

#### POST /browser/:id/page/:pageIndex/content

Get page HTML.

**Response:**
```json
{
  "success": true,
  "html": "<!DOCTYPE html>..."
}
```

#### POST /browser/:id/page/:pageIndex/cookies

Get cookies.

**Response:**
```json
{
  "success": true,
  "cookie": [
    {
      "name": "session",
      "value": "abc123",
      "domain": ".example.com",
      "path": "/"
    }
  ]
}
```

#### POST /browser/:id/page/:pageIndex/cookies/set

Set cookie.

**Request:**
```json
{
  "cookie": {
    "name": "token",
    "value": "xyz789",
    "domain": ".example.com",
    "path": "/"
  }
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/hover

Hover over element.

**Request:**
```json
{
  "selector": "#menu"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/doubleclick

Double click element.

**Request:**
```json
{
  "selector": ".item"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/clickright

Right click element.

**Request:**
```json
{
  "selector": ".context-menu-target"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/keyboard

Keyboard operations.

**Request:**
```json
{
  "action": "press",
  "key": "Enter"
}
```
or
```json
{
  "action": "type",
  "text": "hello world"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/select

Select dropdown option.

**Request:**
```json
{
  "selector": "#country",
  "value": "CN"
}
```

**Response:**
```json
{
  "success": true,
  "selected": ["CN"]
}
```

#### POST /browser/:id/page/:pageIndex/upload

Upload file.

**Request:**
```json
{
  "selector": "input[type=file]",
  "filePath": "/path/to/file.pdf"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/viewport

Set viewport.

**Request:**
```json
{
  "width": 1920,
  "height": 1080,
  "deviceScaleFactor": 2,
  "isMobile": false
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/setua

Set User-Agent.

**Request:**
```json
{
  "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)..."
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/storage/local

Get localStorage/sessionStorage.

**Response:**
```json
{
  "success": true,
  "storage": {
    "local": { "token": "abc123" },
    "session": { "sessionId": "xyz" }
  }
}
```

#### POST /browser/:id/page/:pageIndex/storage/local/set

Set storage.

**Request:**
```json
{
  "key": "token",
  "value": "abc123",
  "storageType": "local"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/new-tab

Open new tab.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "success": true,
  "pageIndex": 1,
  "url": "https://example.com"
}
```

#### POST /browser/:id/page/:pageIndex/close

Close current page.

**Response:**
```json
{
  "success": true,
  "remainingPages": 1
}
```

#### POST /browser/:id/page/:pageIndex/switch

Switch to page.

**Response:**
```json
{
  "success": true,
  "url": "https://example.com/page2",
  "title": "Page Title"
}
```

#### POST /browser/:id/page/:pageIndex/waitnav

Wait for navigation.

**Request:**
```json
{
  "timeout": 30000
}
```

**Response:**
```json
{
  "success": true,
  "url": "https://example.com/newpage"
}
```

#### POST /browser/:id/page/:pageIndex/waitfn

Wait for function to return true.

**Request:**
```json
{
  "script": "() => document.querySelector('.loaded') !== null",
  "timeout": 30000
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/waitidle

Wait for network idle.

**Request:**
```json
{
  "timeout": 30000
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/dialog

Set dialog handler.

**Request:**
```json
{
  "accept": true,
  "promptText": "default input"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /browser/:id/page/:pageIndex/title

Get page title and URL.

**Response:**
```json
{
  "success": true,
  "title": "Page Title",
  "url": "https://example.com"
}
```

### System

#### GET /health

Health check.

**Response:**
```json
{
  "status": "ok",
  "browserCount": 2
}
```

#### GET /browser/list

List all browsers.

**Response:**
```json
{
  "success": true,
  "browsers": [
    { "id": "browser_1", "active": true },
    { "id": "browser_2", "active": false }
  ]
}
```

## Client Library API

### RPAController

```javascript
const controller = new RPAController(options)
```

**Options:**
- `host` - Service host (default: 'localhost')
- `port` - Service port (default: 18765)
- `browserId` - Browser instance ID
- `debug` - Debug mode (default: false)

**Methods:**
- `launch(browserId)` - Launch browser
- `close()` - Close browser
- `newTab(url)` - Open new tab
- `closeTab()` - Close current tab
- `switchTab(index)` - Switch to tab
- `goto(url, options)` - Navigate to URL
- `waitNavigation(timeout)` - Wait for navigation
- `waitIdle(timeout)` - Wait for network idle
- `waitFunction(script, timeout)` - Wait for JS condition
- `getA11yTree()` - Get accessibility tree
- `getTitle()` - Get page title
- `getContent()` - Get HTML
- `click(selector)` - Click element
- `doubleClick(selector)` - Double click
- `rightClick(selector)` - Right click
- `hover(selector)` - Hover element
- `type(selector, text, delay)` - Input text
- `select(selector, value)` - Select dropdown
- `upload(selector, filePath)` - Upload file
- `keyboard(action, params)` - Keyboard operations
- `wait(selector, timeout)` - Wait for selector
- `scroll(distance)` - Scroll page
- `screenshot(fullPage)` - Take screenshot
- `getCookies()` - Get cookies
- `setCookie(cookie)` - Set cookie
- `getStorage()` - Get storage
- `setStorage(key, value, type)` - Set storage
- `setViewport(config)` - Set viewport
- `setUserAgent(ua)` - Set User-Agent
- `handleDialog(accept, text)` - Handle dialog
- `execute(script, scriptType)` - Execute script
- `health()` - Health check
- `listBrowsers()` - List browsers

### A11yParser

```javascript
// Parse accessibility tree
const { elements, summary, root } = A11yParser.parse(tree)

// Find elements by criteria
const results = A11yParser.find(tree, { role: 'button', name: 'Submit' })

// Generate readable description
const desc = A11yParser.toDescription(tree)
```

**Find criteria:**
- `role` - Element role (link, button, textbox, etc.)
- `name` - Element name contains string
- `contains` - Name contains string

### ScriptGenerator

```javascript
// Generate Playwright script
const pwScript = ScriptGenerator.toPlaywright(operations)

// Generate Puppeteer script
const ppScript = ScriptGenerator.toPuppeteer(operations)
```

**Operation types:**
- `{ type: 'goto', url: '...' }`
- `{ type: 'click', selector: '...' }`
- `{ type: 'type', selector: '...', text: '...' }`
- `{ type: 'wait', selector: '...', timeout: 30000 }`
- `{ type: 'scroll', distance: 500 }`

### RPAAgent

```javascript
const agent = new RPAAgent(controller, options)
```

**Options:**
- `apiKey` - LLM API key (required)
- `model` - Model name (default: 'gpt-4')
- `temperature` - Temperature (default: 0.7)
- `maxTokens` - Max tokens (default: 2000)

**Methods:**
- `execute(userInstruction)` - Execute AI automation
- `getOperationLog()` - Get operation history
- `generateScript(format)` - Generate script (playwright/puppeteer)

### OperationRecorder

Record operations during execution, then generate reusable scripts.

```javascript
const recorder = new OperationRecorder();
```

**Methods:**
- `record(operation)` - Record an operation with type and params
- `getOperations()` - Get all recorded operations array
- `generateScript(format)` - Generate script (puppeteer/node/playwright)
- `exportJSON()` - Export operations as JSON string
- `importJSON(json)` - Import operations from JSON
- `clear()` - Clear all recorded operations

**Usage:**
```javascript
// Record operations during execution
recorder.record({ type: 'launch', browserId: 'my-browser' });
recorder.record({ type: 'goto', url: 'https://example.com' });
recorder.record({ type: 'click', selector: '#submit' });
recorder.record({ type: 'screenshot', fullPage: false });

// Generate script after task completion
const script = recorder.generateScript('puppeteer');
require('fs').writeFileSync('auto-script.js', script);

// Or generate Node.js client script
const nodeScript = recorder.generateScript('node');
require('fs').writeFileSync('auto-script-node.js', nodeScript);
```

**Supported operation types for recording:**
- `{ type: 'launch', browserId: '...' }`
- `{ type: 'goto', url: '...' }`
- `{ type: 'click', selector: '...' }`
- `{ type: 'doubleClick', selector: '...' }`
- `{ type: 'type', selector: '...', text: '...' }`
- `{ type: 'hover', selector: '...' }`
- `{ type: 'select', selector: '...', value: '...' }`
- `{ type: 'scroll', distance: 500 }`
- `{ type: 'wait', selector: '...', timeout: 30000 }`
- `{ type: 'screenshot', fullPage: true/false }`
- `{ type: 'getContent' }`
- `{ type: 'newTab', url: '...' }`
- `{ type: 'close' }`