import requests
import csv
import os
import json
import subprocess
from collections import defaultdict
import time

# --- 辅助类：游戏逻辑与分析算法 ---
class MaimaiAnalyzer:
    def __init__(self):
        # 评分系数表 (Achievement -> Coefficient)
        self.coeff_table = [
            (100.5, 22.4), (100.0, 21.6), (99.5, 21.1), (99.0, 20.8),
            (98.0, 20.3), (97.0, 20.0), (94.0, 16.8), (90.0, 15.2),
            (80.0, 13.6), (79.0, 12.8), (75.0, 12.0), (70.0, 11.2),
            (60.0, 9.6),  (50.0, 8.0),  (40.0, 6.4),  (30.0, 4.8),
            (20.0, 3.2),  (10.0, 1.6),  (0.0, 0.0)
        ]

    def get_rate_coeff(self, achievement):
        for threshold, coeff in self.coeff_table:
            if achievement >= threshold:
                return coeff
        return 0.0

    def analyze_difficulty_bias(self, official_ds, fit_diff):
        """判断 诈称/水/正常"""
        if fit_diff == 0: return "无数据"
        diff = fit_diff - official_ds
        if diff >= 0.4: return "严重诈称" 
        if diff >= 0.2: return "诈称"
        if diff <= -0.4: return "严重逆诈称(水)" 
        if diff <= -0.2: return "逆诈称(水)"
        return "正常"

    def analyze_score_fc_bias(self, dist, fc_dist, total_cnt):
        """分析是容易FC还是容易高分"""
        if total_cnt == 0: return "无数据", "无数据"
        
        fc_plus_count = sum(fc_dist[1:]) # FC+AP
        ap_plus_count = sum(fc_dist[3:]) # AP
        
        sss_plus_count = 0
        if len(dist) >= 2:
            sss_plus_count = dist[-1] + dist[-2] 
            
        fc_ratio = fc_plus_count / total_cnt
        ap_ratio = ap_plus_count / total_cnt
        sss_ratio = sss_plus_count / total_cnt
        
        res_fc = "均衡"
        diff_fc = fc_ratio - sss_ratio
        if diff_fc > 0.05: res_fc = "易FC难高分" 
        elif diff_fc < -0.15: res_fc = "易高分难FC" 
        
        res_ap = "均衡"
        if ap_ratio > 0.1 and ap_ratio > sss_ratio * 0.5: res_ap = "易AP"
        elif ap_ratio < 0.01 and sss_ratio > 0.3: res_ap = "难AP"
        
        return res_fc, res_ap

    def analyze_note_type(self, notes, chart_type, averages):
        """分析谱面属性 (键盘/星星)"""
        total = sum(notes)
        if total == 0: return "无数据"
        
        tap = notes[0]
        hold = notes[1]
        slide = notes[2]
        
        tap_hold_ratio = (tap + hold) / total
        slide_ratio = slide / total
        
        avg_th = averages.get('tap_hold_ratio', 0.6)
        avg_slide = averages.get('slide_ratio', 0.2)
        
        tags = []
        if tap_hold_ratio > avg_th + 0.05: tags.append("键盘倾向")
        if slide_ratio > avg_slide + 0.05: tags.append("星星倾向")
        
        if not tags: return "综合"
        return "&".join(tags)

    def analyze_volume(self, total_notes, avg_notes):
        """分析物量"""
        if avg_notes == 0: return "正常"
        ratio = total_notes / avg_notes
        if ratio > 1.2: return "超大物量"
        if ratio > 1.1: return "大物量"
        if ratio < 0.8: return "超小物量"
        if ratio < 0.9: return "小物量"
        return "正常"

    def analyze_bpm(self, bpm, avg_bpm):
        """分析BPM"""
        try:
            if isinstance(bpm, str) and '-' in bpm:
                val = float(bpm.split('-')[-1])
            else:
                val = float(bpm)
            
            if val > 200: return "超高BPM"
            if val > 160: return "高BPM"
            if val < 120: return "低BPM"
            return "中等BPM"
        except:
            return "未知"


