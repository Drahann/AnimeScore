#!/usr/bin/env python3
"""
HTML动漫排名卡片生成器
生成HTML格式的排名卡片，支持更好的字体显示和样式控制
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
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("❌ 结果目录不存在")
        return None
    
    # 优先查找JSON文件
    json_files = list(results_dir.glob("anime_ranking_*.json"))
    if json_files:
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        print(f"📂 加载JSON文件: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        data = json_data.get('rankings', [])
        return data, latest_file
    
    print("❌ 没有找到JSON结果文件")
    return None

def create_html_card(anime_data, rank):
    """创建单个动漫的HTML卡片"""
    title = anime_data.get('title_chinese') or anime_data.get('title') or '未知动漫'
    score = anime_data.get('composite_score', 0)
    banner_url = anime_data.get('banner_image', '')
    anime_type = anime_data.get('anime_type', '')
    episodes = anime_data.get('episodes', '')
    website_count = anime_data.get('website_count', 0)
    
    # 处理评分显示
    try:
        score_num = float(score)
        score_display = f"{score_num:.1f}"
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
    
    # 处理附加信息
    info_parts = []
    if anime_type:
        info_parts.append(anime_type)
    if episodes:
        info_parts.append(f"{episodes}话")
    if website_count:
        info_parts.append(f"{website_count}个评分网站")
    
    info_text = " • ".join(info_parts)
    
    return f"""
    <div class="ranking-card" style="{background_style}">
        <div class="rank-badge">
            <span class="rank-number">{rank:02d}</span>
        </div>
        
        <div class="content-area">
            <div class="title-section">
                <div class="title-badge">
                    <span class="title-text">{title}</span>
                </div>
                <div class="star-decoration">⭐</div>
            </div>
            
            <div class="info-section">
                <span class="info-text">{info_text}</span>
            </div>
        </div>
        
        <div class="score-section">
            <div class="score-container">
                <span class="score-number">{score_display}</span>
            </div>
        </div>
    </div>
    """

def create_detailed_html_card(anime_data, rank):
    """创建详细版HTML卡片"""
    title = anime_data.get('title_chinese') or anime_data.get('title') or '未知动漫'
    score = anime_data.get('composite_score', 0)
    banner_url = anime_data.get('banner_image', '')
    
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
            background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.7)), url('{banner_url}');
            background-size: cover;
            background-position: center;
        """
    else:
        background_style = """
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        """
    
    # 获取网站评分数据
    ratings = anime_data.get('ratings', [])
    website_cards = ""
    
    website_colors = {
        'anilist': '#02A9FF',
        'bangumi': '#F06795',
        'filmarks': '#FF5733',
        'imdb': '#F5C518',
        'mal': '#2E5192'
    }
    
    for rating in ratings:
        website = rating.get('website', '').upper()
        raw_score = rating.get('raw_score', 0)
        vote_count = rating.get('vote_count', 0)
        site_rank = rating.get('site_rank', '')
        
        color = website_colors.get(rating.get('website', ''), '#666666')
        
        website_cards += f"""
        <div class="website-card" style="background-color: {color};">
            <div class="website-name">{website}</div>
            <div class="website-score">{raw_score:.1f}</div>
            <div class="website-votes">{vote_count}票</div>
            <div class="website-rank">#{site_rank}</div>
        </div>
        """
    
    return f"""
    <div class="detailed-ranking-card" style="{background_style}">
        <div class="rank-badge-large">
            <span class="rank-number-large">{rank:02d}</span>
        </div>
        
        <div class="content-area-detailed">
            <div class="title-section-detailed">
                <div class="title-badge-large">
                    <span class="title-text-large">{title}</span>
                </div>
                <div class="score-container-detailed">
                    <span class="score-number-detailed">{score_display}</span>
                </div>
            </div>
            
            <div class="websites-section">
                {website_cards}
            </div>
        </div>
    </div>
    """

