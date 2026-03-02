/**
 * RPA Client - 与 Puppeteer Stealth Service 交互的客户端
 * 支持大模型驱动的自动化流程开发
 */

const http = require('http');
const https = require('https');

class RPAController {
  constructor(options = {}) {
    this.host = options.host || 'localhost';
    this.port = options.port || 18765;
    this.browserId = options.browserId || null;
    this.pageIndex = 0;
    this.conversationHistory = [];
    this.debug = options.debug || false;
  }

  // HTTP 请求封装
  _request(method, path, data = null) {
    return new Promise((resolve, reject) => {
      const isHttps = this.port === 443;
      const client = isHttps ? https : http;

      const options = {
        hostname: this.host,
        port: this.port,
        path: path,
        method: method,
        headers: {
          'Content-Type': 'application/json'
        }
      };

      const req = client.request(options, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
          // 处理空响应
          if (!body || body.trim() === '') {
            resolve({ success: true });
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            resolve(body);
          }
        });
      });

      req.on('error', reject);

      // 始终发送数据（即使是空对象），避免 Content-Length 问题
      const payload = data ? JSON.stringify(data) : '{}';
      req.write(payload);
      req.end();
    });
  }

  // 启动浏览器
  async launch(browserId = 'rpa-browser') {
    const result = await this._request('POST', '/browser/launch', { id: browserId });
    if (result.success) {
      this.browserId = browserId;
      this.debug && console.log(`[RPA] Browser launched: ${browserId}`);
    }
    return result;
  }

  // 关闭浏览器
  async close() {
    if (!this.browserId) return { success: false, error: 'No browser' };
    const result = await this._request('POST', `/browser/${this.browserId}/close`);
    this.browserId = null;
    return result;
  }

  // 访问页面
  async goto(url, options = {}) {
    const data = {
      url,
      waitUntil: options.waitUntil || 'networkidle2',
      timeout: options.timeout || 30000,
      headers: options.headers || {}
    };
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/goto`, data);
    this.debug && console.log(`[RPA] goto: ${url} -> ${result.status}`);
    return result;
  }

  // 获取无障碍树
  async getA11yTree() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/a11y`);
    return result;
  }

  // 点击元素
  async click(selector) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/click`, { selector });
    this.debug && console.log(`[RPA] click: ${selector}`);
    return result;
  }

  // 输入文本
  async type(selector, text, delay = 0) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/type`, {
      selector, text, delay
    });
    this.debug && console.log(`[RPA] type: ${selector} <- "${text}"`);
    return result;
  }

  // 等待元素
  async wait(selector, timeout = 30000) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/wait`, {
      selector, timeout
    });
    this.debug && console.log(`[RPA] wait: ${selector}`);
    return result;
  }

  // 执行自定义脚本
  async execute(script, scriptType = 'function') {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/execute`, {
      script, scriptType
    });
    return result;
  }

  // 截图
  async screenshot(fullPage = false) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/screenshot`, {
      fullPage
    });
    return result;
  }

  // 获取 Cookie
  async getCookies() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/cookies`);
    return result;
  }

  // 设置 Cookie
  async setCookie(cookie) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/cookies/set`, {
      cookie
    });
    return result;
  }

  // 获取页面内容
  async getContent() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/content`);
    return result;
  }

  // 滚动页面
  async scroll(distance = 500) {
    const result = await this.execute(`() => window.scrollBy(0, ${distance})`);
    this.debug && console.log(`[RPA] scroll: ${distance}px`);
    return result;
  }

  // 悬停元素
  async hover(selector) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/hover`, { selector });
    this.debug && console.log(`[RPA] hover: ${selector}`);
    return result;
  }

  // 双击元素
  async doubleClick(selector) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/doubleclick`, { selector });
    this.debug && console.log(`[RPA] doubleClick: ${selector}`);
    return result;
  }

  // 右键点击
  async rightClick(selector) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/clickright`, { selector });
    this.debug && console.log(`[RPA] rightClick: ${selector}`);
    return result;
  }

  // 键盘操作
  async keyboard(action, params = {}) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/keyboard`, { action, ...params });
    this.debug && console.log(`[RPA] keyboard: ${action}`);
    return result;
  }

  // 下拉选择
  async select(selector, value) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/select`, { selector, value });
    this.debug && console.log(`[RPA] select: ${selector} <- ${value}`);
    return result;
  }

  // 文件上传
  async upload(selector, filePath) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/upload`, { selector, filePath });
    this.debug && console.log(`[RPA] upload: ${selector} <- ${filePath}`);
    return result;
  }

  // 设置视口
  async setViewport(config) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/viewport`, config);
    this.debug && console.log(`[RPA] setViewport: ${config.width}x${config.height}`);
    return result;
  }

  // 设置 User-Agent
  async setUserAgent(userAgent) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/setua`, { userAgent });
    this.debug && console.log(`[RPA] setUserAgent: ${userAgent}`);
    return result;
  }

  // 获取存储
  async getStorage() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/storage/local`);
    return result;
  }

  // 设置存储
  async setStorage(key, value, storageType = 'local') {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/storage/local/set`, { key, value, storageType });
    this.debug && console.log(`[RPA] setStorage: ${key}`);
    return result;
  }

  // 打开新标签页
  async newTab(url = 'about:blank') {
    const result = await this._request('POST', `/browser/${this.browserId}/page/new-tab`, { url });
    if (result.success) {
      this.pageIndex = result.pageIndex;
      this.debug && console.log(`[RPA] newTab: ${url} (index: ${this.pageIndex})`);
    }
    return result;
  }

  // 关闭当前页
  async closeTab() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/close`);
    if (result.success && result.remainingPages > 0) {
      this.pageIndex = 0;
    }
    return result;
  }

  // 切换页面
  async switchTab(pageIndex) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${pageIndex}/switch`);
    if (result.success) {
      this.pageIndex = pageIndex;
    }
    return result;
  }

  // 等待导航
  async waitNavigation(timeout = 30000) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/waitnav`, { timeout });
    return result;
  }

  // 等待函数返回 true
  async waitFunction(script, timeout = 30000) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/waitfn`, { script, timeout });
    return result;
  }

  // 等待网络空闲
  async waitIdle(timeout = 30000) {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/waitidle`, { timeout });
    return result;
  }

  // 设置对话框处理
  async handleDialog(accept = true, promptText = '') {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/dialog`, { accept, promptText });
    return result;
  }

  // 获取页面标题
  async getTitle() {
    const result = await this._request('POST', `/browser/${this.browserId}/page/${this.pageIndex}/title`);
    return result;
  }

  // 健康检查
  async health() {
    return await this._request('GET', '/health');
  }

  // 列出所有浏览器
  async listBrowsers() {
    return await this._request('GET', '/browser/list');
  }

  // 记录对话
  addMessage(role, content) {
    this.conversationHistory.push({ role, content, timestamp: Date.now() });
  }

  // 获取对话历史
  getHistory() {
    return this.conversationHistory;
  }

  // 清空对话历史
  clearHistory() {
    this.conversationHistory = [];
  }
}

