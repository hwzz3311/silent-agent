#!/usr/bin/env node
/**
 * RPA CLI - 交互式 RPA 开发工具
 * 使用方法: node rpa-cli.js
 */

const readline = require('readline');
const { RPAController, A11yParser, ScriptGenerator, RPAAgent } = require('./rpa-client');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const controller = new RPAController({ debug: true });
const agent = new RPAAgent(controller);

let browserLaunched = false;

// 显示帮助
function showHelp() {
  console.log(`
╔══════════════════════════════════════════════════════════╗
║           RPA 开发工具 - 命令列表                  ║
╠══════════════════════════════════════════════════════════╣
║ 浏览器:                                                   ║
║   launch      启动浏览器                                ║
║   close      关闭浏览器                                 ║
║                                                           ║
║ 页面操作:                                                ║
║   goto <url>  访问页面                                  ║
║   a11y       获取无障碍树                               ║
║   click <s>  点击元素 (CSS selector)                   ║
║   type <s> <t>  输入文本                                 ║
║   wait <s>   等待元素出现                               ║
║   scroll    滚动页面                                    ║
║   screenshot 截图                                        ║
║   content   获取 HTML                                   ║
║                                                           ║
║ AI Agent:                                                ║
║   ask <问题>  AI 自动执行操作                           ║
║   agent <指令>  大模型驱动的自动化                    ║
║                                                           ║
║ 脚本生成:                                                ║
║   script     显示操作脚本                               ║
║   export pw  导出 Playwright 脚本                       ║
║   export pp  导出 Puppeteer 脚本                        ║
║                                                           ║
║ 工具:                                                    ║
║   history   显示操作历史                                ║
║   find <role>  按 role 查找元素                         ║
║   find <text>  按 text 查找元素                         ║
║   health    健康检查                                    ║
║   help      显示帮助                                    ║
║   quit      退出                                         ║
╚══════════════════════════════════════════════════════════╝
  `);
}

// 解析命令
async function parseCommand(line) {
  const parts = line.trim().split(/\s+/);
  const cmd = parts[0].toLowerCase();
  const args = parts.slice(1);

  try {
    switch (cmd) {
      // 浏览器
      case 'launch':
      case 'open':
        if (!browserLaunched) {
          const result = await controller.launch();
          if (result.success) {
            console.log('✓ 浏览器已启动');
            browserLaunched = true;
          } else {
            console.log('✗ 启动失败:', result.error);
          }
        } else {
          console.log('浏览器已启动');
        }
        break;

      case 'close':
      case 'quit-browser':
        if (browserLaunched) {
          await controller.close();
          console.log('✓ 浏览器已关闭');
          browserLaunched = false;
        }
        break;

      // 页面操作
      case 'goto':
      case 'visit':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const url = args.join(' ') || 'https://www.baidu.com';
        const gotoResult = await controller.goto(url);
        console.log(`✓ 访问 ${url}, 状态: ${gotoResult.status}`);
        break;

      case 'a11y':
      case 'tree':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const a11y = await controller.getA11yTree();
        if (a11y.success) {
          const desc = A11yParser.toDescription(a11y.a11y);
          console.log(desc);
        }
        break;

      case 'click':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const selector = args.join(' ');
        await controller.click(selector);
        console.log(`✓ 点击: ${selector}`);
        break;

      case 'type':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const typeSel = args[0];
        const typeText = args.slice(1).join(' ');
        await controller.type(typeSel, typeText);
        console.log(`✓ 输入: ${typeSel} <- "${typeText}"`);
        break;

      case 'wait':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        await controller.wait(args[0]);
        console.log(`✓ 等待: ${args[0]}`);
        break;

      case 'scroll':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        await controller.scroll(500);
        console.log('✓ 已滚动');
        break;

      case 'screenshot':
      case 'shot':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        await controller.screenshot();
        console.log('✓ 截图已保存');
        break;

      case 'content':
      case 'html':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const content = await controller.getContent();
        console.log(content.html?.substring(0, 500) || '无内容');
        break;

      // AI Agent
      case 'ask':
      case 'agent':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const instruction = args.join(' ');
        console.log('🤖 正在执行:', instruction);
        const result = await agent.execute(instruction);
        if (result.error) {
          console.log('✗ 错误:', result.error);
        } else {
          console.log('✓ 执行完成, 操作数:', result.operations?.length || 0);
        }
        break;

      // 脚本生成
      case 'script':
      case 'ops':
        const log = agent.getOperationLog();
        console.log(`操作历史 (${log.length} 个):`);
        log.forEach((op, i) => console.log(`  ${i + 1}. ${op.type}:`, op));
        break;

      case 'export':
        const format = args[0] || 'pw';
        const script = agent.generateScript(format.startsWith('pw') ? 'playwright' : 'puppeteer');
        console.log('\n' + script);
        break;

      // 工具
      case 'find':
        if (!browserLaunched) {
          console.log('请先启动浏览器: launch');
          return;
        }
        const a11yResult = await controller.getA11yTree();
        const findStr = args.join(' ');
        const isRole = ['link', 'button', 'textbox', 'input'].includes(findStr);

        const found = A11yParser.find(a11yResult.a11y, {
          role: isRole ? findStr : undefined,
          name: !isRole ? findStr : undefined
        });

        console.log(`找到 ${found.length} 个元素:`);
        found.slice(0, 20).forEach((el, i) => {
          console.log(`  ${i + 1}. [${el.role}] ${el.name}`);
        });
        break;

      case 'history':
        const hist = controller.getHistory();
        console.log(`对话历史 (${hist.length} 条):`);
        hist.forEach(h => console.log(`  ${h.role}: ${h.content.substring(0, 50)}`));
        break;

      case 'health':
        const health = await controller.health();
        console.log(health);
        break;

      case 'help':
      case '?':
        showHelp();
        break;

      case 'quit':
      case 'exit':
        if (browserLaunched) {
          await controller.close();
        }
        process.exit(0);

      default:
        console.log(`未知命令: ${cmd}, 输入 help 查看帮助`);
    }
  } catch (e) {
    console.log('✗ 错误:', e.message);
  }

  prompt();
}

// 显示提示符
function prompt() {
  rl.prompt();
}

// 主入口
async function main() {
  console.log(`
╔══════════════════════════════════════════════════════════╗
║           欢迎使用 RPA 开发工具                      ║
║  连接: ${controller.host}:${controller.port}                   ║
║  输入 help 查看命令                                    ║
╚══════════════════════════════════════════════════════════╝
  `);

  // 自动启动浏览器
  await controller.launch('cli-browser');
  browserLaunched = true;
  console.log('✓ 浏览器已自动启动\n');

  rl.on('line', parseCommand);
  prompt();
}

main();