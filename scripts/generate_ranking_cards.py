#!/usr/bin/env python3
"""
生成动漫排名卡片图片
仿照提供的设计风格，使用横幅图片和中文标题
"""
import csv
import sys
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_latest_data():
    """加载最新的结果文件（优先JSON，然后CSV）"""
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("❌ 结果目录不存在")
        return None

    # 优先查找JSON文件
    json_files = list(results_dir.glob("anime_ranking_*.json"))
    if json_files:
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        print(f"📂 加载JSON文件: {latest_file.name}")

        # 读取JSON数据
        import json
        with open(latest_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 提取排名数据
        data = json_data.get('rankings', [])
        return data, latest_file

    # 如果没有JSON文件，查找CSV文件
    csv_files = list(results_dir.glob("anime_ranking_*.csv"))
    csv_files = [f for f in csv_files if not f.name.endswith('_simple.csv')]

    if not csv_files:
        # 如果没有完整版，尝试简化版
        csv_files = list(results_dir.glob("*_simple.csv"))

    if not csv_files:
        print("❌ 没有找到结果文件")
        return None

    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"📂 加载CSV文件: {latest_file.name}")
    print("⚠️ 注意：CSV文件不包含横幅图片，建议使用JSON文件")

    # 读取CSV数据
    data = []
    with open(latest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    return data, latest_file

def download_image(url, timeout=10):
    """下载图片"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print(f"⚠️ 下载图片失败 {url}: {e}")
        return None

def create_ranking_card(anime_data, rank, card_width=800, card_height=200):
    """创建单个排名卡片"""
    # 创建卡片背景
    card = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    
    # 1. 下载并处理背景图片
    banner_url = anime_data.get('banner_image') or anime_data.get('横幅图片')
    if banner_url and banner_url.strip():
        bg_image = download_image(banner_url)
        if bg_image:
            # 调整背景图片大小并添加暗化效果
            bg_image = bg_image.resize((card_width, card_height), Image.Resampling.LANCZOS)
            # 创建暗化遮罩
            overlay = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 120))
            bg_image = bg_image.convert('RGBA')
            bg_image = Image.alpha_composite(bg_image, overlay)
            card.paste(bg_image, (0, 0))
    else:
        # 如果没有背景图片，使用渐变背景
        for y in range(card_height):
            alpha = int(255 * (1 - y / card_height * 0.5))
            color = (20, 30, 40, alpha)
            draw.rectangle([(0, y), (card_width, y+1)], fill=color)
    
    # 2. 绘制排名徽章（左侧圆形）
    badge_size = 80
    badge_x = 30
    badge_y = (card_height - badge_size) // 2
    
    # 徽章背景（深色圆形）
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], 
                 fill=(30, 30, 30, 200), outline=(255, 215, 0, 255), width=3)
    
    # 排名数字
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
    except:
        font_large = ImageFont.load_default()
    
    rank_text = f"{rank:02d}"
    bbox = draw.textbbox((0, 0), rank_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = badge_x + (badge_size - text_width) // 2
    text_y = badge_y + (badge_size - text_height) // 2
    draw.text((text_x, text_y), rank_text, fill=(255, 255, 255), font=font_large)
    
    # 3. 动漫标题（黄色标签）
    title = anime_data.get('title_chinese') or anime_data.get('Title_Chinese') or \
            anime_data.get('中文名') or anime_data.get('title') or anime_data.get('Title') or '未知动漫'
    
    # 标题背景
    title_bg_x = 150
    title_bg_y = 30
    title_bg_width = min(300, len(title) * 20 + 40)
    title_bg_height = 40
    
    draw.rounded_rectangle([title_bg_x, title_bg_y, 
                           title_bg_x + title_bg_width, title_bg_y + title_bg_height],
                          radius=20, fill=(255, 193, 7, 220))
    
    # 标题文字
    try:
        font_title = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = ImageFont.load_default()
    
    # 截断过长的标题
    if len(title) > 15:
        title = title[:15] + "..."
    
    bbox = draw.textbbox((0, 0), title, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = title_bg_x + (title_bg_width - text_width) // 2
    text_y = title_bg_y + 10
    draw.text((text_x, text_y), title, fill=(0, 0, 0), font=font_title)
    
    # 4. 综合评分（右侧大数字）
    score = anime_data.get('composite_score') or anime_data.get('Composite_Score') or \
            anime_data.get('综合评分') or '0.0'
    
    try:
        score_num = float(score)
        score_text = f"{score_num:.1f}"
    except:
        score_text = "N/A"
    
    try:
        font_score = ImageFont.truetype("arial.ttf", 72)
    except:
        font_score = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), score_text, font=font_score)
    text_width = bbox[2] - bbox[0]
    score_x = card_width - text_width - 50
    score_y = (card_height - (bbox[3] - bbox[1])) // 2
    
    # 评分背景
    draw.rounded_rectangle([score_x - 20, score_y - 10, 
                           score_x + text_width + 20, score_y + (bbox[3] - bbox[1]) + 10],
                          radius=15, fill=(0, 0, 0, 150))
    
    draw.text((score_x, score_y), score_text, fill=(255, 255, 255), font=font_score)
    
    # 5. 附加信息（左下角）
    info_lines = []
    
    # 动漫类型和集数
    anime_type = anime_data.get('anime_type') or anime_data.get('Type') or ''
    episodes = anime_data.get('episodes') or anime_data.get('Episodes') or ''
    if anime_type or episodes:
        type_info = f"{anime_type}" + (f" • {episodes}话" if episodes else "")
        info_lines.append(type_info)
    
    # 网站数量
    website_count = anime_data.get('website_count') or anime_data.get('Website_Count') or \
                   anime_data.get('网站数') or '0'
    info_lines.append(f"{website_count}个评分网站")
    
    try:
        font_info = ImageFont.truetype("arial.ttf", 14)
    except:
        font_info = ImageFont.load_default()
    
    info_y = card_height - 60
    for i, line in enumerate(info_lines):
        draw.text((150, info_y + i * 20), line, fill=(255, 215, 0), font=font_info)
    
    # 6. 装饰星星
    star_x = title_bg_x + title_bg_width + 20
    star_y = title_bg_y + 10
    draw.text((star_x, star_y), "⭐", font=font_title)
    
    return card

def create_ranking_list(data, max_count=10, output_dir="data/ranking_cards"):
    """创建排名列表图片"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🎨 开始生成排名卡片...")
    
    cards = []
    for i, anime in enumerate(data[:max_count], 1):
        print(f"📊 生成第 {i} 名: {anime.get('title_chinese') or anime.get('title') or '未知'}")
        card = create_ranking_card(anime, i)
        cards.append(card)
        
        # 保存单个卡片
        card_filename = f"rank_{i:02d}.png"
        card.save(output_path / card_filename, "PNG")
    
    # 创建完整排名列表
    if cards:
        total_height = len(cards) * 220  # 每个卡片200px + 20px间距
        full_list = Image.new('RGBA', (800, total_height), (15, 23, 42, 255))
        
        for i, card in enumerate(cards):
            y_pos = i * 220
            full_list.paste(card, (0, y_pos), card)
        
        # 保存完整列表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_filename = f"anime_ranking_top{len(cards)}_{timestamp}.png"
        full_list.save(output_path / full_filename, "PNG")
        
        print(f"✅ 排名卡片生成完成!")
        print(f"📁 输出目录: {output_path}")
        print(f"🖼️ 完整列表: {full_filename}")
        print(f"📊 单个卡片: rank_01.png ~ rank_{len(cards):02d}.png")
        
        return output_path / full_filename
    
    return None

