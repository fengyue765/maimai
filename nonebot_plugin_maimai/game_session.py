"""
猜歌游戏会话管理：跟踪每个用户/群组的游戏状态。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# 游戏模式配置
# ---------------------------------------------------------------------------

GAME_MODES: Dict[str, dict] = {
    "1": {
        "name": "Expert:初级",
        "description": "Expert 定数 7.0–9.5",
        "diff_type": "expert",
        "min_ds": 7.0,
        "max_ds": 9.5,
        "rounds": 4,
        "max_errors": 70,
    },
    "2": {
        "name": "Expert:中级",
        "description": "Expert 定数 9.6–11.5",
        "diff_type": "expert",
        "min_ds": 9.6,
        "max_ds": 11.5,
        "rounds": 4,
        "max_errors": 60,
    },
    "3": {
        "name": "Expert:上级",
        "description": "Expert 定数 11.6–12.5",
        "diff_type": "expert",
        "min_ds": 11.6,
        "max_ds": 12.5,
        "rounds": 4,
        "max_errors": 50,
    },
    "4": {
        "name": "Expert:超上级",
        "description": "Expert 定数 12.6–13.9",
        "diff_type": "expert",
        "min_ds": 12.6,
        "max_ds": 13.9,
        "rounds": 4,
        "max_errors": 40,
    },
    "5": {
        "name": "Master:初级",
        "description": "Master 定数 10.6–11.9",
        "diff_type": "master",
        "min_ds": 10.6,
        "max_ds": 11.9,
        "rounds": 4,
        "max_errors": 70,
    },
    "6": {
        "name": "Master:中级",
        "description": "Master 定数 12.0–13.5",
        "diff_type": "master",
        "min_ds": 12.0,
        "max_ds": 13.5,
        "rounds": 4,
        "max_errors": 50,
    },
    "7": {
        "name": "Master:上级",
        "description": "Master 定数 13.0–14.5",
        "diff_type": "master",
        "min_ds": 13.0,
        "max_ds": 14.5,
        "rounds": 4,
        "max_errors": 30,
    },
    "8": {
        "name": "Master:超上级",
        "description": "Master 定数 14.0–14.9",
        "diff_type": "master",
        "min_ds": 14.0,
        "max_ds": 14.9,
        "rounds": 4,
        "max_errors": 10,
    },
}


def get_modes_text() -> str:
    """返回模式列表的格式化文本。"""
    lines = ["🎮 猜歌挑战 — 选择模式（回复模式编号开始游戏）\n"]
    for mode_id, mode in GAME_MODES.items():
        lines.append(
            f"  {mode_id}. {mode['name']}  {mode['description']}"
            f"  允许错误：{mode['max_errors']} 次"
        )
    lines.append("\n输入「/猜歌 <模式编号>」直接开始，如：/猜歌 1")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 歌曲信息
# ---------------------------------------------------------------------------

@dataclass
class SongInfo:
    song_id: int
    title: str
    song_type: str
    genre: str
    bpm: float
    version: str
    expert_ds: Optional[float]
    master_ds: Optional[float]
    remaster_ds: Optional[float]  # 新增字段
    has_remaster: bool
    aliases: List[str] = field(default_factory=list)


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None and str(val).strip() else None
    except (ValueError, TypeError):
        return None


def build_song_pool(csv_path: str) -> tuple[Dict[int, SongInfo], Dict[str, set[int]]]:
    """
    读取 CSV，构建 (song_info_map, alias_to_ids) 数据结构。

    Returns:
        song_info_map: song_id -> SongInfo
        alias_to_ids:  lowercase key -> set of song_id
    """
    df = pd.read_csv(csv_path, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]

    song_info_map: Dict[int, SongInfo] = {}
    alias_to_ids: Dict[str, set[int]] = {}

    unique_songs = df.drop_duplicates(subset=["Song ID"])

    for _, row in unique_songs.iterrows():
        song_id = int(row["Song ID"])
        title = str(row["Title"])
        song_type = str(row.get("Type", ""))
        genre = str(row.get("Genre", ""))
        version = str(row.get("Version", ""))

        try:
            bpm_raw = str(row.get("BPM", "0"))
            bpm = float(bpm_raw.split("-")[-1]) if "-" in bpm_raw else float(bpm_raw)
        except (ValueError, TypeError):
            bpm = 0.0

        expert_rows = df[(df["Song ID"] == row["Song ID"]) & (df["Difficulty"] == "Expert")]
        master_rows = df[(df["Song ID"] == row["Song ID"]) & (df["Difficulty"] == "Master")]
        remaster_rows = df[(df["Song ID"] == row["Song ID"]) & (df["Difficulty"] == "Re:MASTER")]

        expert_ds = _safe_float(expert_rows["Official DS"].iloc[0]) if not expert_rows.empty else None
        master_ds = _safe_float(master_rows["Official DS"].iloc[0]) if not master_rows.empty else None
        remaster_ds = _safe_float(remaster_rows["Official DS"].iloc[0]) if not remaster_rows.empty else None
        has_remaster = not remaster_rows.empty

        aliases_raw = str(row.get("Aliases", ""))
        aliases = [a.strip() for a in aliases_raw.split(";") if a.strip() and aliases_raw != "nan"]

        info = SongInfo(
            song_id=song_id,
            title=title,
            song_type=song_type,
            genre=genre,
            bpm=bpm,
            version=version,
            expert_ds=expert_ds,
            master_ds=master_ds,
            remaster_ds=remaster_ds,  # 新增
            has_remaster=has_remaster,
            aliases=aliases,
        )
        song_info_map[song_id] = info

        for key in [str(song_id), title] + aliases:
            kl = key.strip().lower()
            if kl:
                alias_to_ids.setdefault(kl, set())
                alias_to_ids[kl].add(song_id)

    return song_info_map, alias_to_ids


# ---------------------------------------------------------------------------
# 游戏会话
# ---------------------------------------------------------------------------

@dataclass
class GuessSession:
    mode: dict
    song_info_map: Dict[int, SongInfo]
    alias_to_ids: Dict[str, set[int]]
    target_ids: List[int]
    current_round: int = 0
    total_errors: int = 0
    round_guesses: List[dict] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    finished: bool = False
    _last_guess_image: Optional[bytes] = field(default=None, repr=False)

    # --- helpers ---

    @property
    def rounds_total(self) -> int:
        return len(self.target_ids)

    @property
    def current_target(self) -> SongInfo:
        return self.song_info_map[self.target_ids[self.current_round]]

    @property
    def max_errors(self) -> int:
        return self.mode["max_errors"]

    def resolve_guess(self, user_input: str) -> Optional[int]:
        """
        将用户输入解析为 song_id。
        返回 song_id，或 None（未找到），或 -1（多个候选）。
        """
        uid = user_input.strip()

        digitalias = ["39", "411892", "211985", "1919810"]
        
        # 如果是纯数字，进行完全匹配
        if uid.isdigit() and uid not in digitalias:
            sid = int(uid)
            if sid in self.song_info_map:
                return sid
            # 数字但不在映射中，返回 None
            return None
        
        # 非纯数字，使用别名匹配
        key = uid.lower()
        if key in self.alias_to_ids:
            matched = self.alias_to_ids[key]
            if len(matched) == 1:
                return next(iter(matched))
            # 多个候选
            return -1
        
        return None

    def _cmp(self, guess_val, target_val, kind: str = "category") -> str:
        """返回比较符号。"""
        if guess_val is None or target_val is None:
            return "?"
        if kind == "category":
            return "√" if guess_val == target_val else "×"
        if kind == "bpm":
            if guess_val == target_val:
                return "√"
            if abs(guess_val - target_val) <= 10:
                return "○"
            return "↑" if guess_val < target_val else "↓"
        if kind == "boolean":
            return "√" if guess_val == target_val else "×"
        # numeric
        if guess_val == target_val:
            return "√"
        return "↑" if guess_val < target_val else "↓"

    def process_guess(self, song_id: int) -> tuple[bool, str]:
        """
        处理一次猜测。
        Returns:
            (is_correct, result_text)
        """
        guess_info = self.song_info_map[song_id]
        target = self.current_target

        is_correct = (song_id == target.song_id)

        lines = [f"第 {self.current_round + 1} 局  第 {len(self.round_guesses) + 1} 次猜测"]

        # 表头
        """
        lines.append("曲名         | 分类     | 分区     | 版本   | BPM    | Expert | Master | Re:M")
        lines.append("-" * 82)
        """

        # 添加本次猜测
        self.round_guesses.append({
            "id": song_id,
            "title": guess_info.title,
            "type": guess_info.song_type,
            "genre": guess_info.genre,
            "version": guess_info.version,
            "bpm": guess_info.bpm,
            "expert_ds": guess_info.expert_ds,
            "master_ds": guess_info.master_ds,
            "has_remaster": guess_info.has_remaster,
            "is_correct": is_correct,
        })

        # 显示所有猜测历史
        for g in self.round_guesses:
            gi = self.song_info_map[g["id"]]
            tc = self._cmp(gi.song_type, target.song_type)
            gc = self._cmp(gi.genre, target.genre)
            # 版本：相同返回"√"，不同则按 song_id 大小给方向
            if gi.version == target.version:
                vc = "√"
            else:
                vc = "↑" if g["id"] < target.song_id else "↓"
            bc = self._cmp(gi.bpm, target.bpm, "bpm")
            ec = self._cmp(gi.expert_ds, target.expert_ds, "ds")
            mc = self._cmp(gi.master_ds, target.master_ds, "ds")
            rc = self._cmp(gi.has_remaster, target.has_remaster, "boolean")

            def _fmt(v, sym, kind="cat") -> str:
                if v is None:
                    return f"N/A({sym})"
                if kind == "ds":
                    return f"{v:.1f}({sym})"
                if kind == "bool":
                    return f"{'有' if v else '无'}({sym})"
                return f"{v}({sym})"

            t_s = gi.title[:12] + "…" if len(gi.title) > 12 else gi.title
            """
            lines.append(
                f"{t_s:<13} | {_fmt(gi.song_type, tc):<8} | {_fmt(gi.genre, gc):<8} | "
                f"{_fmt(gi.version, vc):<6} | {_fmt(gi.bpm, bc):<6} | "
                f"{_fmt(gi.expert_ds, ec, 'ds'):<6} | {_fmt(gi.master_ds, mc, 'ds'):<6} | "
                f"{_fmt(gi.has_remaster, rc, 'bool')}"
            )
            """

        if is_correct:
            # 在清除猜测历史前生成图片
            self._last_guess_image = self._render_guess_image()
            self.round_guesses = []
            self.current_round += 1
            lines.append(f"\n✅ 猜对了！答案：{target.title} (ID: {target.song_id})")
            if self.current_round >= self.rounds_total:
                self.finished = True
        else:
            self.total_errors += 1
            remaining = self.max_errors - self.total_errors
            lines.append(f"\n❌ 猜错了！已用错误次数：{self.total_errors}/{self.max_errors}（剩余 {remaining}）")
            self._last_guess_image = self._render_guess_image()

        return is_correct, "\n".join(lines)

    def _render_guess_image(self) -> bytes:
        """内部方法：将当前 round_guesses 渲染为图片字节。"""
        from .image_utils import draw_table, CORRECT_BG

        target = self.current_target
        headers = ["曲名", "分类", "分区", "版本", "BPM", "Expert", "Master", "Re:M"]
        rows: List[List[str]] = []
        row_colors = []

        for g in self.round_guesses:
            gi = self.song_info_map[g["id"]]
            tc = self._cmp(gi.song_type, target.song_type)
            gc = self._cmp(gi.genre, target.genre)
            if gi.version == target.version:
                vc = "√"
            else:
                vc = "↑" if g["id"] < target.song_id else "↓"
            bc = self._cmp(gi.bpm, target.bpm, "bpm")
            ec = self._cmp(gi.expert_ds, target.expert_ds, "ds")
            mc = self._cmp(gi.master_ds, target.master_ds, "ds")
            rc = self._cmp(gi.has_remaster, target.has_remaster, "boolean")

            def _fmt(v, sym, kind="cat") -> str:
                if v is None:
                    return f"N/A({sym})"
                if kind == "ds":
                    return f"{v:.1f}({sym})"
                if kind == "bool":
                    return f"{'有' if v else '无'}({sym})"
                return f"{v}({sym})"

            t_s = gi.title[:12] + "…" if len(gi.title) > 12 else gi.title
            rows.append([
                t_s,
                _fmt(gi.song_type, tc),
                _fmt(gi.genre, gc),
                _fmt(gi.version, vc),
                _fmt(gi.bpm, bc),
                _fmt(gi.expert_ds, ec, "ds"),
                _fmt(gi.master_ds, mc, "ds"),
                _fmt(gi.has_remaster, rc, "bool"),
            ])
            row_colors.append(CORRECT_BG if g["is_correct"] else None)

        # title reflects state at time of call
        guess_num = len(self.round_guesses)
        round_num = self.current_round + 1
        title = (
            f"第 {round_num} 局  第 {guess_num} 次猜测"
            f"  错误：{self.total_errors}/{self.max_errors}"
        )
        return draw_table(headers, rows, row_colors=row_colors, title=title)

    def draw_guess_result(self) -> bytes:
        """
        返回最近一次猜测的结果图片（PNG 字节）。
        图片在 process_guess 内部渲染并缓存，此方法直接返回缓存值。
        若尚无缓存（未进行过任何猜测），返回空白图片。
        """
        if self._last_guess_image is not None:
            return self._last_guess_image
        # 还没有任何猜测，返回提示图片
        from .image_utils import draw_table
        return draw_table(
            ["曲名", "分类", "分区", "版本", "BPM", "Expert", "Master", "Re:M"],
            [],
            title="暂无猜测记录",
        )

    def give_up_round(self) -> str:
        """放弃当前局，返回答案信息文本。"""
        target = self.current_target
        self.round_guesses = []
        self.current_round += 1
        if self.current_round >= self.rounds_total:
            self.finished = True
        lines = [
            f"🏳️ 已放弃本局。",
            f"正确答案：{target.title} (ID: {target.song_id})",
            f"  分类：{target.song_type}　分区：{target.genre}",
            f"  版本：{target.version}　BPM：{target.bpm}",
        ]
        if target.expert_ds is not None:
            lines.append(f"  Expert 定数：{target.expert_ds:.1f}")
        if target.master_ds is not None:
            lines.append(f"  Master 定数：{target.master_ds:.1f}")
        lines.append(f"  有 Re:MASTER：{'是' if target.has_remaster else '否'}")
        return "\n".join(lines)

    def summary(self) -> str:
        """返回游戏结束的总结文本。"""
        duration = datetime.now() - self.start_time
        m = int(duration.total_seconds() // 60)
        s = int(duration.total_seconds() % 60)
        lines = [
            "🏁 游戏结束！",
            f"模式：{self.mode['name']}",
            f"进度：{self.current_round}/{self.rounds_total} 局完成",
            f"错误次数：{self.total_errors}/{self.max_errors}",
            f"游戏时间：{m} 分 {s} 秒",
        ]
        return "\n".join(lines)

    def next_round_prompt(self) -> str:
        """返回当前局的提示文本（不包含答案）。"""
        if self.finished:
            return ""
        mode_name = self.mode["name"]
        r = self.current_round + 1
        total = self.rounds_total
        errs = self.total_errors
        max_e = self.max_errors
        return (
            f"第 {r}/{total} 局  [{mode_name}]\n"
            f"已用错误次数：{errs}/{max_e}\n"
            f"请输入歌曲 ID 或曲名/别名进行猜测（输入「放弃」跳过本局）："
        )


# ---------------------------------------------------------------------------
# 全局会话存储
# ---------------------------------------------------------------------------

_sessions: Dict[str, GuessSession] = {}


def get_session(session_key: str) -> Optional[GuessSession]:
    return _sessions.get(session_key)


def create_session(
    session_key: str,
    mode_id: str,
    csv_path: str,
) -> tuple[Optional[GuessSession], str]:
    """
    创建新游戏会话。
    Returns:
        (session, error_message)  — error_message 为空表示成功
    """
    if mode_id not in GAME_MODES:
        return None, f"⚠️ 无效的模式编号：{mode_id}，有效范围：1–{len(GAME_MODES)}"

    import os
    if not os.path.exists(csv_path):
        return None, f"⚠️ 找不到数据文件：{csv_path}，请先执行「更新数据库」。"

    mode = GAME_MODES[mode_id]
    song_info_map, alias_to_ids = build_song_pool(csv_path)

    # 筛选符合模式的歌曲
    diff_type = mode["diff_type"]
    available = []
    
    for sid, info in song_info_map.items():
        if diff_type == "expert":
            # Expert 模式只检查 expert_ds
            if info.expert_ds is not None and mode["min_ds"] <= info.expert_ds <= mode["max_ds"]:
                available.append(sid)
        elif diff_type == "master":
            # Master 模式检查 master_ds 和 remaster_ds
            if info.master_ds is not None and mode["min_ds"] <= info.master_ds <= mode["max_ds"]:
                available.append(sid)
            elif info.remaster_ds is not None and mode["min_ds"] <= info.remaster_ds <= mode["max_ds"]:
                available.append(sid)


    if len(available) < mode["rounds"]:
        return None, (
            f"⚠️ 符合条件的歌曲不足 {mode['rounds']} 首（当前仅 {len(available)} 首），"
            "请更新数据库后重试。"
        )

    target_ids = random.sample(available, mode["rounds"])
    session = GuessSession(
        mode=mode,
        song_info_map=song_info_map,
        alias_to_ids=alias_to_ids,
        target_ids=target_ids,
    )
    _sessions[session_key] = session
    return session, ""


def remove_session(session_key: str) -> None:
    _sessions.pop(session_key, None)
