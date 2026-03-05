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

  // 获取页面标题确认访问成功
  const title = await controller.getTitle();
  console.log('[INFO] 页面标题:', title);

  console.log('[3] 点击登录按钮...');
  await controller.click('text=登录');
  recorder.record({ type: 'click', selector: 'text=登录' });

  await controller.waitIdle(3000);

  console.log('[4] 获取二维码位置并截图...');
  // 使用 #semi-modal-body > div > div 选择器获取二维码容器位置
  let qrcodeBox = null;
  const getBoxScript = `
    () => {
      const el = document.querySelector("#semi-modal-body > div > div");
      if (el) {
        const b = el.getBoundingClientRect();
        return { x: Math.round(b.x), y: Math.round(b.y), width: Math.round(b.width), height: Math.round(b.height) };
      }
      return null;
    }
  `;

  try {
    const result = await controller.execute(getBoxScript, 'function');
    if (result && result.result) {
      qrcodeBox = typeof result.result === 'string' ? JSON.parse(result.result) : result.result;
      console.log('[INFO] 找到二维码区域:', qrcodeBox);
    }
  } catch (e) {
    console.log('[WARN] 获取二维码位置失败:', e.message);
  }

  // 计算截图区域
  let clip = null;
  if (qrcodeBox && qrcodeBox.x !== undefined) {
    clip = {
      x: qrcodeBox.x,
      y: qrcodeBox.y,
      width: qrcodeBox.width,
      height: qrcodeBox.height
    };
    console.log('[INFO] 使用局部截图区域:', clip);
  } else {
    console.log('[WARN] 未找到二维码元素，使用全页截图');
  }

  console.log('[5] 截图保存二维码...');
  const screenshot = await controller.screenshot(false, clip, 'doubao_qrcode.png');
  recorder.record({ type: 'screenshot', fullPage: false, clip: clip, savePath: 'doubao_qrcode.png' });
  console.log('[OK] 二维码已保存到 doubao_qrcode.png');

  console.log('\n========================================');
  console.log('请使用豆包APP扫码登录...');
  console.log('========================================\n');

  // 轮询检测登录状态
  let loginSuccess = false;
  let checkCount = 0;
  const maxChecks = 60; // 最多检查60次 (约120秒)

  while (!loginSuccess && checkCount < maxChecks) {
    checkCount++;
    await controller.waitIdle(2000);

    // 获取页面内容检测登录状态
    const contentResult = await controller.getContent();
    const content = contentResult.html || '';

    // 检查是否出现登录成功标志（URL 包含 from_login 或有用户元素）
    const isLoggedIn = content.includes('from_login=1') ||
                       content.includes('历史对话') ||
                       content.includes('云盘');

    // 检查是否显示"二维码失效"
    const isQRCodeExpired = content.includes('二维码失效');

    if (isQRCodeExpired) {
      console.log('[INFO] 检测到二维码失效，尝试刷新...');
      try {
        await controller.click('text=点击刷新');
        console.log('[OK] 已点击刷新二维码');

        // 等待刷新后重新截图
        await controller.waitIdle(2000);
        await controller.screenshot(false, clip, 'doubao_qrcode_refresh.png');
        console.log('[OK] 刷新后二维码已保存到 doubao_qrcode_refresh.png');
      } catch (e) {
        console.log('[WARN] 刷新二维码失败:', e.message);
      }
      continue;
    }

    if (isLoggedIn) {
      loginSuccess = true;
      console.log('[成功] 检测到登录成功！');

      // 获取用户名和头像
      let username = '未知';
      let avatarUrl = '';

      try {
        // 获取用户名: [id^="radix-"] > div > div
        const userResult = await controller.execute(
          "document.querySelector(\"[id^=\\\"radix-\\\"] > div > div\")?.textContent",
          'function'
        );
        username = userResult.result || '未知';
        console.log('[INFO] 用户名:', username);
      } catch (e) {
        console.log('[WARN] 获取用户名失败:', e.message);
      }

      try {
        // 获取头像: [id^="radix-"] > div > img
        const avatarResult = await controller.execute(
          "document.querySelector(\"[id^=\\\"radix-\\\"] > div > img\")?.src",
          'function'
        );
        avatarUrl = avatarResult.result || '';
        console.log('[INFO] 头像URL:', avatarUrl);
      } catch (e) {
        console.log('[WARN] 获取头像失败:', e.message);
      }

      // 保存登录后信息
      const userInfo = { username, avatarUrl, loginTime: new Date().toISOString() };
      require('fs').writeFileSync('doubao_user_info.json', JSON.stringify(userInfo, null, 2));
      console.log('[OK] 用户信息已保存到 doubao_user_info.json');

      // 保存登录后的截图
      await controller.screenshot(false, null, 'doubao_logged_in.png');
      console.log('[OK] 登录后截图已保存到 doubao_logged_in.png');

      break;
    }

    console.log(`[等待] 等待扫码中... (${checkCount}/${maxChecks})`);
  }

  if (!loginSuccess) {
    console.log('[超时] 扫码超时，未检测到登录成功');
  }

  console.log('[6] 关闭浏览器...');
  await controller.close();
  recorder.record({ type: 'close' });

  // 生成可复用脚本
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
