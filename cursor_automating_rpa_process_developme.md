# Automating RPA process development
_Exported on 2026/2/11 at GMT+8 16:21:37 from Cursor (2.4.35)_

---

**User**

@README.md 

这是一个 通过 插件和python来操作浏览器，实现rpa操作的项目，现在需要针对一些网站来开发rpa流程，但是传统的开发方式是手动打开浏览器的开发者模式，然后定位元素，编写代码，反复测试实现，调试流程，纯人工干预；

帮我查一下是否有一些可以让大模型或者其他程序自动编写rpa流程的工作方式，降低人工参与，或者不需要人工参与。

---

**Cursor**

非常好的问题！你的 Neurone 项目架构已经很完善了（Chrome 扩展 + WebSocket Relay + Python 控制器），而且 README 中已经提到了 **AI 集成**和**录制回放**的扩展计划。目前业界确实已经有多种成熟/半成熟的方案可以让大模型自动编写 RPA 流程，以下是我调研到的主要方向：

---

## 一、当前主流方案总览

### 1. Browser-Use（GitHub 35.7K+ Stars）

这是目前最热门的 **LLM 驱动浏览器自动化** Python 框架，与你的项目定位非常接近。

**核心思路**：用户给出自然语言指令，LLM（GPT-4、Claude、Gemini 等）通过 ReAct（推理+行动）范式自动规划和执行浏览器操作。

```python
from browser_use import Agent

task = "去 kayak.com 搜索最便宜的航班"
agent = Agent(task=task, llm=llm)
await agent.run()
```

**关键特性**：
- **DOM 解析引擎**：将页面可交互元素提取为 LLM 友好的文本格式，节省 80% token 开销
- **自动生成 Playwright 脚本**：最新版本支持 `PlaywrightScriptGenerator`，将 AI Agent 的操作历史自动转换为可复用的 Playwright 脚本——**即 LLM 只需要跑一次，之后就可以无 LLM 成本地反复执行**
- **底层基于 Playwright**，而你的项目基于 `chrome.scripting`

### 2. Workflow-Use（Browser-Use 的扩展，3.9K Stars）

这是 Browser-Use 团队推出的 **RPA 2.0 平台**，更接近你的需求：

**核心功能**：
- **录制模式**：通过浏览器操作录制，自动生成工作流
- **自然语言生成工作流**：直接用自然语言描述需求，LLM 生成完整流程
- **两种执行模式**：确定性模式（不需要 AI）和 AI 增强模式（自动修复错误）
- **自愈能力**：页面变化时自动调整选择器
- **MCP Server 集成**：可将工作流暴露为 API 工具

CLI 工具链：
- `create-workflow`：录制并创建工作流
- `run-workflow`：执行工作流
- `run-as-tool`：LLM 自动推断参数执行
- `mcp-server`：将工作流暴露为标准工具

### 3. Playwright MCP（Microsoft 官方，26K+ Stars）

Microsoft 推出的 **Model Context Protocol** 服务器，让 AI Agent 通过**无障碍树（Accessibility Tree）** 而非截图来理解和操作页面。

**核心优势**：
- 不需要视觉模型，通过结构化数据操作浏览器
- 可以直接集成到 Claude Desktop、Cursor、VS Code 等 MCP 客户端
- 适合探索性自动化和自愈式测试

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

### 4. Computer Use Agent（Claude / OpenAI Operator）

**Anthropic Claude** 和 **OpenAI Operator** 提供的 **计算机使用代理**：
- 通过截图 + 视觉理解来操控浏览器
- 用自然语言描述任务，AI 自动截图→识别元素→执行操作
- 优势：最通用，无需了解任何页面结构
- 劣势：速度慢、成本高、准确率有限（约 70-85%）

### 5. HyperAgent

生产级 AI 浏览器自动化框架：
- 基于 Playwright，提供 `page.ai()` 和 `page.perform()` 等 AI 增强 API
- 内置隐身模式（stealth mode）
- 支持云端扩展

---

## 二、与 Neurone 项目结合的建议路径

