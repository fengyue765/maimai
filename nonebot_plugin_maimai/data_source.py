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
from PIL import Image, ImageDraw, ImageFont
from nonebot import get_plugin_config
from .config import Config

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
    """构建别名索引，返回 (alias_map, id_to_title)。
       注意：现在 ID 使用完全匹配，名称使用子串匹配。
    """
    alias_map: dict[str, list[str]] = {}
    id_to_title: dict[str, str] = {}

    unique = df[["Song ID", "Title", "Aliases"]].drop_duplicates(subset=["Song ID"])
    for _, row in unique.iterrows():
        sid = str(row["Song ID"]).strip()
        title = str(row["Title"]).strip()
        aliases_str = str(row.get("Aliases", ""))

        id_to_title[sid] = title

        # 索引 ID - 使用完全匹配（只存原始ID，不存部分）
        alias_map.setdefault(sid, [])
        if sid not in alias_map[sid]:
            alias_map[sid].append(sid)

        # 索引曲名 - 保留子串匹配
        tl = title.lower()
        alias_map.setdefault(tl, [])
        if sid not in alias_map[tl]:
            alias_map[tl].append(sid)

        # 索引别名 - 保留子串匹配
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

    query = query.strip()
    matched: set[str] = set()
    
    # 判断是否是纯数字
    if query.isdigit():
        # 纯数字：完全匹配
        if query in alias_map:
            matched.update(alias_map[query])
    else:
        # 非纯数字：子串匹配（转小写）
        query_lower = query.lower()
        for key, sids in alias_map.items():
            if query_lower in key:
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
        f"{title} (ID: {song_id})",
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


def get_song_detail_image(song_id: str, csv_path: str) -> bytes | str:
    """生成包含封面的歌曲详情图片，返回图片字节数据。"""
    rows = _load_csv_rows(csv_path)
    
    # 查找歌曲数据
    song_row = None
    for r in rows:
        if str(r.get("Song ID")) == str(song_id):
            song_row = r
            break
            
    if not song_row:
        return f"❌ 未找到 ID: {song_id}"

    # 读取配置中的封面目录
    config = get_plugin_config(Config)
    cover_dir = config.maimai_cover_dir
    image_file = song_row.get("Image_File", "")
    
    # 尝试加载封面
    cover_img = None
    if image_file and os.path.exists(cover_dir):
        cover_path = os.path.join(cover_dir, image_file)
        if os.path.exists(cover_path):
            try:
                cover_img = Image.open(cover_path).convert("RGBA")
            except Exception:
                pass

    # --- 开始绘图 ---
    # 画布尺寸
    width = 600
    height = 400
    bg_color = (240, 240, 240)
    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 字体 (尝试加载系统字体，否则使用默认)
    try:
        # 这里为了演示简单使用了默认字体，建议换成实际存在的字体路径，如 "msyh.ttc"
        font_title = ImageFont.truetype("msyh.ttc", 24)
        font_text = ImageFont.truetype("msyh.ttc", 18)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # 1. 绘制封面 (左上角)
    if cover_img:
        # 调整封面大小为 150x150
        cover_img = cover_img.resize((150, 150))
        img.paste(cover_img, (20, 20), cover_img)
    else:
        # 绘制灰色占位符
        draw.rectangle([(20, 20), (170, 170)], fill=(200, 200, 200), outline=(100, 100, 100))
        draw.text((60, 80), "No Cover", fill=(0, 0, 0), font=font_text)

    # 2. 绘制基本信息 (右侧)
    title = song_row.get("Title", "Unknown")
    artist = song_row.get("Artist", "Unknown")
    bpm = song_row.get("BPM", "?")
    genre = song_row.get("Genre", "-")
    version = song_row.get("Version", "-")
    
    text_x = 190
    draw.text((text_x, 20), f"{title}", fill=(0, 0, 0), font=font_title)
    draw.text((text_x, 60), f"Artist: {artist}", fill=(50, 50, 50), font=font_text)
    draw.text((text_x, 90), f"BPM: {bpm}  |  Genre: {genre}", fill=(50, 50, 50), font=font_text)
    draw.text((text_x, 120), f"Ver: {version}", fill=(50, 50, 50), font=font_text)

    # 3. 绘制难度列表 (下方)
    # 简单绘制一个表格
    table_y = 200
    headers = ["Diff", "Level", "DS", "Notes", "Fit"]
    col_widths = [100, 80, 80, 80, 80]
    
    # 表头
    curr_x = 20
    for i, h in enumerate(headers):
        draw.text((curr_x, table_y), h, fill=(0, 0, 0), font=font_text)
        curr_x += col_widths[i]
    
    draw.line([(20, table_y + 25), (width - 20, table_y + 25)], fill=(0, 0, 0), width=1)

    # 难度数据
    diffs = ["Basic", "Advanced", "Expert", "Master", "Re:MASTER"]
    row_h = 30
    curr_y = table_y + 35
    
    # 这里需要重新遍历 CSV 或根据 song_row 的数据结构来获取各难度信息
    # 由于 song_row 是一行数据（对应一个难度），我们需要再次查询该 Song ID 的所有难度
    # 为简化，这里演示只从当前 CSV 重新筛选该 ID 的所有行
    all_diffs = [r for r in rows if str(r.get("Song ID")) == str(song_id)]
    
    # 排序
    diff_order = {d: i for i, d in enumerate(diffs)}
    all_diffs.sort(key=lambda x: diff_order.get(x.get("Difficulty"), 99))

    for d_row in all_diffs:
        diff_label = d_row.get("Difficulty", "")
        level = d_row.get("Level Label", "")
        ds = d_row.get("Official DS", "")
        notes = d_row.get("Total Notes", "")
        fit = d_row.get("Chart_fit_diff", "")
        try:
            fit = f"{float(fit):.2f}" if fit else "-"
        except: fit = "-"

        cx = 20
        draw.text((cx, curr_y), diff_label, fill=(0, 0, 0), font=font_text); cx += col_widths[0]
        draw.text((cx, curr_y), level, fill=(0, 0, 0), font=font_text); cx += col_widths[1]
        draw.text((cx, curr_y), ds, fill=(0, 0, 0), font=font_text); cx += col_widths[2]
        draw.text((cx, curr_y), notes, fill=(0, 0, 0), font=font_text); cx += col_widths[3]
        draw.text((cx, curr_y), fit, fill=(0, 0, 0), font=font_text); cx += col_widths[4]
        
        curr_y += row_h

    # 输出为 BytesIO
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_song_rows(song_id: str, csv_path: str) -> List[dict]:
    """返回指定 song_id 的全部行（原始字段字典列表），供封面绘图等用途。"""
    rows = _load_csv_rows(csv_path)
    return [
        row for row in rows
        if str(row.get("Song ID", "")).strip() == str(song_id).strip()
    ]

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
