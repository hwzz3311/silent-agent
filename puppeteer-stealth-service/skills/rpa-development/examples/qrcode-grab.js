/**
 * QR Code Grab Example
 * 从网站获取二维码图片
 *
 * Usage: node examples/qrcode-grab.js
 */

const path = require('path');
const rpaClient = require(path.join(__dirname, '../scripts/rpa-client.js'));

const { RPAController, A11yParser } = rpaClient;

async function main() {
  const controller = new RPAController({
    host: 'localhost',
    port: 18765,
    browserId: 'qrcode-bot',
    debug: true
  });

  try {
    // 启动浏览器
    console.log('[Step 1] Launching browser...');
    await controller.launch('qrcode-bot');

    // 访问目标网站
    console.log('[Step 2] Navigating to target page...');
    await controller.goto('https://tongyi.aliyun.com/');

    // 等待页面加载
    console.log('[Step 3] Waiting for page load...');
    await new Promise(r => setTimeout(r, 3000));

    // 打印页面结构（调试用）
    const a11yResult = await controller.getA11yTree();
    const { summary } = A11yParser.parse(a11yResult.a11y);
    console.log('[Debug] Page summary:', summary);

    // 截图
    console.log('[Step 4] Taking screenshot...');
    const screenshot = await controller.screenshot(false);

    // 保存图片
    const buffer = Buffer.from(screenshot.data, 'base64');
    const fs = require('fs');
    fs.writeFileSync('qrcode.png', buffer);
    console.log('[Success] QR code saved to qrcode.png');

  } catch (error) {
    console.error('[Error]', error.message);
  } finally {
    // 关闭浏览器
    console.log('[Cleanup] Closing browser...');
    await controller.close();
  }
}

main();