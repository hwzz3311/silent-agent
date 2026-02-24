"""
选择器适配器

提供选择器的多种匹配策略和自适应功能。
"""

import re
from typing import Any, Dict, List, Optional


class SelectorAdapter:
    """
    选择器适配器

    提供多种选择器匹配策略，包括：
    - 精确匹配
    - 部分匹配
    - 备用选择器
    - 无障碍树辅助定位
    - 文本内容匹配
    """

    def __init__(self):
        self._fallback_selectors: Dict[str, List[str]] = {}

    def generate_fallback_selectors(
        self,
        original_selector: str,
        element_info: Dict[str, Any],
    ) -> List[str]:
        """
        生成备用选择器列表

        Args:
            original_selector: 原始选择器
            element_info: 元素信息

        Returns:
            备用选择器列表（按优先级排序）
        """
        fallbacks = []

        # 1. ID 选择器
        if element_info.get("id"):
            fallbacks.append(f"#{element_info['id']}")

        # 2. data 属性选择器
        for key in ["data-testid", "data-role", "data-id"]:
            value = self._extract_data_attr(element_info.get("attributes", {}), key)
            if value:
                fallbacks.append(f"[{key}='{value}']")

        # 3. 类名选择器（第一个类名）
        class_name = element_info.get("className", "").split()[0] if element_info.get("className") else ""
        if class_name:
            fallbacks.append(f".{class_name}")

        # 4. 属性选择器
        if element_info.get("tag") == "INPUT":
            if element_info.get("name"):
                fallbacks.append(f'input[name="{element_info["name"]}"]')
            if element_info.get("placeholder"):
                fallbacks.append(f'input[placeholder*="{element_info["placeholder"]}"]')
            if element_info.get("inputType"):
                fallbacks.append(f'input[type="{element_info["inputType"]}"]')

        # 5. 文本内容选择器
        if element_info.get("text"):
            text = element_info["text"].replace('"', '\\"')
            fallbacks.append(f'*:contains("{text[:50]}")')

        # 6. ARIA role 选择器
        if element_info.get("role"):
            fallbacks.append(f'[role="{element_info["role"]}"]')

        # 7. nth-child 简化的路径
        fallback_path = self._simplify_selector(original_selector)
        if fallback_path and fallback_path != original_selector:
            fallbacks.append(fallback_path)

        return fallbacks

    def _extract_data_attr(self, attributes: Dict[str, str], key: str) -> Optional[str]:
        """提取 data 属性"""
        return attributes.get(key) or attributes.get(key.replace("-", "_"))

    def _simplify_selector(self, selector: str) -> str:
        """简化选择器"""
        # 移除过长的路径
        parts = selector.split(" > ")
        if len(parts) > 5:
            # 只保留后3个部分
            return " > ".join(parts[-3:])
        return selector

    def match_element(
        self,
        selector: str,
        fallback_selectors: List[str],
        element_finder: Optional[callable] = None,
    ) -> Optional[Any]:
        """
        匹配元素（尝试所有选择器）

        Args:
            selector: 原始选择器
            fallback_selectors: 备用选择器列表
            element_finder: 元素查找函数 (selector) -> element

        Returns:
            匹配到的元素，未找到返回 None
        """
        # 1. 尝试原始选择器
        element = element_finder(selector)
        if element:
            return element

        # 2. 尝试备用选择器
        for fallback in fallback_selectors:
            element = element_finder(fallback)
            if element:
                return element

        # 3. 返回 None
        return None

    def normalize_selector(self, selector: str) -> str:
        """规范化选择器"""
        # 移除多余空格
        normalized = " ".join(selector.split())
        # 转义特殊字符
        normalized = self._escape_selector(normalized)
        return normalized

    def _escape_selector(self, selector: str) -> str:
        """转义选择器中的特殊字符"""
        # 转义属性值中的引号
        return re.sub(r'(["\'])([^\'"]*)\1', r'\1\2\1', selector)


