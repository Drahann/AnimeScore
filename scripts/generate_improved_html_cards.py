#!/usr/bin/env python3
"""
改进版HTML动漫排名卡片生成器
包含更好的设计：海报背景、网站图标、更好的字体、去除背景色
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_latest_data():
    """加载最新的结果文件"""
    # 优先查找final_results目录
    final_results_dir = Path("data/results/final_results")
    results_dir = Path("data/results")

    # 首先尝试final_results目录
    if final_results_dir.exists():
        json_files = list(final_results_dir.glob("anime_ranking_*.json"))
        if json_files:
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            print(f"📂 加载JSON文件: {latest_file.name} (来自final_results)")

            with open(latest_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            data = json_data.get('rankings', [])
            return data, latest_file

    # 如果final_results目录没有文件，则查找主results目录
    if results_dir.exists():
        json_files = list(results_dir.glob("anime_ranking_*.json"))
        if json_files:
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            print(f"📂 加载JSON文件: {latest_file.name} (来自results)")

            with open(latest_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            data = json_data.get('rankings', [])
            return data, latest_file

    print("❌ 没有找到JSON结果文件")
    return None

def load_svg_icon(website_name):
    """加载网站SVG图标，完全保持原始内容不变"""
    logo_map = {
        'anilist': 'AniList_logo.svg',
        'bangumi': 'bangumi.svg',  # 文件不存在，需要重新下载
        'douban': 'douban.svg',  # 豆瓣logo
        'filmarks': 'Filmarks.svg',  # 文件名已更新
        'imdb': 'IMDB_Logo_2016.svg',
        'mal': 'MyAnimeList_Current_Logo.svg'
    }

    logo_file = logo_map.get(website_name.lower())
    if not logo_file:
        return ""

    logo_path = Path("WebsiteLogo") / logo_file
    if not logo_path.exists():
        return ""

    try:
        with open(logo_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # 完全不修改SVG内容，原封不动返回
        return svg_content.strip()
    except Exception as e:
        print(f"⚠️ 无法加载图标 {logo_file}: {e}")
        # 如果文件不存在，返回一个简单的文字标识
        return f'<div style="font-weight: bold; font-size: 10px; color: white;">{website_name.upper()}</div>'

def load_people_icon():
    """加载人数SVG图标并改为白色"""
    icon_path = Path("WebsiteLogo") / "人数.svg"
    if not icon_path.exists():
        return ""

    try:
        with open(icon_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # 将SVG中的路径颜色改为白色
        # 移除原有的fill属性并添加白色fill
        svg_content = svg_content.replace('p-id="1523"', 'p-id="1523" fill="white"')
        svg_content = svg_content.replace('p-id="1524"', 'p-id="1524" fill="white"')
        svg_content = svg_content.replace('p-id="1525"', 'p-id="1525" fill="white"')

        return svg_content.strip()
    except Exception as e:
        print(f"⚠️ 无法加载人数图标: {e}")
        return ""

def create_detailed_html_card(anime_data, rank):
    """创建改进版详细HTML卡片"""
    title = anime_data.get('title_chinese') or anime_data.get('title') or '未知动漫'
    score = anime_data.get('composite_score', 0)
    banner_url = anime_data.get('banner_image', '')
    poster_url = anime_data.get('poster_image', '') or anime_data.get('cover_image', '')
    
    # 处理评分显示
    try:
        score_num = float(score)
        score_display = f"{score_num:.2f}"
    except:
        score_display = "N/A"
    
    # 处理背景图片
    background_style = ""
    if banner_url:
        background_style = f"""
            background-image: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.6)), url('{banner_url}');
            background-size: cover;
            background-position: center;
        """
    else:
        background_style = """
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        """
    
    # 处理海报图片用于排名徽章
    poster_style = ""
    if poster_url:
        poster_style = f"""
            background-image: url('{poster_url}');
            background-size: cover;
            background-position: center;
        """
    else:
        poster_style = """
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        """
    
    # 获取网站评分数据
    ratings = anime_data.get('ratings', [])
    website_cards = ""

    website_colors = {
        'anilist': 'rgba(30, 41, 59, 0.6)',
        'bangumi': 'rgba(30, 41, 59, 0.6)',
        'douban': 'rgba(30, 41, 59, 0.6)',
        'filmarks': 'rgba(30, 41, 59, 0.6)',
        'imdb': 'rgba(30, 41, 59, 0.6)',
        'mal': 'rgba(30, 41, 59, 0.6)'
    }

    # 定义所有网站的顺序和显示名称
    all_websites = [
        ('anilist', 'ANILIST'),
        ('bangumi', 'BANGUMI'),
        ('douban', 'DOUBAN'),
        ('filmarks', 'FILMARKS'),
        ('imdb', 'IMDB'),
        ('mal', 'MAL')
    ]

    # 将评分数据转换为字典，便于查找
    ratings_dict = {}
    for rating in ratings:
        website_key = rating.get('website', '').lower()
        ratings_dict[website_key] = rating

    # 加载人数图标
    people_icon = load_people_icon()

    # 为所有网站生成卡片
    for website_key, website_display in all_websites:
        color = website_colors.get(website_key, 'rgba(30, 41, 59, 0.6)')
        svg_icon = load_svg_icon(website_key)

        if website_key in ratings_dict:
            # 有评分数据
            rating = ratings_dict[website_key]
            raw_score = rating.get('raw_score', 0)
            vote_count = rating.get('vote_count', 0)
            site_rank = rating.get('site_rank', '')
            vote_display = f"{vote_count:,}"

            website_cards += f"""
        <div class="website-card" style="background-color: {color};">
            <div class="website-icon {website_key}">
                {svg_icon}
            </div>
            <div class="website-name">{website_display}</div>
            <div class="website-score">{raw_score:.1f}</div>
            <div class="website-votes">
                <div class="people-icon">{people_icon}</div>
                <span>{vote_display}</span>
            </div>
            <div class="website-rank">#{site_rank}</div>
        </div>
        """
        else:
            # 无评分数据
            website_cards += f"""
        <div class="website-card" style="background-color: {color}; opacity: 0.5;">
            <div class="website-icon {website_key}">
                {svg_icon}
            </div>
            <div class="website-name">{website_display}</div>
            <div class="website-score" style="font-size: 0.9rem; color: #94a3b8;">无评分</div>
            <div class="website-votes" style="color: #64748b;">
                <span style="font-size: 0.6rem;">暂无数据</span>
            </div>
            <div class="website-rank" style="color: #64748b;">-</div>
        </div>
        """
    
    return f"""
    <div class="detailed-ranking-card" style="{background_style}">
        <div class="rank-badge-large" style="{poster_style}">
            <div class="rank-overlay">
                <span class="rank-number-large">{rank:02d}</span>
            </div>
        </div>
        
        <div class="content-area-detailed">
            <div class="title-section-detailed">
                <div class="title-text-large">{title}</div>
                <div class="score-number-detailed">{score_display}</div>
            </div>
            
            <div class="websites-section">
                {website_cards}
            </div>
        </div>
    </div>
    """

def create_html_page(cards_html, title):
    """创建完整的HTML页面"""
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .page-title {{
            text-align: center;
            color: #ffffff;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            letter-spacing: -0.02em;
        }}
        
        .detailed-ranking-card {{
            width: 1200px;
            height: 300px;
            margin: 20px auto;
            border-radius: 20px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border: 2px solid rgba(255,255,255,0.1);
        }}
        
        .rank-badge-large {{
            width: 120px;
            height: 120px;
            border: 4px solid #FFD700;
            border-radius: 50%;
            margin-left: 30px;
            z-index: 10;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }}
        
        .rank-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .rank-number-large {{
            color: #ffffff;
            font-size: 2.8rem;
            font-weight: 800;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            letter-spacing: -0.02em;
        }}
        
        .content-area-detailed {{
            flex: 1;
            padding: 20px 30px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        
        .title-section-detailed {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        
        .title-text-large {{
            color: #ffffff;
            font-size: 1.8rem;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            letter-spacing: -0.01em;
            max-width: 600px;
            line-height: 1.3;
        }}
        
        .score-number-detailed {{
            color: #FFD700;
            font-size: 3rem;
            font-weight: 800;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            letter-spacing: -0.02em;
        }}
        
        .websites-section {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .website-card {{
            border-radius: 12px;
            padding: 12px;
            min-width: 120px;
            text-align: center;
            color: white;
            position: relative;
            opacity: 0.95;
            transition: all 0.3s ease;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .website-card:hover {{
            opacity: 1;
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }}
        
        .website-icon {{
            width: 24px;
            height: 24px;
            margin: 0 auto 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}

        .website-icon svg {{
            width: 20px;
            height: 20px;
            object-fit: contain;
        }}

        /* Filmarks和MAL图标更大一些 (1.5倍) */
        .website-icon.filmarks svg,
        .website-icon.mal svg {{
            width: 30px;
            height: 30px;
        }}
        
        .website-name {{
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .website-score {{
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 4px;
            letter-spacing: -0.01em;
        }}
        
        .website-votes {{
            font-size: 0.7rem;
            opacity: 0.9;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 3px;
        }}

        .people-icon {{
            width: 10px;
            height: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .people-icon svg {{
            width: 10px;
            height: 10px;
        }}
        
        .website-rank {{
            font-size: 0.7rem;
            color: #ffffff;
            font-weight: 700;
            margin-top: 2px;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .detailed-ranking-card {{
                break-inside: avoid;
                margin: 10px auto;
            }}
        }}
        
        @media (max-width: 1280px) {{
            .detailed-ranking-card {{
                width: 95%;
                max-width: 1200px;
            }}
            
            .title-text-large {{
                font-size: 1.5rem;
                max-width: 400px;
            }}
            
            .score-number-detailed {{
                font-size: 2.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="page-title">{title}</h1>
        {cards_html}
    </div>
</body>
</html>
    """