class GlobalExporter:
    def __init__(self):
        self.api_stats = "https://www.diving-fish.com/api/maimaidxprober/chart_stats"
        self.api_music = "https://www.diving-fish.com/api/maimaidxprober/music_data"
        
        # 本地仓库配置
        self.repo_url = "https://github.com/CrazyKidCN/maimaiDX-CN-songs-database.git"
        self.repo_dir = "maimaiDX-CN-songs-database"
        self.json_path = os.path.join(self.repo_dir, "maidata.json")
        
        self.analyzer = MaimaiAnalyzer()

    def _update_local_repo(self):
        """执行 git clone 或 git pull"""
        print(f"[Git] 正在检查本地数据库: {self.repo_dir}")
        try:
            subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except:
            print("[警告] 未检测到 Git 环境，将尝试直接读取。")
            return os.path.exists(self.json_path)

        if os.path.exists(self.repo_dir):
            try:
                subprocess.run(["git", "-C", self.repo_dir, "pull"], check=True)
            except: pass
        else:
            try:
                subprocess.run(["git", "clone", self.repo_url, self.repo_dir], check=True)
            except: pass
        
        return os.path.exists(self.json_path)

    def _load_local_db(self):
        """读取本地 JSON 建立 Title -> Info 映射"""
        if not self._update_local_repo():
            return {}
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            local_map = {}
            for item in data:
                title = item.get('title', '').strip()
                if title: local_map[title] = item
            return local_map
        except Exception as e:
            print(f"[错误] 读取 JSON 失败: {e}")
            return {}

    def _fetch_aliases(self):
        """[NEW] 获取乐曲别名数据 (基于 API 文档)"""
        print("正在获取乐曲别名数据...")
        
        # 1. 主API (yuzuchan.moe)
        # 2. 备用源 (oss.lista233.cn - 静态文件，不易被封)
        sources = [
            "https://api.yuzuchan.moe/maimaidx/maimaidxalias",
            "https://oss.lista233.cn/alias.json"
        ]
        
        # 必须添加 Header 伪装，否则 yuzuchan API 会返回 403 Forbidden
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://mai.lista233.cn/",
            "Origin": "https://mai.lista233.cn"
        }

        data_content = None
        
        for url in sources:
            try:
                print(f"-> 尝试下载别名: {url}")
                # 增加超时设置，防止脚本卡死
                resp = requests.get(url, headers=headers, timeout=20)
                resp.raise_for_status()
                json_data = resp.json()
                
                # 根据文档，数据结构应为 {"status_code": 200, "content": [...]} 或 直接是内容列表
                # 这里做兼容处理
                if 'content' in json_data:
                    data_content = json_data['content']
                    print(f"   [成功] 从 {url} 获取数据")
                    break
                elif isinstance(json_data, list):
                    # 有些备用源可能直接返回列表
                    data_content = json_data
                    print(f"   [成功] 从 {url} 获取数据 (列表格式)")
                    break
                else:
                    print(f"   [失败] 数据格式不匹配，未找到 'content' 字段")
            except Exception as e:
                print(f"   [失败] 无法获取: {e}")
                continue
        
        if not data_content:
            print("[警告] 所有别名源均不可用，导出的 CSV 将不包含别名。")
            return {}

        # 解析数据
        alias_map = {}
        count = 0
        
        # 遍历 content 列表
        # 数据结构示例: {"SongID": 8, "Name": "...", "Alias": ["别名1", "别名2"]}
        if isinstance(data_content, dict):
            # 防止 content 本身是个 dict 而不是 list (虽然文档说是 list)
            data_content = [data_content]

        for item in data_content:
            try:
                # 兼容可能的 key 大小写差异 (SongID vs song_id)
                sid = item.get('SongID') or item.get('song_id')
                if sid is None: continue
                sid = int(sid)
                
                aliases = item.get('Alias') or item.get('alias', [])
                if aliases and isinstance(aliases, list):
                    # 过滤掉空字符串
                    valid_aliases = [str(a) for a in aliases if a]
                    if valid_aliases:
                        alias_map[sid] = valid_aliases
                        count += 1
            except (ValueError, TypeError):
                continue
        
        print(f"[完成] 解析了 {count} 首歌曲的别名信息")
        return alias_map

    def _calculate_global_averages(self, music_map):
        """预计算平均值"""
        accumulators = defaultdict(lambda: defaultdict(list))
        
        for music in music_map.values():
            try:
                bpm_val = 0
                bpm_str = str(music.get('basic_info', {}).get('bpm', 0))
                if '-' in bpm_str: bpm_val = float(bpm_str.split('-')[-1])
                else: bpm_val = float(bpm_str)
            except: bpm_val = 140

            charts = music.get('charts', [])
            for idx, chart in enumerate(charts):
                notes = chart.get('notes', [])
                if not notes: continue
                
                total = sum(notes)
                if total == 0: continue
                
                tap_hold = notes[0] + notes[1]
                slide = notes[2]
                
                accumulators[idx]['total_notes'].append(total)
                accumulators[idx]['tap_hold'].append(tap_hold / total)
                accumulators[idx]['slide'].append(slide / total)
                accumulators[idx]['bpm'].append(bpm_val)

        averages = {}
        for idx, data in accumulators.items():
            averages[idx] = {
                'avg_notes': sum(data['total_notes']) / len(data['total_notes']),
                'tap_hold_ratio': sum(data['tap_hold']) / len(data['tap_hold']),
                'slide_ratio': sum(data['slide']) / len(data['slide']),
                'avg_bpm': sum(data['bpm']) / len(data['bpm'])
            }
        return averages

    def run(self, music_map=None):
        filename = "maimai_global_stats.csv"
        print(f"\n[模块: 全服数据] 正在启动...")

        # 1. 本地增强数据
        local_db_map = self._load_local_db()

        # 2. 基础数据
        if not music_map:
            print("正在获取 DivingFish 基础歌曲列表...")
            try:
                music_map = {int(s['id']): s for s in requests.get(self.api_music).json()}
            except Exception as e:
                print(f"[错误] API 连接失败: {e}")
                return

        # 3. 预分析
        print("正在进行全库预分析 (计算平均水平)...")
        global_averages = self._calculate_global_averages(music_map)

        # 4. 全服统计
        print("正在下载全服统计数据 (chart_stats)...")
        try:
            resp = requests.get(self.api_stats)
            resp.raise_for_status()
            stats_data = resp.json()
        except Exception as e:
            print(f"[错误] 统计数据获取失败: {e}")
            return
            
        # 5. [NEW] 获取别名 (调用更新后的函数)
        alias_map = self._fetch_aliases()

        charts_map = stats_data.get('charts', {})
        diff_data_map = stats_data.get('diff_data', {})
        
        chart_keys = set()
        diff_keys = set()
        for v in charts_map.values():
            for item in v:
                if item: chart_keys.update(item.keys())
        if 'diff' in chart_keys: chart_keys.remove('diff')

        for v in diff_data_map.values():
            if v: diff_keys.update(v.keys())

        print("正在合并数据、执行高级分析并生成 CSV...")
        level_labels = ["Basic", "Advanced", "Expert", "Master", "Re:MASTER"]
        rows = []

        # 6. 主遍历
        for song_id, music in music_map.items():
            title = music.get('title', '').strip()
            basic_info = music.get('basic_info', {})
            
            artist = basic_info.get('artist', '')
            genre = basic_info.get('genre', '')
            bpm = basic_info.get('bpm', '')
            version_api = basic_info.get('from', '')
            is_new = basic_info.get('is_new', False)
            
            local_info = local_db_map.get(title, {})
            cn_category = local_info.get('category', '')
            cn_version = local_info.get('version', '')
            image_file = local_info.get('image_file', '')
            
            # [NEW] 别名处理
            aliases_list = alias_map.get(song_id, [])
            # 使用分号连接所有别名，方便 Excel 查看
            aliases_str = "; ".join(aliases_list)
            
            ds_list = music.get('ds', [])
            level_list = music.get('level', [])
            charts_detail = music.get('charts', [])
            
            for idx in range(len(ds_list)):
                if idx >= len(level_list): continue
                
                display_level = level_list[idx]
                official_ds = ds_list[idx]
                difficulty_label = level_labels[idx] if idx < 5 else "Utage"
                
                charter = ""
                notes = []
                if idx < len(charts_detail):
                    charter = charts_detail[idx].get('charter', '')
                    notes = charts_detail[idx].get('notes', [])

                c_stats = charts_map.get(str(song_id), [])
                curr_c_stat = {}
                if idx < len(c_stats) and c_stats[idx]:
                    curr_c_stat = c_stats[idx]

                # 分析数据
                fit_diff = curr_c_stat.get('fit_diff', 0)
                if fit_diff is None: fit_diff = 0
                bias_label = self.analyzer.analyze_difficulty_bias(official_ds, fit_diff)
                
                dist = curr_c_stat.get('dist', [])
                fc_dist = curr_c_stat.get('fc_dist', [])
                total_cnt = curr_c_stat.get('cnt', 0)
                fc_bias, ap_bias = self.analyzer.analyze_score_fc_bias(dist, fc_dist, total_cnt)
                
                curr_avgs = global_averages.get(idx, {})
                type_bias = self.analyzer.analyze_note_type(notes, music.get('type'), curr_avgs)
                
                total_notes = sum(notes) if notes else 0
                vol_bias = self.analyzer.analyze_volume(total_notes, curr_avgs.get('avg_notes', 0))

                break_count = notes[-1] if notes else 0
                bpm_bias = self.analyzer.analyze_bpm(bpm, curr_avgs.get('avg_bpm', 0))

                row = {
                    "Song ID": song_id,
                    "Title": title,
                    "Aliases": aliases_str, # [NEW]
                    "Type": music.get('type'),
                    "Difficulty": difficulty_label,
                    "Level Index": idx,
                    "Level Label": display_level,
                    "Official DS": official_ds,
                    
                    "Artist": artist,
                    "Genre": genre,
                    "BPM": bpm,
                    "Version": version_api,
                    "Is_New": is_new,
                    "Charter": charter,
                    "Total Notes": total_notes,
                    "Break Count": break_count,
                    "CN_Category": cn_category,
                    "CN_Version": cn_version,
                    "Image_File": image_file,
                    
                    "Ana_DiffBias": bias_label,
                    "Ana_FCBias": fc_bias,
                    "Ana_APBias": ap_bias,
                    "Ana_NoteType": type_bias,
                    "Ana_Volume": vol_bias,
                    "Ana_BPM": bpm_bias,
                }

                for k in chart_keys:
                    row[f"Chart_{k}"] = curr_c_stat.get(k, "")

                curr_d_stat = diff_data_map.get(display_level, {})
                for k in diff_keys:
                    row[f"Global_{k}"] = curr_d_stat.get(k, "")

                rows.append(row)

        if rows:
            base_headers = [
                "Song ID", "Title", "Aliases", "Type", "Difficulty", "Level Index", "Level Label", "Official DS",
                "Artist", "Genre", "BPM", "Version", "Is_New", "Charter", "Total Notes", "Break Count",
                "CN_Category", "CN_Version", "Image_File",
                "Ana_DiffBias", "Ana_FCBias", "Ana_APBias", 
                "Ana_NoteType", "Ana_Volume", "Ana_BPM"
            ]
            
            chart_headers = sorted([f"Chart_{k}" for k in chart_keys])
            global_headers = sorted([f"Global_{k}" for k in diff_keys])
            final_headers = base_headers + chart_headers + global_headers
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=final_headers)
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"[成功] 数据已分析并保存至: {os.path.abspath(filename)}")
                print(f"       包含 {len(rows)} 条谱面数据。")
                print(f"       已集成列: Aliases (别名)")
            except IOError:
                print(f"[错误] 写入失败，文件可能被占用。")

if __name__ == "__main__":
    exporter = GlobalExporter()
    exporter.run()