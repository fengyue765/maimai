# maimai_song_game.py
import pandas as pd
import numpy as np
import os
import random
from datetime import datetime
from prettytable import PrettyTable

class SongGuessingGame:
    def __init__(self):
        self.global_data = None
        self.difficulty_maps = None
        self.song_info = None  # 初始化song_info
        self.alias_to_ids = None # 别名到ID的映射字典
        self.game_modes = self.load_game_modes()
        self.current_game = None
        
    def load_game_modes(self):
        """加载游戏模式配置（开发者可编辑）"""
        # 基础游戏模式配置 - 开发者可以在这里编辑
        modes = {
            "1": {
                "name": "Expert:初级",
                "description": "Expert定数 7.0—9.5",
                "min_expert_ds": 7.0,
                "max_expert_ds": 9.5,
                "games_per_challenge": 4,
                "max_errors": 70
            },
            "2": {
                "name": "Expert:中级",
                "description": "Expert定数 9.6—11.5",
                "min_expert_ds": 9.6,
                "max_expert_ds": 11.5,
                "games_per_challenge": 4,
                "max_errors": 60
            },
            "3": {
                "name": "Expert:上级",
                "description": "Expert定数 11.6—12.5",
                "min_expert_ds": 11.6,
                "max_expert_ds": 12.5,
                "games_per_challenge": 4,
                "max_errors": 50
            },
            "4": {
                "name": "Expert:超上级",
                "description": "Expert定数 12.6—13.9",
                "min_expert_ds": 12.6,
                "max_expert_ds": 13.9,
                "games_per_challenge": 4,
                "max_errors": 40
            },
            "5": {
                "name": "Master:初级",
                "description": "Master定数 10.6—11.9",
                "min_master_ds": 10.6,
                "max_master_ds": 11.9,
                "games_per_challenge": 4,
                "max_errors": 70
            },
            "6": {
                "name": "Master:中级",
                "description": "Master定数 12.0—13.5",
                "min_master_ds": 12.0,
                "max_master_ds": 13.5,
                "games_per_challenge": 4,
                "max_errors": 50
            },
            "7": {
                "name": "Master:上级",
                "description": "Master定数 13.0—14.5",
                "min_master_ds": 13.0,
                "max_master_ds": 14.5,
                "games_per_challenge": 4,
                "max_errors": 30
            },
            "8": {
                "name": "Master:超上级",
                "description": "Master定数 14.0—14.9",
                "min_master_ds": 14.0,
                "max_master_ds": 14.9,
                "games_per_challenge": 4,
                "max_errors": 10
            }
        }
        return modes
    
    def load_data(self):
        """加载数据"""
        if not os.path.exists("maimai_global_stats.csv"):
            print("[错误] 找不到全服数据文件: maimai_global_stats.csv")
            return False
            
        try:
            self.global_data = pd.read_csv("maimai_global_stats.csv", encoding='utf-8')
            # 清理列名：去除前后空格
            self.global_data.columns =[col.strip() for col in self.global_data.columns]
            print(f"[系统] 已加载全服数据: {len(self.global_data)} 条记录")
            
            # 创建歌曲信息映射表
            self.create_song_maps()
            return True
        except Exception as e:
            print(f"[错误] 加载数据失败: {e}")
            return False
    
    def create_song_maps(self):
        """创建歌曲信息及别名映射表"""
        # 获取所有唯一的歌曲
        unique_songs = self.global_data.drop_duplicates(subset=['Song ID'])
        
        # 创建歌曲信息字典
        self.song_info = {}
        self.alias_to_ids = {} # 用于快速根据别名/曲名查找ID，值类型为set集合
        
        for _, row in unique_songs.iterrows():
            song_id = row['Song ID']
            title = row['Title']
            song_type = row['Type']
            
            # 处理别名
            aliases = []
            if 'Aliases' in row and pd.notna(row['Aliases']):
                # 以分号分割并去除空格
                aliases = [a.strip() for a in str(row['Aliases']).split(';') if a.strip()]
            
            # 获取各难度定数
            expert_data = self.global_data[
                (self.global_data['Song ID'] == song_id) & 
                (self.global_data['Difficulty'].isin(['Expert', 'expert', 'EXPERT']))
            ]
            master_data = self.global_data[
                (self.global_data['Song ID'] == song_id) & 
                (self.global_data['Difficulty'].isin(['Master', 'master', 'MASTER']))
            ]
            remaster_data = self.global_data[
                (self.global_data['Song ID'] == song_id) & 
                (self.global_data['Difficulty'].isin(['Re:MASTER', 'Re:Master', 're:master', 'RE:MASTER']))
            ]
            
            expert_ds = expert_data['Official DS'].iloc[0] if len(expert_data) > 0 else None
            master_ds = master_data['Official DS'].iloc[0] if len(master_data) > 0 else None
            has_remaster = len(remaster_data) > 0
            
            self.song_info[song_id] = {
                'title': title,
                'aliases': aliases,
                'type': song_type,
                'genre': row['Genre'],
                'bpm': row['BPM'],
                'version': row['Version'],
                'expert_ds': expert_ds,
                'master_ds': master_ds,
                'has_remaster': has_remaster  # 新增：是否有Re:MASTER难度
            }
            
            # 建立通过标题和别名快速反查ID的字典 (全部转小写实现大小写不敏感)
            keys_to_index = [str(title)] + aliases
            for k in keys_to_index:
                k_lower = k.lower()
                if k_lower not in self.alias_to_ids:
                    self.alias_to_ids[k_lower] = set()
                self.alias_to_ids[k_lower].add(song_id)
    
    def filter_songs_by_mode(self, mode):
        """根据模式筛选歌曲"""
        filtered_songs =[]
        
        for song_id, info in self.song_info.items():
            include = True
            
            # 根据模式条件筛选
            if 'min_expert_ds' in mode:
                if info['expert_ds'] is None or not (mode['min_expert_ds'] <= info['expert_ds'] <= mode['max_expert_ds']):
                    include = False
            elif 'min_master_ds' in mode:
                if info['master_ds'] is None or not (mode['min_master_ds'] <= info['master_ds'] <= mode['max_master_ds']):
                    include = False
            elif 'min_bpm' in mode:
                if info['bpm'] is None or not (mode['min_bpm'] <= info['bpm'] <= mode['max_bpm']):
                    include = False
            elif 'song_type' in mode:
                if info['type'] != mode['song_type']:
                    include = False
            
            if include:
                filtered_songs.append(song_id)
        
        return filtered_songs
    
    def get_comparison_symbol(self, guess_value, target_value, value_type='number'):
        """获取比较符号"""
        if pd.isna(guess_value) or pd.isna(target_value):
            return "?"
        
        if value_type == 'id':
            # ID比较
            if guess_value == target_value:
                return "√"
            elif guess_value < target_value:
                return "↑"
            else:
                return "↓"
        elif value_type == 'category':
            # 分类比较
            if guess_value == target_value:
                return "√"
            else:
                return "×"
        elif value_type == 'bpm':
            # BPM比较
            if guess_value == target_value:
                return "√"
            elif abs(guess_value - target_value) <= 10:
                return "○"
            elif guess_value < target_value:
                return "↑"
            else:
                return "↓"
        elif value_type == 'boolean':
            # 布尔值比较（如是否有Re:MASTER难度）
            if guess_value == target_value:
                return "√"
            else:
                return "×"
        else:
            # 数值比较（定数）
            if guess_value == target_value:
                return "√"
            elif guess_value < target_value:
                return "↑"
            else:
                return "↓"
    
    def format_comparison_value(self, value, symbol, value_type='category'):
        """格式化比较值，添加符号"""
        if pd.isna(value):
            return "N/A"
        
        if value_type == 'category':
            return f"{value}({symbol})"
        elif value_type == 'bpm':
            return f"{int(value) if isinstance(value, (int, float)) else value}({symbol})"
        elif value_type == 'ds':
            return f"{float(value):.1f}({symbol})"
        elif value_type == 'boolean':
            # 布尔值显示为有/无
            display_value = "有" if value else "无"
            return f"{display_value}({symbol})"
        else:
            return f"{value}({symbol})"
    
    def display_guess_history(self, target_info, guess_history):
        """显示本局游戏的猜测历史"""
        if not guess_history:
            return
        
        print(f"\n本局猜测历史 (目标歌曲: {target_info['title']}):")
        history_table = PrettyTable()
        history_table.field_names =["曲名", "分类", "分区", "版本", "BPM", "Expert定数", "Master定数", "Re:MASTER"]
        history_table.align = "l"
        
        for guess_data in guess_history:
            guess_info = self.song_info[guess_data['guess_id']]
            
            # 获取比较符号
            type_symbol = self.get_comparison_symbol(guess_info['type'], target_info['type'], 'category')
            genre_symbol = self.get_comparison_symbol(guess_info['genre'], target_info['genre'], 'category')
            
            # 版本比较
            if guess_info['version'] == target_info['version']:
                version_symbol = "√"
            else:
                version_symbol = self.get_comparison_symbol(guess_data['guess_id'], target_info['title'], 'id')
            
            bpm_symbol = self.get_comparison_symbol(guess_info['bpm'], target_info['bpm'], 'bpm')
            expert_symbol = self.get_comparison_symbol(guess_info['expert_ds'], target_info['expert_ds'])
            master_symbol = self.get_comparison_symbol(guess_info['master_ds'], target_info['master_ds'])
            remaster_symbol = self.get_comparison_symbol(guess_info['has_remaster'], target_info['has_remaster'], 'boolean')
            
            # 格式化显示值
            title_display = guess_info['title']
            type_display = self.format_comparison_value(guess_info['type'], type_symbol, 'category')
            genre_display = self.format_comparison_value(guess_info['genre'], genre_symbol, 'category')
            version_display = self.format_comparison_value(guess_info['version'], version_symbol, 'category')
            bpm_display = self.format_comparison_value(guess_info['bpm'], bpm_symbol, 'bpm')
            expert_display = self.format_comparison_value(guess_info['expert_ds'], expert_symbol, 'ds')
            master_display = self.format_comparison_value(guess_info['master_ds'], master_symbol, 'ds')
            remaster_display = self.format_comparison_value(guess_info['has_remaster'], remaster_symbol, 'boolean')
            
            history_table.add_row([title_display, type_display, genre_display, version_display, 
                                 bpm_display, expert_display, master_display, remaster_display])
        
        print(history_table)
    
    def play_game(self):
        """开始游戏"""
        print("\n>>> 启动猜歌游戏...")
        
        if not self.load_data():
            return
        
        # 选择游戏模式
        print("\n" + "="*60)
        print("猜歌游戏 - 选择模式")
        print("="*60)
        
        mode_table = PrettyTable()
        mode_table.field_names =["ID", "名称", "描述", "局数", "允许错误"]
        mode_table.align = "l"
        
        for mode_id, mode in self.game_modes.items():
            mode_table.add_row([mode_id, mode["name"], mode["description"], 
                              mode["games_per_challenge"], mode["max_errors"]])
        
        print(mode_table)
        
        while True:
            mode_choice = input("\n请选择游戏模式ID (输入0返回主菜单): ").strip()
            if mode_choice == "0":
                return
            if mode_choice in self.game_modes:
                break
            print("[错误] 无效的模式ID")
        
        mode = self.game_modes[mode_choice]
        
        # 筛选符合条件的歌曲
        available_songs = self.filter_songs_by_mode(mode)
        if len(available_songs) < mode['games_per_challenge']:
            print(f"[错误] 符合条件的歌曲不足 {mode['games_per_challenge']} 首，只有 {len(available_songs)} 首")
            return
        
        print(f"\n模式: {mode['name']}")
        print(f"描述: {mode['description']}")
        print(f"歌曲池: {len(available_songs)} 首歌曲")
        print(f"挑战: 猜对 {mode['games_per_challenge']} 首歌")
        print(f"限制: 最多允许 {mode['max_errors']} 次错误")
        
        input("\n按回车键开始游戏...")
        
        # 初始化游戏状态
        self.current_game = {
            'mode': mode,
            'target_songs': random.sample(available_songs, mode['games_per_challenge']),
            'current_round': 0,
            'total_errors': 0,
            'remaining_errors': mode['max_errors'],  # 新增：剩余错误次数
            'round_results': [],  # 新增：存储每局结果
            'guesses_history':[],
            'start_time': datetime.now()
        }
        
        print(f"\n游戏开始! 共有 {len(self.current_game['target_songs'])} 首歌需要猜对。")
        print("输入 'giveup' 可以放弃当前局并查看答案")
        
        # 开始游戏循环
        while self.current_game['current_round'] < len(self.current_game['target_songs']):
            if not self.play_round():
                break
        
        # 游戏结束
        self.end_game()
    
    def play_round(self):
        """进行一局游戏"""
        round_num = self.current_game['current_round'] + 1
        target_song_id = self.current_game['target_songs'][self.current_game['current_round']]
        target_info = self.song_info[target_song_id]
        
        print(f"\n" + "="*60)
        print(f"第 {round_num} 局 / 共 {len(self.current_game['target_songs'])} 局")
        print(f"当前错误次数: {self.current_game['total_errors']} / {self.current_game['mode']['max_errors']}")
        print(f"剩余错误次数: {self.current_game['remaining_errors']}")
        print("="*60)
        
        guesses_in_round = 0
        round_guesses =[]
        
        while True:
            guesses_in_round += 1
            
            # 获取用户输入
            while True:
                guess_input = input(f"\n第 {guesses_in_round} 次猜测 (输入歌曲ID或别名): ").strip()
                
                if guess_input.lower() == "giveup":
                    print(f"\n你放弃了这一局...")
                    print(f"正确答案是: {target_info['title']} (ID: {target_song_id})")
                    print(f"歌曲信息:")
                    print(f"  - DX/SD分类: {target_info['type']}")
                    print(f"  - 分区: {target_info['genre']}")
                    print(f"  - 版本: {target_info['version']}")
                    print(f"  - BPM: {target_info['bpm']}")
                    print(f"  - Expert定数: {target_info['expert_ds']:.1f}" if target_info['expert_ds'] else "  - Expert定数: N/A")
                    print(f"  - Master定数: {target_info['master_ds']:.1f}" if target_info['master_ds'] else "  - Master定数: N/A")
                    print(f"  - 有Re:MASTER难度: {'是' if target_info['has_remaster'] else '否'}")
                    
                    # 记录本局结果为放弃
                    self.current_game['round_results'].append({
                        'round': round_num,
                        'target_song': target_info['title'],
                        'status': '放弃',
                        'guesses_count': guesses_in_round,
                        'gave_up': True
                    })
                    
                    # 记录放弃
                    self.current_game['guesses_history'].append({
                        'round': round_num,
                        'target_song': target_info['title'],
                        'target_id': target_song_id,
                        'guesses': round_guesses,
                        'total_guesses': guesses_in_round,
                        'gave_up': True
                    })
                    
                    self.current_game['current_round'] += 1
                    return True
                
                guess_id = None
                
                # 优先当做纯数字ID解析
                if guess_input.isdigit() and int(guess_input) in self.song_info:
                    guess_id = int(guess_input)
                else:
                    # 如果不是纯数字或者该ID不存在，则进入别名/曲名查询
                    search_key = guess_input.lower()
                    if search_key in self.alias_to_ids:
                        matched_ids = list(self.alias_to_ids[search_key])
                        if len(matched_ids) == 1:
                            guess_id = matched_ids[0]
                        else:
                            # 不能唯一匹配时：提示所有可能结果，利用continue重新外层输入（不增加计次）
                            print(f"[提示] '{guess_input}' 匹配到多首歌曲，请使用ID进行精准选择:")
                            for m_id in matched_ids:
                                m_info = self.song_info[m_id]
                                print(f"  ID: {m_id} - {m_info['title']} ({m_info['type']})")
                            continue
                    else:
                        print("[错误] 未找到对应歌曲，请输入正确的ID或别名")
                        continue
                
                break
            
            # 获取猜测歌曲信息
            guess_info = self.song_info[guess_id]
            
            # 比较并显示结果
            is_correct = (guess_id == target_song_id)
            
            # 获取比较符号
            type_symbol = self.get_comparison_symbol(guess_info['type'], target_info['type'], 'category')
            genre_symbol = self.get_comparison_symbol(guess_info['genre'], target_info['genre'], 'category')
            
            # 版本比较
            if guess_info['version'] == target_info['version']:
                version_symbol = "√"
            else:
                version_symbol = self.get_comparison_symbol(guess_id, target_song_id, 'id')
            
            bpm_symbol = self.get_comparison_symbol(guess_info['bpm'], target_info['bpm'], 'bpm')
            expert_symbol = self.get_comparison_symbol(guess_info['expert_ds'], target_info['expert_ds'])
            master_symbol = self.get_comparison_symbol(guess_info['master_ds'], target_info['master_ds'])
            remaster_symbol = self.get_comparison_symbol(guess_info['has_remaster'], target_info['has_remaster'], 'boolean')
            
            # 格式化显示值
            title_display = guess_info['title']
            type_display = self.format_comparison_value(guess_info['type'], type_symbol, 'category')
            genre_display = self.format_comparison_value(guess_info['genre'], genre_symbol, 'category')
            version_display = self.format_comparison_value(guess_info['version'], version_symbol, 'category')
            bpm_display = self.format_comparison_value(guess_info['bpm'], bpm_symbol, 'bpm')
            expert_display = self.format_comparison_value(guess_info['expert_ds'], expert_symbol, 'ds')
            master_display = self.format_comparison_value(guess_info['master_ds'], master_symbol, 'ds')
            remaster_display = self.format_comparison_value(guess_info['has_remaster'], remaster_symbol, 'boolean')
            
            # 创建本次猜测的结果行
            guess_row =[title_display, type_display, genre_display, version_display, 
                        bpm_display, expert_display, master_display, remaster_display]
            
            # 添加本次猜测到历史记录
            round_guesses.append({
                'guess_id': guess_id,
                'guess_title': guess_info['title'],
                'is_correct': is_correct,
                'guess_row': guess_row  # 保存格式化的猜测行
            })
            
            # 显示本局所有猜测历史
            print(f"\n第 {guesses_in_round} 次猜测结果:")
            history_table = PrettyTable()
            history_table.field_names =["曲名", "分类", "分区", "版本", "BPM", "Expert定数", "Master定数", "Re:MASTER"]
            history_table.align = "l"
            
            # 添加所有历史猜测
            for guess_data in round_guesses:
                history_table.add_row(guess_data['guess_row'])
            
            print(history_table)
            
            if is_correct:
                print(f"\n[成功] 恭喜！猜对了！")
                print(f"正确答案: {target_info['title']} (ID: {target_song_id})")
                print(f"本轮猜测次数: {guesses_in_round}")
                
                # 记录本局结果为成功
                self.current_game['round_results'].append({
                    'round': round_num,
                    'target_song': target_info['title'],
                    'status': '可',
                    'guesses_count': guesses_in_round,
                    'gave_up': False,
                    'errors_in_round': 0  # 新增：记录本局错误次数
                })
                
                # 记录历史
                self.current_game['guesses_history'].append({
                    'round': round_num,
                    'target_song': target_info['title'],
                    'target_id': target_song_id,
                    'guesses': round_guesses,
                    'total_guesses': guesses_in_round,
                    'gave_up': False,
                    'errors_in_round': guesses_in_round - 1  # 本局错误次数
                })
                
                self.current_game['current_round'] += 1
                return True
            else:
                self.current_game['total_errors'] += 1
                self.current_game['remaining_errors'] -= 1
                print(f"\n猜错了！当前错误次数: {self.current_game['total_errors']}/{self.current_game['mode']['max_errors']}")
                print(f"剩余错误次数: {self.current_game['remaining_errors']}")
                
                # 错误次数耗尽不影响游戏流程，继续猜测
                if self.current_game['remaining_errors'] < 0:
                    print(f"[警告] 错误次数已耗尽，但游戏将继续...")
    
    def end_game(self):
        """结束游戏并显示结果"""
        if not self.current_game:
            return
        
        print("\n" + "="*60)
        print("游戏结束!")
        print("="*60)
        
        # 计算游戏时间
        end_time = datetime.now()
        duration = end_time - self.current_game['start_time']
        minutes = duration.total_seconds() // 60
        seconds = duration.total_seconds() % 60
        
        # 显示成绩单
        print("\n游戏成绩单")
        print("="*60)
        
        # 创建成绩单表格
        score_table = PrettyTable()
        score_table.field_names = ["曲目", "结果"]
        score_table.align = "l"
        
        # 统计成功和失败的歌曲
        total_songs = len(self.current_game['target_songs'])
        successful_songs = 0
        
        for i in range(1, total_songs + 1):
            target_song_id = self.current_game['target_songs'][i-1]
            target_info = self.song_info[target_song_id]
            
            # 查找这一局的结果
            round_result = None
            for result in self.current_game.get('round_results', []):
                if result['round'] == i:
                    round_result = result
                    break
            
            if round_result:
                if round_result['status'] == '可':
                    status = '可'
                    successful_songs += 1
                else:
                    # 如果用户放弃了，标记为放弃
                    status = '放弃'
            else:
                # 如果没有记录结果，说明歌曲没有被猜测（可能因为错误次数耗尽提前结束）
                status = '不可'
            
            score_table.add_row([f"曲目{i}: {target_info['title']}", status])
        
        print(score_table)
        
        # 显示剩余错误次数
        remaining_errors = max(0, self.current_game['remaining_errors'])
        print(f"\n剩余错误次数: {remaining_errors}")
        
        # 判断最终结果
        # 只有当所有歌曲都猜对（状态为'可'）且剩余错误次数>=0才算成功
        final_result = "可" if (successful_songs == total_songs and remaining_errors >= 0) else "不可"
        print(f"最终结果: {final_result}")
        
        # 显示详细统计
        print(f"\n详细统计:")
        print(f"游戏模式: {self.current_game['mode']['name']}")
        print(f"成功歌曲: {successful_songs}/{total_songs}")
        print(f"总错误次数: {self.current_game['total_errors']}/{self.current_game['mode']['max_errors']}")
        print(f"剩余错误次数: {remaining_errors}")
        print(f"游戏时间: {int(minutes)}分{int(seconds)}秒")
        
        # 如果有放弃的歌曲，显示正确答案
        abandoned_songs =[r for r in self.current_game.get('round_results', []) if r.get('gave_up', False)]
        if abandoned_songs:
            print("\n放弃局的正确答案:")
            for round_result in abandoned_songs:
                print(f"第 {round_result['round']} 局: {round_result['target_song']}")
        
        # 询问是否再来一局
        while True:
            choice = input("\n是否再来一局? (y/n): ").strip().lower()
            if choice in['y', 'yes', '是']:
                self.current_game = None
                self.play_game()
                break
            elif choice in ['n', 'no', '否']:
                print("返回主菜单...")
                self.current_game = None
                break
            else:
                print("请输入 y/n 或 是/否")
    
    def run(self):
        """运行猜歌游戏主界面"""
        print("\n>>> 启动猜歌游戏...")
        
        while True:
            print("\n" + "="*60)
            print("猜歌游戏")
            print("="*60)
            print("1. 开始游戏")
            print("2. 游戏说明")
            print("0. 返回主菜单")
            print("="*60)
            
            choice = input("\n请选择: ").strip()
            
            if choice == "1":
                self.play_game()
            elif choice == "2":
                self.show_instructions()
            elif choice == "0":
                print("返回主菜单...")
                break
            else:
                print("[错误] 无效的选择")
    
    def show_instructions(self):
        """显示游戏说明"""
        print("\n" + "="*60)
        print("猜歌游戏说明")
        print("="*60)
        print("游戏目标:")
        print("  1. 根据提示猜出目标歌曲")
        print("  2. 每次猜测会显示与目标歌曲的比较结果")
        print("  3. 完成指定局数且错误次数不超过限制即为挑战成功")
        print("\n比较符号说明:")
        print("  √ : 完全正确")
        print("  × : 分类或分区不同")
        print("  ↑ : 猜测值小于目标值")
        print("  ↓ : 猜测值大于目标值")
        print("  ○ : BPM相差不超过10但不相等")
        print("\n游戏模式:")
        print("  有8种不同的挑战模式:")
        for mode_id, mode in self.game_modes.items():
            print(f"  {mode_id}. {mode['name']}: {mode['description']}")
        print("\n操作说明:")
        print("  1. 输入歌曲ID或别名进行猜测")
        print("  2. 输入 'giveup' 可以放弃当前局并查看答案")
        print("  3. 若输入的别名命中多首歌（非唯一），程序会退回并列出对应ID供你准确选择")
        print("  4. 错误次数耗尽不影响游戏流程，只影响最终成绩")
        print("\n新增判定条件:")
        print("  - Re:MASTER难度: 显示歌曲是否有Re:MASTER难度")
        print("  - 比较符号: √表示与目标歌曲相同，×表示不同")
        print("="*60)
        input("\n按回车键返回...")