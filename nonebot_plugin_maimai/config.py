from pydantic import BaseModel


class Config(BaseModel):
    """maimai DX 插件配置"""

    # 全服统计 CSV 文件路径
    maimai_data_path: str = "maimai_global_stats.csv"

    # 曲绘封面目录路径
    maimai_cover_dir: str = "maimaiDX-CN-songs-database/cover"

    # 是否限制「更新数据库」命令仅管理员可用
    maimai_admin_only_update: bool = True
