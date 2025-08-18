#!/usr/bin/env python3
"""
手动数据补全程序
读取分析结果，识别缺失数据的动漫，允许用户手动输入评分，然后重新计算排名
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
import click
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import Config
from src.models.anime import AnimeScore, AnimeInfo, RatingData, WebsiteName
from src.core.analyzer import AnimeAnalyzer
# 移除不存在的导入
from loguru import logger


class ManualDataCompletion:
    """手动数据补全类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.analyzer = AnimeAnalyzer(config)
        self.enabled_websites = self._get_enabled_websites()
        
    def _get_enabled_websites(self) -> List[WebsiteName]:
        """获取启用的网站列表（排除数据补全排除列表中的网站）"""
        enabled_websites = []
        excluded_websites = set(self.config.data_completion.excluded_websites)

        for website_name, website_config in self.config.websites.items():
            if website_config.enabled and website_name not in excluded_websites:
                try:
                    website_enum = WebsiteName(website_name)
                    enabled_websites.append(website_enum)
                except ValueError:
                    continue

        logger.info(f"📊 手动补全启用的网站: {[w.value for w in enabled_websites]}")
        if excluded_websites:
            logger.info(f"📊 手动补全排除的网站: {list(excluded_websites)}")

        return enabled_websites

    def find_latest_results_file(self) -> str:
        """查找最新的结果文件（优先从 final_results 目录）"""
        from pathlib import Path

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
                poster_image=ranking.get('poster_image'),
                cover_image=ranking.get('cover_image'),
                banner_image=ranking.get('banner_image')
            )
            
            # 重建RatingData列表
            ratings = []
            for rating in ranking['ratings']:
                website = WebsiteName(rating['website'])

                # 从URL中提取ID并存储到external_ids
                if website == WebsiteName.MAL and 'myanimelist.net/anime/' in rating.get('url', ''):
                    mal_id = rating['url'].split('/anime/')[-1].split('/')[0]
                    anime_info.external_ids[WebsiteName.MAL] = mal_id
                elif website == WebsiteName.ANILIST and 'anilist.co/anime/' in rating.get('url', ''):
                    anilist_id = rating['url'].split('/anime/')[-1].split('/')[0]
                    anime_info.external_ids[WebsiteName.ANILIST] = anilist_id
                elif website == WebsiteName.BANGUMI and 'bgm.tv/subject/' in rating.get('url', ''):
                    bangumi_id = rating['url'].split('/subject/')[-1].split('/')[0]
                    anime_info.external_ids[WebsiteName.BANGUMI] = bangumi_id
                elif website == WebsiteName.DOUBAN and 'douban.com/subject/' in rating.get('url', ''):
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
    
    def identify_incomplete_anime(self, anime_scores: List[AnimeScore]) -> List[Dict]:
        """识别数据不完整的动漫"""
        incomplete_anime = []
        
        for anime_score in anime_scores:
            existing_websites = {rating.website for rating in anime_score.ratings}
            missing_websites = set(self.enabled_websites) - existing_websites
            
            if missing_websites:
                incomplete_anime.append({
                    'anime_score': anime_score,
                    'existing_websites': existing_websites,
                    'missing_websites': missing_websites
                })
        
        # 按缺失网站数量排序（缺失少的优先）
        incomplete_anime.sort(key=lambda x: len(x['missing_websites']))
        
        return incomplete_anime
    
    def display_anime_info(self, anime_score: AnimeScore):
        """显示动漫信息"""
        info = anime_score.anime_info
        print(f"\n{'='*60}")
        print(f"📺 动漫: {info.title}")
        if info.title_english:
            print(f"🌍 英文名: {info.title_english}")
        if info.anime_type:
            print(f"📋 类型: {info.anime_type}")
        if info.episodes:
            print(f"📺 集数: {info.episodes}")
        if info.start_date:
            print(f"📅 开播: {info.start_date}")
        if info.studios:
            print(f"🏢 制作: {', '.join(info.studios[:3])}")
        if info.genres:
            print(f"🏷️ 类型: {', '.join(info.genres[:5])}")
        
        print(f"\n📊 现有评分数据:")
        for rating in anime_score.ratings:
            print(f"   {rating.website.value}: {rating.raw_score} ({rating.vote_count} 票)")
    
    def get_manual_rating(self, website: WebsiteName) -> Optional[RatingData]:
        """获取用户手动输入的评分"""
        print(f"\n🔍 请为 {website.value} 网站输入评分数据:")
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
        
        # 获取URL（可选）
        url_input = input(f"   URL (可选): ").strip()
        if not url_input:
            url_input = f"https://manual-input/{website.value}"
        
        return RatingData(
            website=website,
            raw_score=score,
            vote_count=votes,
            site_mean=0.0,  # 会重新计算
            site_std=0.0,   # 会重新计算
            url=url_input
        )
    
    def manual_completion_session(self, incomplete_anime: List[Dict]) -> Dict[str, List[RatingData]]:
        """手动补全会话"""
        logger.info(f"🎯 开始手动数据补全会话，共 {len(incomplete_anime)} 个动漫需要补全")
        
        completed_data = {}
        
        for i, item in enumerate(incomplete_anime, 1):
            anime_score = item['anime_score']
            missing_websites = item['missing_websites']
            
            print(f"\n🔢 进度: {i}/{len(incomplete_anime)}")
            self.display_anime_info(anime_score)
            
            print(f"\n❌ 缺失网站: {[w.value for w in missing_websites]}")
            
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
                    continue
            
            if choice in ['n', 'no', '否']:
                continue
            
            # 为每个缺失的网站获取数据
            anime_completed_data = []
            for website in missing_websites:
                rating_data = self.get_manual_rating(website)
                if rating_data:
                    anime_completed_data.append(rating_data)
                    print(f"   ✅ 已添加 {website.value} 数据: {rating_data.raw_score}")
            
            if anime_completed_data:
                completed_data[anime_score.anime_info.title] = anime_completed_data
                print(f"   🎉 成功为 {anime_score.anime_info.title} 添加了 {len(anime_completed_data)} 条数据")
        
        return completed_data
    
    def merge_manual_data(self, anime_scores: List[AnimeScore], 
                         manual_data: Dict[str, List[RatingData]]) -> List[AnimeScore]:
        """合并手动输入的数据"""
        logger.info(f"🔄 合并手动输入的数据...")
        
        merged_count = 0
        
        for anime_score in anime_scores:
            anime_title = anime_score.anime_info.title
            
            if anime_title in manual_data:
                # 添加手动输入的评分数据
                for rating_data in manual_data[anime_title]:
                    # 检查是否已存在该网站的数据
                    existing_websites = {r.website for r in anime_score.ratings}
                    
                    if rating_data.website not in existing_websites:
                        anime_score.ratings.append(rating_data)
                        merged_count += 1
                        logger.info(f"✅ 为 {anime_title} 添加 {rating_data.website.value} 手动数据")
        
        logger.info(f"🎉 成功合并 {merged_count} 条手动数据")
        return anime_scores

    def _save_analysis_results(self, analysis, output_dir: str, output_formats: List[str], filename_suffix: str = ""):
        """保存分析结果"""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        season_str = f"{analysis.season.value}_{analysis.year}"
        base_filename = f"anime_ranking_{season_str}{filename_suffix}_{timestamp}"

        # 准备数据
        results_data = {
            "analysis_info": {
                "season": analysis.season.value,
                "year": analysis.year,
                "analysis_date": analysis.analysis_date.isoformat(),
                "total_anime_count": analysis.total_anime_count,
                "analyzed_anime_count": analysis.analyzed_anime_count,
                "manual_completion": True,
                "manual_completion_date": datetime.now().isoformat()
            },
            "rankings": []
        }

        # 转换动漫评分数据
        for i, anime_score in enumerate(analysis.anime_scores, 1):
            anime_data = {
                "rank": i,
                "title": anime_score.anime_info.title,
                "title_english": anime_score.anime_info.title_english,
                "title_japanese": anime_score.anime_info.title_japanese,
                "title_chinese": anime_score.anime_info.title_chinese,
                "anime_type": anime_score.anime_info.anime_type.value if anime_score.anime_info.anime_type else None,
                "episodes": anime_score.anime_info.episodes,
                "start_date": anime_score.anime_info.start_date.isoformat() if anime_score.anime_info.start_date else None,
                "studios": anime_score.anime_info.studios,
                "genres": anime_score.anime_info.genres,
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
                'Start_Date', 'Studios', 'Genres', 'Composite_Score', 'Confidence',
                'Total_Votes', 'Website_Count'
            ]

            # 添加各网站的评分和投票数列
            for website in all_websites:
                headers.extend([
                    f"{website.upper()}_Score",
                    f"{website.upper()}_Votes"
                ])

            writer.writerow(headers)

            # 写入数据
            for anime in data['rankings']:
                # 基础信息
                row = [
                    anime['rank'],
                    anime['title'],
                    anime.get('title_english', ''),
                    anime.get('title_japanese', ''),
                    anime.get('anime_type', ''),
                    anime.get('episodes', ''),
                    anime.get('start_date', ''),
                    ', '.join(anime.get('studios', [])),
                    ', '.join(anime.get('genres', [])),
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
                        'votes': rating['vote_count']
                    }

                # 添加各网站的评分和投票数
                for website in all_websites:
                    if website in website_ratings:
                        row.extend([
                            website_ratings[website]['score'],
                            website_ratings[website]['votes']
                        ])
                    else:
                        row.extend(['', ''])

                writer.writerow(row)


