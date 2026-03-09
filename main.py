# main.py
import sys
import requests
from maimai_global import GlobalExporter

# 引入新模块
try:
    from maimai_global import GlobalExporter
    from maimai_b50 import B50Generator
    from maimai_recommend import Recommender
    from maimai_progress import ProgressTracker
    from maimai_rating_curve import RatingCurveAnalyzer
    from maimai_song_query import SongQuery
    from maimai_charter import CharterAnalyzer
    from maimai_song_game import SongGuessingGame
    from maimai_cross_tier import CrossTierAnalyzer  # 新增导入
except ImportError as e:
    print(f"[警告] 模块加载失败: {e}")
    pass

class MainApp:
    def __init__(self):
        self.music_map = None 
        self.api_music = "https://www.diving-fish.com/api/maimaidxprober/music_data"

    def _ensure_music_cache(self):
        if self.music_map is not None:
            return True 
        print("\n[系统] 正在初始化基础歌曲列表...")
        try:
            resp = requests.get(self.api_music)
            resp.raise_for_status()
            data = resp.json()
            self.music_map = {int(song['id']): song for song in data}
            print(f"[系统] 缓存建立完成，共 {len(self.music_map)} 首歌曲。")
            return True
        except Exception as e:
            print(f"[严重错误] 无法获取基础数据: {e}")
            return False

    def run(self):
        while True:
            print("\n" + "="*45)
            print("   Maimai DX 本地数据工具箱")
            print("="*45)
            print("1. 更新全服数据库 (maimai_global_stats.csv)")
            print("2. 生成 B50 图片 (需 乐谱.csv)")
            print("3. 吃分推荐 (查询水曲)")
            print("4. 地雷预警 (查询诈称)")
            print("5. 实力发展路径分析")
            print("6. 定数-Rating曲线分析")
            print("7. 单曲信息查询")
            print("8. 谱师数据分析")
            print("9. [游戏] 猜歌挑战")
            print("10. 跨定数区间查询")  # 新增菜单项
            print("0. 退出程序")
            print("="*45)
            
            choice = input("\n请选择功能 [0-10]: ").strip()
            
            if choice == '1':
                if self._ensure_music_cache():
                    exporter = GlobalExporter()
                    exporter.run(self.music_map)
                    
            elif choice == '2':
                print("\n>>> 启动 B50 生成器...")
                try:
                    b50_gen = B50Generator()
                    b50_gen.generate_image()
                except UnicodeDecodeError:
                    print("[错误] CSV 编码错误！请将 '乐谱.csv' 或 'maimai_global_stats.csv' 另存为 UTF-8 编码。")
                except NameError:
                    print("[错误] B50 模块未加载。")
                except Exception as e:
                    print(f"[错误] 生成失败: {e}")

            elif choice == '3':
                print("\n>>> 启动吃分推荐...")
                try:
                    val = input("请输入定数 (如 13.5) 或 等级 (如 13, 13+): ").strip()
                    rec = Recommender()
                    rec.recommend_score(val)
                except Exception as e:
                    print(f"[错误] {e}")

            elif choice == '4':
                print("\n>>> 启动地雷预警...")
                try:
                    val = input("请输入定数 (如 13.5) 或 等级 (如 13, 13+): ").strip()
                    rec = Recommender()
                    rec.recommend_landmine(val)
                except Exception as e:
                    print(f"[错误] {e}")

            elif choice == '5':
                print("\n>>> 启动实力发展路径分析...")
                try:
                    tracker = ProgressTracker()
                    tracker.analyze_progress_paths()
                except NameError:
                    print("[错误] 进度追踪模块未加载。")
                except Exception as e:
                    print(f"[错误] 分析失败: {e}")
            
            elif choice == '6':
                print("\n>>> 启动定数-Rating曲线分析...")
                try:
                    analyzer = RatingCurveAnalyzer()
                    analyzer.run_analysis()
                except NameError:
                    print("[错误] 曲线分析模块未加载。")
                except Exception as e:
                    print(f"[错误] 分析失败: {e}")

            elif choice == '7':
                print("\n>>> 启动单曲信息查询...")
                try:
                    query = SongQuery()
                    query.run_interactive_query()
                except NameError:
                    print("[错误] 查询模块未加载。")
                except Exception as e:
                    print(f"[错误] 查询失败: {e}")

            elif choice == '8':
                print("\n>>> 启动谱师数据分析...")
                try:
                    charter_analyzer = CharterAnalyzer()
                    charter_analyzer.analyze()
                except NameError:
                    print("[错误] 谱师分析模块未加载。")
                except Exception as e:
                    print(f"[错误] 分析失败: {e}")

            elif choice == '9':
                print("\n>>> 启动猜歌挑战...")
                try:
                    game = SongGuessingGame()
                    game.run()
                except NameError:
                    print("[错误] 游戏模块未加载。")
                except Exception as e:
                    print(f"[错误] 游戏启动失败: {e}")

            elif choice == '10':  # 新增逻辑
                print("\n>>> 启动跨定数区间查询...")
                try:
                    analyzer = CrossTierAnalyzer()
                    analyzer.find_cross_tier_songs()
                except NameError:
                    print("[错误] 跨定数查询模块未加载。")
                except Exception as e:
                    print(f"[错误] 查询失败: {e}")

            elif choice == '0':
                print("再见！")
                sys.exit()
            else:
                print("无效输入。")

if __name__ == "__main__":
    app = MainApp()
    app.run()