#!/usr/bin/env python3
"""
分析动漫评分结果，找出缺失网站数据的动漫
输出缺失数据的动漫列表，方便人工查找和添加
"""

import json
import csv
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any
from collections import defaultdict

def load_analysis_result(file_path: str) -> Dict[str, Any]:
    """加载分析结果文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.json'):
            return json.load(f)
        else:
            raise ValueError("目前只支持JSON格式的结果文件")

def load_enabled_websites(config_path: str = "config/config.yaml") -> Set[str]:
    """从配置文件加载启用的网站列表（排除数据补全排除列表中的网站）"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        enabled_websites = set()
        websites_config = config.get('websites', {})

        # 获取数据补全排除列表
        data_completion_config = config.get('data_completion', {})
        excluded_websites = set(data_completion_config.get('excluded_websites', []))

        for website_name, website_config in websites_config.items():
            if website_config.get('enabled', False) and website_name not in excluded_websites:
                enabled_websites.add(website_name)

        print(f"📊 数据分析启用的网站: {sorted(enabled_websites)}")
        if excluded_websites:
            print(f"📊 数据分析排除的网站: {sorted(excluded_websites)}")

        return enabled_websites
    except Exception as e:
        print(f"⚠️  无法加载配置文件 {config_path}: {e}")
        print("使用默认的网站列表: anilist, bangumi, filmarks, mal")
        return {'anilist', 'bangumi', 'filmarks', 'mal'}

def analyze_missing_data(data: Dict[str, Any], enabled_websites: Set[str] = None) -> Dict[str, Any]:
    """分析缺失的网站数据"""

    # 如果没有提供启用的网站列表，从配置文件加载
    if enabled_websites is None:
        enabled_websites = load_enabled_websites()

    print(f"📋 启用的网站: {', '.join(sorted(enabled_websites))}")

    # 只分析启用的网站
    all_websites = enabled_websites
    
    # 统计信息
    stats = {
        'total_anime': len(data['rankings']),
        'website_coverage': defaultdict(int),
        'missing_patterns': defaultdict(int),
        'missing_anime': []
    }
    
    for anime in data['rankings']:
        # 获取当前动漫有数据的网站
        current_websites = set()
        for rating in anime.get('ratings', []):
            current_websites.add(rating['website'])
        
        # 统计网站覆盖率
        for website in all_websites:
            if website in current_websites:
                stats['website_coverage'][website] += 1
        
        # 找出缺失的网站
        missing_websites = all_websites - current_websites
        
        if missing_websites:
            # 统计缺失模式
            missing_pattern = ','.join(sorted(missing_websites))
            stats['missing_patterns'][missing_pattern] += 1
            
            # 记录缺失数据的动漫
            anime_info = {
                'rank': anime['rank'],
                'title': anime['title'],
                'title_english': anime.get('title_english', ''),
                'anime_type': anime.get('anime_type', ''),
                'episodes': anime.get('episodes', ''),
                'start_date': anime.get('start_date', ''),
                'studios': ', '.join(anime.get('studios', [])),
                'genres': ', '.join(anime.get('genres', [])),
                'composite_score': anime.get('composite_score', 0),
                'total_votes': anime.get('total_votes', 0),
                'website_count': anime.get('website_count', 0),
                'current_websites': ', '.join(sorted(current_websites)),
                'missing_websites': ', '.join(sorted(missing_websites)),
                'missing_count': len(missing_websites),
                'confidence': anime.get('confidence', 0),
                'percentile': anime.get('percentile', 0)
            }
            
            # 添加各启用网站的具体信息
            for website in sorted(all_websites):
                anime_info[f'{website}_score'] = ''
                anime_info[f'{website}_votes'] = ''
                anime_info[f'{website}_url'] = ''
            
            # 填入已有的网站数据
            for rating in anime.get('ratings', []):
                website = rating['website']
                anime_info[f'{website}_score'] = rating.get('raw_score', '')
                anime_info[f'{website}_votes'] = rating.get('vote_count', '')
                anime_info[f'{website}_url'] = rating.get('url', '')
            
            stats['missing_anime'].append(anime_info)
    
    return stats

