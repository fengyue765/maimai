import csv
import os
from PIL import Image, ImageDraw, ImageFont
import chardet
import unicodedata

SCORE_COEFFICIENT_TABLE = [
    [0, 0, 'D'], [10, 1.6, 'D'], [20, 3.2, 'D'], [30, 4.8, 'D'], [40, 6.4, 'D'],
    [50, 8.0, 'C'], [60, 9.6, 'B'], [70, 11.2, 'BB'], [75, 12.0, 'BBB'],
    [79.9999, 12.8, 'BBB'], [80, 13.6, 'A'], [90, 15.2, 'AA'], [94, 16.8, 'AAA'],
    [96.9999, 17.6, 'AAA'], [97, 20.0, 'S'], [98, 20.3, 'S+'], [98.9999, 20.6, 'S+'],
    [99, 20.8, 'SS'], [99.5, 21.1, 'SS+'], [99.9999, 21.4, 'SS+'], [100, 21.6, 'SSS'],
    [100.4999, 22.2, 'SSS'], [100.5, 22.4, 'SSS+']
]

DIFF_COLORS = {
    "Basic": (34, 172, 56),
    "Advanced": (243, 152, 0),
    "Expert": (230, 0, 18),
    "Master": (165, 0, 181),
    "Re:MASTER": (210, 200, 230)
}

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read(10000))
        enc = result['encoding']
        return 'gb18030' if enc and 'gb' in enc.lower() else 'utf-8'

def normalize_text(text):
    """标准化文本：移除特殊符号，统一空白字符"""
    if not text:
        return ""
    
    # 替换常见的编码问题字符
    char_replacements = {
        '∈': '∈',  # 保持原样，如果可能
        'Χ': 'Χ',
        'ℝ': 'ℝ',
        '？': '?',  # 全角问号转半角
        '　': ' ',  # 全角空格转半角
    }
    
    for old, new in char_replacements.items():
        text = text.replace(old, new)
    
    # 移除所有空白字符（保留单词间的单个空格）
    text = ' '.join(text.split())
    
    return text.strip().lower()

