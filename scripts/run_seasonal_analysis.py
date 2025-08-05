#!/usr/bin/env python3
"""
运行季度动漫评分分析的主脚本
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import click
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.config import Config
from src.models.anime import Season
from src.core.analyzer import AnimeAnalyzer
from src.utils.season_utils import get_current_season, parse_season_string


def setup_logging(config: Config):
    """设置日志"""
    # 确保日志目录存在
    log_file = Path(config.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置 loguru
    logger.remove()  # 移除默认处理器
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 添加文件输出
    logger.add(
        config.logging.file,
        level=config.logging.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=config.logging.max_file_size,
        retention=config.logging.backup_count
    )


def save_results(analysis, output_dir: Path, formats: list):
    """保存分析结果"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    season_str = f"{analysis.season.value}_{analysis.year}"
    base_filename = f"anime_ranking_{season_str}_{timestamp}"
    
    # 准备数据
    results_data = {
        "analysis_info": {
            "season": analysis.season.value,
            "year": analysis.year,
            "analysis_date": analysis.analysis_date.isoformat(),
            "total_anime_count": analysis.total_anime_count,
            "analyzed_anime_count": analysis.analyzed_anime_count
        },
        "rankings": []
    }
    
    for anime_score in analysis.anime_scores:
        if anime_score.composite_score:
            anime_data = {
                "rank": anime_score.composite_score.rank,
                "title": anime_score.anime_info.title,
                "title_english": anime_score.anime_info.title_english,
                "title_japanese": anime_score.anime_info.title_japanese,
                "title_chinese": anime_score.anime_info.title_chinese,
                "composite_score": round(anime_score.composite_score.final_score, 3),
                "confidence": round(anime_score.composite_score.confidence, 3),
                "total_votes": anime_score.composite_score.total_votes,
                "website_count": anime_score.composite_score.website_count,
                "percentile": round(anime_score.composite_score.percentile, 1),
                "anime_type": anime_score.anime_info.anime_type.value if anime_score.anime_info.anime_type else None,
                "episodes": anime_score.anime_info.episodes,
                "start_date": anime_score.anime_info.start_date.isoformat() if anime_score.anime_info.start_date else None,
                "studios": anime_score.anime_info.studios,
                "genres": anime_score.anime_info.genres,
                "poster_image": anime_score.anime_info.poster_image,
                "cover_image": anime_score.anime_info.cover_image,
                "banner_image": anime_score.anime_info.banner_image,
                "ratings": []
            }
            
            # 添加各网站评分详情
            for rating in anime_score.ratings:
                if rating.raw_score is not None:
                    rating_data = {
                        "website": rating.website.value,
                        "raw_score": rating.raw_score,
                        "bayesian_score": round(rating.bayesian_score, 3) if rating.bayesian_score else None,
                        "z_score": round(rating.z_score, 3) if rating.z_score else None,
                        "vote_count": rating.vote_count,
                        "weight": round(rating.weight, 3) if rating.weight else None,
                        "site_rank": rating.site_rank,
                        "site_percentile": round(rating.site_percentile, 1) if rating.site_percentile else None,
                        "url": rating.url
                    }
                    anime_data["ratings"].append(rating_data)
            
            results_data["rankings"].append(anime_data)
    
    # 保存为不同格式
    if "json" in formats:
        json_file = output_dir / f"{base_filename}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {json_file}")
    
    if "csv" in formats:
        try:
            import pandas as pd
            
            # 创建简化的CSV数据
            csv_data = []
            for anime_data in results_data["rankings"]:
                row = {
                    "排名": anime_data["rank"],
                    "标题": anime_data["title"],
                    "英文标题": anime_data["title_english"],
                    "日文标题": anime_data["title_japanese"],
                    "综合评分": anime_data["composite_score"],
                    "置信度": anime_data["confidence"],
                    "总投票数": anime_data["total_votes"],
                    "网站数量": anime_data["website_count"],
                    "百分位数": anime_data["percentile"],
                    "类型": anime_data["anime_type"],
                    "集数": anime_data["episodes"],
                    "开播日期": anime_data["start_date"],
                    "制作公司": ", ".join(anime_data["studios"]) if anime_data["studios"] else "",
                    "类型标签": ", ".join(anime_data["genres"]) if anime_data["genres"] else ""
                }
                
                # 添加各网站评分
                for rating in anime_data["ratings"]:
                    website = rating["website"]
                    row[f"{website}_评分"] = rating["raw_score"]
                    row[f"{website}_投票数"] = rating["vote_count"]
                    row[f"{website}_排名"] = rating.get("site_rank", "")
                
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            csv_file = output_dir / f"{base_filename}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            logger.info(f"Results saved to {csv_file}")
            
        except ImportError:
            logger.warning("pandas not available, skipping CSV export")
    
    if "xlsx" in formats:
        try:
            import pandas as pd
            
            # 使用与CSV相同的数据
            csv_data = []
            for anime_data in results_data["rankings"]:
                row = {
                    "排名": anime_data["rank"],
                    "标题": anime_data["title"],
                    "英文标题": anime_data["title_english"],
                    "日文标题": anime_data["title_japanese"],
                    "综合评分": anime_data["composite_score"],
                    "置信度": anime_data["confidence"],
                    "总投票数": anime_data["total_votes"],
                    "网站数量": anime_data["website_count"],
                    "百分位数": anime_data["percentile"],
                    "类型": anime_data["anime_type"],
                    "集数": anime_data["episodes"],
                    "开播日期": anime_data["start_date"],
                    "制作公司": ", ".join(anime_data["studios"]) if anime_data["studios"] else "",
                    "类型标签": ", ".join(anime_data["genres"]) if anime_data["genres"] else ""
                }
                
                # 添加各网站评分
                for rating in anime_data["ratings"]:
                    website = rating["website"]
                    row[f"{website}_评分"] = rating["raw_score"]
                    row[f"{website}_投票数"] = rating["vote_count"]
                    row[f"{website}_排名"] = rating.get("site_rank", "")
                
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            xlsx_file = output_dir / f"{base_filename}.xlsx"
            df.to_excel(xlsx_file, index=False, engine='openpyxl')
            logger.info(f"Results saved to {xlsx_file}")
            
        except ImportError:
            logger.warning("pandas or openpyxl not available, skipping Excel export")

    # 简化版CSV输出
    if "simple_csv" in formats:
        save_simple_csv(analysis, output_dir, base_filename)


