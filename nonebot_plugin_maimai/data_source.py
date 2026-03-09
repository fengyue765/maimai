"""
数据源适配层：将原始模块的输出从 print() 改为返回字符串，
供 NoneBot2 命令处理器调用。
"""

from __future__ import annotations

import csv
import io
import os
import sys
from typing import List, Optional

import pandas as pd
from PIL import Image, ImageDraw

from . import image_utils


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _load_csv_rows(csv_path: str) -> List[dict]:
    """读取 CSV 文件，兼容 UTF-8 和 GBK 编码。"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"找不到数据文件: {csv_path}，请先执行「更新数据库」。"
        )
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        with open(csv_path, "r", encoding="gbk") as f:
            return list(csv.DictReader(f))


def _parse_ds_range(user_input: str) -> Optional[List[str]]:
    """
    解析用户输入的定数或等级，返回匹配的官方定数字符串列表。
    支持：整数 "13"、半星 "13+"、具体定数 "13.5"。
    """
    user_input = user_input.strip()
    try:
        if user_input.endswith("+"):
            base = int(user_input[:-1])
            return [f"{base + 0.6:.1f}", f"{base + 0.7:.1f}",
                    f"{base + 0.8:.1f}", f"{base + 0.9:.1f}"]
        elif "." in user_input:
            val = float(user_input)
            return [f"{val:.1f}"]
        else:
            base = int(user_input)
            return [f"{base + i * 0.1:.1f}" for i in range(6)]
    except ValueError:
        return None


def _ds_range_label(user_input: str) -> str:
    """将用户输入转换为可读的定数范围描述。"""
    user_input = user_input.strip()
    if user_input.endswith("+"):
        base = int(user_input[:-1])
        return f"{base + 0.6:.1f}–{base + 0.9:.1f}"
    elif "." in user_input:
        return f"{float(user_input):.1f}"
    else:
        base = int(user_input)
        return f"{base}.0–{base}.5"


# ---------------------------------------------------------------------------
# 推荐功能（水曲 / 诈称）
# ---------------------------------------------------------------------------

def get_water_songs(user_input: str, csv_path: str) -> str:
    """返回格式化的逆诈称（水曲）列表文本。"""
    target_ds_list = _parse_ds_range(user_input)
    if target_ds_list is None:
        return "⚠️ 输入格式无效，示例：13、13+、13.5"

    rows = _load_csv_rows(csv_path)

    serious_water: List[dict] = []
    water: List[dict] = []

    for row in rows:
        genre = row.get("Genre", "").strip()
        if genre == "宴会場":
            continue
        official_ds = row.get("Official DS", "").strip()
        status = row.get("Ana_DiffBias", "")
        if official_ds in target_ds_list:
            if "严重逆诈称" in status:
                serious_water.append(row)
            elif "逆诈称" in status:
                water.append(row)

    def _fit(r: dict) -> float:
        try:
            return float(r.get("Chart_fit_diff", "0") or "0")
        except ValueError:
            return 0.0

    serious_water.sort(key=_fit)
    water.sort(key=_fit)

    range_label = _ds_range_label(user_input)
    lines = [f"🎵 定数 [{range_label}] 吃分推荐（逆诈称）\n"]

    def _fmt_section(title: str, data: List[dict]) -> str:
        if not data:
            return f"【{title}】暂无数据\n"
        buf = [f"【{title}】共 {len(data)} 首"]
        for r in data:
            fit = _fit(r)
            fit_s = f"{fit:.2f}" if fit else "-"
            buf.append(
                f"  [{r.get('Song ID', '?')}] {r.get('Title', '?')} "
                f"({r.get('Type', '?')} {r.get('Difficulty', '?')}) "
                f"定数 {r.get('Official DS', '?')} 拟合 {fit_s}"
            )
        return "\n".join(buf)

    lines.append(_fmt_section("严重逆诈称（大水）", serious_water))
    lines.append(_fmt_section("逆诈称（小水）", water))
    return "\n".join(lines)


def get_landmine_songs(user_input: str, csv_path: str) -> str:
    """返回格式化的诈称（地雷）列表文本。"""
    target_ds_list = _parse_ds_range(user_input)
    if target_ds_list is None:
        return "⚠️ 输入格式无效，示例：13、13+、13.5"

    rows = _load_csv_rows(csv_path)

    serious_mine: List[dict] = []
    mine: List[dict] = []

    for row in rows:
        genre = row.get("Genre", "").strip()
        if genre == "宴会場":
            continue
        official_ds = row.get("Official DS", "").strip()
        status = row.get("Ana_DiffBias", "")
        if official_ds in target_ds_list:
            if "严重诈称" in status:
                serious_mine.append(row)
            elif "诈称" in status and "逆" not in status:
                mine.append(row)

    def _fit(r: dict) -> float:
        try:
            return float(r.get("Chart_fit_diff", "0") or "0")
        except ValueError:
            return 0.0

    serious_mine.sort(key=_fit, reverse=True)
    mine.sort(key=_fit, reverse=True)

    range_label = _ds_range_label(user_input)
    lines = [f"⚠️ 定数 [{range_label}] 地雷警报（诈称）\n"]

    def _fmt_section(title: str, data: List[dict]) -> str:
        if not data:
            return f"【{title}】暂无数据\n"
        buf = [f"【{title}】共 {len(data)} 首"]
        for r in data:
            fit = _fit(r)
            fit_s = f"{fit:.2f}" if fit else "-"
            buf.append(
                f"  [{r.get('Song ID', '?')}] {r.get('Title', '?')} "
                f"({r.get('Type', '?')} {r.get('Difficulty', '?')}) "
                f"定数 {r.get('Official DS', '?')} 拟合 {fit_s}"
            )
        return "\n".join(buf)

    lines.append(_fmt_section("严重诈称（大雷）", serious_mine))
    lines.append(_fmt_section("诈称（小雷）", mine))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 单曲信息查询
# ---------------------------------------------------------------------------

def _build_song_index(df: pd.DataFrame):
    """构建别名索引，返回 (alias_map, id_to_title)。"""
    alias_map: dict[str, list[str]] = {}
    id_to_title: dict[str, str] = {}

    unique = df[["Song ID", "Title", "Aliases"]].drop_duplicates(subset=["Song ID"])
    for _, row in unique.iterrows():
        sid = str(row["Song ID"]).strip()
        title = str(row["Title"]).strip()
        aliases_str = str(row.get("Aliases", ""))

        id_to_title[sid] = title

        # 索引 ID
        alias_map.setdefault(sid, [])
        if sid not in alias_map[sid]:
            alias_map[sid].append(sid)

        # 索引曲名
        tl = title.lower()
        alias_map.setdefault(tl, [])
        if sid not in alias_map[tl]:
            alias_map[tl].append(sid)

        # 索引别名
        if aliases_str and aliases_str != "nan":
            for alias in aliases_str.split(";"):
                alias = alias.strip()
                if alias:
                    al = alias.lower()
                    alias_map.setdefault(al, [])
                    if sid not in alias_map[al]:
                        alias_map[al].append(sid)

    return alias_map, id_to_title


def search_songs(query: str, csv_path: str) -> List[str]:
    """搜索歌曲，返回匹配的 Song ID 列表。"""
    df = pd.read_csv(csv_path, encoding="utf-8", dtype={"Song ID": str})
    df.columns = [c.strip() for c in df.columns]
    alias_map, _ = _build_song_index(df)

    query = query.strip().lower()
    matched: set[str] = set()
    if query in alias_map:
        matched.update(alias_map[query])
    for key, sids in alias_map.items():
        if query in key:
            matched.update(sids)
    return list(matched)


def get_song_detail(song_id: str, csv_path: str) -> str:
    """返回单曲详情的格式化文本。"""
    df = pd.read_csv(csv_path, encoding="utf-8", dtype={"Song ID": str})
    df.columns = [c.strip() for c in df.columns]

    song_rows = df[df["Song ID"] == str(song_id)]
    if song_rows.empty:
        return f"❌ 未找到 ID: {song_id}"

    base = song_rows.iloc[0]
    title = base["Title"]
    aliases = str(base.get("Aliases", ""))
    if aliases == "nan":
        aliases = "无"

    lines = [
        f"🎵 {title} (ID: {song_id})",
        f"艺术家：{base.get('Artist', '?')}　BPM：{base.get('BPM', '?')}",
        f"分类：{base.get('Genre', '?')}　版本：{base.get('Version', '?')}",
        f"类型：{base.get('Type', '?')}",
        f"别名：{aliases[:80]}{'…' if len(aliases) > 80 else ''}",
        "",
        "难度   | 等级  | 定数  | 拟合  | 物量  | 属性",
        "-" * 48,
    ]

    order = {"Basic": 0, "Advanced": 1, "Expert": 2, "Master": 3, "Re:MASTER": 4, "Utage": 5}
    for _, row in sorted(song_rows.iterrows(), key=lambda x: order.get(x[1].get("Difficulty", ""), 9)):
        diff = str(row.get("Difficulty", "-"))
        level = str(row.get("Level Label", "-"))
        ds = str(row.get("Official DS", "-"))
        fit = row.get("Chart_fit_diff", "")
        try:
            fit_str = f"{float(fit):.2f}" if pd.notna(fit) and str(fit).strip() else "-"
        except (ValueError, TypeError):
            fit_str = "-"
        notes = str(row.get("Total Notes", "-"))
        note_type = str(row.get("Ana_NoteType", "-"))
        if note_type == "综合":
            note_type = "-"
        lines.append(f"{diff:<8} | {level:<5} | {ds:<5} | {fit_str:<5} | {notes:<5} | {note_type}")

    return "\n".join(lines)


def get_id_to_title(csv_path: str) -> dict[str, str]:
    """返回 song_id -> title 映射。"""
    df = pd.read_csv(csv_path, encoding="utf-8", dtype={"Song ID": str})
    df.columns = [c.strip() for c in df.columns]
    _, id_to_title = _build_song_index(df)
    return id_to_title


# ---------------------------------------------------------------------------
# 跨定数区间查询
# ---------------------------------------------------------------------------

def get_cross_tier_songs(range_a_str: str, range_b_str: str, csv_path: str) -> str:
    """返回跨定数区间查询结果的格式化文本。"""

    def _parse(s: str):
        parts = s.strip().split("-")
        if len(parts) != 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    range_a = _parse(range_a_str)
    range_b = _parse(range_b_str)

    if range_a is None:
        return f"⚠️ 区间 A 格式错误：{range_a_str}（示例：12.0-12.5）"
    if range_b is None:
        return f"⚠️ 区间 B 格式错误：{range_b_str}（示例：14.0-14.5）"

    df = pd.read_csv(csv_path, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    df["Official DS"] = pd.to_numeric(df["Official DS"], errors="coerce")

    results = []
    for song_id, group in df.groupby("Song ID"):
        charts_a = group[(group["Official DS"] >= range_a[0]) & (group["Official DS"] <= range_a[1])]
        charts_b = group[(group["Official DS"] >= range_b[0]) & (group["Official DS"] <= range_b[1])]

        if charts_a.empty or charts_b.empty:
            continue

        valid_pairs = [
            (ca, cb)
            for _, ca in charts_a.iterrows()
            for _, cb in charts_b.iterrows()
            if ca["Difficulty"] != cb["Difficulty"]
        ]

        if valid_pairs:
            ca, cb = valid_pairs[0]
            results.append({
                "id": song_id,
                "title": group.iloc[0]["Title"],
                "a": f"{ca['Difficulty']} {ca['Official DS']}",
                "b": f"{cb['Difficulty']} {cb['Official DS']}",
            })

    if not results:
        return (
            f"🔍 未找到同时包含 [{range_a[0]}–{range_a[1]}] 和 "
            f"[{range_b[0]}–{range_b[1]}] 的歌曲。"
        )

    lines = [
        f"🔍 跨定数区间查询结果：[{range_a[0]}–{range_a[1]}] × [{range_b[0]}–{range_b[1]}]",
        f"共找到 {len(results)} 首歌曲：",
        "",
    ]
    for r in results:
        title = r["title"]
        if len(title) > 22:
            title = title[:21] + "…"
        lines.append(f"[{r['id']}] {title}  {r['a']} / {r['b']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 单曲信息图片生成
# ---------------------------------------------------------------------------

def get_song_detail_image(song_id: str, csv_path: str) -> bytes:
    """返回单曲详情的图片字节（PNG）。"""
    df = pd.read_csv(csv_path, encoding="utf-8", dtype={"Song ID": str})
    df.columns = [c.strip() for c in df.columns]

    song_rows = df[df["Song ID"] == str(song_id)]
    if song_rows.empty:
        # 返回错误提示图片
        img = Image.new("RGB", (400, 80), (255, 230, 230))
        draw = ImageDraw.Draw(img)
        font = image_utils.get_font(18)
        draw.text((16, 24), f"未找到 ID: {song_id}", font=font, fill=(180, 0, 0))
        return image_utils.image_to_bytes(img)

    base = song_rows.iloc[0]
    title = str(base["Title"])
    artist = str(base.get("Artist", "?"))
    bpm = str(base.get("BPM", "?"))
    genre = str(base.get("Genre", "?"))
    version = str(base.get("Version", "?"))
    song_type = str(base.get("Type", "?"))
    aliases = str(base.get("Aliases", ""))
    if aliases == "nan":
        aliases = "无"

    # 难度表格
    diff_order = {"Basic": 0, "Advanced": 1, "Expert": 2, "Master": 3, "Re:MASTER": 4, "Utage": 5}
    diff_headers = ["难度", "等级", "定数", "拟合", "物量", "属性"]
    diff_rows: List[List[str]] = []
    for _, row in sorted(song_rows.iterrows(), key=lambda x: diff_order.get(x[1].get("Difficulty", ""), 9)):
        diff = str(row.get("Difficulty", "-"))
        level = str(row.get("Level Label", "-"))
        ds = str(row.get("Official DS", "-"))
        fit_raw = row.get("Chart_fit_diff", "")
        try:
            fit_str = f"{float(fit_raw):.2f}" if pd.notna(fit_raw) and str(fit_raw).strip() else "-"
        except (ValueError, TypeError):
            fit_str = "-"
        notes = str(row.get("Total Notes", "-"))
        note_type = str(row.get("Ana_NoteType", "-"))
        if note_type == "综合":
            note_type = "-"
        diff_rows.append([diff, level, ds, fit_str, notes, note_type])

    # 估算图片尺寸
    font_size = 16
    padding = 8
    line_h = font_size + padding * 2

    font = image_utils.get_font(font_size)

    # 将别名截断到合理宽度（最多 400px）
    aliases = image_utils.truncate_text(aliases, font, 400)

    info_lines = [
        f"  {title}  (ID: {song_id})",
        f"艺术家: {artist}    BPM: {bpm}",
        f"分类: {genre}    版本: {version}",
        f"类型: {song_type}",
        f"别名: {aliases}",
    ]

    # 计算信息区宽度
    info_area_width = max(image_utils.text_width(line, font) for line in info_lines) + padding * 4

    # 计算表格列宽
    col_widths = []
    for i, h in enumerate(diff_headers):
        max_w = image_utils.text_width(h, font)
        for dr in diff_rows:
            cell = str(dr[i]) if i < len(dr) else ""
            max_w = max(max_w, image_utils.text_width(cell, font))
        col_widths.append(max_w + padding * 2)

    table_width = sum(col_widths)
    img_width = max(info_area_width, table_width + padding * 2)
    info_area_height = len(info_lines) * line_h + padding * 2
    table_height = line_h * (len(diff_rows) + 1) + padding * 2
    img_height = info_area_height + table_height + padding

    image = Image.new("RGB", (img_width, img_height), (250, 250, 255))
    draw = ImageDraw.Draw(image)

    # 绘制信息区背景
    draw.rectangle([0, 0, img_width, info_area_height], fill=(230, 235, 255))

    title_font = image_utils.get_font(font_size + 2)
    y = padding
    draw.text((padding * 2, y), info_lines[0], font=title_font, fill=(30, 30, 120))
    y += line_h
    for line in info_lines[1:]:
        draw.text((padding * 2, y), line, font=font, fill=(50, 50, 80))
        y += line_h

    # 绘制难度表格
    image_utils.draw_table(
        draw=draw,
        headers=diff_headers,
        rows=diff_rows,
        start_x=padding,
        start_y=info_area_height + padding,
        col_widths=col_widths,
        font_size=font_size,
        padding=padding,
    )

    return image_utils.image_to_bytes(image)
