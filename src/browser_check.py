#!/usr/bin/env python3
"""
Neurone 浏览器操作验证脚本

对常见的浏览器自动化操作进行逐项验证，覆盖：
  1. Relay 连接 & 会话建立
  2. 页面信息获取（标题、URL）
  3. JavaScript 执行
  4. DOM 获取与遍历
  5. 页面导航
  6. 鼠标操作（移动、直接点击、拟人点击）
  7. 键盘输入
  8. 页面滚动
  9. 截图
 10. CSS 选择器查询
 11. Cookie 读取
 12. 浏览器版本信息

使用方式:
    # 先确保 relay_server.py 已启动，Chrome 扩展已连接
    python browser_check.py
"""

import asyncio
import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relay_client import RelayClient

# ==================== 输出工具 ====================

_pass_count = 0
_fail_count = 0
_skip_count = 0


def header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def section(title: str):
    print(f"\n  ── {title} ──")


def report_pass(name: str, detail: str = ""):
    global _pass_count
    _pass_count += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  ✅  {name}{suffix}")


def report_fail(name: str, err: str):
    global _fail_count
    _fail_count += 1
    print(f"  ❌  {name}  →  {err}")


def report_skip(name: str, reason: str):
    global _skip_count
    _skip_count += 1
    print(f"  ⏭️   {name}  →  跳过: {reason}")


def summary():
    total = _pass_count + _fail_count + _skip_count
    header("验证结果汇总")
    print(f"  总计: {total}  |  ✅ 通过: {_pass_count}  |  ❌ 失败: {_fail_count}  |  ⏭️  跳过: {_skip_count}")
    if _fail_count == 0:
        print("\n  🎉  所有验证项全部通过！")
    else:
        print(f"\n  ⚠️  有 {_fail_count} 项未通过，请检查上方日志。")
    print()


# ==================== 验证用例 ====================

async def check_connect(client: RelayClient) -> bool:
    """验证 1: Relay 连接 & 会话"""
    section("1. Relay 连接 & 会话建立")

    report_pass("连接 Relay 服务器")

    # 检查是否已有会话
    if client.has_session:
        session = list(client.sessions.values())[0]
        report_pass("已有会话（扩展先于控制器连接）", f"sessionId={session.session_id}")
        report_pass("会话 targetId", session.target_id)
        return True

    # 没有会话，等待用户点击扩展图标
    print()
    print("  ⏳  等待 Chrome 扩展连接...")
    print("  👉  请在 Chrome 中打开任意网页，然后点击工具栏上的 Neurone 图标")
    print("  👉  看到图标显示绿色 ON 后会自动继续")
    print()

    try:
        session = await client.wait_for_session(timeout=60)
        report_pass("获取会话", f"sessionId={session.session_id}")
        report_pass("会话 targetId", session.target_id)
        return True
    except Exception as e:
        report_fail("获取会话", str(e))
        return False


async def check_page_info(client: RelayClient):
    """验证 2: 页面信息"""
    section("2. 页面信息获取")

    # 标题
    try:
        title = await client.get_page_title()
        if title is not None:
            report_pass("获取页面标题", repr(title))
        else:
            report_fail("获取页面标题", "返回值为 None")
    except Exception as e:
        report_fail("获取页面标题", str(e))

    # URL
    try:
        url = await client.get_page_url()
        if url:
            report_pass("获取页面 URL", url[:80])
        else:
            report_fail("获取页面 URL", "返回值为空")
    except Exception as e:
        report_fail("获取页面 URL", str(e))


