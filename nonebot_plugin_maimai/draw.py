"""
绘制单曲查询结果卡片，包含封面图、基本信息和难度表格。
"""

from __future__ import annotations

import io
import os
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from .image_utils import (
    BG_COLOR,
    BORDER_COLOR,
    TEXT_COLOR,
    TITLE_COLOR,
    PAD,
    ROW_H,
    _text_size,
    draw_table,
    get_font,
)

# 封面图目标尺寸（正方形）
COVER_SIZE = 160

# 难度行配色
_DIFF_COLORS: dict[str, Tuple[int, int, int]] = {
    "Basic": (200, 240, 200),
    "Advanced": (255, 240, 180),
    "Expert": (255, 200, 200),
    "Master": (220, 200, 255),
    "Re:MASTER": (240, 210, 255),
    "Utage": (200, 230, 255),
}

_DIFF_ORDER = {"Basic": 0, "Advanced": 1, "Expert": 2,
               "Master": 3, "Re:MASTER": 4, "Utage": 5}


def _load_cover(cover_dir: str, image_file: str) -> Optional[Image.Image]:
    """加载封面图，失败时返回 None。"""
    if not image_file or image_file.strip().lower() == "nan":
        return None
    path = os.path.join(cover_dir, image_file.strip())
    if not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGB")
        img = img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        return img
    except Exception:
        return None


def draw_song_card(rows: List[dict], cover_dir: str) -> bytes:
    """
    绘制单曲查询卡片，返回 PNG 字节。

    Args:
        rows: 由 ``get_song_rows`` 返回的原始行列表（同一首歌的各难度）。
        cover_dir: 封面图目录路径。

    Returns:
        PNG 格式的图片字节。若 rows 为空，则返回错误提示图。
    """
    if not rows:
        font = get_font(16)
        msg = "未找到歌曲数据"
        probe = Image.new("RGB", (1, 1))
        probe_draw = ImageDraw.Draw(probe)
        tw, th = _text_size(probe_draw, msg, font)
        img = Image.new("RGB", (tw + PAD * 4, th + PAD * 4), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw.text((PAD * 2, PAD * 2), msg, font=font, fill=(200, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    base = rows[0]
    title = str(base.get("Title", "?"))
    song_id = str(base.get("Song ID", "?")).strip()
    artist = str(base.get("Artist", "?"))
    bpm = str(base.get("BPM", "?"))
    genre = str(base.get("Genre", "?"))
    version = str(base.get("Version", "?"))
    song_type = str(base.get("Type", "?"))
    aliases = str(base.get("Aliases", ""))
    if aliases == "nan":
        aliases = "无"
    if len(aliases) > 80:
        aliases = aliases[:80] + "…"
    image_file = str(base.get("Image_File", ""))

    info_lines = [
        f"🎵 {title}  (ID: {song_id})",
        f"艺术家：{artist}　BPM：{bpm}",
        f"分区：{genre}　版本：{version}　类型：{song_type}",
        f"别名：{aliases}",
    ]

    # 按难度排序
    sorted_rows = sorted(rows, key=lambda r: _DIFF_ORDER.get(r.get("Difficulty", ""), 9))

    diff_headers = ["难度", "等级", "定数", "拟合", "物量", "属性"]
    diff_rows = []
    for row in sorted_rows:
        diff = str(row.get("Difficulty", "-"))
        level = str(row.get("Level Label", "-"))
        ds = str(row.get("Official DS", "-"))
        fit_raw = row.get("Chart_fit_diff", "")
        try:
            fit_raw_str = str(fit_raw).strip()
            fit_str = f"{float(fit_raw_str):.2f}" if fit_raw_str and fit_raw_str.lower() != "nan" else "-"
        except (ValueError, TypeError):
            fit_str = "-"
        notes = str(row.get("Total Notes", "-"))
        note_type = str(row.get("Ana_NoteType", "-"))
        if note_type == "综合":
            note_type = "-"
        diff_rows.append([diff, level, ds, fit_str, notes, note_type])

    row_colors = [_DIFF_COLORS.get(r[0]) for r in diff_rows]

    # 绘制难度表格
    table_bytes = draw_table(diff_headers, diff_rows, row_colors=row_colors, font_size=14)
    table_img = Image.open(io.BytesIO(table_bytes))
    tw, th = table_img.size

    # 测量信息文字高度
    font = get_font(15)
    title_font = get_font(17)
    probe = Image.new("RGB", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    line_heights = []
    for i, line in enumerate(info_lines):
        f = title_font if i == 0 else font
        _, h = _text_size(probe_draw, line, f)
        line_heights.append(h + 4)
    info_h = sum(line_heights) + PAD * 2

    # 封面图
    cover_img = _load_cover(cover_dir, image_file)

    cover_w = (COVER_SIZE + PAD * 2) if cover_img is not None else 0
    text_area_w = max(tw, 500)
    total_w = cover_w + text_area_w + PAD * 2
    info_block_h = max(info_h, COVER_SIZE + PAD * 2) if cover_img is not None else info_h
    total_h = info_block_h + PAD + 1 + PAD + th + PAD * 2

    img = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 粘贴封面图（左侧垂直居中于信息区）
    text_x = PAD
    if cover_img is not None:
        cover_y = PAD + (info_block_h - COVER_SIZE) // 2
        img.paste(cover_img, (PAD, cover_y))
        text_x = PAD + COVER_SIZE + PAD

    # 绘制信息文字
    y = PAD
    for i, line in enumerate(info_lines):
        f = title_font if i == 0 else font
        color = TITLE_COLOR if i == 0 else TEXT_COLOR
        draw.text((text_x, y), line, font=f, fill=color)
        y += line_heights[i]

    # 分隔线
    sep_y = info_block_h + PAD
    draw.line([(PAD, sep_y), (total_w - PAD, sep_y)], fill=BORDER_COLOR, width=1)

    # 粘贴难度表
    table_y = sep_y + PAD
    img.paste(table_img, (PAD, table_y))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
