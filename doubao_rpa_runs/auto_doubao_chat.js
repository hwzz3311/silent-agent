/**
 * 豆包平台自动发消息并获取回复结果
 * 使用方法: node auto_doubao_chat.js
 */

const { RPAController, OperationRecorder } = require('/Users/leon_zheng/.claude/skills/rpa-development/scripts/rpa-client.js');

async function doubaoChat(message) {
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

  console.log('[2] 访问豆包聊天页面...');
  await controller.goto('https://www.doubao.com/chat/');
  recorder.record({ type: 'goto', url: 'https://www.doubao.com/chat/' });

  await controller.waitIdle(3000);

  console.log('[3] 点击输入框...');
  await controller.click('textarea, [contenteditable], [role="textbox"]');
  recorder.record({ type: 'click', selector: 'textarea, [contenteditable], [role="textbox"]' });

  console.log('[4] 输入消息:', message);
  await controller.type('textarea, [contenteditable], [role="textbox"]', message);
  recorder.record({ type: 'type', selector: 'textarea, [contenteditable], [role="textbox"]', text: message });

  console.log('[5] 发送消息...');
  await controller.keyboard('press', 'Enter');
  recorder.record({ type: 'keyboard', action: 'press', key: 'Enter' });

  // 等待回复
  console.log('[6] 等待大模型回复...');
  await controller.waitIdle(8000);

  // 获取无障碍树解析回复
  const a11y = await controller.getA11yTree();
  const elements = parseA11yResponse(a11y.a11y, message);

  console.log('\n========== 回复结果 ==========');
  console.log('用户消息:', message);
  console.log('AI回复:', elements.aiResponse);
  console.log('=====================================\n');

  // 保存结果
  const result = {
    success: true,
    message: message,
    response: elements.aiResponse,
    timestamp: new Date().toISOString(),
    chatUrl: a11y.a11y.url || ''
  };

  require('fs').writeFileSync('doubao_chat_result.json', JSON.stringify(result, null, 2));
  console.log('[OK] 结果已保存到 doubao_chat_result.json');

  // 截图保存
  await controller.screenshot(false, null, 'doubao_chat_result.png');
  console.log('[OK] 截图已保存到 doubao_chat_result.png');

  await controller.close();
  recorder.record({ type: 'close' });

  // 生成可复用脚本
  const script = recorder.generateScript('puppeteer');
  require('fs').writeFileSync('auto_doubao_chat.js', script);
  console.log('[OK] RPA脚本已生成到 auto_doubao_chat.js');

  return result;
}

// 解析无障碍树提取AI回复
function parseA11yResponse(a11yTree, userMsg) {
  const result = {
    userMessage: '',
    aiResponse: ''
  };

  const findTexts = (node) => {
    if (!node) return [];

    let texts = [];
    if (node.role === 'StaticText' && node.name) {
      texts.push(node.name);
    }

    if (node.children) {
      for (const child of node.children) {
        texts = texts.concat(findTexts(child));
      }
    }

    return texts;
  };

  const allTexts = findTexts(a11yTree);

  // 查找用户消息和AI回复
  for (let i = 0; i < allTexts.length; i++) {
    const text = allTexts[i];
    if (text.includes(userMsg)) {
      result.userMessage = text;
      // 下一条可能是AI回复
      if (i + 1 < allTexts.length) {
        const nextText = allTexts[i + 1];
        if (!nextText.includes('豆包') && nextText.length > 5) {
          result.aiResponse = nextText;
        }
      }
    }
    // 常见的AI回复特征
    if (text.includes('你好呀') || text.includes('我是豆包') || text.includes('AI 助手')) {
      result.aiResponse = text;
    }
  }

  return result;
}

// 获取命令行参数
const message = process.argv[2] || '你好，请用一句话介绍你自己';

doubaoChat(message)
  .then(result => {
    console.log('\n任务完成: 成功');
    process.exit(0);
  })
  .catch(err => {
    console.error('[错误]', err.message);
    process.exit(1);
  });
