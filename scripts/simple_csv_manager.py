#!/usr/bin/env python3
"""
简化版本CSV手动管理工具
支持对简化版本CSV文件进行增删改操作
"""
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil

def find_latest_simple_csv():
    """查找最新的简化版本CSV文件"""
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("❌ 结果目录不存在: data/results")
        return None
    
    # 查找所有简化版本CSV文件
    csv_files = list(results_dir.glob("*simple.csv"))
    
    if not csv_files:
        print("❌ 未找到简化版本CSV文件")
        return None
    
    # 返回最新的文件
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    return latest_file

def load_simple_csv(csv_path):
    """加载简化版本CSV文件"""
    data = []
    headers = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            for row in reader:
                if len(row) >= len(headers):
                    data.append(row)
                else:
                    # 补齐缺失的列
                    row.extend([''] * (len(headers) - len(row)))
                    data.append(row)
        
        print(f"✅ 成功加载 {len(data)} 条动漫数据")
        return headers, data
        
    except Exception as e:
        print(f"❌ 加载CSV文件失败: {e}")
        return None, None

def save_simple_csv(headers, data, output_path):
    """保存简化版本CSV文件"""
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
        
        print(f"✅ 成功保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 保存CSV文件失败: {e}")
        return False

def display_anime_list(headers, data, start=0, count=10):
    """显示动漫列表"""
    print(f"\n📋 动漫列表 (显示 {start+1}-{min(start+count, len(data))} / 共 {len(data)} 条)")
    print("-" * 80)
    
    for i in range(start, min(start + count, len(data))):
        row = data[i]
        rank = row[0] if row[0] else str(i+1)
        title_cn = row[1] if len(row) > 1 else "未知"
        title_jp = row[2] if len(row) > 2 else "未知"
        score = row[3] if len(row) > 3 else "0"
        
        print(f"{i+1:3d}. 排名{rank:>3} | {title_cn:<30} | {title_jp:<25} | 评分: {score}")

def search_anime(headers, data, keyword):
    """搜索动漫"""
    results = []
    keyword_lower = keyword.lower()
    
    for i, row in enumerate(data):
        # 搜索中文名和日文名
        title_cn = row[1] if len(row) > 1 else ""
        title_jp = row[2] if len(row) > 2 else ""
        
        if (keyword_lower in title_cn.lower() or 
            keyword_lower in title_jp.lower() or
            keyword in title_cn or keyword in title_jp):
            results.append((i, row))
    
    return results

def add_anime_interactive(headers, data):
    """交互式添加动漫"""
    print("\n➕ 添加新动漫")
    print("=" * 50)
    
    # 获取基本信息
    title_cn = input("中文名: ").strip()
    if not title_cn:
        print("❌ 中文名不能为空")
        return False
    
    title_jp = input("日文名: ").strip()
    if not title_jp:
        title_jp = title_cn
    
    try:
        composite_score = float(input("综合评分: ").strip())
    except ValueError:
        print("❌ 综合评分必须是数字")
        return False
    
    # 创建新行数据
    new_row = ['', title_cn, title_jp, str(composite_score)]
    
    # 添加各网站评分数据
    websites = ['ANILIST', 'FILMARKS', 'IMDB', 'MAL']
    for website in websites:
        print(f"\n--- {website} 数据 ---")
        score = input(f"{website}_评分 (留空跳过): ").strip()
        votes = input(f"{website}_投票数 (留空跳过): ").strip()
        rank = input(f"{website}_排名 (留空跳过): ").strip()
        
        new_row.extend([score, votes, rank])
    
    # 添加到数据中
    data.append(new_row)
    
    # 重新排序和分配排名
    rerank_data(data)
    
    print(f"✅ 成功添加动漫: {title_cn}")
    return True

def remove_anime_interactive(headers, data):
    """交互式删除动漫"""
    print("\n🗑️ 删除动漫")
    print("=" * 50)
    
    keyword = input("请输入要删除的动漫名称关键词: ").strip()
    if not keyword:
        print("❌ 关键词不能为空")
        return False
    
    # 搜索匹配的动漫
    results = search_anime(headers, data, keyword)
    
    if not results:
        print(f"❌ 未找到包含 '{keyword}' 的动漫")
        return False
    
    print(f"\n🔍 找到 {len(results)} 个匹配结果:")
    for i, (idx, row) in enumerate(results):
        rank = row[0] if row[0] else str(idx+1)
        title_cn = row[1] if len(row) > 1 else "未知"
        title_jp = row[2] if len(row) > 2 else "未知"
        score = row[3] if len(row) > 3 else "0"
        print(f"{i+1}. 排名{rank:>3} | {title_cn} | {title_jp} | 评分: {score}")
    
    try:
        choice = int(input(f"\n请选择要删除的动漫 (1-{len(results)}): ")) - 1
        if choice < 0 or choice >= len(results):
            print("❌ 选择无效")
            return False
    except ValueError:
        print("❌ 请输入有效数字")
        return False
    
    # 确认删除
    idx, row = results[choice]
    title_cn = row[1] if len(row) > 1 else "未知"
    
    confirm = input(f"确认删除 '{title_cn}' ? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消删除")
        return False
    
    # 删除动漫
    del data[idx]
    
    # 重新排序和分配排名
    rerank_data(data)
    
    print(f"✅ 成功删除动漫: {title_cn}")
    return True

