#!/usr/bin/env python3
"""
生成人工查找清单
根据缺失数据分析结果，生成便于人工查找的动漫清单
按优先级排序，提供搜索关键词和网站链接
"""

import json
import csv
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set
from urllib.parse import quote

def generate_search_keywords(anime: Dict[str, Any]) -> List[str]:
    """生成搜索关键词"""
    keywords = []
    
    # 主标题
    if anime['title']:
        keywords.append(anime['title'])
    
    # 英文标题
    if anime['title_english'] and anime['title_english'] != anime['title']:
        keywords.append(anime['title_english'])
    
    # 简化标题（去除特殊字符）
    title_simple = anime['title'].replace(':', '').replace('-', ' ').replace('  ', ' ').strip()
    if title_simple != anime['title']:
        keywords.append(title_simple)
    
    # 英文标题简化
    if anime['title_english']:
        english_simple = anime['title_english'].replace(':', '').replace('-', ' ').replace('  ', ' ').strip()
        if english_simple != anime['title_english'] and english_simple not in keywords:
            keywords.append(english_simple)
    
    return keywords

def load_enabled_websites(config_path: str = "config/config.yaml") -> Set[str]:
    """从配置文件加载启用的网站列表"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        enabled_websites = set()
        websites_config = config.get('websites', {})

        for website_name, website_config in websites_config.items():
            if website_config.get('enabled', False):
                enabled_websites.add(website_name)

        return enabled_websites
    except Exception as e:
        print(f"⚠️  无法加载配置文件 {config_path}: {e}")
        print("使用默认的网站列表: anilist, bangumi, filmarks, mal")
        return {'anilist', 'bangumi', 'filmarks', 'mal'}

def generate_search_urls(keywords: List[str], missing_websites: List[str]) -> Dict[str, str]:
    """生成搜索URL"""
    urls = {}

    primary_keyword = keywords[0] if keywords else ""
    encoded_keyword = quote(primary_keyword)

    for website in missing_websites:
        if website == 'imdb':
            urls['imdb'] = f"https://www.imdb.com/find/?q={encoded_keyword}&s=tt&ttype=tv"
        elif website == 'douban':
            urls['douban'] = f"https://search.douban.com/movie/subject_search?search_text={encoded_keyword}"
        elif website == 'anilist':
            urls['anilist'] = f"https://anilist.co/search/anime?search={encoded_keyword}"
        elif website == 'bangumi':
            urls['bangumi'] = f"https://bgm.tv/subject_search/{encoded_keyword}?cat=2"
        elif website == 'filmarks':
            urls['filmarks'] = f"https://filmarks.com/search/animes?q={encoded_keyword}"
        elif website == 'mal':
            urls['mal'] = f"https://myanimelist.net/anime.php?q={encoded_keyword}"

    return urls

def calculate_priority(anime: Dict[str, Any]) -> float:
    """计算查找优先级"""
    # 基础分数：排名越高优先级越高
    rank_score = (100 - anime['rank']) / 100 * 50
    
    # 投票数分数：投票越多优先级越高
    vote_score = min(anime['total_votes'] / 100000 * 30, 30)
    
    # 置信度分数：置信度越高优先级越高
    confidence_score = anime['confidence'] * 20
    
    # 缺失网站数惩罚：缺失越多优先级越低
    missing_penalty = anime['missing_count'] * 5
    
    return rank_score + vote_score + confidence_score - missing_penalty

def generate_search_list(missing_data_file: str, output_prefix: str = None):
    """生成人工查找清单"""

    # 加载启用的网站列表
    enabled_websites = load_enabled_websites()
    print(f"📋 启用的网站: {', '.join(sorted(enabled_websites))}")

    # 加载缺失数据
    with open(missing_data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing_anime = data['missing_anime']
    
    # 计算优先级并排序
    for anime in missing_anime:
        anime['priority'] = calculate_priority(anime)
        anime['search_keywords'] = generate_search_keywords(anime)
        missing_websites = anime['missing_websites'].split(', ')
        anime['search_urls'] = generate_search_urls(anime['search_keywords'], missing_websites)
    
    # 按优先级排序
    missing_anime.sort(key=lambda x: x['priority'], reverse=True)
    
    # 生成输出文件名
    if not output_prefix:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_prefix = f"search_list_{timestamp}"

    # 创建searchlist目录
    searchlist_dir = Path("data/searchlist")
    searchlist_dir.mkdir(parents=True, exist_ok=True)

    # 生成CSV清单
    csv_path = searchlist_dir / f"{output_prefix}.csv"
    generate_csv_search_list(missing_anime, str(csv_path), enabled_websites)

    # 生成JSON清单
    json_path = searchlist_dir / f"{output_prefix}.json"
    generate_json_search_list(missing_anime, data['analysis_info'], str(json_path))

    # 生成按网站分组的清单
    website_csv_path = searchlist_dir / f"{output_prefix}_by_website.csv"
    generate_website_grouped_list(missing_anime, str(website_csv_path), enabled_websites)
    
    print(f"\n🎉 查找清单生成完成!")
    print(f"📋 主要清单: {csv_path}")
    print(f"📋 详细数据: {json_path}")
    print(f"📋 按网站分组: {website_csv_path}")
    
    # 打印统计信息
    print_search_statistics(missing_anime)

def generate_csv_search_list(missing_anime: List[Dict], output_path: str, enabled_websites: Set[str]):
    """生成CSV格式的查找清单"""
    base_fieldnames = [
        'priority', 'rank', 'title', 'title_english', 'anime_type', 'start_date',
        'missing_websites', 'missing_count', 'composite_score', 'total_votes', 'confidence',
        'search_keyword_1', 'search_keyword_2', 'search_keyword_3'
    ]

    # 为每个启用的网站添加搜索URL字段
    search_url_fieldnames = []
    for website in sorted(enabled_websites):
        search_url_fieldnames.append(f'{website}_search_url')

    end_fieldnames = ['current_websites', 'studios', 'genres']
    fieldnames = base_fieldnames + search_url_fieldnames + end_fieldnames
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for anime in missing_anime:
            row = {
                'priority': f"{anime['priority']:.1f}",
                'rank': anime['rank'],
                'title': anime['title'],
                'title_english': anime['title_english'],
                'anime_type': anime['anime_type'],
                'start_date': anime['start_date'],
                'missing_websites': anime['missing_websites'],
                'missing_count': anime['missing_count'],
                'composite_score': f"{anime['composite_score']:.3f}",
                'total_votes': anime['total_votes'],
                'confidence': f"{anime['confidence']:.3f}",
                'current_websites': anime['current_websites'],
                'studios': anime['studios'],
                'genres': anime['genres']
            }
            
            # 添加搜索关键词
            keywords = anime['search_keywords']
            for i in range(3):
                key = f'search_keyword_{i+1}'
                row[key] = keywords[i] if i < len(keywords) else ''
            
            # 添加搜索URL（只包含启用的网站）
            search_urls = anime['search_urls']
            for website in sorted(enabled_websites):
                row[f'{website}_search_url'] = search_urls.get(website, '')
            
            writer.writerow(row)

def generate_json_search_list(missing_anime: List[Dict], analysis_info: Dict, output_path: str):
    """生成JSON格式的查找清单"""
    output_data = {
        'analysis_info': analysis_info,
        'generation_date': datetime.now().isoformat(),
        'total_missing_anime': len(missing_anime),
        'search_list': missing_anime
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

def generate_website_grouped_list(missing_anime: List[Dict], output_path: str, enabled_websites: Set[str]):
    """生成按网站分组的查找清单"""
    # 按缺失网站分组
    website_groups = {}
    for anime in missing_anime:
        missing_websites = anime['missing_websites']
        if missing_websites not in website_groups:
            website_groups[missing_websites] = []
        website_groups[missing_websites].append(anime)
    
    fieldnames = [
        'missing_websites', 'priority', 'rank', 'title', 'title_english', 
        'search_keyword_1', 'search_keyword_2', 'composite_score', 'total_votes'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # 按缺失网站数量排序
        sorted_groups = sorted(website_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        for missing_websites, anime_list in sorted_groups:
            for anime in anime_list:
                keywords = anime['search_keywords']
                row = {
                    'missing_websites': missing_websites,
                    'priority': f"{anime['priority']:.1f}",
                    'rank': anime['rank'],
                    'title': anime['title'],
                    'title_english': anime['title_english'],
                    'search_keyword_1': keywords[0] if len(keywords) > 0 else '',
                    'search_keyword_2': keywords[1] if len(keywords) > 1 else '',
                    'composite_score': f"{anime['composite_score']:.3f}",
                    'total_votes': anime['total_votes']
                }
                writer.writerow(row)

def print_search_statistics(missing_anime: List[Dict]):
    """打印查找统计信息"""
    print(f"\n📊 查找清单统计")
    print("=" * 50)
    
    # 按缺失网站分组统计
    website_stats = {}
    for anime in missing_anime:
        missing_websites = anime['missing_websites']
        if missing_websites not in website_stats:
            website_stats[missing_websites] = 0
        website_stats[missing_websites] += 1
    
    print("🔍 按缺失网站分组:")
    for missing_websites, count in sorted(website_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  缺失 {missing_websites:30}: {count:3d} 个动漫")
    
    # 高优先级动漫
    high_priority = [a for a in missing_anime if a['priority'] >= 70]
    print(f"\n⭐ 高优先级动漫 (优先级 >= 70): {len(high_priority)} 个")
    for anime in high_priority[:5]:
        print(f"  #{anime['rank']:2d} {anime['title']:40} (优先级: {anime['priority']:.1f})")

def main():
    parser = argparse.ArgumentParser(description='生成人工查找清单')
    parser.add_argument('missing_data_file', help='缺失数据JSON文件路径')
    parser.add_argument('-o', '--output', help='输出文件前缀')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.missing_data_file).exists():
        print(f"❌ 输入文件不存在: {args.missing_data_file}")
        return
    
    print(f"📂 加载缺失数据: {args.missing_data_file}")
    
    try:
        generate_search_list(args.missing_data_file, args.output)
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
