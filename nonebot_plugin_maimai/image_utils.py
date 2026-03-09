"""
图片生成工具：加载字体、绘制表格等共用函数。
"""

from __future__ import annotations

import io
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# 字体加载
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

_FONT_PATHS = [
    # Linux 常见中文字体
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    # Windows 常见中文字体
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
]


def get_font(size: int = 16) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """返回指定大小的字体，优先使用支持中文的字体，否则回退到默认字体。"""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    for path in _FONT_PATHS:
        try:
            font = ImageFont.truetype(path, size)
            _FONT_CACHE[size] = font
            return font
        except (IOError, OSError):
            continue
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


# ---------------------------------------------------------------------------
# 颜色常量
# ---------------------------------------------------------------------------

BG_COLOR = (245, 245, 250)
HEADER_BG = (60, 60, 100)
HEADER_FG = (255, 255, 255)
ROW_BG_EVEN = (255, 255, 255)
ROW_BG_ODD = (235, 235, 245)
TEXT_COLOR = (30, 30, 30)
BORDER_COLOR = (180, 180, 200)
CORRECT_BG = (200, 240, 200)    # 猜对行的背景色
TITLE_COLOR = (40, 40, 120)

# 比较符号颜色映射
SYMBOL_COLORS = {
    "√": (0, 160, 0),
    "×": (200, 0, 0),
    "↑": (0, 100, 200),
    "↓": (200, 100, 0),
    "○": (160, 100, 0),
    "?": (120, 120, 120),
}


def _symbol_color(text: str) -> Tuple[int, int, int]:
    """根据文本中包含的比较符号返回颜色。"""
    for sym, color in SYMBOL_COLORS.items():
        if sym in text:
            return color
    return TEXT_COLOR


# ---------------------------------------------------------------------------
# 文字尺寸测量
# ---------------------------------------------------------------------------

def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> Tuple[int, int]:
    """返回 (width, height) 文本尺寸，兼容新旧 Pillow API。"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 通用表格绘制
# ---------------------------------------------------------------------------

PAD = 8       # 单元格内边距
ROW_H = 28    # 行高


def draw_table(
    headers: List[str],
    rows: List[List[str]],
    col_widths: Optional[List[int]] = None,
    row_colors: Optional[List[Optional[Tuple[int, int, int]]]] = None,
    title: str = "",
    font_size: int = 14,
) -> bytes:
    """
    绘制通用表格并返回 PNG 字节。

    Args:
        headers: 表头文字列表。
        rows: 每行数据（字符串列表）。
        col_widths: 可选的列宽列表（像素）。若为 None 则自动计算。
        row_colors: 每行可选的背景色，None 表示使用默认交替色。
        title: 可选的标题文字（绘制在表格上方）。
        font_size: 字体大小。

    Returns:
        PNG 格式的图片字节。
    """
    font = get_font(font_size)
    title_font = get_font(font_size + 4)

    # 先用临时画布测量文字宽度
    probe = Image.new("RGB", (1, 1))
    probe_draw = ImageDraw.Draw(probe)

    n_cols = len(headers)

    # 计算列宽
    if col_widths is None:
        col_widths = []
        for i in range(n_cols):
            w = _text_size(probe_draw, headers[i], font)[0] + PAD * 2
            for row in rows:
                if i < len(row):
                    w = max(w, _text_size(probe_draw, row[i], font)[0] + PAD * 2)
            col_widths.append(w)

    total_w = sum(col_widths) + n_cols + 1  # 包含竖线

    # 标题高度
    title_h = 0
    if title:
        title_h = _text_size(probe_draw, title, title_font)[1] + PAD * 2

    header_h = ROW_H
    table_h = header_h + len(rows) * ROW_H + len(rows) + 1  # 包含横线
    total_h = title_h + table_h + PAD * 2

    img = Image.new("RGB", (total_w + PAD * 2, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 标题
    y = PAD
    if title:
        draw.text((PAD, y), title, font=title_font, fill=TITLE_COLOR)
        y += title_h

    # 表格起始坐标
    tx = PAD
    ty = y

    # 表头背景
    draw.rectangle([tx, ty, tx + total_w - 1, ty + header_h - 1], fill=HEADER_BG)

    # 绘制表头文字
    x = tx + 1
    for i, h in enumerate(headers):
        draw.text((x + PAD, ty + (header_h - font_size) // 2), h, font=font, fill=HEADER_FG)
        x += col_widths[i] + 1  # +1 for border

    # 绘制数据行
    for ri, row in enumerate(rows):
        ry = ty + header_h + ri * ROW_H + ri + 1
        # 行背景
        if row_colors and ri < len(row_colors) and row_colors[ri] is not None:
            bg = row_colors[ri]
        else:
            bg = ROW_BG_EVEN if ri % 2 == 0 else ROW_BG_ODD
        draw.rectangle([tx, ry, tx + total_w - 1, ry + ROW_H - 1], fill=bg)

        x = tx + 1
        for ci, cell in enumerate(row):
            if ci >= n_cols:
                break
            color = _symbol_color(cell)
            draw.text(
                (x + PAD, ry + (ROW_H - font_size) // 2),
                cell,
                font=font,
                fill=color,
            )
            x += col_widths[ci] + 1

    # 绘制网格线（先列后行）
    # 列线
    x = tx
    for w in col_widths:
        draw.line([(x, ty), (x, ty + table_h - 1)], fill=BORDER_COLOR)
        x += w + 1
    draw.line([(x, ty), (x, ty + table_h - 1)], fill=BORDER_COLOR)

    # 行线
    for ri in range(len(rows) + 2):
        if ri == 0:
            line_y = ty
        elif ri == 1:
            line_y = ty + header_h
        else:
            line_y = ty + header_h + (ri - 1) * ROW_H + (ri - 1)
        draw.line([(tx, line_y), (tx + total_w - 1, line_y)], fill=BORDER_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
