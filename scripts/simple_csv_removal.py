#!/usr/bin/env python3
"""
简化CSV手动删除程序
允许用户按排名序号删除特定动漫，然后重新计算排名
专门针对简化CSV格式（*_simple.csv）
"""
import csv
import sys
from pathlib import Path
from datetime import datetime
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_latest_simple_csv():
    """加载最新的简化CSV结果"""
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("❌ 结果目录不存在")
        return None
    
    # 找到最新的简化CSV文件
    csv_files = list(results_dir.glob("*_simple.csv"))
    if not csv_files:
        print("❌ 没有找到简化CSV结果文件")
        return None
    
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"📂 加载最新简化CSV: {latest_file.name}")
    
    # 读取CSV数据
    data = []
    with open(latest_file, 'r', encoding='utf-8-sig') as f:  # 使用utf-8-sig处理BOM
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames)

        # 清理列名中的BOM字符
        clean_headers = []
        for header in headers:
            clean_header = header.strip('\ufeff')  # 移除BOM字符
            clean_headers.append(clean_header)

        print(f"📋 检测到的列名: {clean_headers}")

        for row in reader:
            # 创建清理后的行数据
            clean_row = {}
            for old_header, new_header in zip(headers, clean_headers):
                clean_row[new_header] = row[old_header]

            # 转换排名为整数
            if '排名' in clean_row:
                clean_row['排名'] = int(clean_row['排名'])
            else:
                print(f"❌ 未找到'排名'列")
                return None

            data.append(clean_row)

        # 使用清理后的列名
        headers = clean_headers
    
    return data, headers, latest_file

def display_anime_list_simple(data, start_rank=1, end_rank=20):
    """显示简化动漫列表"""
    print(f"\n📋 当前排名 (#{start_rank}-#{end_rank}):")
    print("=" * 100)
    
    for anime in data:
        rank = anime['排名']
        if start_rank <= rank <= end_rank:
            title = anime.get('日文名', '') or anime.get('英文名', '') or '未知标题'
            title_cn = anime.get('中文名', '')
            title_en = anime.get('英文名', '')
            score = float(anime['综合评分'])
            
            # 计算网站数量
            website_count = 0
            for website in ['ANILIST', 'BANGUMI', 'FILMARKS', 'IMDB', 'MAL']:
                if anime.get(f'{website}_评分') and anime.get(f'{website}_评分').strip():
                    website_count += 1
            
            print(f"{rank:2d}. {title}")
            if title_cn and title_cn != title:
                print(f"    🇨🇳 {title_cn}")
            if title_en and title_en != title and title_en != title_cn:
                print(f"    🌍 {title_en}")
            print(f"    ⭐ 评分: {score:.3f} | 🌐 网站: {website_count}")
            print()

def display_anime_detail_simple(anime):
    """显示简化动漫详细信息"""
    print(f"\n{'='*80}")
    print(f"📺 动漫: {anime.get('日文名', '') or anime.get('英文名', '') or '未知标题'}")
    if anime.get('中文名'):
        print(f"🇨🇳 中文名: {anime['中文名']}")
    if anime.get('英文名'):
        print(f"🌍 英文名: {anime['英文名']}")
    if anime.get('日文名'):
        print(f"🇯🇵 日文名: {anime['日文名']}")
    
    print(f"🏆 当前排名: #{anime['排名']}")
    print(f"⭐ 综合评分: {anime['综合评分']}")
    
    print(f"\n📊 各网站评分:")
    websites = ['ANILIST', 'BANGUMI', 'FILMARKS', 'IMDB', 'MAL']
    for website in websites:
        score_key = f'{website}_评分'
        votes_key = f'{website}_投票数'
        rank_key = f'{website}_排名'
        
        if anime.get(score_key) and anime.get(score_key).strip():
            score = anime[score_key]
            votes = anime.get(votes_key, '0')
            rank = anime.get(rank_key, '-')
            print(f"   {website}: {score} ({votes} 票, 排名 #{rank})")

def get_anime_to_remove_simple(data):
    """获取要删除的动漫（简化版）"""
    total_anime = len(data)
    
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
                        display_anime_list_simple(data, start_rank, end_rank)
                        break
                    else:
                        print(f"❌ 请输入有效的排名范围 (1-{total_anime})")
                except ValueError:
                    print("❌ 请输入有效的数字")
        
        elif choice == '2':
            # 删除指定动漫
            return get_removal_list_simple(data)
        
        elif choice == '3':
            # 查看动漫详情
            try:
                rank_input = input(f"\n请输入要查看的动漫排名 (1-{total_anime}): ").strip()
                rank = int(rank_input)
                
                if 1 <= rank <= total_anime:
                    anime = next(a for a in data if a['排名'] == rank)
                    display_anime_detail_simple(anime)
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