def rerank_data(data):
    """重新分配排名"""
    # 按综合评分降序排序
    try:
        data.sort(key=lambda x: float(x[3]) if x[3] and x[3] != '' else 0, reverse=True)
    except (ValueError, IndexError):
        print("⚠️ 排序时遇到无效数据，使用原始顺序")
    
    # 重新分配排名
    for i, row in enumerate(data):
        row[0] = str(i + 1)
    
    # 重新计算各网站排名
    recalculate_site_rankings(data)

def recalculate_site_rankings(data):
    """重新计算各网站排名"""
    websites = ['ANILIST', 'FILMARKS', 'IMDB', 'MAL']
    
    for website_idx, website in enumerate(websites):
        # 计算列索引 (评分列)
        score_col = 4 + website_idx * 3  # 4, 7, 10, 13
        rank_col = score_col + 2         # 6, 9, 12, 15
        
        # 收集有效评分的动漫
        valid_anime = []
        for i, row in enumerate(data):
            if (len(row) > score_col and row[score_col] and 
                row[score_col] != '' and row[score_col] != '0'):
                try:
                    score = float(row[score_col])
                    valid_anime.append((i, score))
                except ValueError:
                    continue
        
        # 按评分降序排序
        valid_anime.sort(key=lambda x: x[1], reverse=True)
        
        # 分配排名
        for rank, (row_idx, score) in enumerate(valid_anime, 1):
            if len(data[row_idx]) > rank_col:
                data[row_idx][rank_col] = str(rank)
            else:
                # 扩展行长度
                while len(data[row_idx]) <= rank_col:
                    data[row_idx].append('')
                data[row_idx][rank_col] = str(rank)

def edit_anime_interactive(headers, data):
    """交互式编辑动漫"""
    print("\n✏️ 编辑动漫")
    print("=" * 50)
    
    keyword = input("请输入要编辑的动漫名称关键词: ").strip()
    if not keyword:
        print("❌ 关键词不能为空")
        return False
    
    # 搜索匹配的动漫
    results = search_anime(headers, data, keyword)
    
    if not results:
        print(f"❌ 未找到包含 '{keyword}' 的动漫")
        return False
    
    print(f"\n🔍 找到 {len(results)} 个匹配结果:")
    for i, (idx, row) in enumerate(results):
        rank = row[0] if row[0] else str(idx+1)
        title_cn = row[1] if len(row) > 1 else "未知"
        title_jp = row[2] if len(row) > 2 else "未知"
        score = row[3] if len(row) > 3 else "0"
        print(f"{i+1}. 排名{rank:>3} | {title_cn} | {title_jp} | 评分: {score}")
    
    try:
        choice = int(input(f"\n请选择要编辑的动漫 (1-{len(results)}): ")) - 1
        if choice < 0 or choice >= len(results):
            print("❌ 选择无效")
            return False
    except ValueError:
        print("❌ 请输入有效数字")
        return False
    
    # 编辑选中的动漫
    idx, row = results[choice]
    
    print(f"\n编辑动漫: {row[1] if len(row) > 1 else '未知'}")
    print("提示: 直接按回车保持原值不变")
    
    # 编辑基本信息
    current_cn = row[1] if len(row) > 1 else ""
    new_cn = input(f"中文名 [{current_cn}]: ").strip()
    if new_cn:
        row[1] = new_cn
    
    current_jp = row[2] if len(row) > 2 else ""
    new_jp = input(f"日文名 [{current_jp}]: ").strip()
    if new_jp:
        row[2] = new_jp
    
    current_score = row[3] if len(row) > 3 else ""
    new_score = input(f"综合评分 [{current_score}]: ").strip()
    if new_score:
        try:
            float(new_score)
            row[3] = new_score
        except ValueError:
            print("⚠️ 综合评分无效，保持原值")
    
    # 编辑各网站数据
    websites = ['ANILIST', 'FILMARKS', 'IMDB', 'MAL']
    for website_idx, website in enumerate(websites):
        print(f"\n--- {website} 数据 ---")
        
        score_col = 4 + website_idx * 3
        votes_col = score_col + 1
        rank_col = score_col + 2
        
        # 确保行长度足够
        while len(row) <= rank_col:
            row.append('')
        
        current_score = row[score_col]
        new_score = input(f"{website}_评分 [{current_score}]: ").strip()
        if new_score:
            row[score_col] = new_score
        
        current_votes = row[votes_col]
        new_votes = input(f"{website}_投票数 [{current_votes}]: ").strip()
        if new_votes:
            row[votes_col] = new_votes
        
        current_rank = row[rank_col]
        new_rank = input(f"{website}_排名 [{current_rank}]: ").strip()
        if new_rank:
            row[rank_col] = new_rank
    
    # 重新排序和分配排名
    rerank_data(data)
    
    print(f"✅ 成功编辑动漫")
    return True

