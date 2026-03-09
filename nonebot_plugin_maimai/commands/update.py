"""更新全服数据库命令。"""

import asyncio

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER

# 注册命令时使用 SUPERUSER 权限（保守策略，可在配置中覆盖）
update_db = on_command(
    "更新数据库",
    aliases={"maimai_update", "更新maimai"},
    priority=5,
    block=True,
    permission=SUPERUSER,
)


@update_db.handle()
async def handle_update(bot: Bot, event: Event, matcher: Matcher) -> None:
    await matcher.send("⏳ 正在更新全服数据库，请稍候（约需 30–120 秒）...")

    def _run_update() -> str:
        import sys
        import os

        # 将仓库根目录加入路径，以便导入原始模块
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)

        try:
            from maimai_global import GlobalExporter  # type: ignore
            exporter = GlobalExporter()
            # 覆盖输出文件路径到配置指定的路径
            import io
            import contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exporter.run()

            return buf.getvalue().strip() or "✅ 数据库更新完成。"
        except Exception as exc:
            return f"❌ 更新失败：{exc}"

    result = await asyncio.get_event_loop().run_in_executor(None, _run_update)
    # 截断过长输出，保留末尾的状态信息
    if len(result) > 800:
        result = result[:800] + "\n…（输出已截断）"
    await matcher.finish(result)