考虑到你的项目已经有完善的 Chrome 扩展 + WebSocket + Python 架构，以下是几个可行的集成方向：

### 方案 A：在 Python 控制器层接入 LLM（推荐，改动最小）

```
用户自然语言指令
       ↓
  LLM（GPT-4/Claude）规划操作步骤
       ↓
  调用 NeuroneClient 的现有工具（click/fill/navigate/inject...）
       ↓
  截图/提取页面信息 → 反馈给 LLM → 继续下一步
```

**实现思路**：
1. 用 `chrome_screenshot` + `chrome_extract_data` 获取页面当前状态
2. 将页面信息（DOM 摘要/截图）发送给 LLM
3. LLM 返回下一步操作（调用哪个工具、什么参数）
4. 执行操作，循环直到任务完成
5. **记录整个操作序列**，生成可复用脚本

**优势**：完全复用你现有的 12 个工具，不需要改扩展代码，LLM 只负责决策。

### 方案 B：集成 Browser-Use 的 DOM 解析思路

Browser-Use 的核心创新是**将 DOM 转换为 LLM 友好的文本格式**。你可以在 `inject_script` 中注入类似的 DOM 解析脚本：

```python
# 注入 DOM 解析器，提取可交互元素的精简描述
dom_summary = await client.inject("""
    const elements = document.querySelectorAll('a, button, input, select, textarea, [role="button"]');
    return Array.from(elements).map((el, i) => ({
        index: i,
        tag: el.tagName,
        text: el.innerText?.slice(0, 50),
        selector: generateSelector(el),  // 生成唯一选择器
        type: el.type,
        placeholder: el.placeholder,
    }));
""")
```

然后将这些信息发送给 LLM，让它基于元素列表做出决策。

### 方案 C：录制 → AI 优化 → 生成脚本

1. **人工录制一次操作**（通过 content script 监听用户操作事件）
2. **LLM 分析录制结果**，识别关键步骤、去除冗余操作
3. **生成可参数化的 Python 脚本**（使用 NeuroneClient API）
4. 后续直接执行脚本，无需 LLM 参与

---

## 三、各方案对比

| 方案 | 人工参与度 | 成本 | 准确率 | 与 Neurone 集成难度 |
|------|-----------|------|--------|-------------------|
| **方案 A：LLM + Neurone 工具** | 极低（只需描述任务） | 中（每次都用 LLM） | 中高 | **低**（Python 层封装即可） |
| **方案 B：DOM 解析 + LLM 决策** | 极低 | 中 | 高（比截图方案准确） | **低**（inject_script 注入） |
| **方案 C：录制 + AI 优化** | 首次中等，后续零 | 低（LLM 只用一次） | 高 | **中**（需开发录制功能） |
| **Browser-Use 替换** | 极低 | 中 | 中高 | **高**（需更换底层架构） |
| **Computer Use（Claude/OpenAI）** | 极低 | 高 | 中（70-85%） | **中**（API 调用即可） |

---

## 四、我的建议

对于你的项目，**最实际的路径是方案 A + B 的组合**：

1. **短期**：在 Python 控制器层接入 LLM（如 OpenAI API），用 `chrome_screenshot` + DOM 解析结果作为上下文，让 LLM 自动调用 NeuroneClient 的 12 个工具——这样改动最小，可以快速验证
2. **中期**：开发操作录制功能（方案 C），让 LLM 只需要跑一次就能生成可复用脚本
3. **长期**：参考 WALT（ICLR 2026）的思路，将常用网站的操作逆向工程为确定性工具，减少对 LLM 的依赖

你现有的架构（无 CDP、无 webdriver 标志、隐蔽性强）相比 Browser-Use/Playwright 方案有独特优势，特别适合社交平台等有反爬检测的场景，所以**不建议直接替换为 Browser-Use，而是将 AI 决策层叠加在现有架构之上**。

需要我详细说明某个方案的具体实现方式吗？

---

**User**

