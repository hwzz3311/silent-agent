/**
 * Data Extraction via Accessibility Tree
 * 使用无障碍树提取页面数据示例
 *
 * Usage: node examples/data-extract.js
 */

const path = require('path');
const rpaClient = require(path.join(__dirname, '../scripts/rpa-client.js'));

const { RPAController, A11yParser } = rpaClient;

const TARGET_URL = 'https://example.com/products';

async function extractData() {
  const controller = new RPAController({
    host: 'localhost',
    port: 18765,
    browserId: 'data-extract',
    debug: false
  });

  try {
    await controller.launch('data-extract');
    console.log('[Step 1] Browser launched');

    await controller.goto(TARGET_URL);
    console.log('[Step 2] Navigated to target page');

    await new Promise(r => setTimeout(r, 2000));

    // 获取无障碍树
    console.log('[Step 3] Getting accessibility tree...');
    const a11yResult = await controller.getA11yTree();
    const tree = a11yResult.a11y;

    // 解析页面结构
    const { elements, summary } = A11yParser.parse(tree);
    console.log('[Debug] Page summary:', summary);

    // 提取所有链接
    console.log('\n[Extracting] Links:');
    const links = A11yParser.find(tree, { role: 'link' });
    links.slice(0, 10).forEach((link, i) => {
      console.log(`  ${i + 1}. ${link.name} -> ${link.url || link.href || 'N/A'}`);
    });

    // 提取所有按钮
    console.log('\n[Extracting] Buttons:');
    const buttons = A11yParser.find(tree, { role: 'button' });
    buttons.forEach((btn, i) => {
      console.log(`  ${i + 1}. ${btn.name} (${btn.selector})`);
    });

    // 提取所有输入框
    console.log('\n[Extracting] Input fields:');
    const textboxes = A11yParser.find(tree, { role: 'textbox' });
    textboxes.forEach((tb, i) => {
      console.log(`  ${i + 1}. ${tb.name} (focused: ${tb.focused})`);
    });

    // 提取表格数据（如果有）
    console.log('\n[Extracting] Table:');
    const table = A11yParser.find(tree, { role: 'table' });
    if (table.length > 0) {
      const rows = A11yParser.find(tree, { role: 'row' });
      console.log(`  Found ${rows.length} rows`);
    }

    // 生成可读描述
    console.log('\n[Description]');
    const description = A11yParser.toDescription(tree);
    console.log(description.slice(0, 500) + '...');

    // 保存数据到文件
    const data = {
      url: TARGET_URL,
      timestamp: new Date().toISOString(),
      links: links.map(l => ({ name: l.name, url: l.url })),
      buttons: buttons.map(b => ({ name: b.name, selector: b.selector })),
      inputs: textboxes.map(t => ({ name: t.name, focused: t.focused }))
    };

    require('fs').writeFileSync(
      'extracted-data.json',
      JSON.stringify(data, null, 2)
    );
    console.log('\n[Success] Data saved to extracted-data.json');

  } catch (error) {
    console.error('[Error]', error.message);
  } finally {
    await controller.close();
  }
}

extractData();