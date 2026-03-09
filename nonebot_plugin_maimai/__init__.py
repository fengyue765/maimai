"""
nonebot_plugin_maimai — maimai DX 工具箱 NoneBot2 插件

集成功能：
  - 更新全服数据库    (/更新数据库)
  - 查询水曲（逆诈称）(/水曲 <定数>)
  - 查询诈称          (/诈称 <定数>)
  - 单曲信息查询      (/查歌 <关键词>)
  - 猜歌挑战          (/猜歌 [模式])
  - 跨定数区间查询    (/跨定数 <区间A> <区间B>)
"""

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .commands import (  # noqa: F401 — 触发命令注册
    cross_tier_cmd,
    guess_input_handler,
    guess_start_cmd,
    landmine_cmd,
    song_query_cmd,
    update_db,
    water_cmd,
)
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="maimai DX 工具箱",
    description="Maimai DX 数据查询与猜歌游戏插件",
    usage=(
        "更新数据库：/更新数据库\n"
        "查询水曲：  /水曲 <定数>  （如 /水曲 13、/水曲 13+、/水曲 13.5）\n"
        "查询诈称：  /诈称 <定数>\n"
        "单曲查询：  /查歌 <关键词>（支持 ID / 曲名 / 别名）\n"
        "猜歌游戏：  /猜歌 [模式编号]（不带参数显示模式列表）\n"
        "跨定数查询：/跨定数 <区间A> <区间B>（如 /跨定数 12.0-12.5 14.0-14.5）"
    ),
    type="application",
    homepage="https://github.com/fengyue765/maimai",
    config=Config,
    supported_adapters=None,
)

__all__ = ["__plugin_meta__"]
