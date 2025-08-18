#!/usr/bin/env python3
"""
手动数据修正脚本
用于修正搜索错误导致的评分、网址等数据问题，然后重新计算排名
"""
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import click
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import Config
from src.models.anime import AnimeInfo, AnimeScore, RatingData, WebsiteName, Season
from src.core.analyzer import AnimeAnalyzer

class ManualDataCorrection:
    """手动数据修正器"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def load_analysis_results(self, file_path: str) -> List[AnimeScore]:
        """从JSON文件加载分析结果"""
        logger.info(f"📂 加载分析结果: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        anime_scores = []
        for ranking in data['rankings']:
            # 重建AnimeInfo
            anime_info = AnimeInfo(
                title=ranking['title'],
                title_english=ranking.get('title_english'),
                title_japanese=ranking.get('title_japanese'),
                title_chinese=ranking.get('title_chinese'),
                anime_type=ranking.get('anime_type'),
                episodes=ranking.get('episodes'),
                start_date=ranking.get('start_date'),
                studios=ranking.get('studios', []),
                genres=ranking.get('genres', []),
                year=ranking.get('year'),
                poster_image=ranking.get('poster_image'),
                cover_image=ranking.get('cover_image'),
                banner_image=ranking.get('banner_image'),
                external_ids={}
            )
            
            # 重建评分数据
            ratings = []
            for rating in ranking['ratings']:
                website = WebsiteName(rating['website'])
                
                # 从URL中提取ID并存储到external_ids
                if 'url' in rating and rating['url']:
                    if website == WebsiteName.MAL and 'myanimelist.net/anime/' in rating['url']:
                        mal_id = rating['url'].split('/anime/')[-1].split('/')[0]
                        anime_info.external_ids[WebsiteName.MAL] = mal_id
                    elif website == WebsiteName.ANILIST and 'anilist.co/anime/' in rating['url']:
                        anilist_id = rating['url'].split('/anime/')[-1].split('/')[0]
                        anime_info.external_ids[WebsiteName.ANILIST] = anilist_id
                    elif website == WebsiteName.BANGUMI and 'bgm.tv/subject/' in rating['url']:
                        bangumi_id = rating['url'].split('/subject/')[-1].split('/')[0]
                        anime_info.external_ids[WebsiteName.BANGUMI] = bangumi_id
                    elif website == WebsiteName.DOUBAN and 'douban.com/subject/' in rating['url']:
                        douban_id = rating['url'].split('/subject/')[-1].split('/')[0]
                        anime_info.external_ids[WebsiteName.DOUBAN] = douban_id
                
                rating_data = RatingData(
                    website=website,
                    raw_score=rating['raw_score'],
                    vote_count=rating['vote_count'],
                    site_mean=0.0,  # 会重新计算
                    site_std=0.0,   # 会重新计算
                    url=rating.get('url', '')
                )
                ratings.append(rating_data)
            
            anime_score = AnimeScore(
                anime_info=anime_info,
                ratings=ratings
            )
            anime_scores.append(anime_score)
        
        logger.info(f"✅ 成功加载 {len(anime_scores)} 个动漫数据")
        return anime_scores
    
    def find_latest_results_file(self) -> str:
        """查找最新的结果文件（优先从 final_results 目录）"""
        # 首先检查 final_results 目录
        final_results_dir = Path(self.config.storage.final_results_dir)
        if final_results_dir.exists():
            json_files = list(final_results_dir.glob("anime_ranking_*.json"))
            if json_files:
                latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"📂 自动选择 final_results 中的最新文件: {latest_file.name}")
                logger.info(f"   (这是经过手动处理的结果)")
                return str(latest_file)
        
        # 如果 final_results 没有文件，则从普通 results 目录查找
        results_dir = Path(self.config.storage.results_dir)
        if not results_dir.exists():
            raise FileNotFoundError("结果目录不存在")
        
        json_files = list(results_dir.glob("anime_ranking_*.json"))
        if not json_files:
            raise FileNotFoundError("没有找到分析结果文件")
        
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 自动选择 results 中的最新文件: {latest_file.name}")
        logger.info(f"   (这是原始分析结果)")
        return str(latest_file)
    
    def display_anime_list(self, anime_scores: List[AnimeScore]):
        """显示动漫列表供用户选择"""
        print(f"\n📋 动漫列表 (共 {len(anime_scores)} 个):")
        print("=" * 80)
        
        for i, anime_score in enumerate(anime_scores, 1):
            anime = anime_score.anime_info
            ratings_count = len(anime_score.ratings)
            
            # 显示基本信息
            print(f"{i:3d}. {anime.title}")
            if anime.title_english and anime.title_english != anime.title:
                print(f"     英文: {anime.title_english}")
            if anime.title_japanese and anime.title_japanese != anime.title:
                print(f"     日文: {anime.title_japanese}")
            
            print(f"     评分网站数: {ratings_count}")
            
            # 显示评分概览
            if anime_score.ratings:
                ratings_str = []
                for rating in anime_score.ratings[:3]:  # 只显示前3个
                    ratings_str.append(f"{rating.website.value}: {rating.raw_score}")
                if len(anime_score.ratings) > 3:
                    ratings_str.append("...")
                print(f"     评分: {', '.join(ratings_str)}")
            
            print()
    
    def select_anime_to_correct(self, anime_scores: List[AnimeScore]) -> Optional[AnimeScore]:
        """选择要修正的动漫"""
        while True:
            try:
                choice = input("🎯 请输入要修正的动漫编号 (1-{}, 0=退出): ".format(len(anime_scores)))
                
                if choice == '0':
                    return None
                
                index = int(choice) - 1
                if 0 <= index < len(anime_scores):
                    return anime_scores[index]
                else:
                    print("❌ 编号超出范围，请重新输入")
            except ValueError:
                print("❌ 请输入有效的数字")
    
    def display_anime_details(self, anime_score: AnimeScore):
        """显示动漫详细信息"""
        anime = anime_score.anime_info
        
        print(f"\n📺 动漫详情: {anime.title}")
        print("=" * 60)
        print(f"🌍 英文名: {anime.title_english or '未知'}")
        print(f"🇯🇵 日文名: {anime.title_japanese or '未知'}")
        print(f"📋 类型: {anime.anime_type or '未知'}")
        print(f"📺 集数: {anime.episodes or '未知'}")
        print(f"📅 开播: {anime.start_date or '未知'}")
        print(f"🏢 制作: {', '.join(anime.studios) if anime.studios else '未知'}")
        print(f"🏷️ 类型: {', '.join(anime.genres) if anime.genres else '未知'}")
        
        print(f"\n📊 评分数据 (共 {len(anime_score.ratings)} 个网站):")
        for i, rating in enumerate(anime_score.ratings, 1):
            print(f"   {i}. {rating.website.value}: {rating.raw_score} ({rating.vote_count:,} 票)")
            if rating.url:
                print(f"      URL: {rating.url}")
            print()
    
    def correct_rating_data(self, anime_score: AnimeScore) -> bool:
        """修正评分数据"""
        print(f"\n🔧 修正评分数据")
        print("提示: 输入 'skip' 跳过某个网站，输入 'delete' 删除某个网站的数据")
        
        corrections_made = False
        ratings_to_remove = []
        
        for i, rating in enumerate(anime_score.ratings):
            print(f"\n📊 网站: {rating.website.value}")
            print(f"   当前评分: {rating.raw_score}")
            print(f"   当前投票数: {rating.vote_count:,}")
            print(f"   当前URL: {rating.url}")
            
            # 修正评分
            new_score = input(f"   新评分 (当前: {rating.raw_score}, 回车保持不变): ").strip()
            if new_score.lower() == 'delete':
                ratings_to_remove.append(i)
                print("   ❌ 标记删除此网站数据")
                corrections_made = True
                continue
            elif new_score.lower() == 'skip':
                print("   ⏭️ 跳过此网站")
                continue
            elif new_score and new_score != str(rating.raw_score):
                try:
                    rating.raw_score = float(new_score)
                    print(f"   ✅ 评分已更新: {rating.raw_score}")
                    corrections_made = True
                except ValueError:
                    print("   ❌ 无效的评分，保持原值")
            
            # 修正投票数
            new_votes = input(f"   新投票数 (当前: {rating.vote_count:,}, 回车保持不变): ").strip()
            if new_votes and new_votes != str(rating.vote_count):
                try:
                    rating.vote_count = int(new_votes)
                    print(f"   ✅ 投票数已更新: {rating.vote_count:,}")
                    corrections_made = True
                except ValueError:
                    print("   ❌ 无效的投票数，保持原值")
            
            # 修正URL
            new_url = input(f"   新URL (当前: {rating.url}, 回车保持不变): ").strip()
            if new_url and new_url != rating.url:
                rating.url = new_url
                print(f"   ✅ URL已更新: {rating.url}")
                corrections_made = True
        
        # 删除标记的评分数据
        for i in reversed(ratings_to_remove):
            removed_rating = anime_score.ratings.pop(i)
            print(f"   🗑️ 已删除 {removed_rating.website.value} 的数据")
        
        return corrections_made
    
    def data_correction_session(self, anime_scores: List[AnimeScore]) -> List[AnimeScore]:
        """数据修正会话"""
        logger.info("🎯 开始数据修正会话")
        
        corrected_anime = []
        
        while True:
            # 显示动漫列表
            self.display_anime_list(anime_scores)
            
            # 选择要修正的动漫
            selected_anime = self.select_anime_to_correct(anime_scores)
            if selected_anime is None:
                break
            
            # 显示详细信息
            self.display_anime_details(selected_anime)
            
            # 确认是否修正
            confirm = input("🔧 是否要修正这个动漫的数据? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
            
            # 执行修正
            if self.correct_rating_data(selected_anime):
                corrected_anime.append(selected_anime)
                print("✅ 数据修正完成")
            else:
                print("ℹ️ 没有进行任何修改")
            
            # 询问是否继续
            continue_choice = input("\n🔄 是否继续修正其他动漫? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break
        
        logger.info(f"📊 共修正了 {len(corrected_anime)} 个动漫的数据")
        return anime_scores  # 返回所有数据（包含修正）
    
    def save_corrected_results(self, analysis, output_dir: str, output_formats: List[str]):
        """保存修正后的结果"""
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        season_str = f"{analysis.season.value}_{analysis.year}"
        base_filename = f"anime_ranking_{season_str}_data_corrected_{timestamp}"
        
        # 准备数据
        results_data = {
            "analysis_info": {
                "season": analysis.season.value,
                "year": analysis.year,
                "analysis_date": analysis.analysis_date.isoformat(),
                "total_anime_count": analysis.total_anime_count,
                "analyzed_anime_count": analysis.analyzed_anime_count,
                "data_correction": True,
                "correction_date": datetime.now().isoformat()
            },
            "rankings": []
        }
        
        # 转换动漫评分数据
        for i, anime_score in enumerate(analysis.anime_scores, 1):
            # 处理日期序列化
            start_date = anime_score.anime_info.start_date
            if hasattr(start_date, 'isoformat'):
                start_date = start_date.isoformat()
            elif start_date is not None:
                start_date = str(start_date)

            anime_data = {
                "rank": i,
                "title": anime_score.anime_info.title,
                "title_english": anime_score.anime_info.title_english,
                "title_japanese": anime_score.anime_info.title_japanese,
                "title_chinese": anime_score.anime_info.title_chinese,
                "anime_type": anime_score.anime_info.anime_type,
                "episodes": anime_score.anime_info.episodes,
                "start_date": start_date,
                "studios": anime_score.anime_info.studios,
                "genres": anime_score.anime_info.genres,
                "year": anime_score.anime_info.year,
                "composite_score": anime_score.composite_score.final_score if anime_score.composite_score else 0,
                "confidence": anime_score.composite_score.confidence if anime_score.composite_score else 0,
                "total_votes": anime_score.composite_score.total_votes if anime_score.composite_score else 0,
                "website_count": len(anime_score.ratings),
                "poster_image": anime_score.anime_info.poster_image,
                "cover_image": anime_score.anime_info.cover_image,
                "banner_image": anime_score.anime_info.banner_image,
                "percentile": anime_score.composite_score.percentile if anime_score.composite_score else None,
                "ratings": []
            }
            
            # 添加各网站评分
            for rating in anime_score.ratings:
                rating_data = {
                    "website": rating.website.value,
                    "raw_score": rating.raw_score,
                    "vote_count": rating.vote_count,
                    "url": rating.url,
                    "site_rank": getattr(rating, 'site_rank', None)
                }
                anime_data["ratings"].append(rating_data)
            
            results_data["rankings"].append(anime_data)
        
        # 保存为不同格式
        if "json" in output_formats:
            json_file = output_path / f"{base_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to {json_file}")
        
        if "csv" in output_formats:
            csv_file = output_path / f"{base_filename}.csv"
            self._save_csv_results(results_data, csv_file)
            logger.info(f"CSV results saved to {csv_file}")
    
    def _save_csv_results(self, data, csv_path):
        """保存CSV格式结果"""
        import csv
        
        # 获取所有网站
        all_websites = set()
        for anime in data['rankings']:
            for rating in anime.get('ratings', []):
                all_websites.add(rating['website'])
        
        all_websites = sorted(list(all_websites))
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 构建表头
            headers = [
                'Rank', 'Title', 'Title_English', 'Title_Japanese', 'Type', 'Episodes',
                'Start_Date', 'Studios', 'Genres', 'Year', 'Composite_Score', 'Confidence',
                'Total_Votes', 'Website_Count'
            ]
            
            # 添加各网站的评分和投票数列
            for website in all_websites:
                headers.extend([
                    f"{website.upper()}_Score",
                    f"{website.upper()}_Votes",
                    f"{website.upper()}_URL"
                ])
            
            writer.writerow(headers)
            
            # 写入数据
            for anime in data['rankings']:
                # 处理日期字段
                start_date = anime.get('start_date', '')
                if start_date and hasattr(start_date, 'isoformat'):
                    start_date = start_date.isoformat()
                elif start_date is not None:
                    start_date = str(start_date)
                else:
                    start_date = ''

                # 基础信息
                row = [
                    anime['rank'],
                    anime['title'],
                    anime.get('title_english', ''),
                    anime.get('title_japanese', ''),
                    anime.get('anime_type', ''),
                    anime.get('episodes', ''),
                    start_date,
                    ', '.join(anime.get('studios', [])),
                    ', '.join(anime.get('genres', [])),
                    anime.get('year', ''),
                    anime['composite_score'],
                    anime['confidence'],
                    anime['total_votes'],
                    anime['website_count']
                ]
                
                # 各网站评分
                website_ratings = {}
                for rating in anime.get('ratings', []):
                    website_ratings[rating['website']] = {
                        'score': rating['raw_score'],
                        'votes': rating['vote_count'],
                        'url': rating.get('url', '')
                    }
                
                # 添加各网站的评分、投票数和URL
                for website in all_websites:
                    if website in website_ratings:
                        row.extend([
                            website_ratings[website]['score'],
                            website_ratings[website]['votes'],
                            website_ratings[website]['url']
                        ])
                    else:
                        row.extend(['', '', ''])
                
                writer.writerow(row)


@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='配置文件路径')
@click.option('--input', '-i', default=None,
              help='输入的分析结果JSON文件路径 (默认: 自动选择最新文件)')
@click.option('--output', '-o', default=None,
              help='输出目录 (默认: final_results目录)')
@click.option('--formats', '-f', default='json,csv',
              help='输出格式 (逗号分隔: json,csv)')
@click.option('--verbose', '-v', is_flag=True,
              help='启用详细日志')
def main(config, input, output, formats, verbose):
    """手动数据修正程序"""
    
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("🔧 启动手动数据修正程序")
    
    try:
        # 1. 加载配置
        app_config = Config.load_from_file(config)
        logger.info(f"✅ 配置加载成功: {config}")
        
        # 2. 创建数据修正器
        data_corrector = ManualDataCorrection(app_config)
        
        # 3. 确定输入文件
        if input is None:
            logger.info("🔍 未指定输入文件，自动查找最新结果...")
            input_file = data_corrector.find_latest_results_file()
        else:
            input_file = input
            logger.info(f"📂 使用指定的输入文件: {input_file}")
        
        # 4. 加载分析结果
        anime_scores = data_corrector.load_analysis_results(input_file)
        
        # 5. 执行数据修正会话
        corrected_scores = data_corrector.data_correction_session(anime_scores)
        
        # 6. 重新计算综合评分和排名
        logger.info("🔄 重新计算综合评分和排名...")
        analyzer = AnimeAnalyzer(app_config)

        # 重新计算综合评分
        ranked_scores = analyzer.calculate_composite_scores(corrected_scores)

        # 创建分析结果
        from src.models.anime import SeasonalAnalysis
        analysis = SeasonalAnalysis(
            season=Season.SUMMER,
            year=2025,
            anime_scores=ranked_scores,
            total_anime_count=len(corrected_scores),
            analyzed_anime_count=len(ranked_scores)
        )
        
        # 7. 保存结果到 final_results 目录
        output_dir = output or app_config.storage.final_results_dir
        output_formats = [fmt.strip() for fmt in formats.split(',')]
        
        data_corrector.save_corrected_results(analysis, output_dir, output_formats)
        
        logger.success("🎉 数据修正完成！")
        logger.info(f"📁 结果已保存到: {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