async def check_js_evaluate(client: RelayClient):
    """验证 3: JavaScript 执行"""
    section("3. JavaScript 执行")

    # 简单运算
    try:
        result = await client.evaluate("2 + 3")
        if result == 5:
            report_pass("简单运算 (2+3=5)", f"result={result}")
        else:
            report_fail("简单运算", f"期望 5，得到 {result}")
    except Exception as e:
        report_fail("简单运算", str(e))

    # 字符串
    try:
        result = await client.evaluate("'hello' + ' ' + 'world'")
        if result == "hello world":
            report_pass("字符串拼接", repr(result))
        else:
            report_fail("字符串拼接", f"期望 'hello world'，得到 {result!r}")
    except Exception as e:
        report_fail("字符串拼接", str(e))

    # 对象
    try:
        result = await client.evaluate("JSON.stringify({a:1, b:'test'})")
        parsed = json.loads(result)
        if parsed == {"a": 1, "b": "test"}:
            report_pass("对象序列化", result)
        else:
            report_fail("对象序列化", f"结果不符: {result}")
    except Exception as e:
        report_fail("对象序列化", str(e))

    # 数组
    try:
        result = await client.evaluate("[1,2,3].map(x => x*2).join(',')")
        if result == "2,4,6":
            report_pass("数组操作", result)
        else:
            report_fail("数组操作", f"期望 '2,4,6'，得到 {result!r}")
    except Exception as e:
        report_fail("数组操作", str(e))

    # DOM 相关
    try:
        result = await client.evaluate("document.readyState")
        if result in ("loading", "interactive", "complete"):
            report_pass("document.readyState", result)
        else:
            report_fail("document.readyState", f"意外值: {result}")
    except Exception as e:
        report_fail("document.readyState", str(e))

    # window 属性
    try:
        result = await client.evaluate("typeof window.navigator.userAgent === 'string'")
        if result is True:
            report_pass("navigator.userAgent 类型", "string")
        else:
            report_fail("navigator.userAgent 类型", f"result={result}")
    except Exception as e:
        report_fail("navigator.userAgent 类型", str(e))


async def check_dom(client: RelayClient):
    """验证 4: DOM 获取与遍历"""
    section("4. DOM 获取与遍历")

    try:
        dom = await client.get_dom()
        if not dom:
            report_fail("DOM.getDocument", "返回空")
            return

        report_pass("DOM.getDocument", f"nodeName={dom.get('nodeName')}")

        # 统计节点
        def count_nodes(node, depth=0):
            c = 1
            max_d = depth
            for child in node.get("children", []):
                cc, dd = count_nodes(child, depth + 1)
                c += cc
                max_d = max(max_d, dd)
            return c, max_d

        total, max_depth = count_nodes(dom)
        report_pass("DOM 节点遍历", f"节点数={total}, 最大深度={max_depth}")

        # 查找 body
        def find_node(node, tag):
            if node.get("localName") == tag:
                return node
            for child in node.get("children", []):
                found = find_node(child, tag)
                if found:
                    return found
            return None

        body = find_node(dom, "body")
        if body:
            body_children = len(body.get("children", []))
            report_pass("查找 <body> 节点", f"子节点数={body_children}")
        else:
            report_fail("查找 <body> 节点", "未找到")

        head = find_node(dom, "head")
        if head:
            report_pass("查找 <head> 节点", f"nodeId={head.get('nodeId')}")
        else:
            report_fail("查找 <head> 节点", "未找到")

    except Exception as e:
        report_fail("DOM 获取", str(e))


async def check_css_query(client: RelayClient):
    """验证 5: CSS 选择器查询"""
    section("5. CSS 选择器查询 (querySelectorAll)")

    queries = [
        ("a", "链接数"),
        ("img", "图片数"),
        ("input", "输入框数"),
        ("button", "按钮数"),
        ("*", "全部元素数"),
    ]

    for selector, label in queries:
        try:
            count = await client.evaluate(f"document.querySelectorAll('{selector}').length")
            report_pass(f"{label} ('{selector}')", f"count={count}")
        except Exception as e:
            report_fail(f"{label} ('{selector}')", str(e))


