"""猜歌挑战命令。

流程：
  1. 用户发送 /猜歌 [模式] → 创建会话，显示当前局提示
  2. 用户发送猜测（ID / 曲名 / 别名）→ 比较并回显历史，正确则进入下一局
  3. 输入「放弃」跳过当前局
  4. 所有局结束后显示总结
"""

import asyncio
from typing import Optional

from nonebot import get_plugin_config, on_command, on_message
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.rule import Rule

from ..config import Config
from ..game_session import (
    GAME_MODES,
    create_session,
    get_modes_text,
    get_session,
    remove_session,
)



def _session_key(event: Event) -> str:
    """生成会话标识符（群聊用群号+用户ID，私聊用用户ID）。"""
    uid = str(event.get_user_id())
    try:
        group_id = str(getattr(event, "group_id", None) or "private")
    except Exception:
        group_id = "private"
    return f"{group_id}_{uid}"


# ------------------------------------------------------------------ #
# 命令：/猜歌 [模式]                                                  #
# ------------------------------------------------------------------ #

guess_start_cmd = on_command(
    "猜歌",
    aliases={"猜歌挑战", "开始猜歌"},
    priority=5,
    block=True,
)


@guess_start_cmd.handle()
async def handle_guess_start(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    mode_id = args.extract_plain_text().strip()

    # 没有指定模式 → 显示模式列表
    if not mode_id:
        await matcher.finish(get_modes_text())

    csv_path = get_plugin_config(Config).maimai_data_path
    session_key = _session_key(event)

    # 已有进行中的游戏
    if get_session(session_key) is not None:
        await matcher.finish(
            "⚠️ 你已有一局游戏进行中，请先完成或输入「放弃」跳过当前局。"
        )

    await matcher.send(f"⏳ 正在初始化游戏（模式 {mode_id}）...")

    def _create():
        return create_session(session_key, mode_id, csv_path)

    session, error = await asyncio.get_event_loop().run_in_executor(None, _create)

    if error:
        await matcher.finish(error)

    mode = GAME_MODES[mode_id]
    intro = (
        f"🎮 游戏开始！模式：{mode['name']}\n"
        f"  {mode['description']}\n"
        f"  共 {mode['rounds']} 局，最多允许 {mode['max_errors']} 次错误\n\n"
        + session.next_round_prompt()  # type: ignore[union-attr]
    )
    await matcher.finish(intro)


# ------------------------------------------------------------------ #
# 消息监听：处理游戏过程中的猜测输入                                   #
# ------------------------------------------------------------------ #

def _has_active_game(event: Event) -> bool:
    return get_session(_session_key(event)) is not None


active_game_rule = Rule(_has_active_game)

guess_input_handler = on_message(
    rule=active_game_rule,
    priority=4,   # 高于普通消息，但低于猜歌命令本身
    block=True,
)


@guess_input_handler.handle()
async def handle_guess_input(bot: Bot, event: Event, matcher: Matcher) -> None:
    session_key = _session_key(event)
    session = get_session(session_key)

    if session is None:
        return

    user_input = event.get_plaintext().strip()

    # 放弃当前局
    if user_input in ("放弃", "giveup", "跳过"):
        result_text = session.give_up_round()
        if session.finished:
            remove_session(session_key)
            await matcher.finish(result_text + "\n\n" + session.summary())
        else:
            await matcher.finish(result_text + "\n\n" + session.next_round_prompt())

    # 解析歌曲
    guess_id = session.resolve_guess(user_input)

    if guess_id is None:
        await matcher.finish(f"❌ 未找到「{user_input}」，请输入正确的 ID 或曲名/别名。")

    if guess_id == -1:
        # 多个候选
        key = user_input.lower()
        candidates = session.alias_to_ids.get(key, set())
        lines = [f"⚠️「{user_input}」匹配到多首歌曲，请使用 ID 精确选择："]
        for cid in list(candidates)[:10]:
            info = session.song_info_map.get(cid)
            if info:
                lines.append(f"  [{cid}] {info.title}")
        await matcher.finish("\n".join(lines))

    def _process():
        return session.process_guess(guess_id)

    is_correct, result_text = await asyncio.get_event_loop().run_in_executor(None, _process)

    def _draw():
        return session.draw_guess_result()

    result_msg: "MessageSegment | str"
    try:
        img_bytes = await asyncio.get_event_loop().run_in_executor(None, _draw)
        result_msg = MessageSegment.image(img_bytes)
    except Exception:
        result_msg = result_text

    if session.finished:
        remove_session(session_key)
        await matcher.finish(result_msg + "\n\n" + session.summary())
    elif is_correct:
        # 进入下一局
        await matcher.finish(result_msg + "\n\n" + session.next_round_prompt())
    else:
        await matcher.finish(result_msg)
