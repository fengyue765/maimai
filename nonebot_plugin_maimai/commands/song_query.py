"""单曲信息查询命令。"""

import asyncio

from nonebot import get_plugin_config, on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..config import Config
from ..data_source import get_id_to_title, get_song_rows, search_songs
from ..draw import draw_song_card

song_query_cmd = on_command(
    "查歌",
    aliases={"歌曲查询", "查曲", "歌曲信息"},
    priority=5,
    block=True,
)


@song_query_cmd.handle()
async def handle_song_query(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    query = args.extract_plain_text().strip()
    if not query:
        await matcher.finish(
            "🔍 请提供查询关键词，支持 ID、曲名、别名，例如：\n"
            "  /查歌 11451\n"
            "  /查歌 潘多拉\n"
            "  /查歌 鸟折磨"
        )

    cfg = get_plugin_config(Config)
    csv_path = cfg.maimai_data_path
    cover_dir = cfg.maimai_cover_dir

    def _query() -> tuple[list[str], dict[str, str]]:
        try:
            ids = search_songs(query, csv_path)
            id_to_title = get_id_to_title(csv_path)
            return ids, id_to_title
        except FileNotFoundError as exc:
            return [], {"__error__": str(exc)}
        except Exception as exc:
            return [], {"__error__": f"查询失败：{exc}"}

    result_ids, id_to_title = await asyncio.get_event_loop().run_in_executor(None, _query)

    if "__error__" in id_to_title:
        await matcher.finish(f"❌ {id_to_title['__error__']}")

    if not result_ids:
        await matcher.finish(f"❌ 未找到与「{query}」相关的歌曲。")

    if len(result_ids) == 1:
        # 直接显示详情（图片，含封面）
        def _detail() -> bytes:
            try:
                rows = get_song_rows(result_ids[0], csv_path)
                return draw_song_card(rows, cover_dir)
            except Exception as exc:
                raise RuntimeError(f"获取详情失败：{exc}") from exc

        try:
            img_bytes = await asyncio.get_event_loop().run_in_executor(None, _detail)
            await matcher.finish(MessageSegment.image(img_bytes))
        except Exception as exc:
            await matcher.finish(f"❌ {exc}")
    else:
        # 多个结果，显示列表
        result_ids = list(set(result_ids))[:15]
        lines = [f"🔍 找到 {len(result_ids)} 个结果（最多显示 15 条）：\n"]
        for i, sid in enumerate(result_ids, start=1):
            title = id_to_title.get(str(sid), "未知曲名")
            lines.append(f"  {i}. [{sid}] {title}")
        lines.append("\n请使用 ID 精确查询，例如：/查歌 11451")
        await matcher.finish("\n".join(lines))
