# maimai_rating_curve.py (修复中文乱码并平滑曲线)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import Dict, List, Tuple
import os
from scipy.interpolate import make_interp_spline

class RatingCurveAnalyzer:
    def __init__(self):
        self.user_data = None
        self.global_data = None
        self._setup_chinese_font()
        
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            # 方法1: 尝试使用本地字体文件
            font_path = os.path.join(os.getcwd(), "msgothic.ttc")
            if os.path.exists(font_path):
                matplotlib.font_manager.fontManager.addfont(font_path)
                font_name = matplotlib.font_manager.FontProperties(fname=font_path).get_name()
                matplotlib.rcParams['font.sans-serif'] = [font_name]
                matplotlib.rcParams['axes.unicode_minus'] = False
                print(f"[系统] 已加载本地字体: {font_name}")
            else:
                # 方法2: 使用系统字体
                plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                print("[系统] 使用系统默认中文字体")
        except Exception as e:
            print(f"[警告] 字体设置失败: {e}")
            print("[提示] 图表可能显示乱码，请确保msgothic.ttc在程序目录下")
    
    def load_user_data(self, csv_path: str = "乐谱.csv"):
        """加载用户数据"""
        try:
            self.user_data = pd.read_csv(csv_path)
            print(f"[系统] 已加载用户数据: {len(self.user_data)} 条记录")
            
            # 清理列名：去除前后空格
            self.user_data.columns = [col.strip() for col in self.user_data.columns]
            print(f"[调试] 清理后列名: {list(self.user_data.columns)}")
            
            return True
        except Exception as e:
            print(f"[错误] 加载用户数据失败: {e}")
            return False
    
    def load_global_data(self, csv_path: str = "maimai_global_stats.csv"):
        """加载全服数据"""
        try:
            self.global_data = pd.read_csv(csv_path)
            print(f"[系统] 已加载全服数据: {len(self.global_data)} 条记录")
            
            # 清理列名：去除前后空格
            self.global_data.columns = [col.strip() for col in self.global_data.columns]
            
            return True
        except Exception as e:
            print(f"[错误] 加载全服数据失败: {e}")
            return False
    
    def get_rating_factor(self, achievement: float) -> float:
        """根据达成率获取Rating因子（精确阶跃处理）"""
        # 按照你提供的表格精确实现
        rating_rules = [
            (100.5, 0.224),      # SSS+
            (100.4999, 0.222),   # SSS (100.5%以下)
            (100.0, 0.216),      # SSS (100%)
            (99.9999, 0.214),    # SS+ (100%以下)
            (99.5, 0.211),       # SS+
            (99.0, 0.208),       # SS
            (98.9999, 0.206),    # S+ (99%以下)
            (98.0, 0.203),       # S+
            (97.0, 0.200),       # S
            (96.9999, 0.176),    # AAA (97%以下)
            (94.0, 0.168),       # AAA
            (90.0, 0.152),       # AA
            (80.0, 0.136),       # A
            (79.9999, 0.128),    # BBB (80%以下)
            (75.0, 0.120),       # BBB
            (70.0, 0.112),       # BB
            (60.0, 0.096),       # B
            (50.0, 0.080),       # C
            (40.0, 0.064),       # D
            (30.0, 0.048),       # D
            (20.0, 0.032),       # D
            (10.0, 0.016),       # D
        ]
        
        # 从高到低检查
        for threshold, factor in rating_rules:
            if achievement >= threshold:
                return factor
        
        return 0.016  # 最低值
    
    def calculate_single_rating(self, ds: float, achievement: float) -> int:
        """计算单曲Rating"""
        rating_factor = self.get_rating_factor(achievement)
        single_rating = ds * achievement * rating_factor
        return int(np.floor(single_rating))  # 向下取整
    
    def calculate_user_curve(self) -> Tuple[np.ndarray, np.ndarray]:
        """计算用户定数-Rating曲线"""
        if self.user_data is None:
            raise ValueError("请先加载用户数据")
        
        # 检查必需的列是否存在
        required_columns = ['定数', 'DX Rating']
        for col in required_columns:
            if col not in self.user_data.columns:
                raise ValueError(f"用户数据中缺少必需的列: {col}。实际列名: {list(self.user_data.columns)}")
        
        # 确保数据是数值类型
        self.user_data['定数'] = pd.to_numeric(self.user_data['定数'], errors='coerce')
        self.user_data['DX Rating'] = pd.to_numeric(self.user_data['DX Rating'], errors='coerce')
        
        # 移除无效数据
        valid_data = self.user_data.dropna(subset=['定数', 'DX Rating'])
        
        if len(valid_data) == 0:
            raise ValueError("用户数据中没有有效的定数或DX Rating数据")
        
        print(f"[调试] 有效数据条数: {len(valid_data)}")
        
        # 获取用户游玩过的所有定数（精确到0.1）
        user_ds_values = np.unique(np.round(valid_data['定数'].values, 1))
        user_ds_values.sort()
        
        print(f"[调试] 唯一定数值数量: {len(user_ds_values)}")
        
        # 为每个定数值计算平均Rating
        user_ratings = []
        
        for ds in user_ds_values:
            # 找出该定数的所有歌曲
            mask = np.abs(valid_data['定数'].values - ds) < 0.05  # 容差0.05
            if np.any(mask):
                avg_rating = valid_data.loc[mask, 'DX Rating'].mean()
                user_ratings.append(avg_rating)
            else:
                user_ratings.append(np.nan)
        
        return user_ds_values, np.array(user_ratings)
    
    def calculate_global_curve(self, min_ds: float = 1.0, max_ds: float = 15.0, step: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """计算全服定数-Rating曲线"""
        if self.global_data is None:
            raise ValueError("请先加载全服数据")
        
        # 清理数据，确保数值类型
        self.global_data['Official DS'] = pd.to_numeric(self.global_data['Official DS'], errors='coerce')
        self.global_data['Global_achievements'] = pd.to_numeric(self.global_data['Global_achievements'], errors='coerce')
        
        # 移除无效数据
        valid_data = self.global_data.dropna(subset=['Official DS', 'Global_achievements'])
        
        print(f"[调试] 全服有效数据条数: {len(valid_data)}")
        
        # 生成定数网格
        global_ds_values = np.arange(min_ds, max_ds + step/2, step)
        global_ds_values = np.round(global_ds_values, 1)
        global_ratings = []
        
        for ds in global_ds_values:
            # 找出该定数的所有谱面
            mask = np.abs(valid_data['Official DS'].values - ds) < 0.05  # 容差0.05
            subset = valid_data.loc[mask]
            
            if len(subset) > 0:
                # 计算每条谱面的单曲Rating
                single_ratings = []
                for _, row in subset.iterrows():
                    single_rating = self.calculate_single_rating(
                        row['Official DS'], 
                        row['Global_achievements']
                    )
                    single_ratings.append(single_rating)
                
                # 计算该定数的平均Rating
                avg_rating = np.mean(single_ratings)
                global_ratings.append(avg_rating)
            else:
                global_ratings.append(np.nan)
        
        return global_ds_values, np.array(global_ratings)
    
    def smooth_curve(self, x: np.ndarray, y: np.ndarray, num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """平滑曲线"""
        if len(x) < 3:
            return x, y  # 点数太少，无法平滑
        
        # 移除NaN值
        valid_mask = ~np.isnan(y)
        x_valid = x[valid_mask]
        y_valid = y[valid_mask]
        
        if len(x_valid) < 3:
            return x_valid, y_valid
        
        # 确保x是单调递增的
        sort_idx = np.argsort(x_valid)
        x_sorted = x_valid[sort_idx]
        y_sorted = y_valid[sort_idx]
        
        try:
            # 使用三次样条插值平滑曲线
            spline = make_interp_spline(x_sorted, y_sorted, k=3)
            
            # 生成更多的点使曲线平滑
            x_smooth = np.linspace(x_sorted.min(), x_sorted.max(), num_points)
            y_smooth = spline(x_smooth)
            
            return x_smooth, y_smooth
        except Exception as e:
            print(f"[警告] 曲线平滑失败，使用原始数据: {e}")
            return x_sorted, y_sorted
    
    def plot_rating_curves(self, save_path: str = "rating_curve.png"):
        """绘制用户与全服Rating曲线对比图"""
        plt.figure(figsize=(14, 7))
        
        # 计算用户曲线
        user_ds, user_ratings = self.calculate_user_curve()
        
        # 计算全服曲线（覆盖用户定数范围）
        if len(user_ds) > 0:
            min_ds = max(1.0, user_ds.min() - 1.0)
            max_ds = user_ds.max() + 1.0
        else:
            min_ds, max_ds = 1.0, 15.0
        
        print(f"[调试] 全服曲线定数范围: {min_ds:.1f} - {max_ds:.1f}")
        
        global_ds, global_ratings = self.calculate_global_curve(min_ds, max_ds)
        
        # 绘制曲线
        valid_user_mask = ~np.isnan(user_ratings)
        valid_global_mask = ~np.isnan(global_ratings)
        
        if np.any(valid_user_mask):
            # 平滑用户曲线
            x_user = user_ds[valid_user_mask]
            y_user = user_ratings[valid_user_mask]
            
            # 绘制平滑曲线
            x_user_smooth, y_user_smooth = self.smooth_curve(x_user, y_user)
            x_user_smooth, y_user_smooth = self.smooth_curve(x_user_smooth, y_user_smooth)
            
            # 绘制平滑曲线（蓝色实线）
            plt.plot(x_user_smooth, y_user_smooth, 
                    'b-', linewidth=3, alpha=0.8, label='用户平均DX Rating ')
            
            # 在平滑曲线上标记原始数据点
            # plt.scatter(x_user, y_user, color='blue', s=30, alpha=0.5, 
            #           edgecolors='darkblue', linewidth=0.5, zorder=5)
            
            print(f"[调试] 用户曲线有效点数: {len(x_user)}")
            print(f"[调试] 平滑后点数: {len(x_user_smooth)}")
        
        # 全服曲线：虚线（保持原样）
        if np.any(valid_global_mask):
            plt.plot(global_ds[valid_global_mask], global_ratings[valid_global_mask], 
                    'r--', linewidth=2.0, alpha=0.7, label='全服平均单曲Rating')
            print(f"[调试] 全服曲线有效点数: {np.sum(valid_global_mask)}")
        
        # 图表样式
        plt.xlabel('谱面定数', fontsize=13, fontweight='bold')
        plt.ylabel('Rating值', fontsize=13, fontweight='bold')
        plt.title('定数-Rating曲线对比分析', fontsize=15, fontweight='bold', pad=20)
        
        # 设置网格
        plt.grid(True, alpha=0.3, linestyle='--')
        
        # 设置图例
        plt.legend(fontsize=11, loc='upper left', frameon=True, shadow=True)
        
        # 设置坐标轴范围
        if np.any(valid_user_mask):
            x_min = user_ds[valid_user_mask].min() - 0.3
            x_max = user_ds[valid_user_mask].max() + 0.3
            
            # 确保y轴有足够的空间
            y_min = min(user_ratings[valid_user_mask].min(), 
                       global_ratings[valid_global_mask].min() if np.any(valid_global_mask) else 0) - 10
            y_max = max(user_ratings[valid_user_mask].max(), 
                       global_ratings[valid_global_mask].max() if np.any(valid_global_mask) else 300) + 10
            
            plt.xlim(x_min, x_max)
            plt.ylim(y_min, y_max)
        
        # 美化坐标轴
        ax = plt.gca()
        ax.set_axisbelow(True)
        
        # 添加刻度线
        ax.tick_params(axis='both', which='major', labelsize=11)
        
        # 添加背景色
        ax.set_facecolor('#f8f9fa')
        
        plt.tight_layout()
        
        # 保存图片
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
            print(f"[系统] 图表已保存至: {save_path}")
        
        plt.show()
        
        return save_path
    
    def generate_statistics(self):
        """生成统计信息"""
        print("\n" + "="*60)
        print("              定数-Rating曲线统计信息")
        print("="*60)
        
        # 计算用户曲线
        try:
            user_ds, user_ratings = self.calculate_user_curve()
        except ValueError as e:
            print(f"[错误] {e}")
            return
        
        valid_user_mask = ~np.isnan(user_ratings)
        
        if np.any(valid_user_mask):
            user_stats_ds = user_ds[valid_user_mask]
            user_stats_ratings = user_ratings[valid_user_mask]
            
            print(f"\n用户数据统计:")
            print(f"  定数范围: {user_stats_ds.min():.1f} - {user_stats_ds.max():.1f}")
            print(f"  涉及定数点: {len(user_stats_ds)} 个")
            print(f"  最高平均Rating: {user_stats_ratings.max():.1f} (定数 {user_stats_ds[np.argmax(user_stats_ratings)]:.1f})")
            print(f"  最低平均Rating: {user_stats_ratings.min():.1f} (定数 {user_stats_ds[np.argmin(user_stats_ratings)]:.1f})")
            print(f"  总体平均Rating: {user_stats_ratings.mean():.1f}")
        
        # 计算全服曲线
        if np.any(valid_user_mask):
            min_ds = user_stats_ds.min()
            max_ds = user_stats_ds.max()
        else:
            min_ds, max_ds = 1.0, 15.0
            
        global_ds, global_ratings = self.calculate_global_curve(min_ds, max_ds)
        valid_global_mask = ~np.isnan(global_ratings)
        
        if np.any(valid_global_mask) and np.any(valid_user_mask):
            print(f"\n全服数据统计:")
            print(f"  分析定数范围: {global_ds[valid_global_mask].min():.1f} - {global_ds[valid_global_mask].max():.1f}")
            
            # 对比共同定数区间
            common_ratings = []
            for ds in user_stats_ds:
                idx = np.where(np.abs(global_ds - ds) < 0.05)[0]
                if len(idx) > 0 and not np.isnan(global_ratings[idx[0]]):
                    user_idx = np.where(np.abs(user_stats_ds - ds) < 0.05)[0][0]
                    user_rating = user_stats_ratings[user_idx]
                    global_rating = global_ratings[idx[0]]
                    common_ratings.append((ds, user_rating, global_rating))
            
            if common_ratings:
                print(f"  共同分析定数点: {len(common_ratings)} 个")
                
                # 计算平均差距
                gaps = []
                for _, user_rt, global_rt in common_ratings:
                    gaps.append(user_rt - global_rt)
                    
                avg_gap = np.mean(gaps)
                
                if avg_gap > 10:
                    print(f"  用户平均领先全服: {avg_gap:.1f} Rating")
                elif avg_gap < -10:
                    print(f"  用户平均落后全服: {abs(avg_gap):.1f} Rating")
                else:
                    print(f"  用户与全服平均水平接近: 差距 {avg_gap:.1f} Rating")
        
        print("\n" + "="*60)
    
    def run_analysis(self):
        """运行完整分析"""
        print("\n>>> 开始定数-Rating曲线分析...")
        
        # 检查数据文件
        if not os.path.exists("乐谱.csv"):
            print("[错误] 找不到用户数据文件: 乐谱.csv")
            return
        
        if not os.path.exists("maimai_global_stats.csv"):
            print("[错误] 找不到全服数据文件: maimai_global_stats.csv")
            return
        
        # 检查字体文件
        font_path = os.path.join(os.getcwd(), "msgothic.ttc")
        if not os.path.exists(font_path):
            print("[警告] 未找到字体文件 msgothic.ttc，图表中文可能显示乱码")
        
        # 加载数据
        if not self.load_user_data():
            return
        
        if not self.load_global_data():
            return
        
        # 进行检查
        try:
            # 检查用户数据列
            print("[系统] 检查用户数据列...")
            required_columns = ['定数', 'DX Rating']
            missing_columns = [col for col in required_columns if col not in self.user_data.columns]
            if missing_columns:
                print(f"[错误] 用户数据中缺少以下列: {missing_columns}")
                print(f"[调试] 实际列名: {list(self.user_data.columns)}")
                return
                
            # 检查全服数据列
            print("[系统] 检查全服数据列...")
            required_global_columns = ['Official DS', 'Global_achievements']
            missing_global_columns = [col for col in required_global_columns if col not in self.global_data.columns]
            if missing_global_columns:
                print(f"[错误] 全服数据中缺少以下列: {missing_global_columns}")
                print(f"[调试] 实际列名: {list(self.global_data.columns)}")
                return
            
            # 进行分析
            # 生成统计信息
            self.generate_statistics()
            
            # 绘制图表
            print("\n[系统] 正在生成图表...")
            chart_path = self.plot_rating_curves("rating_curve_comparison.png")
            
            print(f"\n分析完成！图表已保存至: {chart_path}")
            
        except Exception as e:
            print(f"[错误] 分析过程中出现异常: {e}")
            import traceback
            traceback.print_exc()