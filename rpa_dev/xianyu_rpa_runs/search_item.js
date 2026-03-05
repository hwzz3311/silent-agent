/**
 * 闲鱼搜索商品 RPA 脚本
 * 功能：搜索关键词并获取搜索结果，支持翻页
 *
 * 使用方法:
 *   node search_item.js [页数]
 *   例如: node search_item.js 3  # 获取3页数据
 *
 * 默认: 1 页
 */

const { RPAController, OperationRecorder } = require("/Users/leon_zheng/.claude/skills/rpa-development/scripts/rpa-client.js");
const fs = require("fs");

const CONFIG = {
  browserId: "xianyu-publish",
  host: "localhost",
  port: 18765,
  // 用户数据目录，用于保持登录状态
  userDataDir: "/tmp/puppeteer-stealth-user-data",
  // 搜索关键词
  keyword: "爱奇艺",
  // 获取页数
  pages: parseInt(process.argv[2]) || 1,
  // 每页商品数
  itemsPerPage: 30
};

async function searchItem() {
  const controller = new RPAController({
    host: CONFIG.host,
    port: CONFIG.port,
    browserId: CONFIG.browserId,
    debug: true
  });

  const recorder = new OperationRecorder();

  try {
    console.log(`[1] 连接已有浏览器 (xianyu-publish)...`);

    const launchResult = await controller._request("POST", `/browser/launch`, {
      id: CONFIG.browserId,
      headless: false,
      userDir: CONFIG.userDataDir
    });

    if (!launchResult.success) {
      console.log("[INFO] 浏览器可能已存在，继续...");
    }

    recorder.record({ type: "launch", browserId: CONFIG.browserId, userDataDir: CONFIG.userDataDir });
    await controller.waitIdle(2000);

    // 确保在搜索结果页面
    const titleResult = await controller.getTitle();
    console.log(`[INFO] 当前页面: ${titleResult.url}`);

    // 如果不在搜索结果页，执行搜索
    if (!titleResult.url?.includes('/search')) {
      console.log(`[2] 搜索关键词: ${CONFIG.keyword}`);
      await controller.click("input.search-input--WY2l9QD3");
      await controller.type("input.search-input--WY2l9QD3", CONFIG.keyword);
      await controller.click("button.search-icon--bewLHteU");
      await controller.waitIdle(3000);
    }

    const allResults = [];

    for (let page = 1; page <= CONFIG.pages; page++) {
      console.log(`\n[3] 获取第 ${page} 页数据...`);

      // 等待页面加载
      await controller.waitIdle(2000);

      // 滚动加载更多内容
      await controller.execute("window.scrollBy(0, 1000)", "function");
      await controller.waitIdle(1000);

      // 提取完整的商品信息
      const extractScript = `(function(){
        var links = document.querySelectorAll("a[href*='/item?']");
        var items = [];
        for(var i = 0; i < Math.min(${CONFIG.itemsPerPage}, links.length); i++) {
          var link = links[i];
          var parent = link.closest('a') || link.parentElement;
          var id = link.href.match(/id=(\\d+)/)?.[1] || "";
          var title = link.textContent?.trim() || "";
          var html = parent?.innerHTML || "";

          // 价格 - 包含小数
          var priceMatch = html.match(/¥(\\d+\\.?\\d*)/);
          var price = priceMatch ? ("¥" + priceMatch[1]) : "";

          // 想要数
          var wantsMatch = html.match(/(\\d+)人想要/);
          var wants = wantsMatch ? wantsMatch[1] : "0";

          // 图片
          var imgMatch = html.match(/src="([^"]+)"/);
          var image = imgMatch ? imgMatch[1] : "";

          // 卖家地区
          var sellerMatch = html.match(/class="seller-text--[^"]+"[^>]*>([^<]+)/);
          var seller = sellerMatch ? sellerMatch[1] : "";

          // 信誉标签
          var creditMatch = html.match(/class="gradient-image-text--[^"]+"[^>]*>([^<]+)/);
          var sellerCredit = creditMatch ? creditMatch[1] : "";

          // 标签
          var tags = [];
          var tagMatches = html.matchAll(/class="cpv--[^"]+"[^>]*>([^<]+)/g);
          for (var m of tagMatches) tags.push(m[1]);

          items.push({
            id: id,
            title: title.substring(0, 150),
            price: price,
            wants: wants,
            image: image,
            seller: seller,
            sellerCredit: sellerCredit,
            tags: tags,
            url: link.href
          });
        }
        return items;
      })()`;

      const extractResult = await controller.execute(extractScript, "function");

      const pageItems = ((extractResult.result || [])).map((item, idx) => ({
        index: allResults.length + idx + 1,
        ...item
      }));

      allResults.push(...pageItems);
      console.log(`[OK] 第 ${page} 页获取 ${pageItems.length} 个商品，累计 ${allResults.length} 个`);

      // 翻页 (如果不是最后一页)
      if (page < CONFIG.pages) {
        console.log(`[4] 翻到第 ${page + 1} 页...`);

        // 滚动到底部
        await controller.execute("window.scrollTo(0, document.body.scrollHeight)", "function");
        await controller.waitIdle(1000);

        // 查找下一页按钮
        const nextResult = await controller.execute(
          "() => { const btns = document.querySelectorAll('[class*=\"pagination\"] a, [class*=\"page\"] a, [class*=\"next\"]'); const nextBtn = Array.from(btns).find(b => b.textContent?.includes('下一页') || b.textContent?.includes('>') || b.getAttribute('aria-label')?.includes('next')); return nextBtn?.href || null; }",
          "function"
        );

        if (nextResult.result) {
          // 直接导航到下一页
          await controller.goto(nextResult.result);
          await controller.waitIdle(3000);
        } else {
          // 尝试点击翻页按钮
          const clickNext = await controller.execute(
            "() => { const btns = Array.from(document.querySelectorAll('button, a')).filter(b => b.textContent?.includes('下一页') || b.getAttribute('aria-label')?.includes('next')); if (btns[0]) { btns[0].click(); return 'clicked'; } return 'not found'; }",
            "function"
          );
          console.log(`[INFO] 翻页点击结果: ${clickNext.result}`);
          await controller.waitIdle(3000);
        }
      }
    }

    // 截图保存最终结果
    const screenshot = await controller.screenshot(false);
    fs.writeFileSync("/tmp/xianyu_search_result.png", Buffer.from(screenshot.data, "base64"));
    console.log("[OK] 截图保存到 /tmp/xianyu_search_result.png");
    recorder.record({ type: "screenshot", savePath: "/tmp/xianyu_search_result.png" });

    // 保存搜索结果到 JSON
    fs.writeFileSync(
      __dirname + "/search_results.json",
      JSON.stringify({
        keyword: CONFIG.keyword,
        totalPage: CONFIG.pages,
        totalItems: allResults.length,
        results: allResults
      }, null, 2)
    );
    console.log(`[OK] 搜索结果已保存到: ${__dirname}/search_results.json`);

    // 打印前5个结果
    console.log("\n========== 搜索结果 (前5) ==========");
    allResults.slice(0, 5).forEach((item, idx) => {
      console.log(`${idx + 1}. ${item.title} - ${item.price} - ${item.wants}人想要`);
      console.log(`   卖家: ${item.seller} | 信誉: ${item.sellerCredit} | 标签: ${item.tags.join(', ')}`);
      console.log(`   链接: ${item.url}`);
    });

    console.log(`\n========== 任务完成 (共 ${allResults.length} 个商品) ==========`);

  } catch (error) {
    console.error("[ERROR]", error.message);

    // 出错时保存截图
    try {
      const errorScreenshot = await controller.screenshot(false);
      fs.writeFileSync("/tmp/xianyu_search_error.png", Buffer.from(errorScreenshot.data, "base64"));
      console.log("[INFO] 错误截图已保存");
    } catch (e) {}

  } finally {
    console.log("[INFO] 浏览器保持打开状态...");
  }
}

// 如果直接运行此脚本
searchItem()
  .then(() => {
    console.log("\n执行完成");
  })
  .catch(err => {
    console.error("执行失败:", err.message);
    process.exit(1);
  });

module.exports = { searchItem, CONFIG };
