# Maimai DX 工具箱 🎵

一个用于 **maimai DX** 数据分析与查询的工具集，同时提供 **NoneBot2 聊天机器人插件** 支持。

maimai DX 是 SEGA 开发的街机音乐游戏，本项目通过 [diving-fish 水鱼查分器](https://www.diving-fish.com/maimaidx/prober/) API 获取全服统计数据，提供多种数据分析、查询与游戏功能。

---

## 功能列表

| 功能 | 命令行菜单 | NoneBot2 命令 | 说明 |
|------|-----------|--------------|------|
| 更新全服数据库 | `1` | `/更新数据库` | 从 DivingFish API 下载并分析全服统计，生成 `maimai_global_stats.csv` |
| 查询水曲 | `3` | `/水曲 <定数>` | 查找官方定数偏高、实际偏简单的谱面（逆诈称） |
| 查询诈称 | `4` | `/诈称 <定数>` | 查找官方定数偏低、实际偏难的谱面（诈称） |
| 单曲信息查询 | `7` | `/查歌 <关键词>` | 按 ID、曲名或别名查询谱面详细信息 |
| 猜歌挑战 | `9` | `/猜歌 [模式]` | 猜曲名的互动小游戏，支持 8 种难度模式 |
| 跨定数区间查询 | `10` | `/跨定数 <区间A> <区间B>` | 查找同时拥有两个定数范围谱面的歌曲 |
| 生成 B50 图片 | `2` | — | 生成玩家 Best 50 排行图片（命令行专用） |
| 实力路径分析 | `5` | — | 分析玩家在 5 个技能维度的成长路径 |
| 定数-Rating 曲线 | `6` | — | 生成定数与 Rating 关系的分析图表 |
| 谱师数据分析 | `8` | — | 统计各谱师的谱面分布与特征 |

---

## 项目结构

```
maimai/
├── main.py                     # 命令行交互菜单入口
├── maimai_global.py            # 全服数据库更新模块
├── maimai_recommend.py         # 水曲/诈称推荐模块
├── maimai_song_query.py        # 单曲信息查询模块
├── maimai_song_game.py         # 猜歌游戏模块
├── maimai_cross_tier.py        # 跨定数区间查询模块
├── maimai_b50.py               # B50 图片生成模块
├── maimai_progress.py          # 实力发展路径分析模块
├── maimai_rating_curve.py      # 定数-Rating 曲线分析模块
├── maimai_charter.py           # 谱师数据分析模块
├── nonebot_plugin_maimai/      # NoneBot2 插件包
│   ├── __init__.py
│   ├── config.py
│   ├── data_source.py
│   ├── game_session.py
│   └── commands/
│       ├── __init__.py
│       ├── update.py
│       ├── recommend.py
│       ├── song_query.py
│       ├── guess_game.py
│       └── cross_tier.py
├── pyproject.toml              # 插件包配置
└── requirements.txt            # Python 依赖
```

---

## 命令行工具使用

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

启动后会显示交互菜单：

```
=============================================
   Maimai DX 本地数据工具箱
=============================================
1. 更新全服数据库 (maimai_global_stats.csv)
2. 生成 B50 图片 (需 乐谱.csv)
3. 吃分推荐 (查询水曲)
4. 地雷预警 (查询诈称)
...
```

### 数据文件说明

- **`maimai_global_stats.csv`**：全服统计数据（由功能 1 生成，其他功能依赖此文件）
- **`乐谱.csv`**（可选）：个人乐谱数据（用于 B50 生成和单曲成绩显示）

---

## NoneBot2 插件使用

### 安装

#### 方式一：从源码安装（推荐开发模式）

```bash
# 克隆本仓库后，在仓库根目录执行
pip install -e .
```

#### 方式二：直接将插件目录放入 NoneBot2 项目

将 `nonebot_plugin_maimai/` 目录复制到你的 NoneBot2 项目的 `src/plugins/` 目录下。

### 加载插件

在 NoneBot2 的 `pyproject.toml` 中添加：

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_maimai"]
```

或在代码中：

```python
nonebot.load_plugin("nonebot_plugin_maimai")
```

### 插件配置

在 `.env` 文件中配置：

```env
# 全服数据 CSV 文件路径（默认：当前目录下的 maimai_global_stats.csv）
MAIMAI_DATA_PATH=./maimai_global_stats.csv

# 是否限制更新数据库命令只允许管理员使用（默认：True）
MAIMAI_ADMIN_ONLY_UPDATE=true
```

### 命令说明

#### 更新全服数据库

```
/更新数据库
```

- 从 DivingFish 下载最新数据并生成 `maimai_global_stats.csv`
- 默认仅管理员可用（可通过配置修改）
- 耗时约 30-120 秒，完成后会发送通知

#### 查询水曲（逆诈称）

```
/水曲 13
/水曲 13+
/水曲 13.5
```

- 查找指定定数范围内实际难度偏低的谱面
- 输入整数（如 `13`）会匹配 13.0–13.5；输入 `13+` 会匹配 13.6–13.9

#### 查询诈称

```
/诈称 13
/诈称 13+
/诈称 13.5
```

- 查找指定定数范围内实际难度偏高的谱面

#### 单曲信息查询

```
/查歌 11451
/查歌 潘多拉
/查歌 鸟折磨
```

- 支持按 Song ID、曲名或别名查询
- 显示所有难度的定数、拟合定数、物量、谱面属性等信息

#### 猜歌挑战

```
/猜歌
/猜歌 1
```

- 不带参数会显示模式列表
- 带模式编号直接开始对应模式的游戏

**模式列表：**

| 模式 | 名称 | 描述 | 允许错误次数 |
|------|------|------|------------|
| 1 | Expert:初级 | Expert 定数 7.0–9.5 | 70 |
| 2 | Expert:中级 | Expert 定数 9.6–11.5 | 60 |
| 3 | Expert:上级 | Expert 定数 11.6–12.5 | 50 |
| 4 | Expert:超上级 | Expert 定数 12.6–13.9 | 40 |
| 5 | Master:初级 | Master 定数 10.6–11.9 | 70 |
| 6 | Master:中级 | Master 定数 12.0–13.5 | 50 |
| 7 | Master:上级 | Master 定数 13.0–14.5 | 30 |
| 8 | Master:超上级 | Master 定数 14.0–14.9 | 10 |

游戏过程中可以输入歌曲 ID 或曲名/别名进行猜测，输入 `放弃` 跳过当前曲目。

**比较符号说明：**
- `√` 完全正确
- `×` 分类/分区不同
- `↑` 猜测值小于目标值
- `↓` 猜测值大于目标值
- `○` BPM 相差 ≤10 但不相等

#### 跨定数区间查询

```
/跨定数 12.0-12.5 14.0-14.5
```

- 查找同一首歌中同时存在两个定数区间谱面的歌曲
- 适合查找"紫谱简单红谱难"类型的特殊歌曲

---

## 数据来源

- **[diving-fish 水鱼查分器](https://www.diving-fish.com/maimaidx/prober/)**：提供全服成绩统计、谱面拟合定数等数据
- **[CrazyKidCN/maimaiDX-CN-songs-database](https://github.com/CrazyKidCN/maimaiDX-CN-songs-database)**：提供国服歌曲分类、版本等本地数据
- **[yuzuchan.moe](https://api.yuzuchan.moe/maimaidx/maimaidxalias)**：提供歌曲别名数据

---

## 环境要求

- Python 3.9+
- NoneBot2 2.x（仅插件功能需要）

---

## 许可证

本项目仅供学习与个人使用，数据来源于第三方 API，请遵守相关服务的使用条款。