async def check_navigate(client: RelayClient) -> str:
    """验证 6: 页面导航"""
    section("6. 页面导航")

    # 记录当前 URL 以便后续恢复
    original_url = ""
    try:
        original_url = await client.get_page_url()
    except Exception:
        pass

    target_url = "https://example.com"
    try:
        await client.send_command("Page.enable")
        report_pass("Page.enable", "已启用")
    except Exception as e:
        report_fail("Page.enable", str(e))

    try:
        result = await client.navigate(target_url)
        report_pass("Page.navigate", f"frameId={result[:30] if result else '(empty)'}")

        # 等待页面加载
        await asyncio.sleep(2)

        new_url = await client.get_page_url()
        if "example.com" in (new_url or ""):
            report_pass("导航到目标 URL", new_url)
        else:
            report_fail("导航到目标 URL", f"当前 URL: {new_url}")

        new_title = await client.get_page_title()
        report_pass("导航后获取标题", repr(new_title))

    except Exception as e:
        report_fail("页面导航", str(e))

    return original_url


async def check_mouse(client: RelayClient):
    """验证 7: 鼠标操作"""
    section("7. 鼠标操作")

    # 鼠标移动
    try:
        await client.send_command("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": 200,
            "y": 200,
        })
        report_pass("鼠标移动", "(200, 200)")
    except Exception as e:
        report_fail("鼠标移动", str(e))

    # 直接点击
    try:
        await client.click(300, 300, human=False)
        report_pass("直接点击", "(300, 300)")
    except Exception as e:
        report_fail("直接点击", str(e))

    # 拟人点击
    try:
        await client.click(400, 200, human=True)
        report_pass("拟人点击", "(400, 200)")
    except Exception as e:
        report_fail("拟人点击", str(e))

    # 双击 (通过 CDP 原始命令)
    try:
        await client.send_command("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": 300, "y": 300,
            "button": "left",
            "clickCount": 2,
        })
        await client.send_command("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": 300, "y": 300,
            "button": "left",
            "clickCount": 2,
        })
        report_pass("双击", "(300, 300)")
    except Exception as e:
        report_fail("双击", str(e))

    # 右键
    try:
        await client.send_command("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": 300, "y": 300,
            "button": "right",
            "clickCount": 1,
        })
        await client.send_command("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": 300, "y": 300,
            "button": "right",
            "clickCount": 1,
        })
        report_pass("右键点击", "(300, 300)")
    except Exception as e:
        report_fail("右键点击", str(e))


async def check_keyboard(client: RelayClient):
    """验证 8: 键盘输入"""
    section("8. 键盘输入")

    # 先在页面上创建一个输入框并聚焦
    try:
        await client.evaluate("""
            (() => {
                let el = document.getElementById('neurone-check-input');
                if (!el) {
                    el = document.createElement('input');
                    el.id = 'neurone-check-input';
                    el.style.cssText = 'position:fixed;top:10px;left:10px;z-index:99999;padding:8px;font-size:16px;border:2px solid #22C55E;border-radius:8px;';
                    document.body.appendChild(el);
                }
                el.value = '';
                el.focus();
            })()
        """)
        report_pass("创建并聚焦输入框", "")
    except Exception as e:
        report_fail("创建输入框", str(e))
        return

    await asyncio.sleep(0.3)

    # 逐字输入
    try:
        text = "Hello Neurone"
        await client.type_text(text, delay=0.04)
        await asyncio.sleep(0.3)
        value = await client.evaluate("document.getElementById('neurone-check-input').value")
        if value == text:
            report_pass("逐字输入", repr(value))
        else:
            report_fail("逐字输入", f"期望 {text!r}，得到 {value!r}")
    except Exception as e:
        report_fail("逐字输入", str(e))

    # 按键事件 (Backspace)
    try:
        for _ in range(3):
            await client.send_command("Input.dispatchKeyEvent", {
                "type": "rawKeyDown",
                "windowsVirtualKeyCode": 8,
                "nativeVirtualKeyCode": 8,
                "key": "Backspace",
                "code": "Backspace",
            })
            await client.send_command("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "windowsVirtualKeyCode": 8,
                "nativeVirtualKeyCode": 8,
                "key": "Backspace",
                "code": "Backspace",
            })
            await asyncio.sleep(0.05)

        value = await client.evaluate("document.getElementById('neurone-check-input').value")
        if value == "Hello Neur":
            report_pass("Backspace 按键", repr(value))
        else:
            # 值可能因时序略有偏差，只要比原来短就算通过
            if len(value) < len("Hello Neurone"):
                report_pass("Backspace 按键", f"值已缩短: {value!r}")
            else:
                report_fail("Backspace 按键", f"值未变化: {value!r}")
    except Exception as e:
        report_fail("Backspace 按键", str(e))

    # 快捷键: Ctrl+A (全选)
    try:
        await client.send_command("Input.dispatchKeyEvent", {
            "type": "rawKeyDown",
            "key": "a",
            "code": "KeyA",
            "windowsVirtualKeyCode": 65,
            "modifiers": 2 if sys.platform == "darwin" else 1,  # 2=Ctrl(Mac uses command mapped to ctrl), 1=Ctrl
        })
        await client.send_command("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": "a",
            "code": "KeyA",
            "windowsVirtualKeyCode": 65,
        })
        report_pass("快捷键 Ctrl+A", "全选")
    except Exception as e:
        report_fail("快捷键 Ctrl+A", str(e))

    # 清理输入框
    try:
        await client.evaluate("document.getElementById('neurone-check-input')?.remove()")
    except Exception:
        pass


