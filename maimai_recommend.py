import csv
import os
from prettytable import PrettyTable

class Recommender:
    def __init__(self):
        self.global_csv = "maimai_global_stats.csv"

    def _load_csv(self):
        """读取 CSV，支持 UTF-8 和 GBK 两种编码，防止报错"""
        if not os.path.exists(self.global_csv):
            print(f"[错误] 找不到 {self.global_csv}，请先执行功能 1 更新数据库。")
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

    def _parse_input_range(self, user_input):
        """解析用户输入的定数或等级"""
        user_input = user_input.strip()
        try:
            # 情况 1: 输入等级 "13+" -> 范围 13.6 ~ 13.9
            # 官方定数只有一位小数，所以 13+ 对应 13.6, 13.7, 13.8, 13.9
            if user_input.endswith('+'):
                base = int(user_input[:-1])
                return [f"{base + 0.6:.1f}", f"{base + 0.7:.1f}", 
                       f"{base + 0.8:.1f}", f"{base + 0.9:.1f}"]
            
            # 情况 2: 输入具体定数 "13.5" -> 精确匹配 13.5
            elif '.' in user_input:
                val = float(user_input)
                # 确保只有一位小数
                return [f"{val:.1f}"]
            
            # 情况 3: 输入整数等级 "13" -> 范围 13.0 ~ 13.5
            # 官方定数只有一位小数，所以 13 对应 13.0, 13.1, 13.2, 13.3, 13.4, 13.5
            else:
                base = int(user_input)
                return [f"{base + 0.0:.1f}", f"{base + 0.1:.1f}", f"{base + 0.2:.1f}",
                       f"{base + 0.3:.1f}", f"{base + 0.4:.1f}", f"{base + 0.5:.1f}"]
        except ValueError:
            print("[错误] 输入格式无效。示例: 13, 13+, 13.5")
            return None

    def _print_table(self, title, data_list, is_descending=False):
        """使用表格格式化输出歌曲列表"""
        if not data_list:
            print(f"\n--- {title} (无数据) ---")
            return

        print(f"\n{'='*80}")
        print(f"{title} (共 {len(data_list)} 首)")
        print('='*80)
        
        # 先对数据进行排序
        def get_fit_diff(row):
            try:
                fit_val = row.get('Chart_fit_diff', '').strip()
                return float(fit_val) if fit_val else 0.0
            except:
                try:
                    return float(row.get('Official DS', '0'))
                except:
                    return 0.0
        
        # 根据is_descending参数决定排序方向
        data_list.sort(key=get_fit_diff, reverse=is_descending)
        
        # 创建表格
        table = PrettyTable()
        table.field_names = ["ID", "歌名", "类型", "难度", "定数", "拟合", "状态"]
        
        # 设置表格对齐方式
        table.align["ID"] = "r"      # 右对齐
        table.align["定数"] = "r"    # 右对齐
        table.align["拟合"] = "r"    # 右对齐
        table.align["歌名"] = "l"    # 左对齐
        table.align["类型"] = "c"    # 居中
        table.align["难度"] = "l"    # 左对齐
        table.align["状态"] = "l"    # 左对齐
        
        # 设置列宽
        table.max_width["歌名"] = 25
        table.max_width["状态"] = 15
        
        # 添加数据行
        for row in data_list:
            # 处理拟合定数
            fit = row.get('Chart_fit_diff', '-')
            if fit and fit.strip(): 
                try:
                    fit_val = float(fit.strip())
                    fit_display = f"{fit_val:.2f}"
                except:
                    fit_display = "-"
            else:
                fit_display = "-"
            
            # 处理歌名
            name = row.get('Title', '-').strip()
            
            # 处理状态
            status = row.get('Ana_DiffBias', '正常').strip()
            
            # 获取类型和难度
            song_type = row.get('Type', '-').strip()
            difficulty = row.get('Difficulty', '-').strip()
            
            # 添加行到表格
            table.add_row([
                row.get('Song ID', '-').strip(),
                name,
                song_type,
                difficulty,
                row.get('Official DS', '-').strip(),
                fit_display,
                status
            ])
        
        # 打印表格
        print(table)
        print()

    def recommend_score(self, user_input):
        """功能 3: 吃分推荐 (逆诈称)"""
        target_ds_list = self._parse_input_range(user_input)
        if target_ds_list is None: 
            return

        all_songs = self._load_csv()
        
        # 分类容器
        serious_water = [] # 严重逆诈称
        water = []         # 逆诈称

        for row in all_songs:
            try:
                # 排除Genre字段为"宴会場"的歌曲
                genre = row.get('Genre', '').strip()
                if genre == "宴会場":
                    continue
                    
                official_ds = row.get('Official DS', '').strip()
                status = row.get('Ana_DiffBias', '')
            except: 
                continue

            # 检查官方定数是否在目标列表中（精确匹配）
            if official_ds in target_ds_list:
                if "严重逆诈称" in status:
                    serious_water.append(row)
                elif "逆诈称" in status:
                    water.append(row)

        # 显示范围
        if user_input.endswith('+'):
            base = int(user_input[:-1])
            range_str = f"{base + 0.6:.1f}-{base + 0.9:.1f}"
        elif '.' in user_input:
            val = float(user_input)
            range_str = f"{val:.1f}"
        else:
            base = int(user_input)
            range_str = f"{base + 0.0:.1f}-{base + 0.5:.1f}"
            
        print(f"\n>>> 官方定数范围 [{range_str}] 的吃分推荐:")
        # 吃分推荐：水曲按拟合难度升序(越小越水)
        self._print_table("严重逆诈称(大水)", serious_water, is_descending=False)
        self._print_table("逆诈称(小水)", water, is_descending=False)

    def recommend_landmine(self, user_input):
        """功能 4: 避雷推荐 (诈称)"""
        target_ds_list = self._parse_input_range(user_input)
        if target_ds_list is None: 
            return

        all_songs = self._load_csv()
        
        # 分类容器
        serious_mine = [] # 严重诈称
        mine = []         # 诈称

        for row in all_songs:
            try:
                # 排除Genre字段为"宴会場"的歌曲
                genre = row.get('Genre', '').strip()
                if genre == "宴会場":
                    continue
                    
                official_ds = row.get('Official DS', '').strip()
                status = row.get('Ana_DiffBias', '')
            except: 
                continue

            # 检查官方定数是否在目标列表中（精确匹配）
            if official_ds in target_ds_list:
                # 注意：如果不加 "逆" 字判断，"逆诈称" 会被当成 "诈称"
                if "严重诈称" in status:
                    serious_mine.append(row)
                elif "诈称" in status and "逆" not in status:
                    mine.append(row)

        # 显示范围
        if user_input.endswith('+'):
            base = int(user_input[:-1])
            range_str = f"{base + 0.6:.1f}-{base + 0.9:.1f}"
        elif '.' in user_input:
            val = float(user_input)
            range_str = f"{val:.1f}"
        else:
            base = int(user_input)
            range_str = f"{base + 0.0:.1f}-{base + 0.5:.1f}"
            
        print(f"\n>>> 官方定数范围 [{range_str}] 的地雷警报:")
        # 地雷推荐：按拟合难度降序(越大越雷)
        self._print_table("严重诈称(大雷)", serious_mine, is_descending=True)
        self._print_table("诈称(小雷)", mine, is_descending=True)

if __name__ == "__main__":
    # 测试代码
    rec = Recommender()
    rec.recommend_score("13+")