@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='配置文件路径')
@click.option('--input', '-i', default=None,
              help='输入的分析结果JSON文件路径 (默认: 自动选择最新文件)')
@click.option('--output', '-o', default=None,
              help='输出目录 (默认: 从配置读取)')
@click.option('--formats', '-f', default='json,csv',
              help='输出格式 (逗号分隔: json,csv,xlsx)')
@click.option('--verbose', '-v', is_flag=True,
              help='启用详细日志')
def main(config, input, output, formats, verbose):
    """手动数据补全程序"""
    
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("🚀 启动手动数据补全程序")
    
    try:
        # 1. 加载配置
        app_config = Config.load_from_file(config)
        logger.info(f"✅ 配置加载成功: {config}")
        
        # 2. 创建手动补全器
        manual_completion = ManualDataCompletion(app_config)

        # 3. 确定输入文件
        if input is None:
            logger.info("🔍 未指定输入文件，自动查找最新结果...")
            input_file = manual_completion.find_latest_results_file()
        else:
            input_file = input
            logger.info(f"📂 使用指定的输入文件: {input_file}")

        # 4. 加载分析结果
        anime_scores = manual_completion.load_analysis_results(input_file)
        
        # 5. 识别不完整的动漫
        incomplete_anime = manual_completion.identify_incomplete_anime(anime_scores)
        
        if not incomplete_anime:
            logger.info("🎉 所有动漫数据都是完整的，无需手动补全！")
            return
        
        logger.info(f"📊 发现 {len(incomplete_anime)} 个动漫需要手动补全数据")
        
        # 显示概览
        print(f"\n📋 数据不完整的动漫概览:")
        for i, item in enumerate(incomplete_anime[:10], 1):  # 只显示前10个
            anime = item['anime_score']
            missing = len(item['missing_websites'])
            print(f"   {i}. {anime.anime_info.title} (缺失 {missing} 个网站)")
        
        if len(incomplete_anime) > 10:
            print(f"   ... 还有 {len(incomplete_anime) - 10} 个动漫")
        
        # 5. 手动补全会话
        manual_data = manual_completion.manual_completion_session(incomplete_anime)
        
        if not manual_data:
            logger.info("ℹ️ 没有手动输入任何数据，程序结束")
            return
        
        # 6. 合并手动数据
        updated_scores = manual_completion.merge_manual_data(anime_scores, manual_data)
        
        # 7. 重新计算排名
        logger.info("🧮 重新计算综合评分和排名...")
        ranked_scores = manual_completion.analyzer.calculate_composite_scores(updated_scores)
        
        # 8. 保存结果到 final_results 目录
        output_dir = output or app_config.storage.final_results_dir
        output_formats = [fmt.strip() for fmt in formats.split(',')]
        
        # 创建分析结果对象
        from src.models.anime import SeasonalAnalysis, Season
        
        # 从原文件名推断季度信息
        input_path = Path(input_file)
        if 'Summer_2025' in input_path.name:
            season = Season.SUMMER
            year = 2025
        else:
            season = Season.SUMMER  # 默认
            year = 2025
        
        analysis = SeasonalAnalysis(
            season=season,
            year=year,
            anime_scores=ranked_scores,
            analysis_date=datetime.now()
        )
        
        # 添加手动补全标记
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_suffix = f"_manual_completed_{timestamp}"

        manual_completion._save_analysis_results(analysis, output_dir, output_formats, filename_suffix)
        
        # 9. 显示最终统计
        website_counts = {}
        for anime_score in ranked_scores:
            count = len(anime_score.ratings)
            website_counts[count] = website_counts.get(count, 0) + 1
        
        print(f"\n📊 手动补全后的数据完整性统计:")
        for count in sorted(website_counts.keys()):
            percentage = website_counts[count] / len(ranked_scores) * 100
            print(f"   {count}个网站: {website_counts[count]}部动漫 ({percentage:.1f}%)")
        
        logger.info("🎉 手动数据补全完成！")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
