import pandas as pd
import numpy as np
import os
from prettytable import PrettyTable

class SongQuery:
    def __init__(self):
        self.user_data = None
        self.global_data = None
        self.alias_map = {} # 别名 -> ID 映射表
        self.id_to_title = {} # ID -> 曲名 映射表
        
        # 评分系数表
        self.SCORE_COEFFICIENT_TABLE = [
            [0, 0, 'D'], [10, 1.6, 'D'], [20, 3.2, 'D'], [30, 4.8, 'D'], [40, 6.4, 'D'],
            [50, 8.0, 'C'], [60, 9.6, 'B'], [70, 11.2, 'BB'], [75, 12.0, 'BBB'],
            [79.9999, 12.8, 'BBB'], [80, 13.6, 'A'], [90, 15.2, 'AA'], [94, 16.8, 'AAA'],
            [96.9999, 17.6, 'AAA'], [97, 20.0, 'S'], [98, 20.3, 'S+'], [98.9999, 20.6, 'S+'],
            [99, 20.8, 'SS'], [99.5, 21.1, 'SS+'], [99.9999, 21.4, 'SS+'], [100, 21.6, 'SSS'],
            [100.4999, 22.2, 'SSS'], [100.5, 22.4, 'SSS+']
        ]
        
    def load_data(self):
        """加载数据并构建索引"""
        if self.global_data is not None:
            return True

        if not os.path.exists("乐谱.csv"):
            print("[错误] 找不到用户数据文件: 乐谱.csv (非必须，但无法显示个人成绩)")
            # 这里不返回 False，允许只查全服数据
            self.user_data = pd.DataFrame()
        else:
            try:
                self.user_data = pd.read_csv("乐谱.csv", encoding='utf-8')
                self.user_data.columns = [col.strip() for col in self.user_data.columns]
                print(f"[系统] 已加载用户数据: {len(self.user_data)} 条记录")
            except Exception as e:
                print(f"[错误] 加载用户数据失败: {e}")
                self.user_data = pd.DataFrame()
            
        if not os.path.exists("maimai_global_stats.csv"):
            print("[错误] 找不到全服数据文件: maimai_global_stats.csv")
            return False
            
        try:
            # 强制读取 Song ID 为字符串，防止前导零问题或后续处理错误
            self.global_data = pd.read_csv("maimai_global_stats.csv", encoding='utf-8', dtype={'Song ID': str})
            self.global_data.columns = [col.strip() for col in self.global_data.columns]
            
            # --- 构建搜索索引 ---
            print("[系统] 正在构建别名索引...")
            
            # 确保 Song ID 列存在
            if 'Song ID' not in self.global_data.columns:
                print("[错误] CSV中缺少 'Song ID' 列")
                return False

            unique_songs = self.global_data[['Song ID', 'Title', 'Aliases']].drop_duplicates(subset=['Song ID'])
            
            for _, row in unique_songs.iterrows():
                sid = str(row['Song ID'])
                title = str(row['Title']).strip()
                aliases_str = str(row['Aliases'])
                
                self.id_to_title[sid] = title
                
                # 索引 ID 和 曲名
                self.alias_map[sid] = [sid]
                
                # 为曲名建立索引
                title_lower = title.lower()
                if title_lower not in self.alias_map:
                    self.alias_map[title_lower] = []
                self.alias_map[title_lower].append(sid)
                
                # 索引别名 (假设别名用分号分隔)
                if pd.notna(aliases_str) and aliases_str != 'nan':
                    aliases = [a.strip() for a in aliases_str.split(';')]
                    for alias in aliases:
                        if alias:
                            alias_lower = alias.lower()
                            if alias_lower not in self.alias_map:
                                self.alias_map[alias_lower] = []
                            # 避免同一个ID重复添加
                            if sid not in self.alias_map[alias_lower]:
                                self.alias_map[alias_lower].append(sid)
                            
            print(f"[系统] 已加载全服数据: {len(unique_songs)} 首歌曲")
            print(f"[系统] 索引构建完成，共 {len(self.alias_map)} 个搜索关键词")
            
        except Exception as e:
            print(f"[错误] 加载全服数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        return True
    
    def get_rank_from_achievement(self, achievement):
        """根据达成率获取评级字母"""
        if pd.isna(achievement): return "-"
        try:
            # 去除百分号
            if isinstance(achievement, str) and achievement.endswith('%'):
                achievement = achievement.replace('%', '')
            val = float(achievement)
        except:
            return "-"
            
        for threshold, _, rank in reversed(self.SCORE_COEFFICIENT_TABLE):
            if val >= threshold:
                return rank
        return "D"
    
    def search_song(self, query):
        """
        搜索歌曲
        返回: 匹配的 Song ID 列表
        """
        query = str(query).strip().lower()
        if not query: return []
        
        matched_ids = set()

        # 1. 精确匹配 (ID, 曲名, 别名)
        if query in self.alias_map:
            for sid in self.alias_map[query]:
                matched_ids.add(sid)
            
        # 2. 模糊匹配 (遍历所有关键词)
        for key, sids in self.alias_map.items():
            if query in key:
                for sid in sids:
                    matched_ids.add(sid)
                
        return list(matched_ids)

    def display_song_details(self, song_id):
        """显示单曲详情（核心逻辑）"""
        song_id = str(song_id)
        # 筛选数据
        song_rows = self.global_data[self.global_data['Song ID'] == song_id]
        if len(song_rows) == 0:
            print(f"[错误] 数据库中未找到 ID: {song_id}")
            return

        base_info = song_rows.iloc[0]
        title = base_info['Title']
        
        # 显示头部信息
        print("\n" + "="*60)
        print(f"🎵 {title} (ID: {song_id})")
        print("="*60)
        
        # 基础信息表
        # [修改点] 使用唯一的列名，并隐藏表头
        info_table = PrettyTable()
        info_table.field_names = ["k1", "v1", "k2", "v2"]
        info_table.header = False # 隐藏表头
        info_table.align = "l"
        info_table.add_row(["艺术家", base_info['Artist'], "BPM", base_info['BPM']])
        info_table.add_row(["分类", base_info['Genre'], "版本", base_info['Version']])
        
        # 尝试获取别名并显示
        aliases = base_info.get('Aliases', '')
        if pd.isna(aliases) or aliases == 'nan': aliases = "无"
        # 如果别名太长，截断显示
        aliases_str = str(aliases)
        if len(aliases_str) > 50: aliases_str = aliases_str[:47] + "..."
        info_table.add_row(["别名", aliases_str, "类型", base_info['Type']])
        
        print(info_table)
        print("\n[谱面详情]")
        
        # 难度详情表
        diff_table = PrettyTable()
        diff_table.field_names = ["难度", "等级", "定数", "拟合", "物量", "属性", "达成率", "评级"]
        diff_table.align = "c"
        # 调整列宽
        diff_table._min_width = {"难度": 8, "属性": 10}
        
        # 难度排序
        diff_order = {"Basic": 0, "Advanced": 1, "Expert": 2, "Master": 3, "Re:MASTER": 4, "Utage": 5}
        
        # 准备每一行数据
        rows_to_print = []
        for _, row in song_rows.iterrows():
            rows_to_print.append(row)
            
        # 排序
        rows_to_print.sort(key=lambda x: diff_order.get(x['Difficulty'], 99))
        
        for row in rows_to_print:
            diff_label = row['Difficulty']
            level = row['Level Label']
            ds = row['Official DS']
            
            # 拟合定数 (Chart_fit_diff)
            # 全服数据里可能是空值或NaN
            fit = row.get('Chart_fit_diff', '-')
            if pd.notna(fit) and str(fit).strip() != '':
                try:
                    # 尝试计算 Official DS + fit_diff
                    fit_diff = float(fit) # 这里假设 CSV 里存的是 diff
                    # 但根据之前的 exporter，存的是 'fit_diff' 值本身吗？
                    # 检查 maimai_global.py: fit_diff = curr_c_stat.get('fit_diff', 0)
                    # 它是 "拟合定数 - 官方定数" 的差值吗？
                    # 回看 analyze_difficulty_bias: diff = fit_diff - official_ds
                    # 所以 fit_diff 应该是 "拟合后的定数" 本身
                    fit_val = float(fit)
                    fit_str = f"{fit_val:.2f}"
                except:
                    fit_str = str(fit)
            else:
                fit_str = "-"
                
            # 物量 & 属性 (Ana_Volume, Ana_NoteType)
            vol = row.get('Total Notes', 0)
            note_type = row.get('Ana_NoteType', '-')
            if note_type == "综合": note_type = "-" # 简化显示
            
            # --- 查询用户成绩 ---
            user_ach = "-"
            rank = "-"
            
            if not self.user_data.empty:
                # 尝试匹配用户数据
                # 用户数据通常没有 ID，只能靠 Title + Difficulty
                u_rows = self.user_data[
                    (self.user_data['曲名'] == title) & 
                    (self.user_data['难度'].astype(str).str.lower() == str(diff_label).lower())
                ]
                
                if not u_rows.empty:
                    ach_val = u_rows.iloc[0].get('达成率', 0)
                    if pd.notna(ach_val):
                        user_ach = f"{ach_val}" # CSV里可能已经带%了
                        rank = self.get_rank_from_achievement(ach_val)
            
            diff_table.add_row([
                diff_label, level, ds, fit_str, vol, note_type, user_ach, rank
            ])
            
        print(diff_table)
        print("="*60)

    def run_interactive_query(self):
        """运行交互式查询主循环"""
        print("\n>>> 初始化查询引擎...")
        if not self.load_data():
            input("按回车键退出...")
            return

        while True:
            print("\n" + "-"*40)
            print("🔍 查歌模式")
            print("支持：ID / 曲名 / 别名 (如: 11451, 潘多拉, 鸟折磨)")
            print("输入 'q' 或 '0' 退出")
            print("-" * 40)
            
            query = input("请输入查询关键词: ").strip()
            
            if query.lower() in ['q', '0', 'exit', 'quit']:
                break
            
            if not query: continue
            
            # 执行搜索
            results = self.search_song(query)
            
            if not results:
                print(f"❌ 未找到与 '{query}' 相关的歌曲。")
                continue
            
            # 将 ID 列表去重
            results = list(set(results))
                
            target_id = None
            
            if len(results) == 1:
                target_id = results[0]
            else:
                # 多个结果，显示列表让用户选
                print(f"\n找到 {len(results)} 个结果:")
                table = PrettyTable()
                table.field_names = ["序号", "ID", "曲名"]
                table.align = "l"
                
                # 截取前 15 个结果防止刷屏
                display_results = results[:15]
                
                for idx, sid in enumerate(display_results):
                    title = self.id_to_title.get(sid, "未知曲名")
                    table.add_row([idx+1, sid, title])
                    
                print(table)
                if len(results) > 15:
                    print(f"... (还有 {len(results)-15} 个结果)")
                    
                sel = input("\n请输入序号选择 (直接回车取消): ").strip()
                if sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(display_results):
                        target_id = display_results[idx]
                    else:
                        print("无效序号")
                else:
                    print("已取消")
                    
            if target_id:
                self.display_song_details(target_id)
                
if __name__ == "__main__":
    app = SongQuery()
    app.run_interactive_query()