def create_detailed_ranking_card(anime_data, rank, card_width=1000, card_height=300):
    """创建包含详细网站评分的排名卡片"""
    # 创建卡片背景
    card = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 1. 背景处理（同上）
    banner_url = anime_data.get('banner_image') or anime_data.get('横幅图片')
    if banner_url and banner_url.strip():
        bg_image = download_image(banner_url)
        if bg_image:
            bg_image = bg_image.resize((card_width, card_height), Image.Resampling.LANCZOS)
            overlay = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 140))
            bg_image = bg_image.convert('RGBA')
            bg_image = Image.alpha_composite(bg_image, overlay)
            card.paste(bg_image, (0, 0))
    else:
        for y in range(card_height):
            alpha = int(255 * (1 - y / card_height * 0.5))
            color = (20, 30, 40, alpha)
            draw.rectangle([(0, y), (card_width, y+1)], fill=color)

    # 2. 排名徽章
    badge_size = 100
    badge_x = 30
    badge_y = (card_height - badge_size) // 2

    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                 fill=(30, 30, 30, 200), outline=(255, 215, 0, 255), width=4)

    try:
        font_large = ImageFont.truetype("arial.ttf", 42)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_tiny = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = font_medium = font_small = font_tiny = ImageFont.load_default()

    rank_text = f"{rank:02d}"
    bbox = draw.textbbox((0, 0), rank_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = badge_x + (badge_size - text_width) // 2
    text_y = badge_y + (badge_size - text_height) // 2
    draw.text((text_x, text_y), rank_text, fill=(255, 255, 255), font=font_large)

    # 3. 动漫标题和综合评分
    title = anime_data.get('title_chinese') or anime_data.get('Title_Chinese') or \
            anime_data.get('中文名') or anime_data.get('title') or anime_data.get('Title') or '未知动漫'

    title_x = 160
    title_y = 30

    # 标题背景
    title_bg_width = min(400, len(title) * 25 + 40)
    draw.rounded_rectangle([title_x, title_y, title_x + title_bg_width, title_y + 50],
                          radius=25, fill=(255, 193, 7, 220))

    # 标题文字
    if len(title) > 20:
        title = title[:20] + "..."

    bbox = draw.textbbox((0, 0), title, font=font_medium)
    text_width = bbox[2] - bbox[0]
    text_x = title_x + (title_bg_width - text_width) // 2
    draw.text((text_x, title_y + 12), title, fill=(0, 0, 0), font=font_medium)

    # 综合评分
    score = anime_data.get('composite_score') or anime_data.get('Composite_Score') or \
            anime_data.get('综合评分') or '0.0'

    try:
        score_num = float(score)
        score_text = f"{score_num:.2f}"
    except:
        score_text = "N/A"

    score_x = title_x + title_bg_width + 50
    score_y = 20

    draw.rounded_rectangle([score_x, score_y, score_x + 120, score_y + 70],
                          radius=15, fill=(0, 0, 0, 180))

    bbox = draw.textbbox((0, 0), score_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_x = score_x + (120 - text_width) // 2
    draw.text((text_x, score_y + 15), score_text, fill=(255, 255, 255), font=font_large)

    # 4. 网站评分详情
    websites = ['ANILIST', 'BANGUMI', 'FILMARKS', 'IMDB', 'MAL']
    website_colors = {
        'ANILIST': (2, 169, 255),
        'BANGUMI': (240, 103, 149),
        'FILMARKS': (255, 87, 51),
        'IMDB': (245, 197, 24),
        'MAL': (46, 81, 162)
    }

    detail_y = 120
    detail_x = 160

    for i, website in enumerate(websites):
        x_pos = detail_x + (i * 160)

        # 获取网站数据
        score_key = f'{website}_Score' if f'{website}_Score' in anime_data else f'{website}_评分'
        votes_key = f'{website}_Votes' if f'{website}_Votes' in anime_data else f'{website}_投票数'
        rank_key = f'{website}_Rank' if f'{website}_Rank' in anime_data else f'{website}_排名'

        website_score = anime_data.get(score_key, '')
        website_votes = anime_data.get(votes_key, '')
        website_rank = anime_data.get(rank_key, '')

        if website_score and str(website_score).strip():
            # 网站背景
            color = website_colors.get(website, (100, 100, 100))
            draw.rounded_rectangle([x_pos, detail_y, x_pos + 140, detail_y + 120],
                                  radius=10, fill=(*color, 180))

            # 网站名称
            draw.text((x_pos + 10, detail_y + 10), website, fill=(255, 255, 255), font=font_small)

            # 评分
            try:
                score_val = float(website_score)
                score_display = f"{score_val:.1f}"
            except:
                score_display = str(website_score)

            draw.text((x_pos + 10, detail_y + 35), score_display, fill=(255, 255, 255), font=font_medium)

            # 投票数
            if website_votes:
                votes_display = f"{website_votes}票"
                draw.text((x_pos + 10, detail_y + 65), votes_display, fill=(255, 255, 255), font=font_tiny)

            # 排名
            if website_rank:
                rank_display = f"#{website_rank}"
                draw.text((x_pos + 10, detail_y + 85), rank_display, fill=(255, 215, 0), font=font_tiny)

    return card

def main():
    """主函数"""
    print("🎨 动漫排名卡片生成器")
    print("=" * 50)

    # 加载数据
    result = load_latest_data()
    if not result:
        return

    data, csv_file = result
    print(f"📊 加载了 {len(data)} 个动漫数据")

    # 获取用户选择
    print(f"\n🎯 请选择生成模式:")
    print("1. 简洁版卡片（类似图片风格）")
    print("2. 详细版卡片（包含所有网站评分）")
    print("3. 两种都生成")

    choice = input("\n请输入选项 (1-3): ").strip()

    try:
        count = int(input(f"请输入要生成的排名数量 (1-{min(len(data), 20)}, 默认10): ").strip() or "10")
        count = min(count, len(data), 20)
    except ValueError:
        count = 10

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if choice in ['1', '3']:
        print(f"\n🎨 生成简洁版卡片...")
        output_file = create_ranking_list(data, count, f"data/ranking_cards/simple_{timestamp}")
        if output_file:
            print(f"✅ 简洁版完成: {output_file}")

    if choice in ['2', '3']:
        print(f"\n🎨 生成详细版卡片...")
        # 生成详细版
        output_dir = Path(f"data/ranking_cards/detailed_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)

        cards = []
        for i, anime in enumerate(data[:count], 1):
            print(f"📊 生成详细卡片 {i}/{count}: {anime.get('title_chinese') or anime.get('title') or '未知'}")
            card = create_detailed_ranking_card(anime, i)
            cards.append(card)

            # 保存单个卡片
            card.save(output_dir / f"detailed_rank_{i:02d}.png", "PNG")

        # 创建完整列表
        if cards:
            total_height = len(cards) * 320
            full_list = Image.new('RGBA', (1000, total_height), (15, 23, 42, 255))

            for i, card in enumerate(cards):
                y_pos = i * 320
                full_list.paste(card, (0, y_pos), card)

            full_filename = f"detailed_anime_ranking_top{len(cards)}_{timestamp}.png"
            full_list.save(output_dir / full_filename, "PNG")
            print(f"✅ 详细版完成: {output_dir / full_filename}")

    print(f"\n🎉 排名卡片生成完成！")

if __name__ == "__main__":
    main()
