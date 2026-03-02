const { RPAController, OperationRecorder } = require('../puppeteer-stealth-service/skills/rpa-development/scripts/rpa-client.js');

async function doubaoQRCodeLogin() {
  const controller = new RPAController({
    host: 'localhost',
    port: 18765,
    browserId: 'doubao-login',
    debug: true
  });
  const recorder = new OperationRecorder();

  console.log('[1] 启动浏览器...');
  await controller.launch('doubao-login');
  recorder.record({ type: 'launch', browserId: 'doubao-login' });

  console.log('[2] 访问豆包首页...');
  await controller.goto('https://www.doubao.com/');
  recorder.record({ type: 'goto', url: 'https://www.doubao.com/' });

  await controller.waitIdle(3000);

  console.log('[3] 点击登录按钮...');
  await controller.click('text=登录');
  recorder.record({ type: 'click', selector: 'text=登录' });

  await controller.waitIdle(3000);

  console.log('[4] 获取二维码位置并截图...');
  // 使用 #semi-modal-body > div > div 选择器获取二维码容器位置
  let qrcodeBox = null;
  const getBoxScript = `() => {
    const el = document.querySelector("#semi-modal-body > div > div");
    if (el) {
      const b = el.getBoundingClientRect();
      return { x: Math.round(b.x), y: Math.round(b.y), width: Math.round(b.width), height: Math.round(b.height) };
    }
    return null;
  }`;

  const result = await controller.execute(getBoxScript, 'function');
  if (result && result.result) {
    qrcodeBox = typeof result.result === 'string' ? JSON.parse(result.result) : result.result;
    console.log('[INFO] 找到二维码区域:', qrcodeBox);
  }

  // 计算截图区域
  const clip = qrcodeBox ? {
    x: qrcodeBox.x,
    y: qrcodeBox.y,
    width: qrcodeBox.width,
    height: qrcodeBox.height
  } : null;

  // 直接保存截图到文件 (server侧保存)
  await controller.screenshot(false, clip, 'doubao_qrcode.png');
  console.log('[OK] 二维码已保存到 doubao_qrcode.png');

  console.log('\n========================================');
  console.log('请使用豆包APP扫码登录...');
  console.log('========================================\n');

  // 轮询检测登录状态
  let loginSuccess = false;
  let checkCount = 0;
  const maxChecks = 60;

  while (!loginSuccess && checkCount < maxChecks) {
    checkCount++;
    await controller.waitIdle(2000);

    const contentResult = await controller.getContent();
    const content = contentResult.html || '';

    // 检测二维码失效
    if (content.includes('二维码失效')) {
      console.log('[INFO] 检测到二维码失效，刷新...');
      await controller.click('text=点击刷新');
      await controller.waitIdle(2000);
      await controller.screenshot(false, clip, 'doubao_qrcode_refresh.png');
      console.log('[OK] 刷新后二维码已保存到 doubao_qrcode_refresh.png');
      continue;
    }

    // 检测登录成功标志
    if (content.includes('from_login=1') || content.includes('历史对话') || content.includes('云盘')) {
      loginSuccess = true;
      console.log('[成功] 检测到登录成功！');

      // 获取用户名: [id^="radix-"] > div > div
      const userResult = await controller.execute(
        'document.querySelector("[id^=\\"radix-\\"] > div > div")?.textContent',
        'function'
      );
      const username = userResult.result || '未知';

      // 获取头像: [id^="radix-"] > div > img
      const avatarResult = await controller.execute(
        'document.querySelector("[id^=\\"radix-\\"] > div > img")?.src',
        'function'
      );
      const avatarUrl = avatarResult.result || '';

      console.log('[INFO] 用户名:', username);
      console.log('[INFO] 头像:', avatarUrl);

      // 保存用户信息
      const userInfo = { username, avatarUrl, loginTime: new Date().toISOString() };
      require('fs').writeFileSync('doubao_user_info.json', JSON.stringify(userInfo, null, 2));
      console.log('[OK] 用户信息已保存到 doubao_user_info.json');

      await controller.screenshot(false, null, 'doubao_logged_in.png');
      console.log('[OK] 登录后截图已保存到 doubao_logged_in.png');
      break;
    }

    console.log(`[等待] 等待扫码中... (${checkCount}/${maxChecks})`);
  }

  if (!loginSuccess) {
    console.log('[超时] 扫码超时，未检测到登录成功');
  }

  console.log('[5] 关闭浏览器...');
  await controller.close();
  recorder.record({ type: 'close' });

  const script = recorder.generateScript('puppeteer');
  require('fs').writeFileSync('auto_doubao_login.js', script);
  console.log('[OK] 可复用脚本已保存到 auto_doubao_login.js');

  return loginSuccess;
}

doubaoQRCodeLogin()
  .then(success => {
    console.log('\n任务完成:', success ? '登录成功' : '登录失败');
    process.exit(success ? 0 : 1);
  })
  .catch(err => {
    console.error('[错误]', err.message);
    process.exit(1);
  });