def main_menu():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("🎌 AnimeScore 简化版本CSV管理工具")
        print("="*60)
        print("1. 📋 查看动漫列表")
        print("2. 🔍 搜索动漫")
        print("3. ➕ 添加动漫")
        print("4. ✏️ 编辑动漫")
        print("5. 🗑️ 删除动漫")
        print("6. 💾 保存并退出")
        print("7. ❌ 退出不保存")
        print("-"*60)

        choice = input("请选择操作 (1-7): ").strip()

        if choice == '1':
            return 'list'
        elif choice == '2':
            return 'search'
        elif choice == '3':
            return 'add'
        elif choice == '4':
            return 'edit'
        elif choice == '5':
            return 'remove'
        elif choice == '6':
            return 'save'
        elif choice == '7':
            return 'exit'
        else:
            print("❌ 无效选择，请重新输入")

def main():
    """主程序"""
    print("🎌 AnimeScore 简化版本CSV管理工具")
    print("="*60)

    # 查找最新的简化版本CSV文件
    csv_path = find_latest_simple_csv()
    if not csv_path:
        return

    print(f"📄 使用文件: {csv_path}")

    # 加载CSV数据
    headers, data = load_simple_csv(csv_path)
    if headers is None or data is None:
        return

    # 备份原文件
    backup_path = csv_path.with_suffix('.backup.csv')
    try:
        shutil.copy2(csv_path, backup_path)
        print(f"📋 已创建备份: {backup_path}")
    except Exception as e:
        print(f"⚠️ 创建备份失败: {e}")

    modified = False

    while True:
        action = main_menu()

        if action == 'list':
            start = 0
            while True:
                display_anime_list(headers, data, start, 10)

                print(f"\n导航选项:")
                if start > 0:
                    print("p. 上一页")
                if start + 10 < len(data):
                    print("n. 下一页")
                print("b. 返回主菜单")

                nav = input("选择: ").strip().lower()
                if nav == 'p' and start > 0:
                    start = max(0, start - 10)
                elif nav == 'n' and start + 10 < len(data):
                    start += 10
                elif nav == 'b':
                    break
                else:
                    print("❌ 无效选择")

        elif action == 'search':
            keyword = input("\n🔍 请输入搜索关键词: ").strip()
            if keyword:
                results = search_anime(headers, data, keyword)
                if results:
                    print(f"\n🔍 找到 {len(results)} 个匹配结果:")
                    for i, (idx, row) in enumerate(results):
                        rank = row[0] if row[0] else str(idx+1)
                        title_cn = row[1] if len(row) > 1 else "未知"
                        title_jp = row[2] if len(row) > 2 else "未知"
                        score = row[3] if len(row) > 3 else "0"
                        print(f"{i+1:3d}. 排名{rank:>3} | {title_cn:<30} | {title_jp:<25} | 评分: {score}")
                else:
                    print(f"❌ 未找到包含 '{keyword}' 的动漫")

            input("\n按回车继续...")

        elif action == 'add':
            if add_anime_interactive(headers, data):
                modified = True

        elif action == 'edit':
            if edit_anime_interactive(headers, data):
                modified = True

        elif action == 'remove':
            if remove_anime_interactive(headers, data):
                modified = True

        elif action == 'save':
            if modified:
                # 生成新的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"anime_ranking_Summer_2025_{timestamp}_simple_edited.csv"
                output_path = csv_path.parent / new_filename

                if save_simple_csv(headers, data, output_path):
                    print(f"✅ 数据已保存到新文件: {output_path}")

                    # 询问是否覆盖原文件
                    overwrite = input("是否覆盖原文件? (y/N): ").strip().lower()
                    if overwrite == 'y':
                        if save_simple_csv(headers, data, csv_path):
                            print(f"✅ 原文件已更新: {csv_path}")
                else:
                    print("❌ 保存失败")
            else:
                print("ℹ️ 没有修改，无需保存")
            break

        elif action == 'exit':
            if modified:
                save_confirm = input("⚠️ 有未保存的修改，确认退出不保存? (y/N): ").strip().lower()
                if save_confirm != 'y':
                    continue
            print("👋 再见！")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，再见！")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
