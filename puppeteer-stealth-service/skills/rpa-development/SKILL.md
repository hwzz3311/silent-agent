---
name: rpa-development
description: This skill should be used when the user asks to "get QR code from website", "automate login flow", "extract page data", "complete web task", "do browser automation", "scrape website", or needs Puppeteer stealth browser control with accessibility tree support. This skill executes real browser operations first, then generates reusable RPA scripts.
version: 0.3.1
---

# RPA Development Skill

Use Puppeteer Stealth Service for browser automation. Execute real browser operations to complete tasks, then generate reusable RPA script from the execution.

## Workflow: Execute First, Generate Script Later

**IMPORTANT**: This skill follows "execute first, generate script later" pattern:

1. **Start Server** - Launch Puppeteer Stealth Service
2. **Execute Operations** - Control browser to complete the task directly
3. **Record Actions** - Operations are recorded during execution
4. **Generate Script** - After task completion, export as reusable RPA script

## Quick Start

### 1. Install Dependencies

```bash
cd skills/rpa-development
npm install
```

### 2. Start the Server

```bash
cd skills/rpa-development
node scripts/server.js
# Or custom port: PORT=18766 node scripts/server.js
```

### 3. Execute Task Directly

Import and use RPAController to perform actual browser operations:

```javascript
const { RPAController, A11yParser, OperationRecorder } = require('./skill/rpa-development/scripts/rpa-client.js');

const controller = new RPAController({
  host: 'localhost',
  port: 18765,
  browserId: 'task-browser',
  debug: true
});

const recorder = new OperationRecorder();

// Execute task directly - operations are recorded
await controller.launch('task-browser');
recorder.record({ type: 'launch', browserId: 'task-browser' });

await controller.goto('https://tongyi.aliyun.com/');
recorder.record({ type: 'goto', url: 'https://tongyi.aliyun.com/' });

await new Promise(r => setTimeout(r, 2000));

const screenshot = await controller.screenshot(false);
recorder.record({ type: 'screenshot', fullPage: false });

// Save screenshot
const buffer = Buffer.from(screenshot.data, 'base64');
require('fs').writeFileSync('qrcode.png', buffer);

// Generate reusable script AFTER task completion
const script = recorder.generateScript('puppeteer');
require('fs').writeFileSync('auto-qrcode.js', script);

await controller.close();
```

## Core Pattern: Execute → Record → Generate

### Step-by-Step Workflow

**Step 1: Create controller and recorder**
```javascript
const { RPAController, A11yParser, OperationRecorder } = require('./skill/rpa-development/scripts/rpa-client.js');

const controller = new RPAController({ browserId: 'my-task' });
const recorder = new OperationRecorder();
```

**Step 2: Execute actual operations (with recording)**
```javascript
// Launch browser - record this action
await controller.launch('my-task');
recorder.record({ type: 'launch', browserId: 'my-task' });

// Navigate - record this action
await controller.goto('https://target-site.com');
recorder.record({ type: 'goto', url: 'https://target-site.com' });

// Interact with page - record each action
await controller.click('.login-btn');
recorder.record({ type: 'click', selector: '.login-btn' });

await controller.type('#username', 'myuser');
recorder.record({ type: 'type', selector: '#username', text: 'myuser' });

await controller.type('#password', 'mypassword');
recorder.record({ type: 'type', selector: '#password', text: 'mypassword' });

// Get result - record this action
const screenshot = await controller.screenshot(true);
recorder.record({ type: 'screenshot', fullPage: true });

// Close - record this action
await controller.close();
recorder.record({ type: 'close' });
```

**Step 3: Generate reusable script**
```javascript
// Generate Puppeteer script
const puppeteerScript = recorder.generateScript('puppeteer');
require('fs').writeFileSync('auto-task.js', puppeteerScript);

// Or generate Node.js client script (uses HTTP API)
const nodeScript = recorder.generateScript('node');
require('fs').writeFileSync('auto-task-node.js', nodeScript);

// Or generate Playwright script
const playwrightScript = recorder.generateScript('playwright');
require('fs').writeFileSync('auto-task.py', playwrightScript);
```

### Practical Example: Login and Get Screenshot

