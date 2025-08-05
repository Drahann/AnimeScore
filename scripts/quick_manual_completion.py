#!/usr/bin/env python3
"""
快速手动数据补全程序 - 简化版
专门用于补全重要动漫的缺失数据
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_latest_results():
    """加载最新的分析结果"""
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("❌ 结果目录不存在")
        return None
    
    # 找到最新的JSON文件
    json_files = list(results_dir.glob("anime_ranking_*.json"))
    if not json_files:
        print("❌ 没有找到分析结果文件")
        return None
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📂 加载最新结果: {latest_file.name}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f), latest_file

def find_incomplete_anime(data):
    """找到数据不完整的动漫"""
    incomplete = []
    
    for anime in data['rankings']:
        if anime['website_count'] < 3:  # 少于3个网站
            missing_websites = []
            existing_websites = [rating['website'] for rating in anime['ratings']]
            
            all_websites = ['anilist', 'mal', 'bangumi']
            for website in all_websites:
                if website not in existing_websites:
                    missing_websites.append(website)
            
            incomplete.append({
                'anime': anime,
                'missing_websites': missing_websites,
                'existing_websites': existing_websites
            })
    
    # 按重要性排序（排名靠前的优先）
    incomplete.sort(key=lambda x: x['anime']['rank'])
    return incomplete

def display_anime_info(anime):
    """显示动漫信息"""
    print(f"\n{'='*60}")
    print(f"📺 动漫: {anime['title']}")
    if anime.get('title_english'):
        print(f"🌍 英文名: {anime['title_english']}")
    print(f"🏆 当前排名: #{anime['rank']}")
    print(f"⭐ 综合评分: {anime['composite_score']:.3f}")
    print(f"📊 置信度: {anime['confidence']:.3f}")
    print(f"🗳️ 总票数: {anime['total_votes']}")
    
    print(f"\n📊 现有评分数据:")
    for rating in anime['ratings']:
        print(f"   {rating['website']}: {rating['raw_score']} ({rating['vote_count']} 票)")

def get_manual_rating(website):
    """获取用户手动输入的评分"""
    print(f"\n🔍 请为 {website} 网站输入评分数据:")
    print("   (如果没有数据或跳过，直接按回车)")
    
    # 获取评分
    while True:
        score_input = input(f"   评分 (0.0-10.0): ").strip()
        if not score_input:
            return None
        
        try:
            score = float(score_input)
            if 0.0 <= score <= 10.0:
                break
            else:
                print("   ❌ 评分必须在 0.0-10.0 之间")
        except ValueError:
            print("   ❌ 请输入有效的数字")
    
    # 获取投票数
    while True:
        votes_input = input(f"   投票数 (默认100): ").strip()
        if not votes_input:
            votes = 100
            break
        
        try:
            votes = int(votes_input)
            if votes > 0:
                break
            else:
                print("   ❌ 投票数必须大于0")
        except ValueError:
            print("   ❌ 请输入有效的整数")
    
    return {
        'website': website,
        'raw_score': score,
        'vote_count': votes,
        'url': f"https://manual-input/{website}"
    }

def manual_completion_session(incomplete_anime):
    """手动补全会话"""
    print(f"\n🎯 开始手动数据补全，共 {len(incomplete_anime)} 个动漫需要补全")
    
    completed_data = {}
    
    for i, item in enumerate(incomplete_anime, 1):
        anime = item['anime']
        missing_websites = item['missing_websites']
        
        print(f"\n🔢 进度: {i}/{len(incomplete_anime)}")
        display_anime_info(anime)
        
        print(f"\n❌ 缺失网站: {missing_websites}")
        
        # 询问是否要补全这个动漫
        while True:
            choice = input(f"\n❓ 是否要为这个动漫补全数据? (y/n/q): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                break
            elif choice in ['n', 'no', '否']:
                print("   ⏭️ 跳过这个动漫")
                break
            elif choice in ['q', 'quit', '退出']:
                print("   🛑 退出手动补全")
                return completed_data
            else:
                print("   ❌ 请输入 y(是)/n(否)/q(退出)")
        
        if choice in ['n', 'no', '否']:
            continue
        elif choice in ['q', 'quit', '退出']:
            break
        
        # 为每个缺失的网站获取数据
        anime_completed_data = []
        for website in missing_websites:
            rating_data = get_manual_rating(website)
            if rating_data:
                anime_completed_data.append(rating_data)
                print(f"   ✅ 已添加 {website} 数据: {rating_data['raw_score']}")
        
        if anime_completed_data:
            completed_data[anime['title']] = anime_completed_data
            print(f"   🎉 成功为 {anime['title']} 添加了 {len(anime_completed_data)} 条数据")
    
    return completed_data

def merge_manual_data(data, manual_data):
    """合并手动输入的数据到原始数据中"""
    print(f"\n🔄 合并手动输入的数据...")
    
    merged_count = 0
    
    for anime in data['rankings']:
        anime_title = anime['title']
        
        if anime_title in manual_data:
            # 添加手动输入的评分数据
            for rating_data in manual_data[anime_title]:
                # 检查是否已存在该网站的数据
                existing_websites = [r['website'] for r in anime['ratings']]
                
                if rating_data['website'] not in existing_websites:
                    # 添加一些默认字段
                    rating_data.update({
                        'bayesian_score': rating_data['raw_score'],
                        'z_score': 0.0,  # 会重新计算
                        'weight': 5.0,   # 默认权重
                        'site_rank': None,  # 排名信息需要重新计算
                        'site_percentile': None
                    })

                    anime['ratings'].append(rating_data)
                    anime['website_count'] = len(anime['ratings'])
                    anime['total_votes'] = sum(r['vote_count'] for r in anime['ratings'])
                    merged_count += 1
                    print(f"✅ 为 {anime_title} 添加 {rating_data['website']} 手动数据")
    
    print(f"🎉 成功合并 {merged_count} 条手动数据")

    # 如果有新数据合并，需要重新计算网站排名
    if merged_count > 0:
        print(f"🔄 重新计算网站排名...")
        recalculate_site_rankings(data)
        print(f"✅ 网站排名重新计算完成")

    return data

def recalculate_site_rankings(data):
    """重新计算网站排名"""
    from collections import defaultdict

    # 按网站分组收集评分数据
    website_anime_scores = defaultdict(list)

    for anime in data['rankings']:
        for rating in anime.get('ratings', []):
            if rating.get('raw_score') is not None:
                website_anime_scores[rating['website']].append({
                    'anime': anime,
                    'rating': rating,
                    'score': rating['raw_score']
                })

    # 为每个网站计算排名
    for website, anime_ratings in website_anime_scores.items():
        if len(anime_ratings) < 2:  # 至少需要2个动漫才能排名
            continue

        # 按评分降序排序
        sorted_ratings = sorted(anime_ratings, key=lambda x: x['score'], reverse=True)
        total_count = len(sorted_ratings)

        # 分配排名
        for i, item in enumerate(sorted_ratings, 1):
            rank = i
            percentile = (total_count - rank + 1) / total_count * 100

            # 更新评分数据中的排名信息
            item['rating']['site_rank'] = rank
            item['rating']['site_percentile'] = percentile

def save_updated_results(data, original_file):
    """保存更新后的结果"""
    # 创建新文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_path = Path(original_file)
    new_name = original_path.stem + f"_manual_completed_{timestamp}" + original_path.suffix
    new_path = original_path.parent / new_name
    
    # 更新分析日期
    data['analysis_info']['analysis_date'] = datetime.now().isoformat()
    data['analysis_info']['manual_completion'] = True
    data['analysis_info']['manual_completion_date'] = datetime.now().isoformat()
    
    # 保存JSON
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存到: {new_path}")
    
    # 也保存CSV版本
    csv_path = new_path.with_suffix('.csv')
    save_csv_results(data, csv_path)
    print(f"💾 CSV结果已保存到: {csv_path}")

def save_csv_results(data, csv_path):
    """保存CSV格式结果（包含网站排名信息）"""
    import csv

    # 获取所有启用的网站
    enabled_websites = set()
    for anime in data['rankings']:
        for rating in anime.get('ratings', []):
            enabled_websites.add(rating['website'])

    enabled_websites = sorted(list(enabled_websites))

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 构建表头（包含网站排名信息）
        headers = [
            'Rank', 'Title', 'Title_English', 'Composite_Score', 'Confidence',
            'Total_Votes', 'Website_Count', 'Percentile', 'Type', 'Episodes',
            'Start_Date', 'Studios', 'Genres'
        ]

        # 添加各网站的评分、投票数和排名列
        for website in enabled_websites:
            headers.extend([
                f"{website.upper()}_Score",
                f"{website.upper()}_Votes",
                f"{website.upper()}_Rank"
            ])

        writer.writerow(headers)

        # 写入数据行
        for anime in data['rankings']:
            row = [
                anime['rank'],
                anime['title'],
                anime.get('title_english', ''),
                anime['composite_score'],
                anime['confidence'],
                anime['total_votes'],
                anime['website_count'],
                anime['percentile'],
                anime.get('anime_type', ''),
                anime.get('episodes', ''),
                anime.get('start_date', ''),
                ', '.join(anime.get('studios', [])),
                ', '.join(anime.get('genres', []))
            ]

            # 创建网站评分字典
            website_ratings = {}
            for rating in anime.get('ratings', []):
                website_ratings[rating['website']] = {
                    'score': rating.get('raw_score'),
                    'votes': rating.get('vote_count', 0),
                    'rank': rating.get('site_rank', '')
                }

            # 添加各网站的评分、投票数和排名
            for website in enabled_websites:
                if website in website_ratings:
                    row.extend([
                        website_ratings[website]['score'],
                        website_ratings[website]['votes'],
                        website_ratings[website]['rank']
                    ])
                else:
                    row.extend(["", "", ""])

            writer.writerow(row)

def main():
    """主函数"""
    print("🚀 启动快速手动数据补全程序")
    
    # 1. 加载最新结果
    result = load_latest_results()
    if not result:
        return
    
    data, original_file = result
    
    # 2. 找到不完整的动漫
    incomplete_anime = find_incomplete_anime(data)
    
    if not incomplete_anime:
        print("🎉 所有动漫数据都是完整的，无需手动补全！")
        return
    
    print(f"\n📊 发现 {len(incomplete_anime)} 个动漫需要手动补全数据")
    
    # 显示概览
    print(f"\n📋 数据不完整的动漫概览 (按排名排序):")
    for i, item in enumerate(incomplete_anime[:10], 1):
        anime = item['anime']
        missing = len(item['missing_websites'])
        print(f"   {i}. #{anime['rank']} {anime['title']} (缺失 {missing} 个网站)")
    
    if len(incomplete_anime) > 10:
        print(f"   ... 还有 {len(incomplete_anime) - 10} 个动漫")
    
    # 3. 手动补全会话
    manual_data = manual_completion_session(incomplete_anime)
    
    if not manual_data:
        print("ℹ️ 没有手动输入任何数据，程序结束")
        return
    
    # 4. 合并手动数据
    updated_data = merge_manual_data(data, manual_data)
    
    # 5. 保存结果
    save_updated_results(updated_data, original_file)
    
    # 6. 显示最终统计
    website_counts = {}
    for anime in updated_data['rankings']:
        count = anime['website_count']
        website_counts[count] = website_counts.get(count, 0) + 1
    
    print(f"\n📊 手动补全后的数据完整性统计:")
    total_anime = len(updated_data['rankings'])
    for count in sorted(website_counts.keys()):
        percentage = website_counts[count] / total_anime * 100
        print(f"   {count}个网站: {website_counts[count]}部动漫 ({percentage:.1f}%)")
    
    print("\n🎉 手动数据补全完成！")

if __name__ == "__main__":
    main()
