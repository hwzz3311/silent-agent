/**
 * Login Flow Automation Example
 * 自动登录流程示例
 *
 * Usage: node examples/login-flow.js
 */

const path = require('path');
const rpaClient = require(path.join(__dirname, '../scripts/rpa-client.js'));

const { RPAController, A11yParser } = rpaClient;

// 配置登录信息
const LOGIN_CONFIG = {
  url: 'https://example.com/login',
  username: 'testuser@example.com',
  password: 'testpassword'
};

async function loginFlow() {
  const controller = new RPAController({
    host: 'localhost',
    port: 18765,
    browserId: 'auto-login',
    debug: true
  });

  try {
    // 启动浏览器
    console.log('[Step 1] Launching browser...');
    await controller.launch('auto-login');

    // 访问登录页面
    console.log('[Step 2] Navigating to login page...');
    await controller.goto(LOGIN_CONFIG.url);

    // 等待页面加载
    await new Promise(r => setTimeout(r, 2000));

    // 获取无障碍树，分析页面结构
    console.log('[Step 3] Analyzing page structure...');
    const a11yResult = await controller.getA11yTree();

    // 查找输入框和按钮
    const inputs = A11yParser.find(a11yResult.a11y, { role: 'textbox' });
    const buttons = A11yParser.find(a11yResult.a11y, { role: 'button' });

    console.log('[Debug] Found inputs fields:', inputs.length);
    console.log('[Debug] Found buttons:', button.length);

    // 输入用户名（假设第一个 textbox 是用户名）
    if (inputs.length > 0) {
      console.log('[Step 4] Typing username...');
      await controller.type(inputs[0].selector, LOGIN_CONFIG.username);
    }

    // 输入密码（假设第二个 textbox 是密码）
    if (inputs.length > 1) {
      console.log('[Step 5] Typing password...');
      await controller.type(inputs[1].selector, LOGIN_CONFIG.password);
    }

    // 点击登录按钮
    if (buttons.length > 0) {
      console.log('[Step 6] Clicking login button...');
      await controller.click(buttons[0].selector);
    }

    // 等待页面跳转
    console.log('[Step 7] Waiting for redirect...');
    await new Promise(r => setTimeout(r, 3000));

    // 验证登录成功
    const afterLogin = await controller.getA11yTree();
    console.log('[Success] Login flow completed');

    // 保存登录后页面截图
    const screenshot = await controller.screenshot(true);
    const buffer = Buffer.from(screenshot.data, 'base64');
    require('fs').writeFileSync('login-success.png', buffer);

  } catch (error) {
    console.error('[Error]', error.message);

    // 失败时保存截图用于调试
    const screenshot = await controller.screenshot(true);
    const buffer = Buffer.from(screenshot.data, 'base64');
    require('fs').writeFileSync('login-error.png', buffer);
  } finally {
    await controller.close();
  }
}

loginFlow();