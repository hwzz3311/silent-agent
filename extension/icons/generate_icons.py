#!/usr/bin/env python3
"""
生成 Neurone 扩展图标

运行: python generate_icons.py
需要: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("请安装 Pillow: pip install pillow")
    exit(1)

import os

SIZES = [16, 32, 48, 128]

def create_icon(size):
    """创建指定尺寸的图标"""
    # 创建图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆形背景（渐变效果模拟）
    padding = size // 8
    
    # 外圈 - 深绿色
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=(34, 197, 94)  # #22C55E
    )
    
    # 内圈 - 稍浅
    inner_padding = size // 5
    draw.ellipse(
        [inner_padding, inner_padding, size - inner_padding, size - inner_padding],
        fill=(74, 222, 128)  # #4ADE80
    )
    
    # 绘制大脑/神经元图案（简化为连接的点）
    center = size // 2
    radius = size // 6
    
    # 中心点
    draw.ellipse(
        [center - radius//2, center - radius//2, 
         center + radius//2, center + radius//2],
        fill='white'
    )
    
    # 连接线（简化表示神经元连接）
    if size >= 32:
        line_width = max(1, size // 16)
        offsets = [
            (-radius, -radius),
            (radius, -radius),
            (-radius, radius),
            (radius, radius),
        ]
        for ox, oy in offsets:
            draw.line(
                [(center, center), (center + ox, center + oy)],
                fill='white',
                width=line_width
            )
            # 端点小圆
            draw.ellipse(
                [center + ox - line_width, center + oy - line_width,
                 center + ox + line_width, center + oy + line_width],
                fill='white'
            )
    
    return img


def main():
    """生成所有尺寸的图标"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    for size in SIZES:
        icon = create_icon(size)
        filename = f"icon{size}.png"
        filepath = os.path.join(script_dir, filename)
        icon.save(filepath, 'PNG')
        print(f"✓ 已生成 {filename}")
        
    print("\n所有图标已生成!")


if __name__ == "__main__":
    main()

