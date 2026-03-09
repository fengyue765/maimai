# maimai_progress.py
import csv
import os
from prettytable import PrettyTable

class ProgressTracker:
    def __init__(self):
        self.global_csv = "maimai_global_stats.csv"
        self.output_dir = "results"
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        
    def _load_csv(self):
        """读取 CSV，支持 UTF-8 和 GBK 两种编码"""
        if not os.path.exists(self.global_csv):
            print(f"[错误] 找不到 {self.global_csv}")
            return []

        rows = []
        # 尝试 UTF-8
        try:
            with open(self.global_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except UnicodeDecodeError:
            # 失败则尝试 GBK
            try:
                with open(self.global_csv, 'r', encoding='gbk') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
            except Exception as e:
                print(f"[错误] 无法识别文件编码: {e}")
                return []
        return rows
    
    def _get_numeric_value(self, row, key, default=0):
        """安全获取数值"""
        try:
            value = row.get(key, '').strip()
            return float(value) if value else default
        except:
            return default
    
    def _get_int_value(self, row, key, default=0):
        """安全获取整数值"""
        try:
            value = row.get(key, '').strip()
            return int(float(value)) if value else default
        except:
            return default
    
    def _save_to_csv(self, path_name, dimension_name, path_data):
        """保存路径到CSV文件"""
        if not path_data:
            return
        
        filename = f"progress_path_{dimension_name.replace(' ', '_')}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # 准备CSV字段
        fieldnames = ["序号", "定数", "歌名", "类型", "难度", "关键特征", "游玩次数", 
                     "总物量", "拟合定数", "BPM", "版本"]
        
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, song in enumerate(path_data, 1):
                row_data = {
                    "序号": idx,
                    "定数": self._get_numeric_value(song, 'Official DS'),
                    "歌名": song.get('Title', '-').strip(),
                    "类型": song.get('Type', '-').strip(),
                    "难度": song.get('Difficulty', '-').strip(),
                    "关键特征": self._get_key_feature(song, dimension_name),
                    "游玩次数": int(self._get_numeric_value(song, 'Chart_cnt')),
                    "总物量": self._get_int_value(song, 'Total Notes'),
                    "拟合定数": self._get_numeric_value(song, 'Chart_fit_diff'),
                    "BPM": self._get_int_value(song, 'BPM'),
                    "版本": song.get('Version', '-').strip()
                }
                writer.writerow(row_data)
        
        print(f"    路径已保存至: {filepath}")
    
    def _get_key_feature(self, song, dimension_name):
        """获取关键特征字符串"""
        if dimension_name == "键盘倾向":
            return song.get('Ana_NoteType', '-').strip()
        elif dimension_name == "星星倾向":
            return song.get('Ana_NoteType', '-').strip()
        elif dimension_name == "物量适应":
            volume = song.get('Ana_Volume', '-').strip()
            total_notes = self._get_int_value(song, 'Total Notes')
            return f"{volume}({total_notes}物)"
        elif dimension_name == "高BPM反应":
            bpm_tag = song.get('Ana_BPM', '-').strip()
            bpm = self._get_int_value(song, 'BPM')
            return f"{bpm_tag}({bpm}BPM)"
        elif dimension_name == "低BPM稳定":
            bpm_tag = song.get('Ana_BPM', '-').strip()
            bpm = self._get_int_value(song, 'BPM')
            return f"{bpm_tag}({bpm}BPM)"
        return "-"
    
    def analyze_progress_paths(self):
        """分析玩家实力发展路径：从5个维度各选一条关键路径"""
        all_songs = self._load_csv()
        if not all_songs:
            print("无数据可用")
            return
        
        print("\n" + "="*80)
        print("玩家实力发展关键路径分析")
        print("="*80)
        print("从5个维度各选择20首代表性歌曲，基于游玩人数和谱面特征选择监测点")
        print("="*80)
        
        # 维度1: 键盘技术（键盘倾向谱面）
        print("\n1. 键盘技术发展路径")
        keyboard_path = self._get_keyboard_path(all_songs)
        self._print_path_table(keyboard_path, "键盘倾向")
        self._save_to_csv("keyboard", "键盘技术", keyboard_path)
        
        # 维度2: 星星谱面（星星倾向谱面）
        print("\n2. 星星谱面路径")
        star_path = self._get_star_path(all_songs)
        self._print_path_table(star_path, "星星倾向")
        self._save_to_csv("star", "星星谱面", star_path)
        
        # 维度3: 物量适应（大物量和超大物量）
        print("\n3. 物量适应路径（大物量+超大物量）")
        volume_path = self._get_volume_path(all_songs)
        self._print_path_table(volume_path, "物量适应")
        self._save_to_csv("volume", "物量适应", volume_path)
        
        # 维度4: 高BPM反应（超高BPM+高BPM）
        print("\n4. 高BPM反应路径（超高BPM+高BPM）")
        high_bpm_path = self._get_high_bpm_path(all_songs)
        self._print_path_table(high_bpm_path, "高BPM反应")
        self._save_to_csv("high_bpm", "高BPM反应", high_bpm_path)
        
        # 维度5: 低BPM稳定
        print("\n5. 低BPM稳定路径")
        low_bpm_path = self._get_low_bpm_path(all_songs)
        self._print_path_table(low_bpm_path, "低BPM稳定")
        self._save_to_csv("low_bpm", "低BPM稳定", low_bpm_path)
        
        print("\n" + "="*80)
        print("使用建议: 每个维度选择20首曲目作为能力监测点，按定数升序练习")
        print("所有路径已保存至 results/ 目录下的CSV文件")
        print("="*80)
    
    def _filter_songs(self, songs):
        """过滤掉Genre为'宴会場'的歌曲"""
        filtered = []
        for row in songs:
            genre = row.get('Genre', '').strip()
            if genre != "宴会場":
                filtered.append(row)
        return filtered
    
    def _get_keyboard_path(self, songs):
        """获取键盘技术发展路径"""
        # 过滤宴会場
        songs = self._filter_songs(songs)
        
        # 筛选键盘倾向谱面
        keyboard_songs = []
        for row in songs:
            ana_note_type = row.get('Ana_NoteType', '').strip()
            ds = self._get_numeric_value(row, 'Official DS')
            play_count = self._get_numeric_value(row, 'Chart_cnt')
            
            if '键盘倾向' in ana_note_type and 10.0 <= ds <= 14.9 and play_count >= 100:
                keyboard_songs.append(row)
        
        if not keyboard_songs:
            print("   无足够键盘倾向谱面数据")
            return []
        
        # 按定数分组（每0.5分一组）
        ds_groups = {}
        for song in keyboard_songs:
            ds = self._get_numeric_value(song, 'Official DS')
            # 按0.5精度分组
            group_key = int(ds * 2) // 2
            
            if group_key not in ds_groups:
                ds_groups[group_key] = []
            ds_groups[group_key].append(song)
        
        # 在每个分组中选择游玩人数最多的谱面
        path = []
        for group_key in sorted(ds_groups.keys()):
            songs_in_group = ds_groups[group_key]
            # 按游玩人数排序
            songs_in_group.sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            
            # 选择前2-3个热门谱面
            for i in range(min(3, len(songs_in_group))):
                path.append(songs_in_group[i])
                if len(path) >= 30:  # 收集30首，最后选20首
                    break
            if len(path) >= 30:
                break
        
        # 按定数升序排序
        path.sort(key=lambda x: self._get_numeric_value(x, 'Official DS'))
        
        # 确保有20首，从低到高均匀选择
        if len(path) >= 20:
            step = max(1, len(path) // 20)
            selected_path = []
            for i in range(0, len(path), step):
                if len(selected_path) < 20:
                    selected_path.append(path[i])
            return selected_path[:20]
        else:
            return path
    
    def _get_star_path(self, songs):
        """获取星星谱面路径"""
        # 过滤宴会場
        songs = self._filter_songs(songs)
        
        # 筛选星星倾向谱面
        star_songs = []
        for row in songs:
            ana_note_type = row.get('Ana_NoteType', '').strip()
            ds = self._get_numeric_value(row, 'Official DS')
            play_count = self._get_numeric_value(row, 'Chart_cnt')
            
            if '星星倾向' in ana_note_type and 10.0 <= ds <= 14.9 and play_count >= 100:
                star_songs.append(row)
        
        if not star_songs:
            print("   无足够星星倾向谱面数据")
            return []
        
        # 按定数分组（每0.5分一组）
        ds_groups = {}
        for song in star_songs:
            ds = self._get_numeric_value(song, 'Official DS')
            group_key = int(ds * 2) // 2
            
            if group_key not in ds_groups:
                ds_groups[group_key] = []
            ds_groups[group_key].append(song)
        
        # 在每个分组中选择游玩人数最多的谱面
        path = []
        for group_key in sorted(ds_groups.keys()):
            songs_in_group = ds_groups[group_key]
            # 按游玩人数排序
            songs_in_group.sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            
            # 选择前2-3个热门谱面
            for i in range(min(3, len(songs_in_group))):
                path.append(songs_in_group[i])
                if len(path) >= 30:
                    break
            if len(path) >= 30:
                break
        
        # 按定数升序排序
        path.sort(key=lambda x: self._get_numeric_value(x, 'Official DS'))
        
        # 确保有20首
        if len(path) >= 20:
            step = max(1, len(path) // 20)
            selected_path = []
            for i in range(0, len(path), step):
                if len(selected_path) < 20:
                    selected_path.append(path[i])
            return selected_path[:20]
        else:
            return path
    
    def _get_volume_path(self, songs):
        """获取物量适应路径 - 专注于大物量和超大物量"""
        # 过滤宴会場
        songs = self._filter_songs(songs)
        
        # 筛选大物量和超大物量谱面
        large_volume_songs = []
        for row in songs:
            volume = row.get('Ana_Volume', '').strip()
            ds = self._get_numeric_value(row, 'Official DS')
            play_count = self._get_numeric_value(row, 'Chart_cnt')
            
            # 只选择大物量和超大物量
            if volume in ['大物量', '超大物量'] and 10.0 <= ds <= 14.9 and play_count >= 100:
                large_volume_songs.append(row)
        
        if not large_volume_songs:
            print("   无足够大物量谱面数据")
            return []
        
        # 按物量类型分组
        volume_groups = {'大物量': [], '超大物量': []}
        for song in large_volume_songs:
            volume = song.get('Ana_Volume', '').strip()
            if volume in volume_groups:
                volume_groups[volume].append(song)
        
        # 优先选择超大物量，其次大物量
        all_volume_songs = []
        
        # 超大物量优先（权重高）
        if volume_groups['超大物量']:
            volume_groups['超大物量'].sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            # 选择所有超大物量谱面
            all_volume_songs.extend(volume_groups['超大物量'])
        
        # 大物量补充
        if volume_groups['大物量']:
            volume_groups['大物量'].sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            # 根据需要补充
            needed = max(0, 30 - len(all_volume_songs))
            all_volume_songs.extend(volume_groups['大物量'][:needed])
        
        # 按定数升序排序
        all_volume_songs.sort(key=lambda x: self._get_numeric_value(x, 'Official DS'))
        
        # 确保有20首
        if len(all_volume_songs) >= 20:
            # 从低到高均匀选择20首，确保覆盖完整定数范围
            if len(all_volume_songs) > 20:
                # 创建定数区间
                min_ds = self._get_numeric_value(all_volume_songs[0], 'Official DS')
                max_ds = self._get_numeric_value(all_volume_songs[-1], 'Official DS')
                ds_range = max_ds - min_ds
                
                path = []
                # 按定数区间均匀选择
                for i in range(20):
                    target_ds = min_ds + (ds_range * i / 19)  # 均匀分布
                    # 找到最接近目标定数的歌曲
                    closest = min(all_volume_songs, 
                                  key=lambda x: abs(self._get_numeric_value(x, 'Official DS') - target_ds))
                    if closest not in path:
                        path.append(closest)
                    else:
                        # 如果重复，选择下一个最接近的
                        sorted_by_ds = sorted(all_volume_songs, 
                                            key=lambda x: abs(self._get_numeric_value(x, 'Official DS') - target_ds))
                        for song in sorted_by_ds:
                            if song not in path:
                                path.append(song)
                                break
                
                return path[:20]
            else:
                return all_volume_songs[:20]
        else:
            return all_volume_songs
    
    def _get_high_bpm_path(self, songs):
        """获取高BPM反应路径 - 专注于超高BPM和高BPM"""
        # 过滤宴会場
        songs = self._filter_songs(songs)
        
        # 筛选超高BPM和高BPM谱面
        high_bpm_songs = []
        for row in songs:
            bpm_type = row.get('Ana_BPM', '').strip()
            ds = self._get_numeric_value(row, 'Official DS')
            play_count = self._get_numeric_value(row, 'Chart_cnt')
            
            # 只选择超高BPM和高BPM
            if bpm_type in ['超高BPM', '高BPM'] and 10.0 <= ds <= 14.9 and play_count >= 100:
                high_bpm_songs.append(row)
        
        if not high_bpm_songs:
            print("   无足够高BPM谱面数据")
            return []
        
        # 按BPM类型分组
        bpm_groups = {'超高BPM': [], '高BPM': []}
        for song in high_bpm_songs:
            bpm_type = song.get('Ana_BPM', '').strip()
            if bpm_type in bpm_groups:
                bpm_groups[bpm_type].append(song)
        
        # 优先选择超高BPM，其次高BPM
        all_bpm_songs = []
        
        # 超高BPM优先
        if bpm_groups['超高BPM']:
            bpm_groups['超高BPM'].sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            all_bpm_songs.extend(bpm_groups['超高BPM'])
        
        # 高BPM补充
        if bpm_groups['高BPM']:
            bpm_groups['高BPM'].sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            needed = max(0, 30 - len(all_bpm_songs))
            all_bpm_songs.extend(bpm_groups['高BPM'][:needed])
        
        # 按定数升序排序
        all_bpm_songs.sort(key=lambda x: self._get_numeric_value(x, 'Official DS'))
        
        # 确保有20首
        if len(all_bpm_songs) >= 20:
            step = max(1, len(all_bpm_songs) // 20)
            path = []
            for i in range(0, len(all_bpm_songs), step):
                if len(path) < 20:
                    path.append(all_bpm_songs[i])
            return path[:20]
        else:
            return all_bpm_songs
    
    def _get_low_bpm_path(self, songs):
        """获取低BPM稳定路径"""
        # 过滤宴会場
        songs = self._filter_songs(songs)
        
        # 筛选低BPM谱面
        low_bpm_songs = []
        for row in songs:
            bpm_type = row.get('Ana_BPM', '').strip()
            ds = self._get_numeric_value(row, 'Official DS')
            play_count = self._get_numeric_value(row, 'Chart_cnt')
            
            if bpm_type == '低BPM' and 10.0 <= ds <= 14.9 and play_count >= 100:
                low_bpm_songs.append(row)
        
        if not low_bpm_songs:
            print("   无足够低BPM谱面数据")
            return []
        
        # 按定数分组（每0.5分一组）
        ds_groups = {}
        for song in low_bpm_songs:
            ds = self._get_numeric_value(song, 'Official DS')
            group_key = int(ds * 2) // 2
            
            if group_key not in ds_groups:
                ds_groups[group_key] = []
            ds_groups[group_key].append(song)
        
        # 在每个分组中选择游玩人数最多的谱面
        path = []
        for group_key in sorted(ds_groups.keys()):
            songs_in_group = ds_groups[group_key]
            # 按游玩人数排序
            songs_in_group.sort(key=lambda x: self._get_numeric_value(x, 'Chart_cnt'), reverse=True)
            
            # 选择前2-3个热门谱面
            for i in range(min(3, len(songs_in_group))):
                path.append(songs_in_group[i])
                if len(path) >= 30:
                    break
            if len(path) >= 30:
                break
        
        # 按定数升序排序
        path.sort(key=lambda x: self._get_numeric_value(x, 'Official DS'))
        
        # 确保有20首
        if len(path) >= 20:
            step = max(1, len(path) // 20)
            selected_path = []
            for i in range(0, len(path), step):
                if len(selected_path) < 20:
                    selected_path.append(path[i])
            return selected_path[:20]
        else:
            return path
    
    def _print_path_table(self, path, dimension_name):
        """打印路径表格"""
        if not path:
            return
        
        table = PrettyTable()
        table.field_names = ["#", "定数", "歌名", "类型", "难度", "关键特征", "游玩次数"]
        
        table.align["#"] = "r"
        table.align["定数"] = "r"
        table.align["游玩次数"] = "r"
        table.align["歌名"] = "l"
        table.align["类型"] = "c"
        table.align["难度"] = "l"
        table.align["关键特征"] = "l"
        
        table.max_width["歌名"] = 20
        table.max_width["关键特征"] = 15
        
        for idx, song in enumerate(path, 1):
            name = song.get('Title', '-').strip()
            ds = self._get_numeric_value(song, 'Official DS')
            song_type = song.get('Type', '-').strip()
            difficulty = song.get('Difficulty', '-').strip()
            play_count = int(self._get_numeric_value(song, 'Chart_cnt'))
            
            # 获取关键特征
            key_feature = self._get_key_feature(song, dimension_name)
            
            table.add_row([
                idx,
                f"{ds:.1f}",
                name,
                song_type,
                difficulty,
                key_feature,
                f"{play_count:,}"
            ])
        
        if path:
            min_ds = self._get_numeric_value(path[0], 'Official DS')
            max_ds = self._get_numeric_value(path[-1], 'Official DS')
            print(f"   共 {len(path)} 首歌曲 (定数范围: {min_ds:.1f} - {max_ds:.1f})")
        else:
            print(f"   共 0 首歌曲")
        
        print(table)

if __name__ == "__main__":
    tracker = ProgressTracker()
    tracker.analyze_progress_paths()