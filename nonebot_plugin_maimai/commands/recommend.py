"""查询水曲（逆诈称）和查询诈称命令。"""

import asyncio

from nonebot import get_plugin_config, on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..config import Config
from ..data_source import get_landmine_songs, get_water_songs

# ------------------------------------------------------------------
# 查询水曲
# ------------------------------------------------------------------

water_cmd = on_command(
    "水曲",
    aliases={"查水曲", "吃分推荐"},
    priority=5,
    block=True,
)


@water_cmd.handle()
async def handle_water(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    user_input = args.extract_plain_text().strip()
    if not user_input:
        await matcher.finish(
            "🎵 请提供定数或等级，例如：\n"
            "  /水曲 13\n"
            "  /水曲 13+\n"
            "  /水曲 13.5"
        )

    # await matcher.send("🔍 查询中...")

    cfg = get_plugin_config(Config)
    csv_path = cfg.maimai_data_path

    def _query() -> str:
        try:
            return get_water_songs(user_input, csv_path)
        except FileNotFoundError as exc:
            return f"❌ {exc}"
        except Exception as exc:
            return f"❌ 查询失败：{exc}"

    result = await asyncio.get_event_loop().run_in_executor(None, _query)
    await matcher.finish(result)


# ------------------------------------------------------------------
# 查询诈称
# ------------------------------------------------------------------

landmine_cmd = on_command(
    "诈称",
    aliases={"查诈称", "地雷预警", "地雷"},
    priority=5,
    block=True,
)


@landmine_cmd.handle()
async def handle_landmine(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    user_input = args.extract_plain_text().strip()
    if not user_input:
        await matcher.finish(
            "⚠️ 请提供定数或等级，例如：\n"
            "  /诈称 13\n"
            "  /诈称 13+\n"
            "  /诈称 13.5"
        )

    # await matcher.send("🔍 查询中...")

    cfg = get_plugin_config(Config)
    csv_path = cfg.maimai_data_path

    def _query() -> str:
        try:
            return get_landmine_songs(user_input, csv_path)
        except FileNotFoundError as exc:
            return f"❌ {exc}"
        except Exception as exc:
            return f"❌ 查询失败：{exc}"

    result = await asyncio.get_event_loop().run_in_executor(None, _query)
    await matcher.finish(result)
