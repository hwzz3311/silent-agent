# -*- coding: utf-8 -*-
"""
闲鱼滑块验证模块

基于 BrowserClient 实现闲鱼/淘宝滑动验证码识别和解决。
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 黄金参数配置
GOLDEN_PARAMS = {
    "trajectory": {
        "overshoot_ratio": (1.02, 1.15),
        "steps": (18, 35),
        "base_delay": (0.004, 0.015),
        "acceleration_curve": (1.3, 2.2),
        "y_jitter_max": (1.0, 3.5),
    },
    "slide_behavior": {
        "approach_offset_x": (-30, -15),
        "approach_offset_y": (8, 22),
        "approach_steps": (6, 12),
        "approach_pause": (0.03, 0.18),
        "precision_step": (6, 12),
        "precision_pause": (0.05, 0.15),
        "skip_hover_rate": 0.25,
        "pre_down_pause": (0.08, 0.20),
        "post_down_pause": (0.08, 0.20),
        "pre_up_pause": (0.02, 0.08),
        "post_up_pause": (0.01, 0.06),
    },
    "timing": {
        "total_elapsed_time": (0.8, 2.0),
        "page_wait": (0.05, 0.30),
    },
}

# 滑块选择器配置
SLIDER_SELECTORS = {
    "button": [
        "#nc_1_n1z",
        "span[id*='nc_1_n1z']",
        "span.nc-lang-cnt[data-nc-lang='SLIDE']",
        ".nc_iconfont",
        ".btn_slide",
    ],
    "track": [
        "#nc_1_n1t",
        ".nc_scale",
        ".nc_wrapper",
        ".nc-container",
    ],
    "container": [
        ".nc_wrapper",
        ".nc_scale",
        ".nc-container",
        "#baxia-dialog-content",
    ],
}


class XianyuSliderSolver:
    """
    闲鱼滑块验证解决器

    基于 BrowserClient 实现滑块验证码的自动识别和解决。
    """

    def __init__(self, browser_client):
        """
        初始化滑块验证解决器

        Args:
            browser_client: BrowserClient 实例
        """
        self._client = browser_client
        self._slider_container = None
        self._slider_button = None
        self._slider_track = None
        self._detected_frame = None  # 记录滑块所在的 frame
        self._current_trajectory_data = None

    async def detect_slider(self) -> bool:
        """
        检测页面是否存在滑块验证

        Returns:
            bool: 是否检测到滑块
        """
        await asyncio.sleep(0.1)

        # 检查多种滑块容器选择器
        for selector in SLIDER_SELECTORS["container"]:
            try:
                result = await self._client.extract(selector, attribute="html", all=False)
                if result.get("success") and result.get("data"):
                    # 检查元素是否可见
                    is_visible = await self._client.inject(
                        f"""
                        () => {{
                            const el = document.querySelector('{selector}');
                            return el && (el.offsetParent !== null) && (el.style.display !== 'none');
                        }}
                        """
                    )
                    if is_visible.get("result"):
                        logger.info(f"[Slider] 检测到滑块容器: {selector}")
                        return True
            except Exception as e:
                logger.info(f"[Slider] 检测选择器 {selector} 失败: {e}")
                continue

        # 检查更具体的按钮元素
        for selector in SLIDER_SELECTORS["button"]:
            try:
                result = await self._client.extract(selector, attribute="html", all=False)
                if result.get("success") and result.get("data"):
                    logger.info(f"[Slider] 检测到滑块按钮: {selector}")
                    return True
            except Exception:
                continue

        logger.info("[Slider] 未检测到滑块验证")
        return False

    async def find_slider_element(self) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
        """
        查找滑块容器、按钮、轨道元素

        Returns:
            tuple: (container, button, track) 元素元组
        """
        logger.info("[Slider] 开始查找滑块元素...")

        # 查找滑块容器
        slider_container = None
        for selector in SLIDER_SELECTORS["container"]:
            try:
                result = await self._client.wait_for(selector, count=1, timeout=3)
                if result.get("success"):
                    slider_container = selector
                    logger.info(f"[Slider] 找到滑块容器: {selector}")
                    break
            except Exception:
                continue

        # 查找滑块按钮
        slider_button = None
        for selector in SLIDER_SELECTORS["button"]:
            try:
                result = await self._client.wait_for(selector, count=1, timeout=3)
                if result.get("success"):
                    slider_button = selector
                    logger.info(f"[Slider] 找到滑块按钮: {selector}")
                    break
            except Exception:
                continue

        # 查找滑块轨道
        slider_track = None
        for selector in SLIDER_SELECTORS["track"]:
            try:
                result = await self._client.wait_for(selector, count=1, timeout=3)
                if result.get("success"):
                    slider_track = selector
                    logger.info(f"[Slider] 找到滑块轨道: {selector}")
                    break
            except Exception:
                continue

        if not all([slider_container, slider_button, slider_track]):
            logger.info("[Slider] 警告: 部分滑块元素未找到")
            if not slider_container:
                slider_container = slider_button
            if not slider_track:
                slider_track = slider_container

        self._slider_container = slider_container
        self._slider_button = slider_button
        self._slider_track = slider_track

        return slider_container, slider_button, slider_track

    async def calculate_slide_distance(
        self, slider_button: str, slider_track: str
    ) -> int:
        """
        计算滑动距离

        Args:
            slider_button: 滑块按钮选择器
            slider_track: 滑块轨道选择器

        Returns:
            int: 滑动距离（像素）
        """
        try:
            # 使用 JavaScript 获取精确的滑动距离
            result = await self._client.inject(
                f"""
                () => {{
                    const button = document.querySelector('{slider_button}') ||
                                   document.querySelector('.nc_iconfont');
                    const track = document.querySelector('{slider_track}') ||
                                 document.querySelector('.nc_scale') ||
                                 document.querySelector('.nc_wrapper');

                    if (button && track) {{
                        const buttonRect = button.getBoundingClientRect();
                        const trackRect = track.getBoundingClientRect();
                        // 计算实际可滑动距离
                        return Math.round(trackRect.width - buttonRect.width);
                    }}
                    return 0;
                }}
                """
            )

            distance = result.get("result", 0)
            if distance > 0:
                # 添加微小随机偏移，防止每次完全相同
                random_offset = random.uniform(-0.5, 0.5)
                distance = int(distance + random_offset)
                logger.info(f"[Slider] 计算滑动距离: {distance}px")
                return distance

            # 后备方案：使用元素尺寸计算
            size_result = await self._client.extract(slider_track, attribute="html")
            if size_result.get("success"):
                # 尝试从样式中获取宽度
                style_result = await self._client.inject(
                    f"""
                    () => {{
                        const track = document.querySelector('{slider_track}');
                        if (track) {{
                            const style = window.getComputedStyle(track);
                            return parseInt(style.width) || track.offsetWidth;
                        }}
                        return 0;
                    }}
                    """
                )
                track_width = style_result.get("result", 300)

                btn_result = await self._client.inject(
                    f"""
                    () => {{
                        const btn = document.querySelector('{slider_button}') ||
                                   document.querySelector('.nc_iconfont');
                        if (btn) {{
                            return btn.offsetWidth;
                        }}
                        return 50;
                    }}
                    """
                )
                button_width = btn_result.get("result", 50)

                distance = int(track_width - button_width)
                logger.info(f"[Slider] 后备方案计算距离: {distance}px (轨道:{track_width}, 按钮:{button_width})")
                return distance

            logger.info("[Slider] 警告: 无法计算滑动距离，使用默认值")
            return 200  # 默认距离

        except Exception as e:
            logger.info(f"[Slider] 计算滑动距离失败: {e}")
            return 200

    def generate_human_trajectory(self, distance: int, attempt: int = 1) -> List[Tuple[int, int, int]]:
        """
        生成人类化滑动轨迹

        Args:
            distance: 滑动距离
            attempt: 当前尝试次数

        Returns:
            list: 轨迹点列表 [(x, y, delay), ...]
        """
        # 获取参数
        traj_params = GOLDEN_PARAMS["trajectory"]

        overshoot_ratio = random.uniform(*traj_params["overshoot_ratio"])
        steps = random.randint(*traj_params["steps"])
        base_delay = random.uniform(*traj_params["base_delay"])
        acceleration_curve = random.uniform(*traj_params["acceleration_curve"])
        y_jitter_max = random.uniform(*traj_params["y_jitter_max"])

        # 根据尝试次数增加扰动
        if attempt > 1:
            perturbation = 1 + (attempt - 1) * 0.08
            overshoot_ratio = min(overshoot_ratio * perturbation, 1.2)

        # 计算目标距离（包含超调）
        target_distance = distance * overshoot_ratio

        trajectory = []
        current_x = 0
        total_steps = steps

        for i in range(total_steps):
            # 进度 (0-1)
            progress = i / (total_steps - 1) if total_steps > 1 else 0

            # 使用 ease-out 曲线模拟人类滑动
            # 人类滑动通常是先慢后快
            eased_progress = 1 - (1 - progress) ** acceleration_curve

            current_x = target_distance * eased_progress

            # 添加 Y 轴抖动
            y_jitter = random.uniform(-y_jitter_max, y_jitter_max) if i > 0 else 0

            # 添加延迟变化（模拟人类不均匀的移动）
            delay = base_delay * (1 + random.uniform(-0.3, 0.5))

            trajectory.append((int(current_x), int(y_jitter), int(delay * 1000)))

        # 保存轨迹数据
        self._current_trajectory_data = {
            "distance": distance,
            "target_distance": target_distance,
            "overshoot_ratio": overshoot_ratio,
            "steps": steps,
            "trajectory": trajectory,
        }

        logger.info(f"[Slider] 生成轨迹: 距离={distance}px, 目标={target_distance:.1f}px, "
              f"超调={(overshoot_ratio-1)*100:.1f}%, 步数={steps}")

        return trajectory

    async def simulate_slide(
        self, slider_button: str, trajectory: List[Tuple[int, int, int]]
    ) -> bool:
        """
        模拟滑动操作

        Args:
            slider_button: 滑块按钮选择器
            trajectory: 滑动轨迹

        Returns:
            bool: 是否成功
        """
        try:
            # 获取按钮位置
            pos_result = await self._client.inject(
                f"""
                () => {{
                    const btn = document.querySelector('{slider_button}') ||
                               document.querySelector('.nc_iconfont');
                    if (btn) {{
                        const box = btn.getBoundingClientRect();
                        return {{ x: box.x + box.width/2, y: box.y + box.height/2 }};
                    }}
                    return null;
                }}
                """
            )

            start_pos = pos_result.get("result")
            if not start_pos:
                logger.info("[Slider] 无法获取滑块按钮位置")
                return False

            start_x = start_pos["x"]
            start_y = start_pos["y"]

            logger.info(f"[Slider] 滑块位置: ({start_x}, {start_y})")

            # 获取 CDP session 进行鼠标操作
            cdp = await self._get_cdp_session()
            if not cdp:
                logger.info("[Slider] 无法获取CDP会话，使用JavaScript模拟")
                # 使用 JavaScript 模拟滑动
                return await self._simulate_slide_js(slider_button, trajectory)

            # 第一阶段：移动到滑块附近
            behavior = GOLDEN_PARAMS["slide_behavior"]

            offset_x = random.uniform(*behavior["approach_offset_x"])
            offset_y = random.uniform(*behavior["approach_offset_y"])

            # 移动到接近位置
            await cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": start_x + offset_x,
                "y": start_y + offset_y,
            })

            # 接近后停顿
            await asyncio.sleep(random.uniform(*behavior["approach_pause"]))

            # 移动到按钮位置
            approach_steps = random.randint(*behavior["approach_steps"])
            for _ in range(approach_steps):
                await cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": start_x,
                    "y": start_y,
                })
                await asyncio.sleep(0.01)

            await asyncio.sleep(random.uniform(*behavior["precision_pause"]))

            # 第二阶段：按下鼠标
            await cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "button": "left",
                "x": start_x,
                "y": start_y,
            })

            await asyncio.sleep(random.uniform(*behavior["pre_down_pause"]))

            # 第三阶段：滑动
            current_x = start_x
            for i, (delta_x, delta_y, delay) in enumerate(trajectory):
                current_x = start_x + delta_x
                current_y = start_y + delta_y

                await cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": current_x,
                    "y": current_y,
                })

                # 最后一个点延迟稍长
                if i < len(trajectory) - 1:
                    await asyncio.sleep(delay / 1000)
                else:
                    await asyncio.sleep(0.1)

            # 第四阶段：释放鼠标
            await asyncio.sleep(random.uniform(*behavior["post_down_pause"]))

            await cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "button": "left",
                "x": current_x,
                "y": start_y + trajectory[-1][1],
            })

            logger.info(f"[Slider] 滑动模拟完成")
            return True

        except Exception as e:
            logger.info(f"[Slider] 滑动模拟失败: {e}")
            return False

    async def _simulate_slide_js(
        self, slider_button: str, trajectory: List[Tuple[int, int, int]]
    ) -> bool:
        """
        使用 JavaScript 模拟滑动（后备方案）

        Args:
            slider_button: 滑块按钮选择器
            trajectory: 滑动轨迹

        Returns:
            bool: 是否成功
        """
        try:
            # 将轨迹转换为 JavaScript 数组
            traj_array = str(trajectory)

            result = await self._client.inject(
                f"""
                () => {{
                    const button = document.querySelector('{slider_button}') ||
                                   document.querySelector('.nc_iconfont');
                    if (!button) return false;

                    const rect = button.getBoundingClientRect();
                    const startX = rect.x + rect.width / 2;
                    const startY = rect.y + rect.height / 2;

                    const trajectory = {traj_array};

                    // 创建鼠标事件
                    function createMouseEvent(type, x, y) {{
                        return new MouseEvent(type, {{
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y,
                            view: window
                        }});
                    }}

                    // 模拟拖拽
                    let currentX = startX;
                    let currentY = startY;

                    // 触发 mousedown
                    button.dispatchEvent(createMouseEvent('mousedown', currentX, currentY));

                    // 滑动
                    for (const [deltaX, deltaY] of trajectory) {{
                        currentX = startX + deltaX;
                        currentY = startY + deltaY;
                        button.dispatchEvent(createMouseEvent('mousemove', currentX, currentY));
                    }}

                    // 触发 mouseup
                    button.dispatchEvent(createMouseEvent('mouseup', currentX, currentY));

                    return true;
                }}
                """
            )

            return result.get("result", False)

        except Exception as e:
            logger.info(f"[Slider] JS滑动模拟失败: {e}")
            return False

    async def check_verification_success(self) -> bool:
        """
        检查验证结果

        Returns:
            bool: 验证是否成功
        """
        try:
            # 等待验证结果
            await asyncio.sleep(0.5)

            # 检查滑块容器是否消失（成功标志）
            for selector in SLIDER_SELECTORS["container"]:
                result = await self._client.inject(
                    f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return !el || el.style.display === 'none' || el.offsetParent === null;
                    }}
                    """
                )
                if result.get("result", False):
                    logger.info("[Slider] 验证成功：滑块容器已消失")
                    return True

            # 检查是否还有验证失败提示
            failure_indicators = [
                ".nc_error",
                ".nc_scale span",
                "[class*='error']",
            ]

            for selector in failure_indicators:
                result = await self._client.extract(selector, attribute="text", all=False)
                if result.get("success") and result.get("data"):
                    text = result.get("data", "")
                    if text and ("验证失败" in text or "错误" in text or "请重试" in text):
                        logger.info(f"[Slider] 验证失败：{text}")
                        return False

            # 等待更长时间再次检查
            await asyncio.sleep(1.0)

            for selector in SLIDER_SELECTORS["container"]:
                result = await self._client.inject(
                    f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return !el || el.style.display === 'none' || el.offsetParent === null;
                    }}
                    """
                )
                if result.get("result", False):
                    logger.info("[Slider] 验证成功：滑块容器已消失")
                    return True

            logger.info("[Slider] 验证结果未知")
            return False

        except Exception as e:
            logger.info(f"[Slider] 检查验证结果失败: {e}")
            return False

    async def solve(self, max_retries: int = 3) -> bool:
        """
        完整滑块验证流程

        Args:
            max_retries: 最大重试次数

        Returns:
            bool: 是否成功
        """
        logger.info(f"[Slider] 开始滑块验证流程 (最大重试: {max_retries})")

        for attempt in range(1, max_retries + 1):
            logger.info(f"[Slider] 第 {attempt}/{max_retries} 次尝试")

            try:
                # 1. 检测滑块是否存在
                if not await self.detect_slider():
                    logger.info(f"[Slider] 第 {attempt} 次：未检测到滑块")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return False

                # 2. 查找滑块元素
                container, button, track = await self.find_slider_element()
                if not all([container, button, track]):
                    logger.info(f"[Slider] 第 {attempt} 次：查找元素失败")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return False

                # 3. 计算滑动距离
                distance = await self.calculate_slide_distance(button, track)
                if distance <= 0:
                    logger.info(f"[Slider] 第 {attempt} 次：距离计算失败")
                    continue

                # 4. 生成人类化轨迹
                trajectory = self.generate_human_trajectory(distance, attempt)
                if not trajectory:
                    logger.info(f"[Slider] 第 {attempt} 次：轨迹生成失败")
                    continue

                # 5. 模拟滑动
                if not await self.simulate_slide(button, trajectory):
                    logger.info(f"[Slider] 第 {attempt} 次：滑动模拟失败")
                    continue

                # 6. 检查验证结果
                if await self.check_verification_success():
                    logger.info(f"[Slider] 第 {attempt} 次：验证成功!")
                    return True

                logger.info(f"[Slider] 第 {attempt} 次：验证失败")

                # 如果不是最后一次，等待后重试
                if attempt < max_retries:
                    retry_delay = 1.5 + attempt * 0.5
                    logger.info(f"[Slider] 等待 {retry_delay:.1f}s 后重试...")
                    await asyncio.sleep(retry_delay)

            except Exception as e:
                logger.info(f"[Slider] 第 {attempt} 次异常: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue

        logger.info(f"[Slider] 滑块验证失败，已尝试 {max_retries} 次")
        return False

    async def _get_cdp_session(self):
        """
        获取 CDP 会话

        Returns:
            CDP session 或 None
        """
        # 尝试从 browser_client 获取 CDP session
        if hasattr(self._client, "_get_cdp_session"):
            return await self._client._get_cdp_session()
        elif hasattr(self._client, "_cdp_session"):
            return self._client._cdp_session
        elif hasattr(self._client, "_page"):
            try:
                return await self._client._page.target.createCDPSession()
            except Exception:
                return None
        return None