def save_missing_data_csv(missing_anime: List[Dict], output_path: str, enabled_websites: Set[str]):
    """保存缺失数据到CSV文件"""
    if not missing_anime:
        print("没有缺失数据的动漫")
        return

    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 动态生成字段名，只包含启用的网站
    base_fieldnames = [
        'rank', 'title', 'title_english', 'anime_type', 'episodes', 'start_date',
        'studios', 'genres', 'composite_score', 'total_votes', 'website_count',
        'current_websites', 'missing_websites', 'missing_count', 'confidence', 'percentile'
    ]

    # 为每个启用的网站添加字段
    website_fieldnames = []
    for website in sorted(enabled_websites):
        website_fieldnames.extend([
            f'{website}_score', f'{website}_votes', f'{website}_url'
        ])

    fieldnames = base_fieldnames + website_fieldnames

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(missing_anime)

    print(f"✅ CSV文件已保存: {output_path}")

def save_missing_data_json(stats: Dict, output_path: str, enabled_websites: Set[str]):
    """保存缺失数据到JSON文件"""
    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        'analysis_info': {
            'analysis_date': datetime.now().isoformat(),
            'total_anime': stats['total_anime'],
            'missing_anime_count': len(stats['missing_anime']),
            'enabled_websites': sorted(enabled_websites)
        },
        'website_coverage': dict(stats['website_coverage']),
        'missing_patterns': dict(stats['missing_patterns']),
        'missing_anime': stats['missing_anime']
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON文件已保存: {output_path}")

def print_summary(stats: Dict):
    """打印统计摘要"""
    print("\n📊 缺失数据分析摘要")
    print("=" * 60)
    
    print(f"总动漫数量: {stats['total_anime']}")
    print(f"有缺失数据的动漫: {len(stats['missing_anime'])}")
    print(f"缺失数据比例: {len(stats['missing_anime'])/stats['total_anime']*100:.1f}%")
    
    print(f"\n🌐 网站覆盖率:")
    for website, count in sorted(stats['website_coverage'].items()):
        coverage = count / stats['total_anime'] * 100
        print(f"  {website:10}: {count:3d}/{stats['total_anime']} ({coverage:5.1f}%)")
    
    print(f"\n❌ 缺失模式 (前10个):")
    sorted_patterns = sorted(stats['missing_patterns'].items(), key=lambda x: x[1], reverse=True)
    for pattern, count in sorted_patterns[:10]:
        print(f"  缺失 {pattern:30}: {count:3d} 个动漫")
    
    print(f"\n🔍 缺失最多数据的动漫 (前10个):")
    sorted_missing = sorted(stats['missing_anime'], key=lambda x: x['missing_count'], reverse=True)
    for anime in sorted_missing[:10]:
        print(f"  {anime['title']:40} | 缺失 {anime['missing_count']} 个网站 | 排名 #{anime['rank']}")

def main():
    parser = argparse.ArgumentParser(description='分析动漫评分结果中的缺失数据')
    parser.add_argument('input_file', help='输入的结果文件路径 (JSON格式)')
    parser.add_argument('-o', '--output', help='输出文件前缀 (默认: missing_data)')
    parser.add_argument('--csv-only', action='store_true', help='只输出CSV格式')
    parser.add_argument('--json-only', action='store_true', help='只输出JSON格式')
    
    args = parser.parse_args()
    
    # 检查输入文件
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_path}")
        return
    
    print(f"📂 加载分析结果: {input_path}")
    
    try:
        # 加载启用的网站列表
        enabled_websites = load_enabled_websites()

        # 加载数据
        data = load_analysis_result(str(input_path))

        # 分析缺失数据
        print("🔍 分析缺失数据...")
        stats = analyze_missing_data(data, enabled_websites)
        
        # 打印摘要
        print_summary(stats)
        
        # 生成输出文件名和路径
        if args.output:
            output_prefix = args.output
        else:
            # 从输入文件名生成输出前缀
            season_info = data.get('analysis_info', {})
            season = season_info.get('season', 'Unknown')
            year = season_info.get('year', 'Unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_prefix = f"missing_data_{season}_{year}_{timestamp}"

        # 创建searchlist目录
        searchlist_dir = Path("data/searchlist")
        searchlist_dir.mkdir(parents=True, exist_ok=True)

        # 保存结果到searchlist目录
        if not args.json_only:
            csv_path = searchlist_dir / f"{output_prefix}.csv"
            save_missing_data_csv(stats['missing_anime'], str(csv_path), enabled_websites)

        if not args.csv_only:
            json_path = searchlist_dir / f"{output_prefix}.json"
            save_missing_data_json(stats, str(json_path), enabled_websites)
        
        print(f"\n🎉 分析完成! 找到 {len(stats['missing_anime'])} 个有缺失数据的动漫")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
