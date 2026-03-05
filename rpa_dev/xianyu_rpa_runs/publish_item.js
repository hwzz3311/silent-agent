/**
 * 闲鱼发布商品 RPA 脚本
 * 功能：自动填写商品信息并发布
 *
 * 使用方法:
 *   node publish_item.js
 *
 * 注意：服务端已修复 setInputFile 问题，现在支持自动上传图片
 */

const { RPAController, OperationRecorder } = require("/Users/leon_zheng/.claude/skills/rpa-development/scripts/rpa-client.js");
const fs = require("fs");

const CONFIG = {
  browserId: "xianyu-publish",
  host: "localhost",
  port: 18765,
  // 用户数据目录，用于保持登录状态
  userDataDir: "/tmp/puppeteer-stealth-user-data",
  // 商品信息
  item: {
    price: "88",
    description: "这是测试商品，RPA自动发布",
    // 图片路径（服务端已修复上传功能）
    imagePath: "/Users/leon_zheng/PycharmProjects/sideline/network_hook/xianyu_rpa_runs/xianyu.png",
    // 第二张图片（可选）
    imagePath2: "/Users/leon_zheng/PycharmProjects/sideline/network_hook/xianyu_rpa_runs/xianyu.png"
  }
};

async function publishItem() {
  const controller = new RPAController({
    host: CONFIG.host,
    port: CONFIG.port,
    browserId: CONFIG.browserId,
    debug: true
  });

  const recorder = new OperationRecorder();

  try {
    console.log("[1] 启动浏览器...");

    // 启动浏览器（使用 userDataDir 保持登录状态）
    const launchResult = await controller._request("POST", `/browser/launch`, {
      id: CONFIG.browserId,
      headless: false,
      userDir: CONFIG.userDataDir
    });

    if (!launchResult.success) {
      // 浏览器可能已存在，尝试直接使用
      console.log("[INFO] 浏览器可能已存在，继续...");
    }

    recorder.record({ type: "launch", browserId: CONFIG.browserId, userDataDir: CONFIG.userDataDir });

    console.log("[2] 导航到发布页面...");
    await controller.goto("https://www.goofish.com/publish");
    recorder.record({ type: "goto", url: "https://www.goofish.com/publish" });

    await controller.waitIdle(3000);

    console.log("[3] 填写商品信息...");

    // 填写价格 - 使用 CSS 选择器
    await controller.click(".ant-input");
    await controller.type(".ant-input", CONFIG.item.price);
    console.log(`[OK] 价格: ${CONFIG.item.price}`);
    recorder.record({ type: "type", selector: ".ant-input", text: CONFIG.item.price });

    // 填写描述 - contenteditable 元素
    await controller.click("div[class^='editor--']");
    await controller.type("div[class^='editor--']", CONFIG.item.description);
    console.log(`[OK] 描述: ${CONFIG.item.description}`);
    recorder.record({ type: "type", selector: "div[class^='editor--']", text: CONFIG.item.description });

    // 图片上传 - 使用修复后的上传功能 (input[name="file"])
    try {
      await controller.upload("input[name=\"file\"]", CONFIG.item.imagePath);
      console.log("[OK] 主图已上传");
      recorder.record({ type: "upload", selector: "input[name=\"file\"]", filePath: CONFIG.item.imagePath });
    } catch (e) {
      console.log(`[WARN] 主图上传失败: ${e.message}`);
    }

    await controller.waitIdle(1000);

    // 继续上传第二张图片（可选）
    if (CONFIG.item.imagePath2) {
      try {
        await controller.upload("input[name=\"file\"]", CONFIG.item.imagePath2);
        console.log("[OK] 细节图已上传");
        recorder.record({ type: "upload", selector: "input[name=\"file\"]", filePath: CONFIG.item.imagePath2 });
      } catch (e) {
        console.log(`[WARN] 细节图上传失败: ${e.message}`);
      }
    }

    await controller.waitIdle(1000);

    // 选择分类 - 等分类下拉框出现后点击
    console.log("[4] 选择分类...");
    await controller.waitIdle(1500);

    // 检查是否出现"网页版暂不支持发布此分类"的警告
    const checkUnsupported = async () => {
      const result = await controller.execute(
        "document.body.innerHTML.includes('网页版暂不支持发布此分类')",
        "function"
      );
      return result.result === true;
    };

    // 选择分类的函数 - 遍历直到找到支持的分类
    const selectCategory = async (startIndex = 0) => {
      // 点击分类下拉框打开选择器
      await controller.click("div.ant-select-selector");
      console.log("[OK] 已点击分类下拉框");
      recorder.record({ type: "click", selector: "div.ant-select-selector" });

      await controller.waitIdle(500);

      // 遍历选项直到找到支持的分类
      for (let i = startIndex; i < 10; i++) {
        // 使用 JS 点击第 i 个选项
        const script = `document.querySelectorAll('div[class*="ant-select-item-option"]')[${i}]?.click()`;
        const scriptObj = { script, returnByValue: true };
        const scriptStr = JSON.stringify(scriptObj);
        const scriptReq = JSON.parse(scriptStr);
        await controller._request("POST", `/browser/${CONFIG.browserId}/page/0/execute`, scriptReq);

        await controller.waitIdle(500);

        // 检查是否还有不支持的警告
        const isUnsupported = await checkUnsupported();
        if (!isUnsupported) {
          console.log(`[OK] 已选择分类 (index: ${i})`);
          return true;
        } else {
          console.log(`[WARN] 分类 ${i} 不支持网页发布，重新选择...`);
          // 再次打开下拉框
          await controller.click("div.ant-select-selector");
          await controller.waitIdle(300);
        }
      }
      console.log("[ERROR] 所有分类都不支持网页发布");
      return false;
    };

    // 执行分类选择
    const categorySelected = await selectCategory(0);
    if (!categorySelected) {
      throw new Error("无法找到支持的分类");
    }

    await controller.waitIdle(500);

    // 截图保存当前状态
    const screenshot = await controller.screenshot(false);
    fs.writeFileSync("/tmp/xianyu_publish_before.png", Buffer.from(screenshot.data, "base64"));
    console.log("[OK] 截图保存到 /tmp/xianyu_publish_before.png");
    recorder.record({ type: "screenshot", savePath: "/tmp/xianyu_publish_before.png" });

    console.log("[5] 点击发布按钮...");
    // 使用 JS 点击发布按钮
    const clickPublishScript = `Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("发布"))?.click()`;
    await controller.execute(clickPublishScript, "function");
    console.log("[OK] 已点击发布按钮");
    recorder.record({ type: "execute", script: "click publish button" });

    await controller.waitIdle(3000);

    // 验证发布是否成功
    const titleResult = await controller.getTitle();
    console.log(`[INFO] 当前页面: ${titleResult.url}`);

    // 检查是否跳转到商品详情页（成功标志：URL 包含 /item?id=）
    const isSuccess = titleResult.url && titleResult.url.includes("/item?id=");
    if (isSuccess) {
      const itemId = titleResult.url.match(/id=(\d+)/)?.[1] || "未知";
      console.log(`[SUCCESS] 商品发布成功！商品ID: ${itemId}`);
      console.log(`[SUCCESS] 商品链接: ${titleResult.url}`);
    } else {
      console.log("[WARN] 发布结果未明，请检查截图");
    }

    // 截图保存发布结果
    const resultScreenshot = await controller.screenshot(false);
    fs.writeFileSync("/tmp/xianyu_publish_result.png", Buffer.from(resultScreenshot.data, "base64"));
    console.log("[OK] 结果截图保存到 /tmp/xianyu_publish_result.png");
    recorder.record({ type: "screenshot", savePath: "/tmp/xianyu_publish_result.png" });

    console.log("[7] 生成 RPA 脚本...");

    // 生成可复用的脚本
    const script = recorder.generateScript("puppeteer");
    fs.writeFileSync(__dirname + "/auto_publish.js", script);
    console.log(`[OK] RPA 脚本已保存到: ${__dirname}/auto_publish.js`);

    // 导出操作记录为 JSON
    const jsonExport = recorder.exportJSON();
    fs.writeFileSync(__dirname + "/publish_operations.json", JSON.stringify(jsonExport, null, 2));
    console.log(`[OK] 操作记录已保存到: ${__dirname}/publish_operation.json`);

    console.log("\n========== 任务完成 ==========");

  } catch (error) {
    console.error("[ERROR]", error.message);

    // 出错时保存截图
    try {
      const errorScreenshot = await controller.screenshot(false);
      fs.writeFileSync("/tmp/xianyu_error.png", Buffer.from(errorScreenshot.data, "base64"));
      console.log("[INFO] 错误截图已保存");
    } catch (e) {}

  } finally {
    console.log("[8] 关闭浏览器...");
    // 不自动关闭，留着让用户查看
    // await controller.close();
    // recorder.record({ type: "close" });
  }
}

// 如果直接运行此脚本
publishItem()
  .then(() => {
    console.log("\n执行完成");
  })
  .catch(err => {
    console.error("执行失败:", err.message);
    process.exit(1);
  });

module.exports = { publishItem, CONFIG };