1、Playwright MCP中的无障碍树（Accessibility Tree） 是如何生成的？是浏览器的原生能力还是需要借助一些扩展？
2、无障碍树 和DOM有什么区别？对于AI来说哪个更好？
3、当前的 Neurone 支持 无障碍树 和DOM 吗？分别如何实现？安全性如何？会被检测到吗？
4、开发操作录制功能  如何实现？有相关的技术路线吗？Browser-Use中的PlaywrightScriptGenerator 是怎么实现的？生成的是什么？

---

**Cursor**

好的，这四个问题都非常深入。让我逐一调研。

现在我已经完整阅读了你的项目代码，下面逐一回答四个问题：

---

## 问题 1：Playwright MCP 的无障碍树（Accessibility Tree）是如何生成的？

**无障碍树是浏览器的原生能力，不需要任何扩展。**

### 生成机制

浏览器（Chrome/Firefox/Safari）在渲染页面时，会从 DOM 树自动生成一棵**平行的无障碍树**，这是操作系统辅助功能（如屏幕阅读器 VoiceOver、NVDA）的基础设施。这个过程完全由浏览器引擎（Blink/Gecko/WebKit）内部完成。

### Playwright MCP 获取它的方式

Playwright MCP 通过 **Chrome DevTools Protocol (CDP)** 来获取无障碍树，具体使用 `Accessibility` 域的方法：

```
CDP → Accessibility.getFullAXTree()     // 获取整棵树
CDP → Accessibility.getPartialAXTree()  // 获取部分树
CDP → Accessibility.getChildAXNodes()   // 获取子节点
```

**关键点**：这需要通过 CDP 协议与浏览器通信（即 Playwright 通过 `--remote-debugging-port` 启动浏览器，建立 WebSocket 连接到 CDP 端口）。**普通 JavaScript 代码（包括 Chrome 扩展注入的脚本）无法直接访问浏览器的原生无障碍树。**

有一个正在开发中的标准 API 叫 **Accessibility Object Model (AOM)**，其中 `window.getComputedAccessibleNode(element)` 可以获取单个元素的无障碍信息，但目前：
- 尚未在主流浏览器中标准化
- Chrome 需要特殊启动参数 `--enable-blink-features=AccessibilityObjectModel`
- 只能获取**单个元素**的信息，无法一次性获取整棵树

---

## 问题 2：无障碍树和 DOM 的区别，对 AI 哪个更好？

### 核心区别

| 维度 | DOM 树 | 无障碍树 |
|------|--------|---------|
| **节点数量** | 所有 HTML 元素（一个页面可能有数千甚至数万节点） | 仅语义相关元素（通常是 DOM 的 1/10 到 1/5） |
| **包含内容** | 所有标签、属性、样式类、data-* 属性、装饰性 div 等 | 仅包含 role、name、description、state 四类属性 |
| **Token 开销** | 一个典型页面的 DOM 可能有 10万-15万 token | 同一页面的无障碍树通常 1万-1.5万 token |
| **语义清晰度** | 需要 AI 推断 `<div class="btn-primary">` 是按钮 | 直接标注 `role: button, name: "提交"` |
| **噪声** | 大量无关信息（广告、追踪脚本、CSS 动画容器等） | 已过滤掉纯装饰性元素 |

### 具体示例

同一个搜索框，DOM 可能是这样：

```html
<div class="search-wrapper" data-v-3e2f8a1c>
  <div class="search-inner" style="position:relative">
    <div class="search-icon-container">
      <svg class="icon-search" viewBox="0 0 24 24">...</svg>
    </div>
    <input type="text" class="search-input s-input" id="kw" 
           autocomplete="off" maxlength="255" 
           data-hook="searchInput" placeholder="搜索">
    <div class="search-clear-btn" style="display:none">...</div>
  </div>
</div>
```

无障碍树里只有：

```
- textbox "搜索" [focused] [editable]
```

### 对 AI 来说哪个更好？

**无障碍树在大多数场景下更优**，原因是：

1. **Token 效率**：减少 10-15 倍的上下文开销，直接降低成本和延迟
2. **减少幻觉**：更少的噪声意味着 AI 不容易被无关信息干扰
3. **语义明确**：`role: button` 比 `<div class="btn-primary" onclick="...">` 更容易让 AI 理解

