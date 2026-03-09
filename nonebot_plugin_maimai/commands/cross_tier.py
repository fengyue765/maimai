"""跨定数区间查询命令。"""

import asyncio

from nonebot import get_plugin_config, on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..config import Config
from ..data_source import get_cross_tier_songs

cross_tier_cmd = on_command(
    "跨定数",
    aliases={"跨定数查询", "cross_tier"},
    priority=5,
    block=True,
)

_USAGE = (
    "📊 用法：/跨定数 <区间A> <区间B>\n"
    "示例：/跨定数 12.0-12.5 14.0-14.5\n"
    "查找同时拥有两个定数范围谱面的歌曲。"
)


@cross_tier_cmd.handle()
async def handle_cross_tier(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    parts = args.extract_plain_text().split()

    if len(parts) < 2:
        await matcher.finish(_USAGE)

    range_a, range_b = parts[0], parts[1]

    await matcher.send("🔍 查询中...")

    csv_path = get_plugin_config(Config).maimai_data_path

    def _query() -> str:
        try:
            return get_cross_tier_songs(range_a, range_b, csv_path)
        except FileNotFoundError as exc:
            return f"❌ {exc}"
        except Exception as exc:
            return f"❌ 查询失败：{exc}"

    result = await asyncio.get_event_loop().run_in_executor(None, _query)
    await matcher.finish(result)
