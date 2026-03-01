---
name: rpa-development
description: This skill should be used when the user asks to "create RPA automation", "build browser automation", "develop web scraping", "automate login flow", "get QR code from website", "extract page data via accessibility tree", "complete multi-step web task", or needs Puppeteer stealth browser control with accessibility tree support.
version: 0.2.0
---

# RPA Development Skill

Use Puppeteer Stealth Service for browser automation with accessibility tree support. Designed for LLM agents to execute complex multi-step tasks with minimal human intervention.

## Quick Start

### 1. Install Dependencies

```bash
cd skills/rpa-development
npm install
```

### 2. Start the Server

Start RPA server (default port 18765):

```bash
# Option 1: Using npm script
cd skills/rpa-development
npm start

# Option 2: Direct node
cd skills/rpa-development
node scripts/server.js

# Option 3: Custom port
cd skills/rpa-development
PORT=18766 node scripts/server.js
```

### 3. Initialize Client

```javascript
// When running from project root
const { RPAController, A11yParser } = require('./skill/rpa-development/scripts/rpa-client.js');

// Or require relative to your script location
const { RPAController, A11yParser } = require('./skills/rpa-development/scripts/rpa-client.js');

const controller = new RPAController({
  host: 'localhost',
  port: 18765,
  browserId: 'agent-browser',
  debug: false
});
```

## LLM Agent Workflow (Multi-Round Execution)

For complex tasks, the LLM agent should execute in a loop until task completion:

### Standard Loop Pattern

```javascript
async function executeTask(taskDescription) {
  // 1. Launch browser
  await controller.launch('agent-browser');

  // 2. Navigate to starting page
  await controller.goto('https://target-site.com/');

  let maxLoops = 20;
  let loopCount = 0;

  while (loopCount < maxLoops) {
    loopCount++;

    // 3. Get accessibility tree to understand current state
    const a11yResult = await controller.getA11yTree();
    const { summary, elements } = A11yParser.parse(a11yResult.a11y);

    // 4. Analyze page and decide next action
    // Look for: buttons, link, textbox, combobox, checkbox, menu

    // 5. Execute action
    const action = decideNextAction(taskDescription, elements);
    if (!action) {
      // Task might be complete
      break;
    }

    // 6. Execute and check result
    await executeAction(controller, action);

    // 7. Check if task is complete
    if (await checkTaskComplete(controller, taskDescription)) {
      break;
    }
  }

  // 8. Return final result
  await controller.close();
  return finalResult;
}
```

### Decision Helper

```javascript
function decideNextAction(task, elements) {
  // Find actionable elements based on task
  const taskLower = task.toLowerCase();

  // Login scenario
  if (taskLower.includes('login') || taskLower.includes('登录')) {
    const inputs = elements.filter(e => e.role === 'textbox');
    const buttons = elements.filter(e => e.role === 'button');

    if (inputs.length >= 2 && !hasInputValue(inputs)) {
      return { type: 'type', selector: inputs[0].selector, text: 'username' };
    }
    if (inputs.length >= 2 && hasPartialInput(inputs)) {
      return { type: 'type', selector: inputs[1].selector, text: 'password' };
    }
    if (button.length > 0) {
      return { type: 'click', selector: button[0].selector };
    }
  }

  // Click button scenario
  if (taskLower.includes('click') || taskLower.includes('submit') || taskLower.includes('confirm')) {
    const button = elements.filter(e => e.role === 'button');
    if (button.length > 0) {
      return { type: 'click', selector: button[0].selector };
    }
  }

  // Select dropdown
  if (taskLower.includes('select') || taskLower.includes('选择')) {
    const combobox = elements.filter(e => e.role === 'combobox');
    if (combobox.length > 0) {
      return { type: 'select', selector: combobox[0].selector, value: 'desired-value' };
    }
  }

  // Hover (for dropdown menus)
  if (taskLower.includes('hover') || taskLower.includes('悬停')) {
    const menuitem = elements.filter(e => e.role === 'menuitem');
    if (menuitem.length > 0) {
      return { type: 'hover', selector: menuitem[0].selector };
    }
  }

  // Scroll for more content
  if (taskLower.includes('scroll') || taskLower.includes('更多')) {
    return { type: 'scroll', distance: 500 };
  }

  return null;
}
```

### Task Complete Check

```javascript
async function checkTaskComplete(controller, task) {
  const a11yResult = await controller.getA11yTree();
  const { elements } = A11yParser.parse(a11yResult.a11y);

  const taskLower = task.toLowerCase();

  // Check for success indicators
  if (taskLower.includes('login') || taskLower.includes('登录')) {
    const hasDashboard = elements.some(e =>
      e.name?.toLowerCase().includes('dashboard') ||
      e.name?.toLowerCase().includes('home') ||
      e.name?.toLowerCase().includes('已登录')
    );
    if (hasDashboard) return true;
  }

  // Check for target content
  if (taskLower.includes('data') || taskLower.includes('数据')) {
    const hasData = elements.some(e => e.role === 'table' || e.role === 'grid');
    if (hasData) return true;
  }

  return false;
}
```