def generate_improved_html_cards(data, count, output_dir):
    """生成改进版HTML卡片"""
    cards_html = ""
    for i, anime in enumerate(data[:count], 1):
        cards_html += create_detailed_html_card(anime, i)

    title = f"动漫排名 TOP {count} - 改进版"
    html_content = create_html_page(cards_html, title)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    html_file = output_path / "ranking_improved.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_file

def main():
    """主函数"""
    print("🎨 改进版HTML动漫排名卡片生成器")
    print("=" * 50)
    print("✨ 新特性:")
    print("   • 更大的排名圆形，使用动漫海报作为背景")
    print("   • 网站矩形包含SVG图标，透明度更高")
    print("   • 使用Inter字体，更加现代美观")
    print("   • 去除标题和评分的背景色，更加简洁")
    print()

    # 加载数据
    result = load_latest_data()
    if not result:
        return

    data, data_file = result
    print(f"📊 成功加载 {len(data)} 个动漫数据")

    # 显示前3名预览
    print(f"\n🏆 排名前3的动漫:")
    for i, anime in enumerate(data[:3], 1):
        title_chinese = anime.get('title_chinese', '')
        title = anime.get('title', '')
        score = anime.get('composite_score', 0)
        poster = anime.get('poster_image', '')
        banner = anime.get('banner_image', '')
        print(f"  {i}. {title_chinese or title}")
        print(f"     综合评分: {score:.3f}")
        print(f"     海报图片: {'✅' if poster else '❌'}")
        print(f"     横幅图片: {'✅' if banner else '❌'}")

    print(f"\n🎯 生成选项:")
    print("1. 生成前3名（演示）")
    print("2. 生成前5名")
    print("3. 生成前10名")
    print("4. 生成前20名")
    print("5. 自定义数量")

    try:
        choice = input("\n请选择 (1-5): ").strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if choice == "1":
            output_file = generate_improved_html_cards(data, 3, f"data/html_cards/improved_top3_{timestamp}")
            print(f"✅ 改进版前3名完成: {output_file}")
        elif choice == "2":
            output_file = generate_improved_html_cards(data, 5, f"data/html_cards/improved_top5_{timestamp}")
            print(f"✅ 改进版前5名完成: {output_file}")
        elif choice == "3":
            output_file = generate_improved_html_cards(data, 10, f"data/html_cards/improved_top10_{timestamp}")
            print(f"✅ 改进版前10名完成: {output_file}")
        elif choice == "4":
            output_file = generate_improved_html_cards(data, 20, f"data/html_cards/improved_top20_{timestamp}")
            print(f"✅ 改进版前20名完成: {output_file}")
        elif choice == "5":
            count = int(input(f"请输入要生成的数量 (1-{min(len(data), 50)}): ").strip())
            count = min(count, len(data), 50)
            output_file = generate_improved_html_cards(data, count, f"data/html_cards/improved_top{count}_{timestamp}")
            print(f"✅ 改进版前{count}名完成: {output_file}")
        else:
            print("❌ 无效选择")
            return

        print(f"\n🎉 改进版HTML卡片生成完成！")
        print(f"📁 输出文件: {output_file}")
        print(f"🌐 使用方法:")
        print(f"   1. 在浏览器中打开HTML文件查看效果")
        print(f"   2. 使用浏览器截图功能保存为图片")
        print(f"   3. 享受更美观的设计和更好的字体显示")

        # 尝试自动打开浏览器
        try:
            import webbrowser
            print(f"\n🌐 正在浏览器中打开...")
            webbrowser.open(f"file:///{output_file.absolute()}")
        except Exception as e:
            print(f"⚠️ 无法自动打开浏览器: {e}")
            print(f"💡 请手动打开: {output_file}")

    except (ValueError, KeyboardInterrupt):
        print("\n❌ 操作已取消")
        return
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()