/**
 * 解析无障碍树为结构化描述
 */
class A11yParser {
  static parse(tree) {
    if (!tree || !tree.children) return { elements: [], summary: '' };

    const elements = [];
    const summary = [];

    const parseNode = (node, depth = 0) => {
      const indent = '  '.repeat(depth);
      if (node.role && node.name) {
        const el = {
          role: node.role,
          name: node.name.substring(0, 100),
          url: node.url || null,
          focused: node.focused || false,
          disabled: node.disabled || false,
          depth
        };
        element.push(el);
        summary.push(`${indent}[${node.role}] ${node.name.substring(0, 50)}`);
      }
      if (node.children) {
        node.children.forEach(child => parseNode(child, depth + 1));
      }
    };

    parseNode(tree);
    return { elements, summary: summary.join('\n'), root: tree };
  }

  // 查找特定元素
  static find(tree, criteria) {
    const results = [];

    const search = (node) => {
      let match = true;
      if (criteria.role && node.role !== criteria.role) match = false;
      if (criteria.name && !node.name?.includes(criteria.name)) match = false;
      if (criteria.contains && !node.name?.includes(criteria.contains)) match = false;

      if (match) results.push(node);

      if (node.children) {
        node.children.forEach(search);
      }
    };

    search(tree);
    return results;
  }