**但 DOM 在某些场景不可替代**：

1. **精确定位**：CSS 选择器 `#kw`、`input[name="email"]` 需要 DOM 信息
2. **数据提取**：`data-*` 属性、隐藏字段的 value、特定 class 标记等只有 DOM 有
3. **复杂交互**：下拉菜单、虚拟滚动、Shadow DOM 等结构需要 DOM 级操作

**最佳实践是两者结合**：用无障碍树让 AI "看懂"页面（决策层），用 DOM 选择器执行具体操作（执行层）。Browser-Use 框架就是这样做的——它的 DOM 解析引擎提取的是一个**融合了语义信息和定位信息的精简结构**。

---

## 问题 3：当前 Neurone 支持无障碍树和 DOM 吗？

### DOM：完全支持，且隐蔽性极佳

你的项目通过 `chrome.scripting.executeScript` 在页面中执行 JS，**天然就能完全访问 DOM**。现有的 12 个工具已经覆盖了 DOM 操作的核心场景：

```137:157:extension/background.js
class InjectScriptTool extends BaseTool {
  constructor() { super('inject_script') }

  async execute({ code, world = 'MAIN', tabId }) {
    // ... 可以执行任意 JS，完全访问 DOM
  }
}
```

```251:299:extension/background.js
class ExtractDataTool extends BaseTool {
  // ... 提取 DOM 元素的文本、属性、HTML 等
}
```

**安全性/检测风险**：极低。`chrome.scripting` 注入的代码在页面沙箱中执行，不暴露 CDP 端口、不设置 `navigator.webdriver`，与用户手动在控制台执行代码无异。网站**无法检测到**这种访问方式。

### 无障碍树：目前不支持，但有两条实现路径

**路径 A：纯 JS 模拟无障碍树（推荐，兼容现有架构）**

虽然浏览器不暴露原生无障碍树的 JS API，但你可以通过 `inject_script` 注入一段 JS，**从 DOM 手动计算出一棵"伪无障碍树"**：

