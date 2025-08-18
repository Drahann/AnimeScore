#!/usr/bin/env python3
"""
手动删除动漫程序
允许用户按排名序号删除特定动漫，然后重新计算排名
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import Config

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

def display_anime_list(data, start_rank=1, end_rank=20):
    """显示动漫列表"""
    print(f"\n📋 当前排名 (#{start_rank}-#{end_rank}):")
    print("=" * 80)
    
    for anime in data['rankings']:
        rank = anime['rank']
        if start_rank <= rank <= end_rank:
            title = anime['title']
            title_en = anime.get('title_english', '')
            score = anime['composite_score']
            confidence = anime['confidence']
            votes = anime['total_votes']
            websites = anime['website_count']
            
            title_cn = anime.get('title_chinese', '')
            title_jp = anime.get('title_japanese', '')

            print(f"{rank:2d}. {title}")
            if title_cn and title_cn != title:
                print(f"    🇨🇳 {title_cn}")
            if title_en and title_en != title:
                print(f"    🌍 {title_en}")
            if title_jp and title_jp != title and title_jp != title_en:
                print(f"    🇯🇵 {title_jp}")
            print(f"    ⭐ 评分: {score:.3f} | 📊 置信度: {confidence:.3f} | 🗳️ 票数: {votes} | 🌐 网站: {websites}")
            print()

def display_anime_detail(anime):
    """显示动漫详细信息"""
    print(f"\n{'='*60}")
    print(f"📺 动漫: {anime['title']}")
    if anime.get('title_chinese'):
        print(f"🇨🇳 中文名: {anime['title_chinese']}")
    if anime.get('title_english'):
        print(f"🌍 英文名: {anime['title_english']}")
    if anime.get('title_japanese'):
        print(f"🇯🇵 日文名: {anime['title_japanese']}")
    print(f"🏆 当前排名: #{anime['rank']}")
    print(f"⭐ 综合评分: {anime['composite_score']:.3f}")
    print(f"📊 置信度: {anime['confidence']:.3f}")
    print(f"🗳️ 总票数: {anime['total_votes']}")
    print(f"🌐 网站数: {anime['website_count']}")
    
    if anime.get('anime_type'):
        print(f"📋 类型: {anime['anime_type']}")
    if anime.get('episodes'):
        print(f"📺 集数: {anime['episodes']}")
    if anime.get('start_date'):
        print(f"📅 开播: {anime['start_date']}")
    if anime.get('studios'):
        print(f"🏢 制作: {', '.join(anime['studios'][:3])}")
    if anime.get('genres'):
        print(f"🏷️ 类型: {', '.join(anime['genres'][:5])}")
    
    print(f"\n📊 评分数据:")
    for rating in anime['ratings']:
        print(f"   {rating['website']}: {rating['raw_score']} ({rating['vote_count']} 票)")

def get_anime_to_remove(data):
    """获取要删除的动漫"""
    total_anime = len(data['rankings'])
    
    while True:
        print(f"\n🎯 请选择操作:")
        print("1. 查看排名列表")
        print("2. 删除指定动漫")
        print("3. 查看动漫详情")
        print("4. 退出程序")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            # 查看排名列表
            while True:
                try:
                    start_input = input(f"\n起始排名 (1-{total_anime}, 默认1): ").strip()
                    start_rank = int(start_input) if start_input else 1
                    
                    end_input = input(f"结束排名 (默认{min(start_rank + 19, total_anime)}): ").strip()
                    end_rank = int(end_input) if end_input else min(start_rank + 19, total_anime)
                    
                    if 1 <= start_rank <= end_rank <= total_anime:
                        display_anime_list(data, start_rank, end_rank)
                        break
                    else:
                        print(f"❌ 请输入有效的排名范围 (1-{total_anime})")
                except ValueError:
                    print("❌ 请输入有效的数字")
        
        elif choice == '2':
            # 删除指定动漫
            return get_removal_list(data)
        
        elif choice == '3':
            # 查看动漫详情
            try:
                rank_input = input(f"\n请输入要查看的动漫排名 (1-{total_anime}): ").strip()
                rank = int(rank_input)
                
                if 1 <= rank <= total_anime:
                    anime = next(a for a in data['rankings'] if a['rank'] == rank)
                    display_anime_detail(anime)
                else:
                    print(f"❌ 请输入有效的排名 (1-{total_anime})")
            except ValueError:
                print("❌ 请输入有效的数字")
            except StopIteration:
                print("❌ 找不到指定排名的动漫")
        
        elif choice == '4':
            print("👋 退出程序")
            return []
        
        else:
            print("❌ 请输入有效的选项 (1-4)")

def get_removal_list(data):
    """获取要删除的动漫列表"""
    total_anime = len(data['rankings'])
    removal_list = []
    
    print(f"\n🗑️ 删除动漫模式")
    print("提示: 可以输入单个排名或用逗号分隔的多个排名")
    print("例如: 5 或 3,7,12 或 1-5,10,15-20")
    
    while True:
        ranks_input = input(f"\n请输入要删除的动漫排名 (1-{total_anime}, 或 'q' 退出): ").strip()
        
        if ranks_input.lower() == 'q':
            break
        
        try:
            ranks = parse_rank_input(ranks_input, total_anime)
            if not ranks:
                continue
            
            # 显示要删除的动漫
            print(f"\n📋 将要删除的动漫:")
            for rank in sorted(ranks):
                anime = next(a for a in data['rankings'] if a['rank'] == rank)
                title_display = anime['title']
                if anime.get('title_chinese'):
                    title_display += f" ({anime['title_chinese']})"
                print(f"   #{rank}: {title_display}")
            
            # 确认删除
            confirm = input(f"\n❓ 确认删除这 {len(ranks)} 个动漫? (y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                removal_list.extend(ranks)
                print(f"✅ 已标记删除 {len(ranks)} 个动漫")
            else:
                print("❌ 取消删除")
            
            # 询问是否继续
            continue_choice = input("\n❓ 是否继续删除其他动漫? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', '是']:
                break
                
        except ValueError as e:
            print(f"❌ 输入格式错误: {e}")
    
    return list(set(removal_list))  # 去重

def parse_rank_input(ranks_input, total_anime):
    """解析排名输入"""
    ranks = []
    
    # 分割逗号
    parts = ranks_input.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # 处理范围 (如 1-5)
            try:
                start, end = part.split('-')
                start_rank = int(start.strip())
                end_rank = int(end.strip())
                
                if start_rank > end_rank:
                    start_rank, end_rank = end_rank, start_rank
                
                if 1 <= start_rank <= total_anime and 1 <= end_rank <= total_anime:
                    ranks.extend(range(start_rank, end_rank + 1))
                else:
                    print(f"❌ 范围 {part} 超出有效排名 (1-{total_anime})")
                    return []
            except ValueError:
                print(f"❌ 无效的范围格式: {part}")
                return []
        else:
            # 处理单个排名
            try:
                rank = int(part)
                if 1 <= rank <= total_anime:
                    ranks.append(rank)
                else:
                    print(f"❌ 排名 {rank} 超出有效范围 (1-{total_anime})")
                    return []
            except ValueError:
                print(f"❌ 无效的排名: {part}")
                return []
    
    return ranks

def remove_anime(data, removal_ranks):
    """删除指定排名的动漫"""
    if not removal_ranks:
        return data
    
    print(f"\n🗑️ 删除 {len(removal_ranks)} 个动漫...")
    
    # 获取要删除的动漫标题（用于日志）
    removed_titles = []
    for rank in removal_ranks:
        anime = next(a for a in data['rankings'] if a['rank'] == rank)
        title_display = anime['title']
        if anime.get('title_chinese'):
            title_display += f" ({anime['title_chinese']})"
        removed_titles.append(f"#{rank}: {title_display}")
    
    # 删除动漫
    data['rankings'] = [anime for anime in data['rankings'] if anime['rank'] not in removal_ranks]
    
    # 重新分配排名
    for i, anime in enumerate(data['rankings'], 1):
        anime['rank'] = i
        # 重新计算百分位
        anime['percentile'] = (len(data['rankings']) - i + 1) / len(data['rankings']) * 100

    # 重新计算网站排名
    print(f"🔄 重新计算网站排名...")
    recalculate_site_rankings(data)

    # 更新分析信息
    data['analysis_info']['analyzed_anime_count'] = len(data['rankings'])
    
    print(f"✅ 成功删除以下动漫:")
    for title in removed_titles:
        print(f"   {title}")
    
    print(f"📊 剩余动漫数量: {len(data['rankings'])}")
    
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

    print(f"✅ 网站排名重新计算完成")

def save_updated_results(data, original_file, removal_count):
    """保存更新后的结果到 final_results 目录"""
    # 加载配置获取 final_results 目录
    try:
        config_path = project_root / "config" / "config.yaml"
        config = Config.load_from_file(str(config_path))
        final_results_dir = Path(config.storage.final_results_dir)
    except Exception as e:
        print(f"⚠️ 无法加载配置，使用默认目录: {e}")
        final_results_dir = Path("data/results/final_results")

    # 确保目录存在
    final_results_dir.mkdir(parents=True, exist_ok=True)

    # 创建新文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_path = Path(original_file)
    new_name = original_path.stem + f"_removed_{removal_count}_anime_{timestamp}" + original_path.suffix
    new_path = final_results_dir / new_name
    
    # 更新分析日期和删除信息
    data['analysis_info']['analysis_date'] = datetime.now().isoformat()
    data['analysis_info']['manual_removal'] = True
    data['analysis_info']['removal_date'] = datetime.now().isoformat()
    data['analysis_info']['removed_anime_count'] = removal_count
    
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
            'Rank', 'Title', 'Title_Chinese', 'Title_English', 'Title_Japanese',
            'Composite_Score', 'Confidence', 'Total_Votes', 'Website_Count',
            'Percentile', 'Type', 'Episodes', 'Start_Date', 'Studios', 'Genres'
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
                anime.get('title_chinese', ''),
                anime.get('title_english', ''),
                anime.get('title_japanese', ''),
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
    print("🚀 启动手动动漫删除程序")
    print("📝 此程序允许您删除指定排名的动漫并重新计算排名")
    
    # 1. 加载最新结果
    result = load_latest_results()
    if not result:
        return
    
    data, original_file = result
    original_count = len(data['rankings'])
    
    print(f"📊 当前共有 {original_count} 个动漫")
    
    # 2. 获取要删除的动漫
    removal_ranks = get_anime_to_remove(data)
    
    if not removal_ranks:
        print("ℹ️ 没有选择删除任何动漫，程序结束")
        return
    
    # 3. 删除动漫并重新排名
    updated_data = remove_anime(data, removal_ranks)
    
    # 4. 保存结果
    removal_count = len(removal_ranks)
    save_updated_results(updated_data, original_file, removal_count)
    
    # 5. 显示最终统计
    final_count = len(updated_data['rankings'])
    print(f"\n📊 删除操作完成:")
    print(f"   原始动漫数量: {original_count}")
    print(f"   删除动漫数量: {removal_count}")
    print(f"   剩余动漫数量: {final_count}")
    print(f"   删除比例: {removal_count / original_count * 100:.1f}%")
    
    # 显示新的前10名
    print(f"\n🏆 删除后的新排名 (前10名):")
    display_anime_list(updated_data, 1, 10)
    
    print("\n🎉 动漫删除和重新排名完成！")

if __name__ == "__main__":
    main()