```javascript
const { RPAController, OperationRecorder } = require('./skill/rpa-development/scripts/rpa-client.js');

async function loginAndCapture(username, password) {
  const controller = new RPAController({ browserId: 'login-capture' });
  const recorder = new OperationRecorder();

  // Execute actual task
  await controller.launch('login-capture');
  recorder.record({ type: 'launch', browserId: 'login-capture' });

  await controller.goto('https://example.com/login');
  recorder.record({ type: 'goto', url: 'https://example.com/login' });

  await controller.type('#username', username);
  recorder.record({ type: 'type', selector: '#username', text: username });

  await controller.type('#password', password);
  recorder.record({ type: 'type', selector: '#password', text: password });

  await controller.click('#login-btn');
  recorder.record({ type: 'click', selector: '#login-btn' });

  await controller.waitIdle(5000);

  const screenshot = await controller.screenshot(true);
  recorder.record({ type: 'screenshot', fullPage: true });

  await controller.close();
  recorder.record({ type: 'close' });

  // Generate reusable script AFTER task completion
  const script = recorder.generateScript('puppeteer');
  require('fs').writeFileSync('auto-login.js', script);
  console.log('[Done] Script saved to auto-login.js');

  // Also save the screenshot
  require('fs').writeFileSync('login-result.png', Buffer.from(screenshot.data, 'base64'));
}

loginAndCapture('myuser', 'mypass');
```

## Available Operations

### Controller Methods

| Method | Description |
|--------|-------------|
| `launch(browserId)` | Launch browser instance |
| `close()` | Close browser |
| `newTab(url)` | Open new tab |
| `closeTab()` | Close current tab |
| `switchTab(index)` | Switch to tab by index |
| `goto(url, options)` | Navigate to URL |
| `waitNavigation(timeout)` | Wait for navigation to complete |
| `waitIdle(timeout)` | Wait for network idle |
| `waitFunction(script, timeout)` | Wait for JS condition |
| `click(selector)` | Click element |
| `doubleClick(selector)` | Double click |
| `rightClick(selector)` | Right click |
| `hover(selector)` | Hover over element |
| `type(selector, text, delay)` | Type text |
| `select(selector, value)` | Select dropdown option |
| `upload(selector, filePath)` | Upload file |
| `keyboard(action, params)` | Keyboard: press/type/up/down |
| `scroll(distance)` | Scroll page |
| `getA11yTree()` | Get accessibility tree |
| `getTitle()` | Get page title |
| `getContent()` | Get HTML content |
| `screenshot(fullPage)` | Take screenshot |
| `getCookies()` | Get cookies |
| `setCookie(cookie)` | Set cookie |
| `getStorage()` | Get localStorage/sessionStorage |
| `setStorage(key, value, type)` | Set storage |
| `setViewport({width, height})` | Set viewport size |
| `setUserAgent(ua)` | Set User-Agent |
| `handleDialog(accept, text)` | Handle alert/confirm/prompt |

### Recorder Methods

| Method | Description |
|--------|-------------|
| `record(operation)` | Record an operation |
| `getOperations()` | Get all recorded operations |
| `generateScript(format)` | Generate script (puppeteer/node/playwright) |
| `exportJSON()` | Export as JSON |
| `clear()` | Clear all records |

### Analysis Methods

| Method | Description |
|--------|-------------|
| `A11yParser.parse(tree)` | Parse tree to elements |
| `A11yParser.find(tree, criteria)` | Find element by role/name |
| `A11yParser.toDescription(tree)` | Generate human-readable description |

## Additional Resources

### Reference Files
- **`references/api.md`** - Complete API documentation

### Example Files
- **`examples/qrcode-grab.js`** - QR code capture
- **`examples/login-flow.js`** - Login automation
- **`examples/data-extract.js`** - Data extraction

### Script Files
- **`scripts/server.js`** - Puppeteer stealth service
- **`scripts/rpa-client.js`** - Client library (RPAController, OperationRecorder, A11yParser)
- **`scripts/rpa-cli.js`** - CLI tool

## HTTP API Usage (Direct curl)

For debugging or manual intervention, use HTTP API directly:

### Common curl Commands

```bash
PORT=18765
BROWSER_ID=my-browser

# Launch browser
curl -X POST http://localhost:$PORT/browser/launch \
  -H "Content-Type: application/json" \
  -d '{"id": "'$BROWSER_ID'", "headless": false}'

# Navigate to URL
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/page/0/goto \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tongyi.aliyun.com/", "waitUntil": "networkidle2"}'

# Get screenshot
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/page/0/screenshot \
  -H "Content-Type: application/json" \
  -d '{"fullPage": false}' -o screenshot.png

# Get accessibility tree
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/page/0/a11y

# Get page content
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/page/0/content

# Click element
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/page/0/click \
  -H "Content-Type: application/json" \
  -d '{"selector": "#login-btn"}'

# Close browser
curl -X POST http://localhost:$PORT/browser/$BROWSER_ID/close

# Health check
curl http://localhost:$PORT/health
```

## Two Workflows: Automated vs Manual Intervention

### Workflow A: Fully Automated Task

For tasks without human interaction (e.g., data scraping, form submission):

```javascript
// 1. Start server
// 2. Execute operations in sequence
// 3. Use OperationRecorder to record
// 4. Generate script at end
```