class B50Generator:
    def __init__(self):
        self.user_csv = "乐谱.csv"
        self.global_csv = "maimai_global_stats.csv"
        self.cover_dir = "maimaiDX-CN-songs-database/cover"
        self.output_dir = "results"
        self.output_file = "b50_result.png"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, self.output_file)
        
        # 字体处理
        self.font_path = self._find_font()
        try:
            self.font_title = ImageFont.truetype(self.font_path, 16)
            self.font_small = ImageFont.truetype(self.font_path, 12)
            self.font_rating = ImageFont.truetype(self.font_path, 14)
        except:
            self.font_title = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_rating = ImageFont.load_default()
    
    def _find_font(self):
        font_paths = [
            'msyh.ttc', 'simhei.ttf', 'simsun.ttc',
            'msgothic.ttc', 'arialuni.ttf'
        ]
        
        for font in font_paths:
            if os.path.exists(font):
                return font
        
        return None

    def get_rank(self, achievement):
        rank = 'd'
        for threshold, _, r_label in SCORE_COEFFICIENT_TABLE:
            if achievement >= threshold:
                rank = r_label
        return rank.upper()

    def find_best_match(self, user_title, user_diff, user_type, global_map):
        """查找最佳匹配（考虑编码差异）"""
        # 尝试完全匹配
        key = (user_title, user_diff, user_type)
        if key in global_map:
            return global_map[key]
        
        # 尝试标准化后的匹配
        normalized_user_title = normalize_text(user_title)
        
        for (global_title, global_diff, global_type), meta in global_map.items():
            normalized_global_title = normalize_text(global_title)
            
            # 检查标准化后的标题是否相似
            if (normalized_user_title == normalized_global_title and 
                user_diff == global_diff and 
                user_type == global_type):
                return meta
            
            # 如果标题主要部分匹配（去掉特殊字符后）
            if (normalized_user_title.replace(' ', '') == normalized_global_title.replace(' ', '') and 
                user_diff == global_diff and 
                user_type == global_type):
                return meta
        
        # 如果还是没找到，尝试类型不同但标题和难度匹配
        for (global_title, global_diff, global_type), meta in global_map.items():
            normalized_global_title = normalize_text(global_title)
            
            if (normalized_user_title == normalized_global_title and 
                user_diff == global_diff):
                # 打印警告但返回匹配
                print(f"警告: 类型不匹配 {user_type} vs {global_type}: {user_title}")
                return meta
        
        return None

    def load_data(self):
        # 加载全局数据
        global_map = {}
        if os.path.exists(self.global_csv):
            encoding = detect_encoding(self.global_csv)
            with open(self.global_csv, 'r', encoding=encoding, errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 保存原始数据
                    key = (row['Title'], row['Difficulty'], row['Type'])
                    global_map[key] = {
                        'is_new': row['Is_New'].lower() == 'true',
                        'image': row['Image_File'],
                        'original_title': row['Title']  # 保存原始标题用于显示
                    }
        
        # 加载用户数据
        encoding = detect_encoding(self.user_csv)
        b35, b15 = [], []
        match_stats = {'exact': 0, 'normalized': 0, 'failed': 0}
        
        with open(self.user_csv, 'r', encoding=encoding, errors='ignore') as f:
            first_line = f.readline()
            f.seek(0)
            delimiter = ',' if ',' in first_line else ('，' if '，' in first_line else '\t')
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row in reader:
                try:
                    row = {k.strip(): v.strip() for k, v in row.items()}
                    title = row.get('曲名', '')
                    diff = row.get('难度', '')
                    chart_type = row.get('类别', '')
                    
                    if not all([title, diff, chart_type, row.get('定数'), row.get('达成率'), row.get('DX Rating')]):
                        continue

                    if diff not in DIFF_COLORS:
                        continue
                    
                    # 使用改进的匹配函数
                    meta = self.find_best_match(title, diff, chart_type, global_map)
                    
                    record = {
                        'title': title,
                        'display_title': meta['original_title'] if meta else title,  # 使用全局数据的标题显示
                        'diff': diff,
                        'type': chart_type,
                        'ds': float(row['定数']),
                        'achievement': float(row['达成率']),
                        'rating': int(float(row['DX Rating'])),
                        'cover': meta['image'] if meta else None,
                        'rank': self.get_rank(float(row['达成率'])),
                        'matched': meta is not None
                    }
                    
                    if meta and meta['is_new']:
                        b15.append(record)
                    else:
                        b35.append(record)
                        
                    # 统计匹配情况
                    if meta:
                        if (title, diff, chart_type) in global_map:
                            match_stats['exact'] += 1
                        else:
                            match_stats['normalized'] += 1
                    else:
                        match_stats['failed'] += 1
                        print(f"未匹配: {title} - {diff} - {chart_type}")
                        
                except Exception as e:
                    print(f"处理行时出错: {e}")
                    continue
        
        print(f"匹配统计: 完全匹配 {match_stats['exact']}, 标准化匹配 {match_stats['normalized']}, 失败 {match_stats['failed']}")
        
        b35.sort(key=lambda x: x['rating'], reverse=True)
        b15.sort(key=lambda x: x['rating'], reverse=True)
        return b35[:35], b15[:15]

    def generate_image(self):
        b35, b15 = self.load_data()
        
        if not b35 and not b15:
            print("无数据")
            return
        
        # 卡片参数
        card_width = 220
        card_height = 70
        cards_per_row = 5
        padding = 5
        
        # 计算图片大小
        b35_rows = (len(b35) + cards_per_row - 1) // cards_per_row
        b15_rows = (len(b15) + cards_per_row - 1) // cards_per_row
        
        img_width = cards_per_row * card_width + (cards_per_row + 1) * padding
        img_height = 100 + (b35_rows + b15_rows) * card_height + (b35_rows + b15_rows + 4) * padding
        
        img = Image.new("RGB", (img_width, img_height), (245, 245, 245))
        draw = ImageDraw.Draw(img)
        
        # 标题
        total_rating = f"{sum(s['rating'] for s in b35) + sum(s['rating'] for s in b15)} = {sum(s['rating'] for s in b35)} + {sum(s['rating'] for s in b15)}"
        draw.text((img_width//2, 45), f"B50 Total: {total_rating}", 
                 font=self.font_title, fill=(0,0,0), anchor='mm')
        
        # 绘制旧曲
        y_offset = 80
        draw.text((padding, y_offset-20), f"PastBest ({len(b35)})", 
                 font=self.font_small, fill=(0,0,0))
        
        for i, song in enumerate(b35):
            row = i // cards_per_row
            col = i % cards_per_row
            
            x = padding + col * (card_width + padding)
            y = y_offset + row * (card_height + padding)
            
            self._draw_song_card(img, draw, song, x, y, card_width, card_height)
        
        # 绘制新曲
        y_offset = y_offset + b35_rows * (card_height + padding) + 30
        draw.text((padding, y_offset-20), f"NewBest ({len(b15)})", 
                 font=self.font_small, fill=(0,0,0))
        
        for i, song in enumerate(b15):
            row = i // cards_per_row
            col = i % cards_per_row
            
            x = padding + col * (card_width + padding)
            y = y_offset + row * (card_height + padding)
            
            self._draw_song_card(img, draw, song, x, y, card_width, card_height)
        
        img.save(self.output_file)
        print(f"完成: {self.output_file}")
    
    def _draw_song_card(self, img, draw, song, x, y, w, h):
        """绘制单个歌曲卡片（带封面）"""
        color = DIFF_COLORS.get(song['diff'], (200, 200, 200))
        
        # 卡片背景（根据匹配状态调整颜色）
        bg_color = (255, 255, 255) if song.get('matched', True) else (255, 240, 240)
        draw.rectangle([x, y, x+w, y+h], fill=bg_color, outline=(220, 220, 220), width=1)
        
        # 绘制封面
        cover_size = 60
        cover_x, cover_y = x+5, y+5
        
        if song['cover'] and self.cover_dir:
            cover_path = os.path.join(self.cover_dir, song['cover'])
            if os.path.exists(cover_path):
                try:
                    cover = Image.open(cover_path).convert("RGBA")
                    cover = cover.resize((cover_size, cover_size), Image.Resampling.LANCZOS)
                    img.paste(cover, (cover_x, cover_y), cover)
                except:
                    draw.rectangle([cover_x, cover_y, cover_x+cover_size, cover_y+cover_size], 
                                 fill=(255, 255, 255))
            else:
                draw.rectangle([cover_x, cover_y, cover_x+cover_size, cover_y+cover_size], 
                             fill=(255, 255, 255))
        else:
            draw.rectangle([cover_x, cover_y, cover_x+cover_size, cover_y+cover_size], 
                         fill=(255, 255, 255))
        
        # 文本区域
        text_x = x + cover_size + 10
        
        # 歌曲名（使用display_title，即全局数据的标题）
        display_title = song.get('display_title', song['title'])
        if len(display_title) > 12:
            display_title = display_title[:11] + "…"
        
        # 添加类型标记
        type_marker = f"{song.get('type', '')} " if song.get('type') else ""
        title_text = f"{display_title}"
        
        # 如果未匹配成功，标记为红色
        text_color = (255, 0, 0) if not song.get('matched', True) else (0, 0, 0)
        
        try:
            draw.text((text_x, y+5), title_text, font=self.font_small, fill=text_color)
        except:
            draw.text((text_x, y+5), title_text, font=ImageFont.load_default(), fill=text_color)
        
        # 难度色条
        draw.rectangle([x, y, x+4, y+h], fill=color)
        
        # 达成率和评级
        score_text = f"{song['achievement']:.4f}% {song['rank']}"
        draw.text((text_x, y+25), score_text, font=self.font_small, fill=(80, 80, 80))
        
        # 定数和Rating
        rating_text = f"DS:{song['ds']} R:{song['rating']}  {type_marker}"
        draw.text((text_x, y+45), rating_text, font=self.font_rating, fill=color)

if __name__ == "__main__":
    gen = B50Generator()
    gen.generate_image()