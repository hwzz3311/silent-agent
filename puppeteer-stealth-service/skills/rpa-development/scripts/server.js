const express = require('express');
const puppeteerExtra = require('puppeteer-extra');
const stealth = require('puppeteer-extra-plugin-stealth');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 18765;

// 启用 stealth 插件
puppeteerExtra.use(stealth());

app.use(bodyParser.json());

// 存储活跃的浏览器实例 - 使用 let 以确保可访问
let browserManager = {};

console.log('Initializing server...');
console.log('Browser manager:', typeof browserManager);

// 默认 Chrome 路径 (macOS)
const DEFAULT_EXECUTABLE_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

/**
 * 启动一个新的浏览器实例
 */
app.post('/browser/launch', async (req, res) => {
  try {
    const { id, headless = true, args = [], executablePath } = req.body;
    const browserId = id || `browser_${Date.now()}`;

    const defaultArgs = [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
    ];

    const launchOptions = {
      headless,
      args: [...defaultArgs, ...args],
      defaultViewport: { width: 1280, height: 720 },
    };

    // 如果提供了 executablePath 或使用默认
    const exePath = executablePath || DEFAULT_EXECUTABLE_PATH;
    launchOptions.executablePath = exePath;

    const browser = await puppeteerExtra.launch(launchOptions);

    browserManager[browserId] = browser;

    // 浏览器关闭时清理
    browser.on('closed', () => {
      delete browserManager[browserId];
      console.log(`Browser ${browserId} closed`);
    });

    const pages = await browser.pages();
    const wsEndpoint = browser.wsEndpoint();

    res.json({
      success: true,
      id: browserId,
      wsEndpoint,
      pageCount: pages ? 1 : 0
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 打开新页面
 */
app.post('/browser/:id/page/new', async (req, res) => {
  try {
    const { id } = req.params;
    const browser = browserManager[id];

    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const page = await browser.newPage();
    res.json({ success: true, pageIndex: browser.pages().length - 1 });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 执行脚本
 */
app.post('/browser/:id/page/:pageIndex/execute', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { script, scriptType = 'function' } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    let result;
    if (scriptType === 'function') {
      // 使用 page.evaluate 执行脚本
      result = await page.evaluate(script);
    } else if (scriptType === 'expression') {
      result = await page.evaluate((...args) => eval(script), ...(req.body.args || []));
    }

    res.json({ success: true, result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取无障碍树
 */
app.post('/browser/:id/page/:pageIndex/a11y', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const snapshot = await page.accessibility.snapshot();
    res.json({ success: true, a11y: snapshot });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 导航到 URL
 */
app.post('/browser/:id/page/:pageIndex/goto', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { url, waitUntil = 'networkidle2', timeout = 30000, headers } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    // 设置自定义 headers
    if (headers) {
      await page.setExtraHTTPHeaders(headers);
    }

    const response = await page.goto(url, { waitUntil, timeout });
    const html = await page.content();

    res.json({
      success: true,
      status: response.status(),
      url: response.url(),
      htmlLength: html.length
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 截图
 */
app.post('/browser/:id/page/:pageIndex/screenshot', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { fullPage = false } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const buffer = await page.screenshot({ fullPage });
    // 确保转换为标准 Buffer 再转 base64
    const base64 = Buffer.from(buffer).toString('base64');

    res.json({
      success: true,
      format: 'png',
      data: base64
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取页面内容
 */
app.post('/browser/:id/page/:pageIndex/content', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const html = await page.content();
    res.json({ success: true, html });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 点击元素
 */
app.post('/browser/:id/page/:pageIndex/click', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.click(selector);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 输入文本
 */
app.post('/browser/:id/page/:pageIndex/type', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector, text, delay = 0 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.type(selector, text, { delay });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 等待元素
 */
app.post('/browser/:id/page/:pageIndex/wait', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector, timeout = 30000 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.waitForSelector(selector, { timeout });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取 cookie
 */
app.post('/browser/:id/page/:pageIndex/cookies', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const cookies = await page.cookies();
    res.json({ success: true, cookie });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 设置 cookie
 */
app.post('/browser/:id/page/:pageIndex/cookies/set', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { cookie } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.setCookie(cookie);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 关闭浏览器
 */
app.post('/browser/:id/close', async (req, res) => {
  try {
    const { id } = req.params;
    const browser = browserManager[id];

    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    await browser.close();
    delete browserManager[id];

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 悬停元素
 */
app.post('/browser/:id/page/:pageIndex/hover', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.hover(selector);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 双击元素
 */
app.post('/browser/:id/page/:pageIndex/doubleclick', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.doubleClick(selector);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 右键点击元素
 */
app.post('/browser/:id/page/:pageIndex/clickright', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.click(selector, { button: 'right' });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 键盘操作
 */
app.post('/browser/:id/page/:pageIndex/keyboard', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { action, key, text } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const keyboard = page.keyboard;

    switch (action) {
      case 'press':
        await keyboard.press(key);
        break;
      case 'type':
        await keyboard.type(text || '');
        break;
      case 'down':
        await keyboard.down(key);
        break;
      case 'up':
        await keyboard.up(key);
        break;
      default:
        return res.status(400).json({ success: false, error: 'Unknown action' });
    }

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 下拉选择
 */
app.post('/browser/:id/page/:pageIndex/select', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector, value } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const result = await page.select(selector, value);
    res.json({ success: true, selected: result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 文件上传
 */
app.post('/browser/:id/page/:pageIndex/upload', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector, filePath } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.uploadFile(selector, filePath);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 设置视口
 */
app.post('/browser/:id/page/:pageIndex/viewport', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { width, height, deviceScaleFactor, isMobile, hasTouch } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.setViewport({
      width: width || 1280,
      height: height || 720,
      deviceScaleFactor: deviceScaleFactor || 1,
      isMobile: isMobile || false,
      hasTouch: hasTouch || false
    });

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 设置 User-Agent
 */
app.post('/browser/:id/page/:pageIndex/setua', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { userAgent } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.setUserAgent(userAgent);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取 localStorage
 */
app.post('/browser/:id/page/:pageIndex/storage/local', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const storage = await page.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage }
    }));

    res.json({ success: true, storage });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 设置 localStorage
 */
app.post('/browser/:id/page/:pageIndex/storage/local/set', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { key, value, storageType = 'local' } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.evaluate((params) => {
      const storage = params.storageType === 'session' ? sessionStorage : localStorage;
      storage.setItem(params.key, params.value);
    }, { key, value, storageType });

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 打开新标签页
 */
app.post('/browser/:id/page/new-tab', async (req, res) => {
  try {
    const { id } = req.params;
    const { url = 'about:blank' } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const page = await browser.newPage();
    if (url !== 'about:blank') {
      await page.goto(url, { waitUntil: 'networkidle2' });
    }

    const pages = await browser.pages();
    res.json({
      success: true,
      pageIndex: pages.length - 1,
      url: page.url()
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 关闭当前页
 */
app.post('/browser/:id/page/:pageIndex/close', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.close();

    const remainingPages = await browser.pages();
    res.json({
      success: true,
      remainingPages: remainingPages.length
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 切换到指定页面
 */
app.post('/browser/:id/page/:pageIndex/switch', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const targetPage = pages[parseInt(pageIndex)];

    if (!targetPage) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    res.json({
      success: true,
      url: targetPage.url(),
      title: await targetPage.title()
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 等待导航完成
 */
app.post('/browser/:id/page/:pageIndex/waitnav', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { timeout = 30000 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.waitForNavigation({ timeout });
    res.json({ success: true, url: page.url() });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 等待函数返回 true
 */
app.post('/browser/:id/page/:pageIndex/waitfn', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { script, timeout = 30000 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.waitForFunction(script, { timeout });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 等待网络空闲
 */
app.post('/browser/:id/page/:pageIndex/waitidle', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { timeout = 30000 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.waitForNetworkIdle({ timeout });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 设置 JavaScript 对话框处理
 */
app.post('/browser/:id/page/:pageIndex/dialog', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { accept = true, promptText } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    page.on('dialog', async dialog => {
      if (accept) {
        await dialog.accept(promptText || '');
      } else {
        await dialog.dismiss();
      }
    });

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取页面标题
 */
app.post('/browser/:id/page/:pageIndex/title', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const title = await page.title();
    const url = page.url();

    res.json({ success: true, title, url });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 列出所有浏览器实例
 */
app.get('/browser/list', (req, res) => {
  const list = Object.keys(browserManager).map(id => ({
    id,
    active: !browserManager[id].isClosed()
  }));
  res.json({ success: true, browsers: list });
});

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', browsersCount: Object.keys(browserManager).length });
});

app.listen(PORT, () => {
  console.log(`Puppeteer Stealth Service running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});