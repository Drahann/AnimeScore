#!/usr/bin/env python3
"""
重新计算权重脚本
用于基于现有JSON文件重新计算综合评分和排名，使用新的权重配置
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

class WeightRecalculator:
    """权重重新计算器"""
    
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
                try:
                    website = WebsiteName(rating['website'])
                except ValueError:
                    logger.warning(f"未知网站: {rating['website']}")
                    continue
                    
                rating_data = RatingData(
                    website=website,
                    raw_score=rating['raw_score'],
                    vote_count=rating['vote_count'],
                    site_rank=rating.get('site_rank', 0),
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
    
    def save_recalculated_results(self, analysis, output_dir: str, output_formats: List[str]):
        """保存重新计算后的结果"""
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        season_str = f"{analysis.season.value}_{analysis.year}"
        base_filename = f"anime_ranking_{season_str}_weights_recalculated_{timestamp}"
        
        # 准备数据
        results_data = {
            "analysis_info": {
                "season": analysis.season.value,
                "year": analysis.year,
                "analysis_date": analysis.analysis_date.isoformat(),
                "total_anime_count": analysis.total_anime_count,
                "analyzed_anime_count": analysis.analyzed_anime_count,
                "weights_recalculated": True,
                "recalculation_date": datetime.now().isoformat(),
                "platform_weights": dict(self.config.model.platform_weights)
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
                "anime_type": anime_score.anime_info.anime_type.value if anime_score.anime_info.anime_type else None,
                "episodes": anime_score.anime_info.episodes,
                "start_date": start_date,
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
            
            # 添加评分数据
            for rating in anime_score.ratings:
                rating_data = {
                    "website": rating.website.value,
                    "raw_score": rating.raw_score,
                    "vote_count": rating.vote_count,
                    "site_rank": rating.site_rank,
                    "url": rating.url
                }
                anime_data["ratings"].append(rating_data)
            
            results_data["rankings"].append(anime_data)
        
        # 保存JSON文件
        if 'json' in output_formats:
            json_file = output_path / f"{base_filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to {json_file}")
        
        # 保存CSV文件
        if 'csv' in output_formats:
            csv_file = output_path / f"{base_filename}.csv"
            self._save_csv(results_data, csv_file)
            logger.info(f"CSV results saved to {csv_file}")
    
    def _save_csv(self, results_data: dict, csv_file: Path):
        """保存CSV格式的结果"""
        import csv
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            headers = ['Rank', 'Title', 'Title_English', 'Title_Japanese', 'Type', 'Episodes', 
                      'Start_Date', 'Studios', 'Genres', 'Composite_Score', 'Confidence', 
                      'Total_Votes', 'Website_Count']
            
            # 添加网站评分列
            websites = ['ANILIST', 'BANGUMI', 'DOUBAN', 'FILMARKS', 'IMDB', 'MAL']
            for website in websites:
                headers.extend([f'{website}_Score', f'{website}_Votes'])
            
            writer.writerow(headers)
            
            # 写入数据
            for ranking in results_data['rankings']:
                row = [
                    ranking['rank'],
                    ranking['title'],
                    ranking.get('title_english', ''),
                    ranking.get('title_japanese', ''),
                    ranking.get('anime_type', ''),
                    ranking.get('episodes', ''),
                    ranking.get('start_date', ''),
                    ', '.join(ranking.get('studios', [])),
                    ', '.join(ranking.get('genres', [])),
                    round(ranking['composite_score'], 6),
                    round(ranking['confidence'], 6),
                    ranking['total_votes'],
                    ranking['website_count']
                ]
                
                # 添加网站评分数据
                rating_dict = {r['website'].upper(): r for r in ranking['ratings']}
                for website in websites:
                    if website in rating_dict:
                        row.extend([rating_dict[website]['raw_score'], rating_dict[website]['vote_count']])
                    else:
                        row.extend(['', ''])
                
                writer.writerow(row)

@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='配置文件路径')
@click.option('--input', '-i', required=True,
              help='输入的分析结果JSON文件路径')
@click.option('--output', '-o', default=None,
              help='输出目录 (默认: final_results目录)')
@click.option('--formats', '-f', default='json,csv',
              help='输出格式 (逗号分隔: json,csv)')
@click.option('--verbose', '-v', is_flag=True,
              help='启用详细日志')
def main(config, input, output, formats, verbose):
    """权重重新计算程序"""
    
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("⚖️ 启动权重重新计算程序")
    
    try:
        # 1. 加载配置
        app_config = Config.load_from_file(config)
        logger.info(f"✅ 配置加载成功: {config}")
        logger.info(f"📊 当前平台权重: {dict(app_config.model.platform_weights)}")
        
        # 2. 创建权重重新计算器
        recalculator = WeightRecalculator(app_config)
        
        # 3. 加载分析结果
        anime_scores = recalculator.load_analysis_results(input)
        
        # 4. 重新计算综合评分和排名
        logger.info("🔄 使用新权重重新计算综合评分和排名...")
        analyzer = AnimeAnalyzer(app_config)

        # 重新计算综合评分
        ranked_scores = analyzer.calculate_composite_scores(anime_scores)

        # 创建分析结果
        from src.models.anime import SeasonalAnalysis
        analysis = SeasonalAnalysis(
            season=Season.SUMMER,
            year=2025,
            anime_scores=ranked_scores,
            total_anime_count=len(anime_scores),
            analyzed_anime_count=len(ranked_scores)
        )
        
        # 5. 保存结果到 final_results 目录
        output_dir = output or app_config.storage.final_results_dir
        output_formats = [fmt.strip() for fmt in formats.split(',')]
        
        recalculator.save_recalculated_results(analysis, output_dir, output_formats)
        
        logger.success("🎉 权重重新计算完成！")
        logger.info(f"📁 结果已保存到: {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
