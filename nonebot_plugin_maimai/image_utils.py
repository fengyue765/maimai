"""
图片生成工具：提供字体加载、表格绘制等共享工具函数。
"""

from __future__ import annotations

import io
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# 字体
# ---------------------------------------------------------------------------

def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """尝试加载中文字体，失败时回退到默认字体。"""
    font_candidates = [
        "msyh.ttc",
        "msyh.ttf",
        "simhei.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for name in font_candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# 文本测量
# ---------------------------------------------------------------------------

def text_width(text: str, font) -> int:
    """测量文本宽度（像素）。"""
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except AttributeError:
        # 回退：使用固定宽度估算
        size = getattr(font, "size", 14)
        return len(text) * size


def truncate_text(text: str, font, max_width: int) -> str:
    """如果文本超出最大宽度，截断并添加省略号。"""
    if text_width(text, font) <= max_width:
        return text
    ellipsis = "…"
    ellipsis_w = text_width(ellipsis, font)
    budget = max_width - ellipsis_w
    while text and text_width(text, font) > budget:
        text = text[:-1]
    return text + ellipsis


# ---------------------------------------------------------------------------
# 表格绘制
# ---------------------------------------------------------------------------

def draw_table(
    draw: ImageDraw.ImageDraw,
    headers: List[str],
    rows: List[List[str]],
    start_x: int,
    start_y: int,
    col_widths: Optional[List[int]] = None,
    font_size: int = 16,
    padding: int = 8,
) -> int:
    """
    在画布上绘制简单表格。

    Args:
        draw:       PIL ImageDraw 对象
        headers:    表头列表
        rows:       数据行（每行是字符串列表）
        start_x:    表格起始 x 坐标
        start_y:    表格起始 y 坐标
        col_widths: 各列宽度（像素）；若为 None，则按内容自动计算
        font_size:  字体大小
        padding:    单元格内边距

    Returns:
        表格底部 y 坐标
    """
    font = get_font(font_size)
    header_font = get_font(font_size)

    # 自动计算列宽
    if col_widths is None:
        col_widths = []
        for i, h in enumerate(headers):
            max_w = text_width(h, header_font)
            for row in rows:
                cell = str(row[i]) if i < len(row) else ""
                max_w = max(max_w, text_width(cell, font))
            col_widths.append(max_w + padding * 2)

    row_height = font_size + padding * 2
    total_width = sum(col_widths)

    # 表头
    draw.rectangle(
        [start_x, start_y, start_x + total_width, start_y + row_height],
        fill=(60, 60, 120),
    )
    cx = start_x
    for i, h in enumerate(headers):
        draw.text((cx + padding, start_y + padding), h, font=header_font, fill=(255, 255, 255))
        cx += col_widths[i]

    y = start_y + row_height

    # 数据行
    for ri, row in enumerate(rows):
        bg = (240, 240, 255) if ri % 2 == 0 else (255, 255, 255)
        draw.rectangle([start_x, y, start_x + total_width, y + row_height], fill=bg)
        cx = start_x
        for ci in range(len(headers)):
            cell = str(row[ci]) if ci < len(row) else ""
            cell = truncate_text(cell, font, col_widths[ci] - padding * 2)
            draw.text((cx + padding, y + padding), cell, font=font, fill=(0, 0, 0))
            cx += col_widths[ci]
        y += row_height

    # 外边框
    draw.rectangle(
        [start_x, start_y, start_x + total_width, y],
        outline=(100, 100, 150),
        width=1,
    )

    return y


# ---------------------------------------------------------------------------
# 图片导出
# ---------------------------------------------------------------------------

def image_to_bytes(image: Image.Image) -> bytes:
    """将 PIL Image 转换为 PNG 字节串。"""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
