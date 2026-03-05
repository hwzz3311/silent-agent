# 闲鱼 RPA 发布问题与解决方案

## 错误 1: 图片上传失败

**错误信息**：
```
page.setInputFile is not a function
```

**错误原因**：
- Puppeteer v24+ 返回 CdpPage 类型（不是标准 Page）
- CdpPage 没有实现 `setInputFile` 方法

**排查过程**：
1. 使用 debug 脚本测试 `page.setInputFile` 类型
2. 发现 `typeof page.setInputFile === 'undefined'`
3. Puppeteer 版本 24.37.5 使用 CDP 封装

**解决方案**：
在 server.js 的 upload 端点添加 fallback 逻辑，使用 DataTransfer 方式：

```javascript
// server.js (line ~835)
if (typeof page.setInputFile === 'function') {
  await page.setInputFile(selector, filePath);
} else {
  // 使用 DataTransfer 模拟文件上传
  await page.evaluate((sel, imgData, fname, mime) => {
    const input = document.querySelector(sel);
    const blob = new Blob([new Uint8Array(imgData)], { type: mime });
    const file = new File([blob], fname, { type: mime });
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('change', { bubble: true }));
  }, selector, Array.from(imageData), fileName, mimeType);
}
```

---

## 错误 2: 分类下拉框无法点击

**错误信息**：
- 点击无反应
- 使用后找到的 CSS 选择器下次失效

**错误原因**：
- 页面使用 Ant Design Select 组件
- CSS 类名包含动态 hash（如 `ant-select-selector.css-d5i8y5`）
- 选择器 `#content > div.container--wQDj33l7...` 每次渲染都变化

**解决方案**：
使用稳定的 CSS 选择器：
```javascript
// 使用 class 前缀匹配
await controller.click("div.ant-select-selector");
```

---

## 错误 3: 分类不支持网页发布

**错误表现**：
- 选择分类后页面显示红色警告
- "网页版暂不支持发布此分类，请使用闲鱼APP扫码继续发布"

**错误原因**：
- 部分分类（如软件/程序/网站开发）只支持 APP 发布

**解决方案**：
循环遍历分类选项，直到找到支持的：

```javascript
const checkUnsupported = async () => {
  const result = await controller.execute(
    "document.body.innerHTML.includes('网页版暂不支持发布此分类')",
    "function"
  );
  return result.result === true;
};

for (let i = 0; i < 10; i++) {
  await controller.click("div.ant-select-selector");
  await controller.execute(
    `document.querySelectorAll('div[class*="ant-select-item-option"]')[${i}]?.click()`
  );
  await controller.waitIdle(500);

  if (!(await checkUnsupported())) {
    console.log(`已选择分类 index: ${i}`);
    break;
  }
}
```

**测试过的分类**：
| index | 分类名称 | 是否支持网页 |
|-------|----------|---------------|
| 0 | 软件安装包/序列号/激活码 | ❌ |
| 1 | 软件/程序/网站开发 | ❌ |
| 2 | 其他服务 | ❌ |
| 3 | 其他技能服务 | ✅ |
| 4 | 其它互联网/软硬件相关服务 | ✅ |

---

## 错误 4: 发布按钮找不到

**错误信息**：
```
No element found for selector: button[name="发布"]
```

**错误原因**：
- a11y 树的 name 属性不是直接可用的选择器
- 按钮实际是动态生成的

**解决方案**：
使用 JS 查找并点击：
```javascript
await controller.execute(
  "Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('发布'))?.click()",
  "function"
);
```

---

## 错误 5: execute API JSON 解析错误

**错误信息**：
```
SyntaxError: Bad escaped character in JSON
```

**错误原因**：
- curl 传递的 script 字符串中包含未转义的特殊字符

**解决方案**：
使用 JSON 文件传递请求：
```bash
# 错误
curl -d '{"script": "..."}'  # 特殊字符导致解析失败

# 正确
echo '{"script": "..."}' > /tmp/request.json
curl -d @/tmp/request.json
```

---

## 验证发布成功的方法

**关键指标**：URL 跳转到商品详情页

```javascript
const titleResult = await controller.getTitle();
// titleResult.url = "https://www.goofish.com/item?id=123456789"

const isSuccess = titleResult.url && titleResult.url.includes("/item?id=");
```

---

## 经验总结

1. **选择器优先使用稳定 class**：避免使用动态生成的 hash 类名
2. **execute API 传参**：复杂 JS 使用 JSON 文件方式
3. **关键步骤后验证**：上传后、检查分类后都要验证状态
4. **循环处理不确定情况**：分类选择等可能失败的情况用循环处理
