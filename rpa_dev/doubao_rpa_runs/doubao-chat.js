const { RPAController, OperationRecorder } = require('../../puppeteer-stealth-service/skills/rpa-development/scripts/rpa-client.js');

async function doubaoChat() {
  const controller = new RPAController({
    host: 'localhost',
    port: 18765,
    browserId: 'doubao-chat',
    debug: true
  });
  const recorder = new OperationRecorder();

  console.log('[1] 启动浏览器...');
  await controller.launch('doubao-chat');
  recorder.record({ type: 'launch', browserId: 'doubao-chat' });

  console.log('[2] 访问豆包首页...');
  await controller.goto('https://www.doubao.com/');
  recorder.record({ type: 'goto', url: 'https://www.doubao.com/' });

  await controller.waitIdle(3000);

  console.log('[3] 检查登录状态...');
  let loginSuccess = false;

  // 轮询检测登录状态，最多30次
  for (let i = 0; i < 30; i++) {
    const contentResult = await controller.getContent();
    const content = contentResult.html || '';

    if (content.includes('from_login=1') || content.includes('历史对话') || content.includes('云盘')) {
      loginSuccess = true;
      console.log('[成功] 检测到已登录！');
      break;
    }

    console.log(`[等待] 等待登录中... (${i + 1}/30)`);
    await controller.waitIdle(2000);
  }

  if (!loginSuccess) {
    console.log('[提示] 未检测到登录，开始扫码登录流程...');

    console.log('[4] 点击登录按钮...');
    await controller.click('text=登录');
    recorder.record({ type: 'click', selector: 'text=登录' });

    await controller.waitIdle(3000);

    // 获取二维码位置并截图
    const getBoxScript = `() => {
      const el = document.querySelector("#semi-modal-body > div > div");
      if (el) {
        const b = el.getBoundingClientRect();
        return { x: Math.round(b.x), y: Math.round(b.y), width: Math.round(b.width), height: Math.round(b.height) };
      }
      return null;
    }`;

    const result = await controller.execute(getBoxScript, 'function');
    const qrcodeBox = result?.result ? JSON.parse(result.result) : null;

    const clip = qrcodeBox ? {
      x: qrcodeBox.x,
      y: qrcodeBox.y,
      width: qrcodeBox.width,
      height: qrcodeBox.height
    } : null;

    await controller.screenshot(false, clip, 'doubao_qrcode.png');
    console.log('[OK] 二维码已保存到 doubao_qrcode.png');

    console.log('\n========================================');
    console.log('请使用豆包APP扫码登录...');
    console.log('========================================\n');

    // 轮询检测登录状态
    for (let i = 0; i < 60; i++) {
      await controller.waitIdle(2000);

      const contentResult = await controller.getContent();
      const content = contentResult.html || '';

      if (content.includes('二维码失效')) {
        console.log('[INFO] 检测到二维码失效，刷新...');
        await controller.click('text=点击刷新');
        await controller.waitIdle(2000);
        continue;
      }

      if (content.includes('from_login=1') || content.includes('历史对话') || content.includes('云盘')) {
        loginSuccess = true;
        console.log('[成功] 检测到登录成功！');
        break;
      }

      console.log(`[等待] 等待扫码中... (${i + 1}/60)`);
    }
  }

  if (!loginSuccess) {
    console.log('[失败] 登录超时');
    await controller.close();
    process.exit(1);
  }

  // ===== 已登录，现在发消息 =====
  console.log('[5] 输入消息...');

  // 查找输入框 - 使用text=发送消息 作为备选，或者直接找textarea
  await controller.waitIdle(2000);

  // 获取页面无障碍树看看结构
  const a11y = await controller.getA11yTree();
  console.log('[DEBUG] 页面结构:', JSON.stringify(a11y.a11y, null, 2).substring(0, 500));

  // 直接在输入框输入消息
  const testMessage = '你好，请用一句话介绍你自己';
  await controller.type('#chat-input', testMessage);
  recorder.record({ type: 'type', selector: '#chat-input', text: testMessage });

  await controller.waitIdle(1000);

  console.log('[6] 点击发送按钮...');
  await controller.click('text=发送');
  recorder.record({ type: 'click', selector: 'text=发送' });

  console.log('[7] 等待回复...');
  await controller.waitIdle(5000);

  // 截图保存
  await controller.screenshot(false, null, 'doubao_response.png');
  console.log('[OK] 对话截图已保存到 doubao_response.png');

  // 获取回复内容 - 通过执行脚本获取最新回复
  const getResponseScript = `() => {
    // 尝试多种选择器获取回复内容
    const selectors = [
      '.message-content',
      '.chat-message',
      '[class*="message"]',
      '[class*="response"]'
    ];

    for (const sel of selectors) {
      const els = document.querySelectorAll(sel);
      if (els.length > 0) {
        return Array.from(els).map(el => el.textContent).join('\\n');
      }
    }

    // 如果没找到，返回整个body文本
    return document.body.innerText.substring(0, 2000);
  }`;

  const responseResult = await controller.execute(getResponseScript, 'function');
  console.log('[回复内容]:', responseResult.result);

  // 保存回复到文件
  const responseData = {
    message: testMessage,
    response: responseResult.result,
    timestamp: new Date().toISOString()
  };
  require('fs').writeFileSync('doubao_chat_result.json', JSON.stringify(responseData, null, 2));
  console.log('[OK] 对话结果已保存到 doubao_chat_result.json');

  console.log('[8] 关闭浏览器...');
  await controller.close();
  recorder.record({ type: 'close' });

  const script = recorder.generateScript('puppeteer');
  require('fs').writeFileSync('auto_doubao_chat.js', script);
  console.log('[OK] 可复用脚本已保存到 auto_doubao_chat.js');

  return true;
}

doubaoChat()
  .then(success => {
    console.log('\n任务完成:', success ? '成功' : '失败');
    process.exit(success ? 0 : 1);
  })
  .catch(err => {
    console.error('[错误]', err.message);
    process.exit(1);
  });