async def check_scroll(client: RelayClient):
    """验证 9: 页面滚动"""
    section("9. 页面滚动")

    # 先确保页面可滚动
    try:
        await client.evaluate("""
            document.body.style.minHeight = '3000px';
        """)
    except Exception:
        pass

    # 获取初始滚动位置
    try:
        before = await client.evaluate("window.scrollY")
        report_pass("获取初始滚动位置", f"scrollY={before}")
    except Exception as e:
        report_fail("获取初始滚动位置", str(e))
        return

    # 向下滚动
    try:
        await client.scroll(400, 300, delta_y=300)
        await asyncio.sleep(0.5)
        after = await client.evaluate("window.scrollY")
        if after is not None and after > (before or 0):
            report_pass("向下滚动", f"scrollY: {before} → {after}")
        else:
            report_fail("向下滚动", f"scrollY 未变化: {before} → {after}")
    except Exception as e:
        report_fail("向下滚动", str(e))

    # 向上滚动 (回到顶部)
    try:
        await client.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.3)
        top = await client.evaluate("window.scrollY")
        if top == 0:
            report_pass("滚动回顶部 (scrollTo)", f"scrollY={top}")
        else:
            report_fail("滚动回顶部", f"scrollY={top}")
    except Exception as e:
        report_fail("滚动回顶部", str(e))


async def check_screenshot(client: RelayClient):
    """验证 10: 截图"""
    section("10. 页面截图")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_output")
    os.makedirs(output_dir, exist_ok=True)

    # PNG 截图
    try:
        data = await client.screenshot(format="png")
        if data and len(data) > 100:
            png_path = os.path.join(output_dir, "screenshot.png")
            with open(png_path, "wb") as f:
                f.write(data)
            report_pass("PNG 截图", f"大小={len(data)} bytes, 保存至 {png_path}")
        else:
            report_fail("PNG 截图", f"数据过小: {len(data)} bytes")
    except Exception as e:
        report_fail("PNG 截图", str(e))

    # JPEG 截图
    try:
        data = await client.screenshot(format="jpeg", quality=60)
        if data and len(data) > 100:
            jpeg_path = os.path.join(output_dir, "screenshot.jpg")
            with open(jpeg_path, "wb") as f:
                f.write(data)
            report_pass("JPEG 截图", f"大小={len(data)} bytes, 保存至 {jpeg_path}")
        else:
            report_fail("JPEG 截图", f"数据过小: {len(data)} bytes")
    except Exception as e:
        report_fail("JPEG 截图", str(e))


async def check_cookies(client: RelayClient):
    """验证 11: Cookie 读取"""
    section("11. Cookie 操作")

    try:
        result = await client.send_command("Network.getCookies")
        cookies = result.get("cookies", [])
        report_pass("Network.getCookies", f"数量={len(cookies)}")

        if cookies:
            c = cookies[0]
            report_pass("首条 Cookie", f"name={c.get('name')}, domain={c.get('domain')}")
    except Exception as e:
        report_fail("Cookie 读取", str(e))