**Best for:**
- 批量数据采集
- 定时任务
- 无验证码/扫码的登录

### Workflow B: Manual Intervention Required

For tasks requiring human action (QR code scan, captcha, phone verification):

```javascript
// 1. Start server with headless: false
// 2. Execute until human action needed
// 3. Pause and prompt user or wait
// 4. After human completes, continue
// 5. Generate script with wait points
```

**Best for:**
- QR code login (wechat, Alipay, etc.)
- Captcha verification
- Phone OTP verification

**Example: QR Code Login Flow**
```javascript
async function qrCodeLogin() {
  const controller = new RPAController({ browserId: 'qr-login' });

  // Launch in non-headless mode for user to see
  await controller.launch('qr-login');

  // Navigate to login page
  await controller.goto('https://example.com/qr-login');

  // Take screenshot for user to scan
  const screenshot = await controller.screenshot(false);
  require('fs').writeFileSync('qrcode.png',
    Buffer.from(screenshot.data, 'base64'));

  console.log('[INFO] QR code saved. Please scan within 60 seconds...');

  // Wait for user to complete scan (poll for login success)
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const a11y = await controller.getA11yTree();
    // Check for logged-in indicators
    if (a11y.a11y.name?.includes('Dashboard') ||
        a11y.a11y.name?.includes('已登录')) {
      console.log('[SUCCESS] Login completed!');
      break;
    }
  }

  // Continue with remaining tasks...
  await controller.close();
}
```

## Authentication State Detection

Detect login/authentication state using multiple methods:

### Method 1: URL Parameters

```javascript
const url = page.url();
const isLoggedIn = url.includes('dashboard') || url.includes('home');
```

### Method 2: Accessibility Tree Elements

```javascript
const a11y = await controller.getA11yTree();
const elements = A11yParser.parse(a11y.a11y).elements;

// Check for logged-in indicators
const hasDashboard = elements.some(e =>
  e.name?.toLowerCase().includes('dashboard') ||
  e.name?.toLowerCase().includes('username') ||
  e.role === 'navigation'
);
```

### Method 3: Page Content

```javascript
const content = await controller.getContent();
const isLoggedIn = content.includes('Welcome') ||
                   content.includes('logout') ||
                   content.includes('退出');
```

### Method 4: Cookies

```javascript
const cookies = await controller.getCookies();
const hasSession = cookie.cookie?.some(c =>
  c.name === 'session' || c.name === 'token'
);
```

### Combined Detection

```javascript
async function checkLoginState(controller) {
  const results = {
    url: controller.getTitle()?.url,
    hasDashboard: false,
    hasUserElement: false,
    hasCookie: false
  };

  // Check URL
  const title = await controller.getTitle();
  results.urlHasKeyword = title?.url?.includes('dashboard');

  // Check a11y tree
  const a11y = await controller.getA11yTree();
  const elements = A11yParser.parse(a11y.a11y).elements;
  results.hasDashboard = elements.some(e =>
    e.name?.toLowerCase().includes('dashboard')
  );
  results.hasUserElement = elements.some(e =>
    e.role === 'button' && e.name?.toLowerCase().includes('profile')
  );

  // Check cookies
  const cookie = await controller.getCookies();
  results.hasCookie = cookie.cookie?.length > 0;

  // Return true if any method indicates logged in
  return results.urlHasKeyword || results.hasDashboard ||
         results.hasUserElement || results.hasCookie;
}
```

## Common Issues and Fixes

### Issue 1: Screenshot Returns Number Array Instead of Base64

**Symptom:** `"data": "137,80,78,71,13,10,26,10..."` (array not string)

**Fix:** Use `Buffer.from(buffer).toString('base64')` on server

```javascript
// In server.js screenshot handler
const buffer = await page.screenshot({ fullPage });
const base64 = Buffer.from(buffer).toString('base64');
res.json({ success: true, format: 'png', data: base64 });
```

### Issue 2: Empty Response Causes JSON.parse Error

**Symptom:** `JSON.parse('')` throws error

**Fix:** Handle empty body in client

```javascript
if (!body || body.trim() === '') {
  resolve({ success: true });
  return;
}
```

### Issue 3: Content-Length Header Issues

**Symptom:** Request hangs with no data sent

**Fix:** Always send a payload, even if empty

```javascript
const payload = data ? JSON.stringify(data) : '{}';
req.write(payload);
```

## Best Practices

1. **Execute first, generate later** - Complete the actual task first, then generate the script

2. **Record every action** - Call `recorder.record()` after each controller operation

3. **Generate after close** - Call `generateScript()` after `controller.close()`

4. **Use appropriate format** - Choose 'puppeteer', 'node', or 'playwright' based on use case

5. **Clean up resources** - Always call `close()` and record it

6. **Save outputs first** - Save screenshots/data before generating script