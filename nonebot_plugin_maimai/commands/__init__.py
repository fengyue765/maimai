"""导入所有命令模块，确保命令被注册到 NoneBot2。"""

from .cross_tier import cross_tier_cmd
from .guess_game import guess_input_handler, guess_start_cmd
from .recommend import landmine_cmd, water_cmd
from .song_query import song_query_cmd
from .update import update_db

__all__ = [
    "update_db",
    "water_cmd",
    "landmine_cmd",
    "song_query_cmd",
    "guess_start_cmd",
    "guess_input_handler",
    "cross_tier_cmd",
]
