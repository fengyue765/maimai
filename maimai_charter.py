import csv
import os
from collections import defaultdict

# 尝试导入 prettytable，如果未安装则提示
try:
    from prettytable import PrettyTable
except ImportError:
    PrettyTable = None

class CharterAnalyzer:
    def __init__(self):
        self.global_csv = "maimai_global_stats.csv"
        self.output_csv = "results/maimai_charter_stats.csv"

    def _load_csv(self):
        """读取 CSV，兼容编码"""
        if not os.path.exists(self.global_csv):
            print(f"[错误] 找不到 {self.global_csv}，请先更新数据库 (功能 1)。")
            return []
        try:
            with open(self.global_csv, 'r', encoding='utf-8-sig') as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            try:
                with open(self.global_csv, 'r', encoding='gbk') as f:
                    return list(csv.DictReader(f))
            except:
                return []
        return []

    def analyze(self):
        rows = self._load_csv()
        if not rows: return

        print(f"[分析] 正在处理 {len(rows)} 条谱面数据...")

        # 检查是否包含 Break 数据
        has_break_data = 'Break Count' in rows[0]

        # 数据聚合
        stats = defaultdict(lambda: {
            'count': 0, 
            'bias_sum': 0.0, 
            'kb_cnt': 0, 
            'st_cnt': 0, 
            'valid_bias_cnt': 0,
            'total_notes': 0,
            'total_breaks': 0,
        })

        for row in rows:
            charter = row.get('Charter', '').strip()
            # 过滤无效谱师名
            if not charter or charter == '-' or charter == 'Unknown':
                continue
            # 过滤 Utage
            if row['Difficulty'] == 'Utage':
                continue

            # 过滤多人合作谱面 (可选，为了统计准确性，这里只统计单人或作为主导的)
            # 如果想统计所有，可以保留。这里不做特殊处理，直接作为字符串统计。

            s = stats[charter]
            s['count'] += 1
            
            # 1. 定数与偏差
            try:
                fit = float(row.get('Chart_fit_diff', 0))
                official = float(row['Official DS'])

                if fit > 0: 
                    diff = fit - official
                    s['bias_sum'] += diff
                    s['valid_bias_cnt'] += 1
            except: pass

            # 2. 风格
            note_type = row.get('Ana_NoteType', '')
            if '键盘' in note_type: s['kb_cnt'] += 1
            if '星星' in note_type: s['st_cnt'] += 1

            # 3. Break
            if has_break_data:
                try:
                    tn = int(row['Total Notes'])
                    bn = int(row['Break Count'])
                    s['total_notes'] += tn
                    s['total_breaks'] += bn
                except: pass

        # --- 数据后处理 ---
        result_list = []
        for name, data in stats.items():
            # 至少写过 10 张谱面才统计
            if data['count'] < 10: continue
            
            # 平均偏差
            avg_bias = data['bias_sum'] / data['valid_bias_cnt'] if data['valid_bias_cnt'] > 0 else 0
            
            # 风格标签
            kb_ratio = data['kb_cnt'] / data['count']
            st_ratio = data['st_cnt'] / data['count']
            style_label = "综合"
            if kb_ratio > 0.4 and kb_ratio > st_ratio * 1.5: style_label = "键盘"
            elif st_ratio > 0.4 and st_ratio > kb_ratio * 1.5: style_label = "星星"
            
            # Break 比例
            bk_ratio = 0
            if data['total_notes'] > 0:
                bk_ratio = (data['total_breaks'] / data['total_notes']) * 100

            result_list.append({
                'Name': name,
                'Count': data['count'],
                'Avg_Bias': avg_bias,
                'Style': style_label,
                'KB_Pct': kb_ratio * 100,
                'ST_Pct': st_ratio * 100,
                'Break_Pct': bk_ratio
            })

        # --- 排序：按数量降序 ---
        result_list.sort(key=lambda x: x['Count'], reverse=True)

        # --- 输出 1: 保存为 CSV ---
        self._save_to_csv(result_list)

        # --- 输出 2: 控制台 PrettyTable ---
        self._print_prettytable(result_list)

    def _save_to_csv(self, data):
        headers = ['Name', 'Count', 'Avg_Bias', 'Style', 'KB_Pct', 'ST_Pct', 'Break_Pct']
        
        try:
            with open(self.output_csv, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                # 格式化数据以便阅读
                formatted_data = []
                for row in data:
                    new_row = row.copy()
                    new_row['Avg_Bias'] = f"{row['Avg_Bias']:+.3f}"
                    new_row['KB_Pct'] = f"{row['KB_Pct']:.1f}%"
                    new_row['ST_Pct'] = f"{row['ST_Pct']:.1f}%"
                    new_row['Break_Pct'] = f"{row['Break_Pct']:.2f}%"
                    formatted_data.append(new_row)
                
                writer.writerows(formatted_data)
            print(f"[成功] 详细数据已导出至: {os.path.abspath(self.output_csv)}")
        except IOError:
            print("[错误] CSV 写入失败，文件可能被占用。")

    def _print_prettytable(self, data):
        if not PrettyTable:
            print("[提示] 未安装 prettytable 库，无法显示美化表格。")
            print("       请运行 `pip install prettytable` 安装。")
            return

        table = PrettyTable()
        table.field_names = ["排名", "谱师", "数量", "偏差(拟-官)", "Break%", "风格"]
        
        # 设置对齐
        table.align["谱师"] = "l"
        table.align["偏差(拟-官)"] = "r"
        table.align["Break%"] = "r"
        
        for idx, row in enumerate(data):
            # 格式化
            bias_str = f"{row['Avg_Bias']:+.2f}"
            bk_str = f"{row['Break_Pct']:.2f}%"
            
            # 截断过长的名字
            name = row['Name']
            if len(name) > 20: name = name[:18] + ".."

            table.add_row([
                idx + 1,
                name,
                row['Count'],
                bias_str,
                bk_str,
                row['Style']
            ])

        print(table)
        print(f"* 共统计到 {len(data)} 位谱师。")
        print("* 偏差 > 0 表示诈称(硬核)，< 0 表示逆诈称(水)。")

if __name__ == "__main__":
    CharterAnalyzer().analyze()