  // 生成可读描述
  static toDescription(tree) {
    const lines = [];
    lines.push(`页面: ${tree.name || 'Unknown'}`);
    lines.push(`URL: ${tree.url || 'N/A'}`);

    const elements = this.find(tree, {});
    const links = elements.filter(e => e.role === 'link').slice(0, 10);
    const buttons = elements.filter(e => e.role === 'button').slice(0, 10);
    const inputs = elements.filter(e => ['textbox', 'searchbox', 'combobox'].includes(e.role));

    if (links.length) {
      lines.push(`\n链接 (${links.length}个, 显示前10):`);
      links.forEach(l => lines.push(`  - ${l.name}`));
    }

    if (buttons.length) {
      lines.push(`\n按钮 (${buttons.length}个):`);
      buttons.forEach(b => lines.push(`  - ${b.name}`));
    }

    if (inputs.length) {
      lines.push(`\n输入框 (${inputs.length}个):`);
      inputs.forEach(i => lines.push(`  - ${i.name || '未命名'}`));
    }

    return lines.join('\n');
  }
}

/**
 * 自动化脚本生成器
 */
class ScriptGenerator {
  // 生成 Playwright 脚本
  static toPlaywright(operations) {
    const lines = [
      '# 自动生成的 Playwright 脚本',
      '# pip install playwright',
      '# playwright install chromium',
      '',
      'from playwright.sync_api import sync_playwright',
      '',
      'def run():',
      '    with sync_playwright() as p:',
      '        browser = p.chromium.launch(headless=True)',
      '        page = browser.new_page()',
      ''
    ];

    // 兼容 op.type 和 op.action 两种格式
    const getOpType = (op) => op.type || op.action || '';

    operations.forEach(op => {
      switch (getOpType(op)) {
        case 'goto':
          lines.push(`        page.goto("${op.url}")`);
          break;
        case 'wait':
          if (op.timeout) {
            lines.push(`        page.wait_for_timeout(${op.timeout})`);
          } else {
            lines.push(`        page.wait_for_selector("${op.selector}", timeout=${op.timeout || 30000})`);
          }
          break;
        case 'click':
          lines.push(`        page.click("${op.selector}")`);
          break;
        case 'type':
          // 使用 type() 模拟真实输入，避免被反爬检测
          const delay = op.delay !== undefined ? op.delay : 50;
          lines.push(`        page.type("${op.selector}", "${op.value || op.text}", delay=${delay})`);
          break;
        case 'fill':
          // fill() 可能被检测，仅在明确指定时使用
          lines.push(`        page.fill("${op.selector}", "${op.value || op.text}")`);
          break;
        case 'scroll':
          lines.push(`        page.evaluate("() => window.scrollBy(0, ${op.distance})")`);
          break;
      }
    });

    lines.push('        browser.close()');
    lines.push('');
    lines.push('if __name__ == "__main__":');
    lines.push('    run()');

    return lines.join('\n');
  }

  // 生成 Puppeteer 脚本
  static toPuppeteer(operations) {
    const lines = [
      '// 自动生成的 Puppeteer 脚本',
      'const puppeteer = require("puppeteer-extra");',
      'const stealth = require("puppeteer-extra-plugin-stealth");',
      '',
      'puppeteer.use(stealth());',
      '',
      '(async () => {',
      '  const browser = await puppeteer.launch({ headless: true });',
      '  const page = await browser.newPage();',
      ''
    ];

    operations.forEach(op => {
      switch (op.type) {
        case 'goto':
          lines.push(`  await page.goto("${op.url}", { waitUntil: "networkidle2" });`);
          break;
        case 'wait':
          lines.push(`  await page.waitForSelector("${op.selector}", { timeout: ${op.timeout || 30000} });`);
          break;
        case 'click':
          lines.push(`  await page.click("${op.selector}");`);
          break;
        case 'type':
          lines.push(`  await page.type("${op.selector}", "${op.text}");`);
          break;
        case 'scroll':
          lines.push(`  await page.evaluate("() => window.scrollBy(0, ${op.distance})");`);
          break;
      }
    });

    lines.push('  await browser.close();');
    lines.push('})();');

    return lines.join('\n');
  }
}

/**
 * 简单的 AI Agent (需要接入大模型 API)
 */
class RPAAgent {
  constructor(controller, options = {}) {
    this.controller = controller;
    this.apiKey = options.apiKey || process.env.OPENAI_API_KEY;
    this.model = options.model || 'gpt-4';
    this.operationsLog = [];
  }