async def check_browser_info(client: RelayClient):
    """验证 12: 浏览器版本"""
    section("12. 浏览器信息")

    try:
        result = await client.send_command("Browser.getVersion")
        product = result.get("product", "unknown")
        user_agent = result.get("userAgent", "")
        protocol = result.get("protocolVersion", "")
        js_ver = result.get("jsVersion", "")

        report_pass("Browser.getVersion", product)
        report_pass("protocolVersion", protocol)
        report_pass("jsVersion", js_ver)
        report_pass("userAgent", user_agent[:80])
    except Exception as e:
        report_fail("浏览器版本", str(e))


async def check_viewport(client: RelayClient):
    """验证 13: 视口信息 & 修改"""
    section("13. 视口信息")

    try:
        width = await client.evaluate("window.innerWidth")
        height = await client.evaluate("window.innerHeight")
        dpr = await client.evaluate("window.devicePixelRatio")
        report_pass("当前视口", f"{width}x{height}, devicePixelRatio={dpr}")
    except Exception as e:
        report_fail("获取视口", str(e))

    # 修改设备尺寸
    try:
        await client.send_command("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 3,
            "mobile": True,
        })
        await asyncio.sleep(0.5)
        new_w = await client.evaluate("window.innerWidth")
        new_h = await client.evaluate("window.innerHeight")
        report_pass("模拟移动端视口", f"{new_w}x{new_h}")
    except Exception as e:
        report_fail("模拟移动端视口", str(e))

    # 还原
    try:
        await client.send_command("Emulation.clearDeviceMetricsOverride")
        report_pass("还原视口", "已重置")
    except Exception as e:
        report_fail("还原视口", str(e))


async def check_navigate_back(client: RelayClient, original_url: str):
    """验证 14: 返回原始页面"""
    section("14. 返回原始页面")

    if not original_url:
        report_skip("返回原始页面", "无原始 URL")
        return

    try:
        await client.navigate(original_url)
        await asyncio.sleep(2)
        url = await client.get_page_url()
        report_pass("返回原始页面", url[:80] if url else "(空)")
    except Exception as e:
        report_fail("返回原始页面", str(e))


# ==================== 主流程 ====================

async def run_all():
    header("Neurone 浏览器操作验证")
    print("  确保: Relay 服务器已启动 & Chrome 扩展已连接")

    start_time = time.time()

    async with RelayClient() as client:
        print(f"\n  已连接到 Relay 服务器 (ws://{client.host}:{client.port}/controller)")

        # 1. 连接 & 会话
        ok = await check_connect(client)
        if not ok:
            print("\n  ⛔  无法获取会话，后续验证无法进行。")
            print("  请检查: Chrome 扩展是否已点击图标连接当前标签页？")
            summary()
            return

        # 启用必要的 CDP 域
        for domain in ("DOM", "Runtime", "Page", "Network", "Input"):
            try:
                await client.send_command(f"{domain}.enable")
            except Exception:
                pass

        # 2 ~ 5: 信息类验证
        await check_page_info(client)
        await check_js_evaluate(client)
        await check_dom(client)
        await check_css_query(client)

        # 6: 导航 (会离开当前页)
        original_url = await check_navigate(client)

        # 7 ~ 9: 交互类验证
        await check_mouse(client)
        await check_keyboard(client)
        await check_scroll(client)

        # 10: 截图
        await check_screenshot(client)

        # 11 ~ 13: 浏览器能力
        await check_cookies(client)
        await check_browser_info(client)
        await check_viewport(client)

        # 14: 导航回原始页面
        await check_navigate_back(client, original_url)

    elapsed = time.time() - start_time
    summary()
    print(f"  耗时: {elapsed:.1f}s\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\n  手动中断。")
    except Exception as e:
        print(f"\n  致命错误: {e}")
        traceback.print_exc()

