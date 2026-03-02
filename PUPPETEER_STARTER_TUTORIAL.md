# Python 启动 Node.js Puppeteer 浏览器指南

本教程介绍如何使用 Python 启动 Node.js 运行的 Puppeteer 浏览器，并启用 puppeteer-extra-plugin-stealth 反检测功能。

## 目录结构

```
project/
├── start_browser.js    # Node.js 启动脚本
├── start_puppeteer.py  # Python 启动脚本
├── package.json        # Node.js 依赖
└── .chrome-data/      # Chrome 配置目录（自动创建）
```

## 1. 安装依赖

### Node.js 依赖

```bash
npm init -y
npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth
```

### Python 依赖

```bash
pip install asyncio subprocess
# 项目自带，无需额外安装
```

## 2. Node.js 启动脚本 (start_browser.js)

```javascript
#!/usr/bin/env node

const path = require('path');
const fs = require('fs');
const puppeteer = require('puppeteer-extra');
const Stealth = require('puppeteer-extra-plugin-stealth');

// 启用 stealth 插件
puppeteer.use(Stealth());

// 配置
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'; // macOS
// const CHROME_PATH = '/usr/bin/google-chrome';  // Linux
// const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';  // Windows

const PROFILE_DIR = path.join(__dirname, '.chrome-data');
if (!fs.existsSync(PROFILE_DIR)) {
    fs.mkdirSync(PROFILE_DIR, { recursive: true });
}

const headless = process.argv.includes('--headless');

async function main() {
    console.log('启动浏览器 (Stealth 模式)...');

    const browser = await puppeteer.launch({
        headless: headless,
        executablePath: CHROME_PATH,
        userDataDir: PROFILE_DIR,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
        ],
        defaultViewport: { width: 1280, height: 800 },
        ignoreDefaultArgs: ['--enable-automation'],
    });

    console.log('浏览器已启动');

    // 验证 stealth
    const page = await browser.newPage();
    const webdriver = await page.evaluate(() => navigator.webdriver);
    console.log('Stealth 验证 - navigator.webdriver:', webdriver);

    // 访问测试网站
    await page.goto('https://bot.incolore.com');
    console.log('页面标题:', await page.title());

    // 保持浏览器运行
    console.log('按 Ctrl+C 停止...');
    await new Promise(() => {});
}

main().catch(console.error);
```

## 3. Python 启动脚本 (start_puppeteer.py)

```python
#!/usr/bin/env python3
"""
Python 启动 Node.js Puppeteer 浏览器
"""

import subprocess
import sys
import os
import asyncio
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(PROJECT_ROOT, "start_browser.js")

def start_puppeteer(headless: bool = False):
    """启动 Puppeteer 浏览器"""

    # 构建命令
    cmd = ["node", NODE_SCRIPT]
    if headless:
        cmd.append("--headless")

    # 启动 Node.js 进程
    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    print(f"Puppeteer 已启动 (PID: {process.pid})")

    # 实时输出日志
    for line in process.stdout:
        print(line, end='')

    return process

def main():
    headless = "--headless" in sys.argv
    process = start_puppeteer(headless)

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n停止浏览器...")
        process.terminate()

if __name__ == "__main__":
    main()
```

## 4. 使用方式

```bash
# 安装依赖
npm install
# 或
npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth

# 启动浏览器（非无头模式）
python start_puppeteer.py

# 启动浏览器（无头模式）
python start_puppeteer.py --headless

# 或直接使用 Node.js
node start_browser.js
node start_browser.js --headless
```

## 5. 各平台 Chrome 路径

| 平台 | 路径 |
|------|------|
| macOS | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| Linux | `/usr/bin/google-chrome` 或 `/usr/bin/chromium` |
| Windows | `C:\Program Files\Google\Chrome\Application\chrome.exe` |

## 6. 常见问题

### Q: Chrome 找不到

**解决**: 修改脚本中的 `CHROME_PATH` 为实际路径

### Q: 端口被占用

**解决**: 关闭占用 9222 端口的进程
```bash
# macOS/Linux
lsof -ti:9222 | xargs kill

# Windows
netstat -ano | findstr :9222
taskkill /PID <pid>
```

### Q: Stealth 不生效

**解决**: 确保使用 `puppeteer.launch()` 而非 `puppeteer.connect()`

### Q: 扩展无法加载

**解决**: 在 args 中添加扩展路径
```javascript
args: [
    `--load-extension=${path.join(__dirname, 'extension')}`,
    '--no-sandbox',
]
```

## 7. 进阶：Stealth 插件功能

`puppeteer-extra-plugin-stealth` 自动处理以下反检测：

- `navigator.webdriver` → `undefined`
- `navigator.plugins` → 真实插件列表
- `navigator.languages` → 真实语言设置
- `window.chrome.runtime` → 正常扩展对象
- Canvas 指纹随机化
- AudioContext 指纹随机化
- 自动化相关 CSS 隐藏

## 8. Python 与 Node.js 通信（可选）

如需 Python 控制浏览器，可通过以下方式：

### 方式 A: 通过 API

Node.js 启动简易 HTTP 服务，Python 通过 HTTP 请求交互

### 方式 B: 通过文件

Node.js 写状态到文件，Python 读取

### 方式 C: 通过子进程

Python 启动 Node.js 脚本，通过 stdin/stdout JSON 通信