  // 调用大模型 API
  async _callLLM(messages) {
    if (!this.apiKey) {
      throw new Error('需要设置 API Key');
    }

    // 这里可以替换为实际的大模型调用
    // 例如 OpenAI, Claude, 通义千问 等
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        temperature: 0.7
      })
    });

    const data = await response.json();
    return data.choices[0].message.content;
  }

  // 发送用户指令
  async execute(userInstruction) {
    // 1. 获取当前页面无障碍树
    const a11yResult = await this.controller.getA11yTree();
    const a11yDesc = A11yParser.toDescription(a11yResult.a11y);

    // 2. 构建提示
    const systemPrompt = `你是一个 RPA 自动化助手。根据用户指令和无障碍树生成操作序列。

可用的操作:
- goto(url): 访问URL
- click(selector): 点击元素
- type(selector, text): 输入文本
- wait(selector): 等待元素
- scroll(distance): 滚动页面

无障碍树信息:
${a11yDesc}

请生成操作序列 JSON 格式:
[
  {"type": "goto", "url": "..."},
  {"type": "click", "selector": "..."},
  ...
]

只输出 JSON，不要其他文字。`;

    const messages = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userInstruction }
    ];

    // 3. 调用大模型
    const response = await this._callLLM(messages);

    // 4. 解析操作序列
    let operations;
    try {
      operations = JSON.parse(response);
    } catch (e) {
      console.error('解析失败:', response);
      return { error: '无法解析大模型响应' };
    }

    // 5. 执行操作序列
    const results = [];
    for (const op of operations) {
      let result;
      try {
        switch (op.type) {
          case 'goto':
            result = await this.controller.goto(op.url);
            break;
          case 'click':
            result = await this.controller.click(op.selector);
            break;
          case 'type':
            result = await this.controller.type(op.selector, op.text);
            break;
          case 'wait':
            result = await this.controller.wait(op.selector);
            break;
          case 'scroll':
            result = await this.controller.scroll(op.distance || 500);
            break;
        }
        results.push({ op, result, success: result.success });

        // 记录操作
        this.operationLog.push(op);
        this.controller.addMessage('assistant', `执行: ${op.type}`);
      } catch (e) {
        results.push({ op, error: e.message, success: false });
      }
    }

    return { operations, results };
  }

  // 获取操作日志
  getOperationLog() {
    return this.operationLog;
  }

  // 生成脚本
  generateScript(format = 'playwright') {
    if (format === 'playwright') {
      return ScriptGenerator.toPlaywright(this.operationLog);
    } else {
      return ScriptGenerator.toPuppeteer(this.operationLog);
    }
  }
}

/**
 * Operation Recorder - 记录操作并在最后生成可复用脚本
 * 核心设计：先执行操作，后生成脚本
 */
class OperationRecorder {
  constructor() {
    this.operations = [];
  }

  // 记录操作
  record(operation) {
    this.operations.push({
      ...operation,
      timestamp: Date.now()
    });
    console.log(`[Recorder] Recorded: ${operation.type}`);
  }

  // 获取所有记录的操作
  getOperations() {
    return this.operations;
  }

  // 导出为 JSON
  exportJSON() {
    return JSON.stringify(this.operations, null, 2);
  }

  // 从 JSON 导入
  importJSON(json) {
    this.operations = JSON.parse(json);
  }

  // 生成 Puppeteer 脚本
  generateScript(format = 'puppeteer') {
    if (format === 'playwright') {
      return ScriptGenerator.toPlaywright(this.operations);
    } else if (format === 'puppeteer') {
      return this._toPuppeteerScript();
    } else if (format === 'node') {
      return this._toNodeScript();
    }
    return this._toPuppeteerScript();
  }