def get_removal_list_simple(data):
    """获取要删除的动漫列表（简化版）"""
    total_anime = len(data)
    removal_list = []
    
    print(f"\n🗑️ 删除动漫模式")
    print("提示: 可以输入单个排名或用逗号分隔的多个排名")
    print("例如: 5 或 3,7,12 或 1-5,10,15-20")
    
    while True:
        ranks_input = input(f"\n请输入要删除的动漫排名 (1-{total_anime}, 或 'q' 退出): ").strip()
        
        if ranks_input.lower() == 'q':
            break
        
        try:
            ranks = parse_rank_input_simple(ranks_input, total_anime)
            if not ranks:
                continue
            
            # 显示要删除的动漫
            print(f"\n📋 将要删除的动漫:")
            for rank in sorted(ranks):
                anime = next(a for a in data if a['排名'] == rank)
                title_display = anime.get('日文名', '') or anime.get('英文名', '') or '未知标题'
                if anime.get('中文名'):
                    title_display += f" ({anime['中文名']})"
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

def parse_rank_input_simple(ranks_input, total_anime):
    """解析排名输入（简化版）"""
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

def remove_anime_simple(data, removal_ranks):
    """删除指定排名的动漫（简化版）"""
    if not removal_ranks:
        return data

    print(f"\n🗑️ 删除 {len(removal_ranks)} 个动漫...")

    # 获取要删除的动漫标题（用于日志）
    removed_titles = []
    for rank in removal_ranks:
        anime = next(a for a in data if a['排名'] == rank)
        title_display = anime.get('日文名', '') or anime.get('英文名', '') or '未知标题'
        if anime.get('中文名'):
            title_display += f" ({anime['中文名']})"
        removed_titles.append(f"#{rank}: {title_display}")

    # 删除动漫
    data = [anime for anime in data if anime['排名'] not in removal_ranks]

    # 重新分配排名
    for i, anime in enumerate(data, 1):
        anime['排名'] = i

    # 重新计算网站排名
    print(f"🔄 重新计算网站排名...")
    recalculate_site_rankings_simple(data)

    print(f"✅ 成功删除以下动漫:")
    for title in removed_titles:
        print(f"   {title}")

    print(f"📊 剩余动漫数量: {len(data)}")

    return data

def recalculate_site_rankings_simple(data):
    """重新计算网站排名（简化版）"""
    websites = ['ANILIST', 'BANGUMI', 'FILMARKS', 'IMDB', 'MAL']

    for website in websites:
        score_key = f'{website}_评分'
        rank_key = f'{website}_排名'

        # 收集有评分的动漫
        anime_with_scores = []
        for anime in data:
            if anime.get(score_key) and anime.get(score_key).strip():
                try:
                    score = float(anime[score_key])
                    anime_with_scores.append((anime, score))
                except ValueError:
                    continue

        if len(anime_with_scores) < 2:  # 至少需要2个动漫才能排名
            continue

        # 按评分降序排序
        anime_with_scores.sort(key=lambda x: x[1], reverse=True)

        # 分配排名
        for i, (anime, score) in enumerate(anime_with_scores, 1):
            anime[rank_key] = str(i)

    print(f"✅ 网站排名重新计算完成")

def save_updated_simple_csv(data, headers, original_file, removal_count):
    """保存更新后的简化CSV结果"""
    # 创建新文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_path = Path(original_file)

    # 移除原文件名中的 _simple 后缀，然后添加删除信息
    base_name = original_path.stem.replace('_simple', '')
    new_name = f"{base_name}_removed_{removal_count}_anime_{timestamp}_simple.csv"
    new_path = original_path.parent / new_name

    # 保存CSV
    with open(new_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

    print(f"💾 简化CSV结果已保存到: {new_path}")
    return new_path

def main():
    """主函数"""
    print("🚀 启动简化CSV手动删除程序")
    print("📝 此程序允许您删除指定排名的动漫并重新计算排名")
    print("🎯 专门针对简化CSV格式 (*_simple.csv)")

    # 1. 加载最新简化CSV结果
    result = load_latest_simple_csv()
    if not result:
        return

    data, headers, original_file = result
    original_count = len(data)

    print(f"📊 当前共有 {original_count} 个动漫")

    # 2. 获取要删除的动漫
    removal_ranks = get_anime_to_remove_simple(data)

    if not removal_ranks:
        print("ℹ️ 没有选择删除任何动漫，程序结束")
        return

    # 3. 删除动漫并重新排名
    updated_data = remove_anime_simple(data, removal_ranks)

    # 4. 保存结果
    removal_count = len(removal_ranks)
    new_file = save_updated_simple_csv(updated_data, headers, original_file, removal_count)

    # 5. 显示最终统计
    final_count = len(updated_data)
    print(f"\n📊 删除操作完成:")
    print(f"   原始动漫数量: {original_count}")
    print(f"   删除动漫数量: {removal_count}")
    print(f"   剩余动漫数量: {final_count}")
    print(f"   删除比例: {removal_count / original_count * 100:.1f}%")

    # 显示新的前10名
    print(f"\n🏆 删除后的新排名 (前10名):")
    display_anime_list_simple(updated_data, 1, min(10, final_count))

    print(f"\n🎉 简化CSV删除和重新排名完成！")
    print(f"📁 新文件: {new_file.name}")

if __name__ == "__main__":
    main()