class ElementMatcher:
    """
    元素匹配器

    提供基于多种策略的元素匹配功能。
    """

    def __init__(self, adapter: SelectorAdapter = None):
        self.adapter = adapter or SelectorAdapter()

    def match_by_info(
        self,
        element_info: Dict[str, Any],
        element_finder: Optional[callable] = None,
    ) -> Optional[Any]:
        """
        根据元素信息匹配元素

        Args:
            element_info: 元素信息（包含 selector, tag, text, role 等）
            element_finder: 元素查找函数

        Returns:
            匹配到的元素
        """
        selector = element_info.get("selector", "")
        fallback_selectors = self.adapter.generate_fallback_selectors(
            selector,
            element_info,
        )

        return self.adapter.match_element(
            selector,
            fallback_selectors,
            element_finder,
        )

    def match_by_text(
        self,
        text: str,
        tag: str = "*",
        exact: bool = False,
        element_finder: Optional[callable] = None,
    ) -> Optional[Any]:
        """
        根据文本内容匹配元素

        Args:
            text: 文本内容
            tag: 标签名
            exact: 是否精确匹配
            element_finder: 元素查找函数

        Returns:
            匹配到的元素
        """
        if exact:
            selector = f'{tag}:contains-exact("{text}")'
        else:
            selector = f'{tag}:contains("{text}")'

        return element_finder(selector)

    def match_by_role(
        self,
        role: str,
        name: str = None,
        element_finder: Optional[callable] = None,
    ) -> Optional[Any]:
        """
        根据 ARIA role 匹配元素

        Args:
            role: ARIA role
            name: 可访问名称（可选）
            element_finder: 元素查找函数

        Returns:
            匹配到的元素
        """
        if name:
            selector = f'[role="{role}"][aria-label*="{name}"]'
        else:
            selector = f'[role="{role}"]'

        return element_finder(selector)


class ElementInfoExtractor:
    """
    元素信息提取器

    从元素中提取用于匹配的信息。
    """

    @staticmethod
    def extract(element) -> Dict[str, Any]:
        """提取元素信息"""
        info = {
            "selector": "",  # 稍后生成
            "tag": element.tagName.lower() if hasattr(element, 'tagName') else "",
            "text": "",
            "role": "",
            "id": element.id if hasattr(element, 'id') else "",
            "className": "",
            "name": "",
            "inputType": "",
            "href": "",
            "placeholder": "",
            "attributes": {},
        }

        if hasattr(element, 'innerText'):
            info["text"] = (element.innerText or "").strip()[:100]

        if hasattr(element, 'getAttribute'):
            info["role"] = element.getAttribute("role") or ""
            info["name"] = element.getAttribute("aria-label") or ""
            info["placeholder"] = element.getAttribute("placeholder") or ""
            info["href"] = element.getAttribute("href") or ""
            info["inputType"] = element.getAttribute("type") or ""

            if hasattr(element, 'className'):
                info["className"] = element.className or ""

            # 提取所有 data 属性
            for attr in element.attributes:
                if attr.name.startswith("data-"):
                    info["attributes"][attr.name] = attr.value

        return info

    @staticmethod
    def generate_selector(element, adapter: SelectorAdapter = None) -> str:
        """生成元素选择器"""
        adapter = adapter or SelectorAdapter()
        return adapter.normalize_selector(adapter.generate_fallback_selectors("", {})[0])


# ========== 便捷函数 ==========

def create_adapter() -> SelectorAdapter:
    """创建选择器适配器"""
    return SelectorAdapter()


def create_matcher(adapter: SelectorAdapter = None) -> ElementMatcher:
    """创建元素匹配器"""
    return ElementMatcher(adapter)


def extract_info(element) -> Dict[str, Any]:
    """提取元素信息"""
    return ElementInfoExtractor.extract(element)


__all__ = [
    "SelectorAdapter",
    "ElementMatcher",
    "ElementInfoExtractor",
    "create_adapter",
    "create_matcher",
    "extract_info",
]