## Available Operations

### Browser Management
| Method | Description |
|--------|-------------|
| `launch(browserId)` | Launch browser instance |
| `close()` | Close browser |
| `newTab(url)` | Open new tab |
| `closeTab()` | Close current tab |
| `switchTab(index)` | Switch to tab by index |

### Navigation
| Method | Description |
|--------|-------------|
| `goto(url, options)` | Navigate to URL |
| `waitNavigation(timeout)` | Wait for navigation to complete |
| `waitIdle(timeout)` | Wait for network idle |
| `waitFunction(script, timeout)` | Wait for JS condition |

### Element Interaction
| Method | Description |
|--------|-------------|
| `click(selector)` | Click element |
| `doubleClick(selector)` | Double click |
| `rightClick(selector)` | Right click |
| `hover(selector)` | Hover over element |
| `type(selector, text, delay)` | Type text |
| `select(selector, value)` | Select dropdown option |
| `upload(selector, filePath)` | Upload file |
| `keyboard(action, params)` | Keyboard: press/type/up/down |
| `scroll(distance)` | Scroll page |

### Content & State
| Method | Description |
|--------|-------------|
| `getA11yTree()` | Get accessibility tree |
| `getTitle()` | Get page title |
| `getContent()` | Get HTML content |
| `screenshot(fullPage)` | Take screenshot |
| `getCookies()` | Get cookies |
| `setCookie(cookie)` | Set cookie |
| `getStorage()` | Get localStorage/sessionStorage |
| `setStorage(key, value, type)` | Set storage |

### Configuration
| Method | Description |
|--------|-------------|
| `setViewport({width, height})` | Set viewport size |
| `setUserAgent(ua)` | Set User-Agent |
| `handleDialog(accept, text)` | Handle alert/confirm/prompt |

### Analysis
| Method | Description |
|--------|-------------|
| `A11yParser.parse(tree)` | Parse tree to elements |
| `A11yParser.find(tree, criteria)` | Find elements by role/name |
| `A11yParser.toDescription(tree)` | Generate human-readable description |

## Complete Agent Example: Auto-Login Flow

```javascript
const { RPAController, A11yParser } = require('./skill/rpa-development/scripts/rpa-client.js');

async function autoLogin(username, password) {
  const controller = new RPAController({ browserId: 'auto-login' });

  await controller.launch('auto-login');
  await controller.goto('https://example.com/login');

  // Loop until logged in
  for (let i = 0; i < 10; i++) {
    const a11y = await controller.getA11yTree();
    const { elements } = A11yParser.parse(a11y.a11y);

    // Find username field
    const usernameInput = elements.find(e => e.role === 'textbox' && !e.focused);
    if (usernameInput && !usernameInput.hasValue) {
      await controller.type(usernameInput.selector, username);
      continue;
    }

    // Find password field
    const passwordInput = elements.find(e => e.role === 'textbox');
    if (passwordInput && !passwordInput.hasValue) {
      await controller.type(passwordInput.selector, password);
      continue;
    }

    // Find login button
    const loginBtn = elements.find(e => e.role === 'button');
    if (loginBtn) {
      await controller.click(loginBtn.selector);
      await controller.waitIdle(30000);

      // Check if logged in
      const newA11y = await controller.getA11yTree();
      const hasDashboard = A11yParser.find(newA11y.a11y, { role: 'heading' })
        .some(h => h.name?.includes('Dashboard'));

      if (hasDashboard) {
        console.log('[Success] Logged in');
        break;
      }
    }
  }

  return controller;
}
```

## Additional Resources

### Reference Files
- **`references/api.md`** - Complete API documentation

### Example Files
- **`examples/qrcode-grab.js`** - QR code capture
- **`examples/login-flow.js`** - Login automation
- **`examples/data-extract.js`** - Data extraction

### Script Files
- **`scripts/server.js`** - Puppeteer stealth service
- **`scripts/rpa-client.js`** - Client library
- **`scripts/rpa-cli.js`** - CLI tool

## Best Practices for LLM Agents

1. **Always get A11y tree first** - Before any action, get the accessibility tree to understand page state

2. **Loop until completion** - Use while/for loops with max iterations to handle dynamic pages

3. **Check after each action** - After click/type, always get new A11y tree to verify result

4. **Use wait functions** - Use `waitNavigation()`, `waitIdle()` after navigation actions

5. **Handle dialogs proactively** - Call `handleDialog()` before triggering actions that might show dialogs

6. **Flexible element selection** - Use `A11yParser.find()` with role + name patterns, not hardcoded selectors

7. **Scroll for lazy-loaded content** - If element not found, scroll down and retry

8. **Multi-tab management** - Use `newTab()`, `switchTab()` for multi-page workflows

9. **Clean up resources** - Always call `close()` in finally block