def save_simple_csv(analysis, output_dir: Path, base_filename: str):
    """保存简化版CSV - 只包含核心信息"""
    import csv

    simple_csv_file = output_dir / f"{base_filename}_simple.csv"

    # 获取所有启用的网站
    enabled_websites = set()
    for anime_score in analysis.anime_scores:
        if anime_score.composite_score:
            for rating in anime_score.ratings:
                if rating.raw_score is not None:
                    enabled_websites.add(rating.website.value)

    enabled_websites = sorted(list(enabled_websites))

    with open(simple_csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 构建表头
        headers = ["排名", "中文名", "日文名", "英文名", "综合评分", "海报图片", "横幅图片"]

        # 添加各网站的评分、投票数和排名列
        for website in enabled_websites:
            headers.extend([f"{website.upper()}_评分", f"{website.upper()}_投票数", f"{website.upper()}_排名"])

        writer.writerow(headers)

        # 写入数据
        for anime_score in analysis.anime_scores:
            if anime_score.composite_score:
                # 基础信息
                # 优先显示中文名，如果没有则显示原标题
                chinese_title = anime_score.anime_info.title_chinese or anime_score.anime_info.title

                row = [
                    anime_score.composite_score.rank,
                    chinese_title,  # 中文名
                    anime_score.anime_info.title_japanese or "",  # 日文名
                    anime_score.anime_info.title_english or "",  # 英文名
                    round(anime_score.composite_score.final_score, 3),  # 综合评分
                    anime_score.anime_info.poster_image or "",  # 海报图片
                    anime_score.anime_info.banner_image or ""   # 横幅图片
                ]

                # 创建网站评分字典
                website_ratings = {}
                for rating in anime_score.ratings:
                    if rating.raw_score is not None:
                        website_ratings[rating.website.value] = {
                            'score': rating.raw_score,
                            'votes': rating.vote_count or 0,
                            'rank': rating.site_rank
                        }

                # 添加各网站的评分、投票数和排名
                for website in enabled_websites:
                    if website in website_ratings:
                        row.extend([
                            website_ratings[website]['score'],
                            website_ratings[website]['votes'],
                            website_ratings[website]['rank'] or ""
                        ])
                    else:
                        row.extend(["", "", ""])

                writer.writerow(row)

    logger.info(f"Simple CSV results saved to {simple_csv_file}")


@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='Configuration file path')
@click.option('--season', '-s', default=None,
              help='Season to analyze (e.g., "2024-1" or "Winter 2024")')
@click.option('--output', '-o', default=None,
              help='Output directory (default: from config)')
@click.option('--formats', '-f', default='json,csv,simple_csv',
              help='Output formats (comma-separated: json,csv,xlsx,simple_csv)')
@click.option('--completion/--no-completion', default=None,
              help='Enable/disable data completion (default: from config)')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose logging')
def main(config, season, output, formats, completion, verbose):
    """运行季度动漫评分分析"""
    
    try:
        # 加载配置
        app_config = Config.load_from_file(config)
        
        # 设置日志
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        # 确保必要目录存在
        app_config.ensure_directories()
        
        logger.info("Starting AnimeScore seasonal analysis")
        
        # 解析季度
        if season:
            target_season, target_year = parse_season_string(season)
        else:
            target_season, target_year = get_current_season()
        
        logger.info(f"Analyzing {target_season.value} {target_year}")
        
        # 创建分析器
        analyzer = AnimeAnalyzer(app_config)
        
        # 检查爬虫状态
        scraper_status = analyzer.get_scraper_status()
        logger.info(f"Scraper status: {scraper_status}")
        
        if not any(scraper_status.values()):
            logger.error("No scrapers are enabled! Please check your configuration.")
            return
        
        # 确定是否启用数据补全
        enable_completion = completion if completion is not None else app_config.data_completion.enabled

        logger.info(f"Data completion: {'enabled' if enable_completion else 'disabled'}")

        # 运行分析
        async def run_analysis():
            return await analyzer.analyze_season_with_completion(
                target_season, target_year, enable_completion=enable_completion
            )

        analysis = asyncio.run(run_analysis())
        
        # 保存结果
        output_dir = Path(output) if output else Path(app_config.storage.results_dir)
        output_formats = [f.strip() for f in formats.split(',')]
        
        save_results(analysis, output_dir, output_formats)
        
        # 显示前10名
        logger.info("\n=== TOP 10 ANIME ===")
        top_anime = analysis.get_top_anime(10)
        for i, anime_score in enumerate(top_anime, 1):
            score = anime_score.composite_score
            logger.info(f"{i:2d}. {anime_score.anime_info.title} "
                       f"(Score: {score.final_score:.3f}, "
                       f"Confidence: {score.confidence:.3f}, "
                       f"Votes: {score.total_votes})")
        
        logger.info("Analysis completed successfully!")
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