def create_html_page(cards_html, title, is_detailed=False):
    """创建完整的HTML页面"""
    card_class = "detailed-ranking-card" if is_detailed else "ranking-card"
    
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .page-title {{
            text-align: center;
            color: #ffffff;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .ranking-card {{
            width: 800px;
            height: 200px;
            margin: 20px auto;
            border-radius: 15px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 2px solid rgba(255,215,0,0.3);
        }}
        
        .detailed-ranking-card {{
            width: 1000px;
            height: 300px;
            margin: 20px auto;
            border-radius: 15px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 2px solid rgba(255,215,0,0.3);
        }}
        
        .rank-badge {{
            width: 80px;
            height: 80px;
            background: rgba(30,30,30,0.9);
            border: 3px solid #FFD700;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 30px;
            z-index: 10;
        }}
        
        .rank-badge-large {{
            width: 100px;
            height: 100px;
            background: rgba(30,30,30,0.9);
            border: 4px solid #FFD700;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 30px;
            z-index: 10;
        }}
        
        .rank-number {{
            color: #ffffff;
            font-size: 2.2rem;
            font-weight: 700;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }}
        
        .rank-number-large {{
            color: #ffffff;
            font-size: 2.8rem;
            font-weight: 700;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }}
        
        .content-area {{
            flex: 1;
            padding: 0 30px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        
        .content-area-detailed {{
            flex: 1;
            padding: 20px 30px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        
        .title-section {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .title-section-detailed {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .title-badge {{
            background: rgba(255,193,7,0.95);
            padding: 8px 20px;
            border-radius: 20px;
            margin-right: 15px;
        }}
        
        .title-badge-large {{
            background: rgba(255,193,7,0.95);
            padding: 12px 25px;
            border-radius: 25px;
        }}
        
        .title-text {{
            color: #000000;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        
        .title-text-large {{
            color: #000000;
            font-size: 1.4rem;
            font-weight: 600;
        }}
        
        .star-decoration {{
            font-size: 1.2rem;
        }}
        
        .info-section {{
            margin-top: 10px;
        }}
        
        .info-text {{
            color: #FFD700;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .score-section {{
            margin-right: 30px;
        }}
        
        .score-container {{
            background: rgba(0,0,0,0.8);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        
        .score-container-detailed {{
            background: rgba(0,0,0,0.8);
            padding: 15px 25px;
            border-radius: 15px;
            text-align: center;
        }}
        
        .score-number {{
            color: #ffffff;
            font-size: 3.5rem;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .score-number-detailed {{
            color: #ffffff;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .websites-section {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .website-card {{
            background: #666666;
            border-radius: 10px;
            padding: 10px;
            min-width: 120px;
            text-align: center;
            color: white;
        }}
        
        .website-name {{
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .website-score {{
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 3px;
        }}
        
        .website-votes {{
            font-size: 0.7rem;
            opacity: 0.9;
        }}
        
        .website-rank {{
            font-size: 0.7rem;
            color: #FFD700;
            font-weight: 600;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .{card_class} {{
                break-inside: avoid;
                margin: 10px auto;
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

def generate_simple_html_cards(data, count, output_dir):
    """生成简洁版HTML卡片"""
    cards_html = ""
    for i, anime in enumerate(data[:count], 1):
        cards_html += create_html_card(anime, i)

    title = f"动漫排名 TOP {count} - 简洁版"
    html_content = create_html_page(cards_html, title, False)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    html_file = output_path / "ranking_simple.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_file

def generate_detailed_html_cards(data, count, output_dir):
    """生成详细版HTML卡片"""
    cards_html = ""
    for i, anime in enumerate(data[:count], 1):
        cards_html += create_detailed_html_card(anime, i)

    title = f"动漫排名 TOP {count} - 详细版"
    html_content = create_html_page(cards_html, title, True)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    html_file = output_path / "ranking_detailed.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_file

def main():
    """主函数"""
    print("🎨 HTML动漫排名卡片生成器")
    print("=" * 50)
    print("📝 生成HTML格式的排名卡片，支持完美的中文显示")
    print("🖼️ 可以直接在浏览器中查看或截图保存")
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
        banner = anime.get('banner_image', '')
        print(f"  {i}. {title_chinese or title}")
        print(f"     综合评分: {score:.3f}")
        print(f"     横幅图片: {'✅' if banner else '❌'}")

    print(f"\n🎯 生成选项:")
    print("1. 生成前5名（简洁版）")
    print("2. 生成前5名（详细版）")
    print("3. 生成前10名（简洁版）")
    print("4. 生成前10名（详细版）")
    print("5. 生成前20名（简洁版）")
    print("6. 生成前20名（详细版）")
    print("7. 自定义数量")
    print("8. 生成所有版本")

    try:
        choice = input("\n请选择 (1-8): ").strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if choice == "1":
            output_file = generate_simple_html_cards(data, 5, f"data/html_cards/simple_top5_{timestamp}")
            print(f"✅ 简洁版前5名完成: {output_file}")
        elif choice == "2":
            output_file = generate_detailed_html_cards(data, 5, f"data/html_cards/detailed_top5_{timestamp}")
            print(f"✅ 详细版前5名完成: {output_file}")
        elif choice == "3":
            output_file = generate_simple_html_cards(data, 10, f"data/html_cards/simple_top10_{timestamp}")
            print(f"✅ 简洁版前10名完成: {output_file}")
        elif choice == "4":
            output_file = generate_detailed_html_cards(data, 10, f"data/html_cards/detailed_top10_{timestamp}")
            print(f"✅ 详细版前10名完成: {output_file}")
        elif choice == "5":
            output_file = generate_simple_html_cards(data, 20, f"data/html_cards/simple_top20_{timestamp}")
            print(f"✅ 简洁版前20名完成: {output_file}")
        elif choice == "6":
            output_file = generate_detailed_html_cards(data, 20, f"data/html_cards/detailed_top20_{timestamp}")
            print(f"✅ 详细版前20名完成: {output_file}")
        elif choice == "7":
            count = int(input(f"请输入要生成的数量 (1-{min(len(data), 50)}): ").strip())
            count = min(count, len(data), 50)
            version = input("选择版本 (s=简洁版, d=详细版): ").strip().lower()

            if version == 's':
                output_file = generate_simple_html_cards(data, count, f"data/html_cards/simple_top{count}_{timestamp}")
                print(f"✅ 简洁版前{count}名完成: {output_file}")
            elif version == 'd':
                output_file = generate_detailed_html_cards(data, count, f"data/html_cards/detailed_top{count}_{timestamp}")
                print(f"✅ 详细版前{count}名完成: {output_file}")
            else:
                print("❌ 无效选择")
                return
        elif choice == "8":
            print(f"\n🎨 生成所有版本...")
            files = []
            files.append(generate_simple_html_cards(data, 5, f"data/html_cards/all_simple_top5_{timestamp}"))
            files.append(generate_detailed_html_cards(data, 5, f"data/html_cards/all_detailed_top5_{timestamp}"))
            files.append(generate_simple_html_cards(data, 10, f"data/html_cards/all_simple_top10_{timestamp}"))
            files.append(generate_detailed_html_cards(data, 10, f"data/html_cards/all_detailed_top10_{timestamp}"))

            print(f"✅ 所有版本生成完成:")
            for file in files:
                print(f"   {file}")
        else:
            print("❌ 无效选择")
            return

        print(f"\n🎉 HTML卡片生成完成！")
        print(f"📁 输出目录: data/html_cards/")
        print(f"🌐 使用方法:")
        print(f"   1. 在浏览器中打开HTML文件查看效果")
        print(f"   2. 使用浏览器的截图功能保存为图片")
        print(f"   3. 可以调整浏览器窗口大小获得最佳效果")

        # 尝试自动打开浏览器
        if 'output_file' in locals():
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
        return

if __name__ == "__main__":
    main()