  // 生成 Puppeteer 脚本
  _toPuppeteerScript() {
    const lines = [
      '// Auto-generated RPA Script',
      '// Generated by RPA Development Skill',
      '',
      'const puppeteerExtra = require("puppeteer-extra");',
      'const stealth = require("puppeteer-extra-plugin-stealth");',
      '',
      'puppeteerExtra.use(stealth());',
      '',
      '(async () => {',
      '  const browser = await puppeteerExtra.launch({',
      '    headless: false,',
      '    args: ["--disable-blink-features=AutomationControlled"]',
      '  });',
      '  const page = await browser.newPage();',
      ''
    ];

    for (const op of this.operations) {
      switch (op.type) {
        case 'launch':
          // 启动已处理在上面
          break;
        case 'goto':
          lines.push(`  await page.goto("${op.url}", { waitUntil: "networkidle2" });`);
          break;
        case 'click':
          lines.push(`  await page.click("${op.selector}");`);
          break;
        case 'doubleClick':
          lines.push(`  await page.doubleClick("${op.selector}");`);
          break;
        case 'type':
          lines.push(`  await page.type("${op.selector}", "${op.text}");`);
          break;
        case 'hover':
          lines.push(`  await page.hover("${op.selector}");`);
          break;
        case 'select':
          lines.push(`  await page.select("${op.selector}", "${op.value}");`);
          break;
        case 'scroll':
          lines.push(`  await page.evaluate("() => window.scrollBy(0, ${op.distance})");`);
          break;
        case 'wait':
          lines.push(`  await page.waitForSelector("${op.selector}", { timeout: ${op.timeout || 30000} });`);
          break;
        case 'screenshot':
          lines.push(`  const screenshot = await page.screenshot({ fullPage: ${op.fullPage || false} });`);
          lines.push(`  require("fs").writeFileSync("output.png", screenshot);`);
          break;
        case 'getContent':
          lines.push(`  const content = await page.content();`);
          break;
        case 'newTab':
          lines.push(`  const newPage = await browser.newPage();`);
          lines.push(`  await newPage.goto("${op.url}", { waitUntil: "networkidle2" });`);
          break;
        case 'close':
          // 关闭在最后处理
          break;
        default:
          if (op.type !== 'close') {
            console.log(`[Recorder] Unknown operation type: ${op.type}`);
          }
      }
    }

    lines.push('  await browser.close();');
    lines.push('})();');

    return lines.join('\n');
  }

  // 生成 Node.js 客户端脚本 (使用 HTTP API)
  _toNodeScript() {
    const lines = [
      '// Auto-generated RPA Script (Node.js Client)',
      '// Requires: npm install axios',
      '',
      'const axios = require("axios");',
      '',
      'const HOST = "localhost";',
      'const PORT = 18765;',
      'const BROWSER_ID = "auto-browser";',
      '',
      'async function request(method, path, data = null) {',
      '  const url = `http://${HOST}:${PORT}${path}`;',
      '  const opts = { method, url };',
      '  if (data) opts.data = data;',
      '  const res = await axios(opts);',
      '  return res.data;',
      '}',
      '',
      'async function main() {',
      '  // Launch browser',
      '  await request("POST", "/browser/launch", { id: BROWSER_ID, headless: false });',
      ''
    ];

    for (const op of this.operations) {
      switch (op.type) {
        case 'launch':
          break;
        case 'goto':
          lines.push(`  // Navigate to ${op.url}`);
          lines.push(`  await request("POST", \`/browser/\${BROWSER_ID}/page/0/goto\`, {`);
          lines.push(`    url: "${op.url}",`);
          lines.push(`    waitUntil: "networkidle2"`);
          lines.push(`  });`);
          lines.push('');
          break;
        case 'click':
          lines.push(`  await request("POST", \`/browser/\${BROWSER_ID}/page/0/click\`, {`);
          lines.push(`    selector: "${op.selector}"`);
          lines.push(`  });`);
          lines.push('');
          break;
        case 'type':
          lines.push(`  await request("POST", \`/browser/\${BROWSER_ID}/page/0/type\`, {`);
          lines.push(`    selector: "${op.selector}",`);
          lines.push(`    text: "${op.text}"`);
          lines.push(`  });`);
          lines.push('');
          break;
        case 'screenshot':
          lines.push(`  const screenshot = await request("POST", \`/browser/\${BROWSER_ID}/page/0/screenshot\`, {`);
          lines.push(`    fullPage: ${op.fullPage || false}`);
          lines.push(`  });`);
          lines.push(`  require("fs").writeFileSync("output.png", Buffer.from(screenshot.data, "base64"));`);
          lines.push('');
          break;
        case 'close':
          lines.push(`  // Close browser`);
          lines.push(`  await request("POST", \`/browser/\${BROWSER_ID}/close\`);`);
          break;
      }
    }

    lines.push('}');
    lines.push('');
    lines.push('main();');

    return lines.join('\n');
  }

  // 清除记录
  clear() {
    this.operations = [];
  }
}

module.exports = {
  RPAController,
  A11yParser,
  ScriptGenerator,
  RPAAgent,
  OperationRecorder
};