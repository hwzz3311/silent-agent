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

// 存储每个页面的网络请求/响应数据
// Map<listenerKey, { requests: [], responses: [], listeners: { request, response } }>
const networkData = new Map();

console.log('Initializing server...');
console.log('Browser manager:', typeof browserManager);

// 默认 Chrome 路径 (macOS)
const DEFAULT_EXECUTABLE_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

// 默认用户数据目录 (固定路径，保留登录状态)
const DEFAULT_USER_DATA_DIR = '/tmp/puppeteer-stealth-user-data';

/**
 * 启动一个新的浏览器实例
 */
app.post('/browser/launch', async (req, res) => {
  try {
    const { id, headless = true, args = [], executablePath, userDir } = req.body;
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
    };

    // 使用默认用户数据目录（保留cookies和session）
    launchOptions.userDir = DEFAULT_USER_DATA_DIR;

    // 如果提供了 userDir，使用指定的用户数据目录（覆盖默认）
    if (userDir) {
      launchOptions.userDir = userDir;
    }

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
 * 支持全页截图和局部截图
 * clip: { x, y, width, height } - 局部截图区域
 */
app.post('/browser/:id/page/:pageIndex/screenshot', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { fullPage = false, clip } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const screenshotOptions = { fullPage };
    // 支持局部截图：clip 参数指定区域
    if (clip && typeof clip === 'object') {
      screenshotOptions.clip = {
        x: clip.x || 0,
        y: clip.y || 0,
        width: clip.width || 100,
        height: clip.height || 100
      };
    }

    const buffer = await page.screenshot(screenshotOptions);
    // 确保转换为标准 Buffer 再转 base64
    const base64 = Buffer.from(buffer).toString('base64');

    res.json({
      success: true,
      format: 'png',
      data: base64,
      clip: screenshotOptions.clip || null
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
 * 获取元素边界框 (boundingBox)
 * 返回元素的位置和尺寸信息
 */
app.post('/browser/:id/page/:pageIndex/element/bounding-box', async (req, res) => {
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

    if (!selector) {
      return res.status(400).json({ success: false, error: 'selector is required' });
    }

    const box = await page.evaluate(async (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;

      const box = el.getBoundingClientRect();
      return {
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        top: box.top,
        right: box.right,
        bottom: box.bottom,
        left: box.left
      };
    }, selector);

    if (!box) {
      return res.status(404).json({ success: false, error: 'Element not found' });
    }

    res.json({ success: true, boundingBox: box });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取元素的盒模型 (boxModel)
 * 返回 content, padding, border, margin 的详细信息
 */
app.post('/browser/:id/page/:pageIndex/element/box-model', async (req, res) => {
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

    if (!selector) {
      return res.status(400).json({ success: false, error: 'selector is required' });
    }

    // 使用 Puppeteer 的 boxModel 方法
    const elementHandle = await page.$(selector);
    if (!elementHandle) {
      return res.status(404).json({ success: false, error: 'Element not found' });
    }

    const boxModel = await elementHandle.boxModel();
    await elementHandle.dispose();

    if (!boxModel) {
      return res.status(404).json({ success: false, error: 'Cannot get box model' });
    }

    res.json({
      success: true,
      boxModel: {
        content: boxModel.content,    // content 区域
        padding: boxModel.padding,    // padding 区域
        border: boxModel.border,      // border 区域
        margin: boxModel.margin       // margin 区域
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取元素在视口中的可见性
 */
app.post('/browser/:id/page/:pageIndex/element/visibility', async (req, res) => {
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

    if (!selector) {
      return res.status(400).json({ success: false, error: 'selector is required' });
    }

    const visibility = await page.evaluate(async (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;

      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();

      return {
        // 可见性状态
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity,
        // 尺寸
        width: style.width,
        height: style.height,
        // 位置
        offsetTop: el.offsetTop,
        offsetLeft: el.offsetLeft,
        offsetWidth: el.offsetWidth,
        offsetHeight: el.offsetHeight,
        // 是否在视口内
        isInViewport: (
          rect.top >= 0 &&
          rect.left >= 0 &&
          rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
          rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        )
      };
    }, selector);

    if (!visibility) {
      return res.status(404).json({ success: false, error: 'Element not found' });
    }

    res.json({ success: true, visibility });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 查找元素并返回其位置（可链式查找）
 * 用于查找动态生成的元素或列表中特定元素
 */
app.post('/browser/:id/page/:pageIndex/element/find', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { selector, index = 0 } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    if (!selector) {
      return res.status(400).json({ success: false, error: 'selector is required' });
    }

    const result = await page.evaluate(async (sel, idx) => {
      const elements = document.querySelectorAll(sel);
      if (!elements || elements.length === 0) return null;

      const el = elements[idx] || elements[0];
      const box = el.getBoundingClientRect();

      return {
        found: true,
        index: idx,
        totalCount: elements.length,
        boundingBox: {
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height
        },
        // 基本属性
        tagName: el.tagName,
        id: el.id,
        className: el.className,
        text: el.textContent?.trim().substring(0, 100)
      };
    }, selector, parseInt(index));

    if (!result) {
      return res.status(404).json({ success: false, error: 'Element not found' });
    }

    res.json({ success: true, ...result });
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

// ============================================
// 网络请求监听与响应拦截
// ============================================

/**
 * 启用网络请求监听
 * 监听指定页面的所有请求/响应
 */
app.post('/browser/:id/page/:pageIndex/network/listen', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { includeUrl, excludeUrl, type } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const listenerKey = `${id}_${pageIndex}`;
    const requests = [];
    const responses = [];

    // 请求监听器
    const requestListener = req => {
      if (includeUrl && !req.url().includes(includeUrl)) return;
      if (excludeUrl && req.url().includes(excludeUrl)) return;

      requests.push({
        url: req.url(),
        method: req.method(),
        headers: req.headers(),
        postData: req.postData(),
        resourceType: req.resourceType(),
        timestamp: Date.now()
      });
    };

    // 响应监听器
    const responseListener = res => {
      if (includeUrl && !res.url().includes(includeUrl)) return;
      if (excludeUrl && res.url().includes(excludeUrl)) return;

      responses.push({
        url: res.url(),
        status: res.status(),
        statusText: res.statusText(),
        headers: res.headers(),
        timestamp: Date.now()
      });
    };

    // 清理旧的监听器
    const existing = networkData.get(listenerKey);
    if (existing && existing.listeners) {
      page.off('request', existing.listeners.request);
      page.off('response', existing.listeners.response);
    }

    // 设置新监听器
    page.on('request', requestListener);
    page.on('response', responseListener);

    // 存储监听器和数据
    networkData.set(listenerKey, {
      requests,
      responses,
      listeners: { request: requestListener, response: responseListener },
      filter: { includeUrl, excludeUrl, type }
    });

    res.json({
      success: true,
      message: 'Network listener enabled',
      filter: { includeUrl, excludeUrl, type },
      captured: { requestCount: 0, responseCount: 0 }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取捕获的网络请求/响应
 */
app.post('/browser/:id/page/:pageIndex/network/captured', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { clear = false } = req.body;

    const listenerKey = `${id}_${pageIndex}`;
    const data = networkData.get(listenerKey);

    if (!data) {
      return res.json({
        success: true,
        requests: [],
        responses: [],
        message: 'No network listener active'
      });
    }

    const result = {
      success: true,
      requestCount: data.requests.length,
      responseCount: data.responses.length,
      requests: [...data.requests],
      responses: [...data.responses]
    };

    // 可选清除数据
    if (clear) {
      data.requests = [];
      data.responses = [];
    }

    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 启用请求拦截并可修改响应
 */
app.post('/browser/:id/page/:pageIndex/network/intercept', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { urlPattern, responseStatus, responseBody, responseHeaders } = req.body;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    await page.setRequestInterception(true);

    page.on('request', async req => {
      if (urlPattern && req.url().includes(urlPattern)) {
        // 拦截并返回自定义响应
        await req.respond({
          status: responseStatus || 200,
          contentType: 'application/json',
          headers: responseHeaders || {},
          body: responseBody || '{}'
        });
      } else {
        await req.continue();
      }
    });

    res.json({
      success: true,
      message: 'Request interception enabled',
      pattern: urlPattern,
      mock: { status: responseStatus, body: responseBody }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 停止网络拦截
 */
app.post('/browser/:id/page/:pageIndex/network/disable', async (req, res) => {
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

    await page.setRequestInterception(false);

    // 清理监听器
    const listenerKey = `${id}_${pageIndex}`;
    const data = networkData.get(listenerKey);
    if (data && data.listeners) {
      page.off('request', data.listeners.request);
      page.off('response', data.listeners.response);
      networkData.delete(listenerKey);
    }

    res.json({ success: true, message: 'Network interception disabled' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * 获取网络日志（需要先启用监听）
 */
app.get('/browser/:id/page/:pageIndex/network/log', async (req, res) => {
  try {
    const { id, pageIndex } = req.params;
    const { clear } = req.query;

    const browser = browserManager[id];
    if (!browser) {
      return res.status(404).json({ success: false, error: 'Browser not found' });
    }

    const pages = await browser.pages();
    const page = pages[parseInt(pageIndex)];

    if (!page) {
      return res.status(404).json({ success: false, error: 'Page not found' });
    }

    const listenerKey = `${id}_${pageIndex}`;
    const data = networkData.get(listenerKey);

    const result = {
      success: true,
      currentUrl: page.url(),
      requestCount: data?.requests?.length || 0,
      responseCount: data?.responses?.length || 0,
      requests: data?.requests || [],
      responses: data?.responses || []
    };

    // 可选清除数据
    if (clear === 'true' && data) {
      data.requests = [];
      data.responses = [];
    }

    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', browsersCount: Object.keys(browserManager).length });
});

app.listen(PORT, () => {
  console.log(`Puppeteer Stealth Service running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});