```javascript
// 通过 inject_script 注入以下代码
function buildAccessibilitySnapshot() {
  const INTERACTIVE_SELECTORS = 'a, button, input, select, textarea, [role], [tabindex], [aria-label], [contenteditable]';
  const SEMANTIC_TAGS = { 'H1':'heading','H2':'heading','H3':'heading','NAV':'navigation',
    'MAIN':'main','HEADER':'banner','FOOTER':'contentinfo','FORM':'form','TABLE':'table' };
  
  function getRole(el) {
    return el.getAttribute('role') 
      || SEMANTIC_TAGS[el.tagName] 
      || (el.tagName === 'A' && el.href ? 'link' : null)
      || (el.tagName === 'BUTTON' ? 'button' : null)
      || (el.tagName === 'INPUT' ? `input-${el.type}` : null)
      || (el.tagName === 'IMG' ? 'image' : null)
      || null;
  }
  
  function getName(el) {
    return el.getAttribute('aria-label') 
      || el.getAttribute('alt')
      || el.getAttribute('title')
      || el.getAttribute('placeholder')
      || (el.tagName === 'INPUT' ? '' : (el.innerText || '').trim().slice(0, 80))
      || '';
  }
  
  function getState(el) {
    const s = {};
    if (el.disabled) s.disabled = true;
    if (el.checked) s.checked = true;
    if (el.readOnly) s.readonly = true;
    if (el.getAttribute('aria-expanded')) s.expanded = el.getAttribute('aria-expanded') === 'true';
    if (!el.offsetParent && el.style?.display !== 'fixed') s.hidden = true;
    return s;
  }
  
  const elements = document.querySelectorAll(INTERACTIVE_SELECTORS);
  return Array.from(elements)
    .filter(el => el.offsetParent || el.tagName === 'INPUT') // 过滤不可见元素
    .map((el, i) => ({
      index: i,
      role: getRole(el),
      name: getName(el),
      tag: el.tagName.toLowerCase(),
      selector: el.id ? `#${el.id}` : generateCssPath(el), // 生成唯一选择器
      state: getState(el),
      value: el.value || undefined,
    }));
}
```

**安全性**：与普通 DOM 操作完全相同，**不会被检测到**。这只是在读取 DOM 属性，和网站自己的 JS 代码做的事情没有任何区别。

**路径 B：通过 `chrome.debugger` API 获取原生无障碍树**

Chrome 扩展可以使用 `chrome.debugger` API 连接到标签页的 CDP：

```javascript
// 需要在 manifest.json 中添加 "debugger" 权限
await chrome.debugger.attach({ tabId }, '1.3');
const result = await chrome.debugger.sendCommand(
  { tabId }, 
  'Accessibility.getFullAXTree', 
  { depth: 5 }
);
// result.nodes 就是完整的无障碍树
await chrome.debugger.detach({ tabId });
```

**安全性**：**会被检测到！** `chrome.debugger` 会触发浏览器顶部的**黄色调试横幅**（"Neurone 正在调试此标签页"），并且页面可以通过一些方式检测到 debugger 的存在。这正是你的 README 中提到的核心痛点——也是你选择 `chrome.scripting` 方案的原因。

### 对比

| 方案 | 数据质量 | 隐蔽性 | 实现难度 |
|------|---------|--------|---------|
| **路径 A：JS 模拟** | 90%（缺少浏览器内部计算的隐式角色） | **极高，完全不可检测** | 低（inject_script 即可） |
| **路径 B：chrome.debugger** | 100%（原生无障碍树） | **低，有调试横幅** | 中（需加权限） |
| **Playwright MCP 方式** | 100% | 低（需要 CDP 端口） | 不适用（与你的架构冲突） |

**建议**：路径 A 是最佳选择。对于 AI 决策来说，90% 的无障碍信息完全足够，而且保持了你项目的核心优势——隐蔽性。

---

## 问题 4：操作录制功能如何实现？

### 技术路线

操作录制的核心思路很简单：**在页面中注入一个事件监听器，捕获用户的所有操作（点击、输入、导航等），序列化为结构化数据。**

#### 方案 A：Content Script 事件监听（推荐）

在 Neurone 中，可以通过 `inject_script` 注入一个录制脚本：

```javascript
// 注入到页面中的录制器
(function() {
  const actions = [];
  
  // 生成唯一 CSS 选择器
  function getCssPath(el) {
    const path = [];
    while (el && el !== document.body) {
      let selector = el.tagName.toLowerCase();
      if (el.id) { path.unshift(`#${el.id}`); break; }
      const siblings = el.parentNode?.children;
      if (siblings?.length > 1) {
        const idx = Array.from(siblings).filter(s => s.tagName === el.tagName).indexOf(el);
        if (idx > 0) selector += `:nth-of-type(${idx + 1})`;
      }
      path.unshift(selector);
      el = el.parentNode;
    }
    return path.join(' > ');
  }
  
  // 监听点击
  document.addEventListener('click', (e) => {
    actions.push({
      type: 'click',
      selector: getCssPath(e.target),
      text: e.target.innerText?.slice(0, 50),
      timestamp: Date.now(),
      x: e.clientX, y: e.clientY
    });
  }, true);
  
  // 监听输入
  document.addEventListener('input', (e) => {
    actions.push({
      type: 'input',
      selector: getCssPath(e.target),
      value: e.target.value,
      timestamp: Date.now()
    });
  }, true);
  
  // 监听键盘（Enter、Tab 等特殊键）
  document.addEventListener('keydown', (e) => {
    if (['Enter', 'Tab', 'Escape', 'Backspace'].includes(e.key)) {
      actions.push({
        type: 'keypress',
        key: e.key,
        selector: getCssPath(e.target),
        timestamp: Date.now()
      });
    }
  }, true);
  
  // 暴露给 Neurone 的接口
  window.__neurone_recorder = {
    getActions: () => [...actions],
    clear: () => { actions.length = 0; },
    isRecording: true
  };
})();
```

然后通过 Python 端随时获取录制结果：

```python
actions = await client.inject("return window.__neurone_recorder.getActions()")
```

#### 方案 B：Chrome DevTools Recorder 导出

Chrome DevTools 自带录制面板（chrome://devtools → Recorder），支持导出为 JSON 或 Puppeteer 脚本。可以通过 `chrome.devtools.recorder` API 扩展导出格式。但这需要用户手动操作 DevTools。

### Browser-Use 的 PlaywrightScriptGenerator 实现原理

通过阅读 PR #1437 的源码，其工作流程如下：

**第一步：Agent 运行时自动记录操作历史**

Browser-Use 的 Agent 在执行每一步操作时，会将操作记录到 `AgentHistoryList` 中，每条记录包含：
- 操作类型（`click`、`input_text`、`go_to_url`、`scroll` 等）
- XPath 选择器（操作时从 DOM 中计算的）
- 参数（填充的值、点击的坐标等）
- 页面状态快照

**第二步：`PlaywrightScriptGenerator` 将历史转换为脚本**

核心类 `PlaywrightScriptGenerator` 做的事情：

1. **遍历 `AgentHistoryList`**，提取每一步的操作类型和参数
2. **通过 action_handlers 字典分发**，将每种操作映射为对应的 Playwright API 调用：
   - `go_to_url` → `await page.goto("...")`
   - `click` → `await _try_locate_and_act(page, xpath, "click")`
   - `input_text` → `await _try_locate_and_act(page, xpath, "fill", value)`
   - `scroll` → `await page.evaluate("window.scrollBy(...)")`
3. **生成 `_try_locate_and_act` 辅助函数**：这是核心的自愈逻辑
   - 先尝试完整 XPath 定位
   - 失败则**逐级裁剪 XPath 前缀**（`/html/body/div[1]/a` → `/body/div[1]/a` → `/div[1]/a`）
   - 每次裁剪后重试定位，直到找到元素或所有路径用尽
4. **继承浏览器配置**：headless、proxy、viewport、cookies 等

**第三步：生成最终 Python 脚本**

生成的是一个**独立可运行的 Python 文件**，大致结构：

```python
import asyncio
from playwright.async_api import async_playwright

