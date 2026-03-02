#!/usr/bin/env node
/**
 * Puppeteer 启动脚本 - 使用 puppeteer-extra-plugin-stealth 启动浏览器
 */

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const puppeteer = require('puppeteer-extra');
const Stealth = require('puppeteer-extra-plugin-stealth');

// 启用 stealth 插件
puppeteer.use(Stealth());

// 配置
const PROJECT_ROOT = path.join(__dirname);
const EXTENSION_PATH = path.join(PROJECT_ROOT, 'extension');
const KEY_FILE = path.join(PROJECT_ROOT, '.extension_key');
const WS_ENDPOINT_FILE = path.join(PROJECT_ROOT, '.ws_endpoint');
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

// 固定 profile 目录
const PROFILE_DIR = path.join(PROJECT_ROOT, '.chrome-data');
if (!fs.existsSync(PROFILE_DIR)) {
    fs.mkdirSync(PROFILE_DIR, { recursive: true });
}

const headless = process.argv.includes('--headless');

console.log('='.repeat(50));
console.log('Puppeteer 启动脚本 (Stealth 版)');
console.log('='.repeat(50));
console.log('  headless:', headless);
console.log('  extension:', EXTENSION_PATH);
console.log('  profile:', PROFILE_DIR);
console.log('  stealth: enabled');
console.log('='.repeat(50));

async function main() {
    const extPath = path.resolve(EXTENSION_PATH);
    console.log('扩展路径:', extPath);

    // 检查是否有 Chrome 正在运行先关闭
    console.log('检查已有 Chrome 进程...');
    try {
        const { execSync } = require('child_process');
        // 查找占用 9222 端口的进程
        const lsof = execSync('lsof -ti:9222').toString().trim();
        if (lsof) {
            console.log('  关闭占用 9222 端口的进程:', lsof);
            execSync(`kill ${lsof}`);
            await new Promise(r => setTimeout(r, 2000));
        }
    } catch (e) {
        // 没有进程占用，正常
    }

    // 使用 puppeteer-extra-plugin-stealth 启动浏览器
    console.log('启动浏览器 (Stealth 模式)...');
    let browser;
    try {
        browser = await puppeteer.launch({
            headless: headless,
            executablePath: CHROME_PATH,
            userDataDir: PROFILE_DIR,
            args: [
                `--load-extension=${extPath}`,
                '--disable-extensions-accessible-urls',
                headless ? '--no-sandbox' : '',
            ].filter(Boolean),
            defaultViewport: null,
            ignoreDefaultArgs: ['--enable-automation'],
        });
        console.log('浏览器已启动 (Stealth 已启用)');

        // 输出 WebSocket 端点供 Hybrid 模式连接
        console.log('\n[WS_ENDPOINT]', browser.wsEndpoint());

        // 写入 WebSocket 端点到文件供 Hybrid 模式使用
        fs.writeFileSync(WS_ENDPOINT_FILE, browser.wsEndpoint());

        // 检查所有 target
        const targets = await browser.targets();
        console.log('\n所有 Target:');
        for (const t of targets) {
            console.log('  [' + t.type() + '] ' + t.url());
        }

        // 检查是否有扩展
        const extTarget = targets.find(t => t.type() === 'background_page' || t.type() === 'service_worker');
        if (extTarget) {
            console.log('\n扩展已加载:', extTarget.url());
        } else {
            console.log('\n警告: 未检测到扩展');
        }

        // 验证 stealth 是否生效
        const pages = await browser.pages();
        if (pages.length > 0) {
            const webdriver = await pages[0].evaluate(() => navigator.webdriver);
            console.log('\nStealth 验证 - navigator.webdriver:', webdriver);
        }

    } catch (e) {
        console.log('启动失败:', e.message);
        console.error(e);
    }

    // 等待扩展密钥文件
    console.log('\n等待扩展密钥...');
    let count = 0;
    while (true) {
        await new Promise(r => setTimeout(r, 1000));
        count++;

        if (fs.existsSync(KEY_FILE)) {
            try {
                const key = fs.readFileSync(KEY_FILE, 'utf8').trim();
                if (key) {
                    console.log('已获取密钥:', key.substring(0, 20) + '...');
                    break;
                }
            } catch (e) {}
        }

        if (count % 5 === 0) {
            console.log('  等待中... (' + count + 's)');
        }

        if (count > 60) {
            console.log('超时，扩展可能未连接');
            break;
        }
    }

    if (browser) {
        // 保持浏览器运行
        console.log('\n浏览器运行中，按 Ctrl+C 停止');
        while (true) {
            await new Promise(r => setTimeout(r, 1000));
        }
    }
}

main().catch(console.error);
