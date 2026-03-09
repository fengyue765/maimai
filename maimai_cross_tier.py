import pandas as pd
import os

class CrossTierAnalyzer:
    def __init__(self, file_path="maimai_global_stats.csv"):
        self.file_path = file_path
        self.df = None

    def _load_data(self):
        if not os.path.exists(self.file_path):
            print(f"[错误] 找不到文件: {self.file_path}")
            return False
        try:
            # 读取CSV，确保定数列为数字
            self.df = pd.read_csv(self.file_path)
            self.df['Official DS'] = pd.to_numeric(self.df['Official DS'], errors='coerce')
            return True
        except Exception as e:
            print(f"[错误] 读取数据失败: {e}")
            return False

    def _parse_range(self, input_str):
        """解析用户输入的范围，例如 '12.0-12.5'"""
        try:
            parts = input_str.split('-')
            if len(parts) != 2:
                return None
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    def find_cross_tier_songs(self):
        if self.df is None and not self._load_data():
            return

        print("\n=== 跨定数区间查询 (Cross-Tier Search) ===")
        print("此功能用于查找同一首歌中，分别满足两个不同定数区间的谱面。")
        print("例如：查找既有 12.0-12.5 的谱面，又有 14.0-14.5 谱面的歌曲（通常用于查找红谱简单紫谱难的跨度歌）。")

        # 获取区间 A
        while True:
            range_a_str = input("\n请输入第一个定数区间 (格式 min-max, 如 12.0-12.6): ").strip()
            range_a = self._parse_range(range_a_str)
            if range_a: break
            print("格式错误，请重试。")

        # 获取区间 B
        while True:
            range_b_str = input("请输入第二个定数区间 (格式 min-max, 如 13.7-14.0): ").strip()
            range_b = self._parse_range(range_b_str)
            if range_b: break
            print("格式错误，请重试。")

        print(f"\n正在搜索同时包含 [{range_a[0]}-{range_a[1]}] 和 [{range_b[0]}-{range_b[1]}] 的歌曲...")

        # 按 Song ID 分组
        grouped = self.df.groupby('Song ID')
        results = []

        for song_id, group in grouped:
            # 筛选满足区间 A 的谱面
            charts_a = group[(group['Official DS'] >= range_a[0]) & (group['Official DS'] <= range_a[1])]
            # 筛选满足区间 B 的谱面
            charts_b = group[(group['Official DS'] >= range_b[0]) & (group['Official DS'] <= range_b[1])]

            if not charts_a.empty and not charts_b.empty:
                # 确保不是同一个谱面（虽然定数不同通常意味着不同谱面，但为了严谨排除完全重合的情况）
                # 如果两个区间有重叠，可能同一个谱面同时满足，我们需要通过 Difficulty 区分
                valid_pairs = []
                for _, ca in charts_a.iterrows():
                    for _, cb in charts_b.iterrows():
                        if ca['Difficulty'] != cb['Difficulty']:
                            valid_pairs.append((ca, cb))
                
                if valid_pairs:
                    # 取第一对作为展示，或者展示所有组合
                    # 这里简单的取 title 和第一对组合
                    title = group.iloc[0]['Title']
                    results.append({
                        'id': song_id,
                        'title': title,
                        'pairs': valid_pairs
                    })

        # 输出结果
        if not results:
            print("没有找到符合条件的歌曲。")
        else:
            print(f"\n找到 {len(results)} 首符合条件的歌曲：")
            print("-" * 60)
            print(f"{'ID':<6} | {'Title':<25} | {'Range A Chart':<20} | {'Range B Chart':<20}")
            print("-" * 60)
            
            for res in results:
                # 只显示第一对匹配，避免刷屏
                ca, cb = res['pairs'][0]
                chart_a_info = f"{ca['Difficulty']} {ca['Official DS']}"
                chart_b_info = f"{cb['Difficulty']} {cb['Official DS']}"
                # 截断过长的标题
                title = (res['title'][:22] + '..') if len(res['title']) > 22 else res['title']
                print(f"{res['id']:<6} | {title:<25} | {chart_a_info:<20} | {chart_b_info:<20}")
                
                # 如果有多对组合且区间重叠较大，可以在这里扩展显示
            print("-" * 60)