async def _try_locate_and_act(page, xpath, action, value=None):
    """自愈定位：逐级裁剪 XPath 直到找到元素"""
    parts = xpath.split('/')
    for i in range(len(parts)):
        trimmed = '/'.join(parts[i:])
        try:
            el = page.locator(f"xpath=//{trimmed}")
            if await el.count() > 0:
                if action == "click": await el.first.click()
                elif action == "fill": await el.first.fill(value)
                return True
        except: continue
    return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        # === Agent 录制的操作序列 ===
        await page.goto("https://www.baidu.com")
        await _try_locate_and_act(page, "/html/body/div/form/input[@id='kw']", "fill", "测试搜索")
        await _try_locate_and_act(page, "/html/body/div/form/input[@id='su']", "click")
        await page.wait_for_timeout(2000)
        
        await browser.close()

asyncio.run(main())
```

**注意**：Browser-Use 的维护者（pirate）在 PR review 中提出了一个更好的方向——将操作历史先导出为**中间 JSON 格式**（兼容 Chrome DevTools Recorder 的 JSON 格式），然后再从 JSON 生成 Playwright 脚本。这样数据和代码分离，未来还可以生成 Puppeteer、WebDriver-BiDi 等其他格式的脚本。

### 对 Neurone 项目的建议

你完全可以实现一套类似但更轻量的方案：

1. **录制层**：通过 `inject_script` 注入事件监听器（方案 A），捕获用户操作
2. **存储层**：将操作序列保存为 JSON（参考 Chrome DevTools Recorder 格式）
3. **回放层**：将 JSON 操作序列转换为 `NeuroneClient` 的 API 调用（比如 `client.click()`、`client.fill()` 等）
4. **AI 优化层（可选）**：将录制的操作序列交给 LLM，让它去除冗余步骤、参数化变量、添加错误处理

这比 Browser-Use 的方案更简单——因为你不需要生成 Playwright 脚本，只需要生成 Neurone 自己的工具调用序列即可。而且你的方案保持了**隐蔽性**优势，不需要 Playwright/CDP。



