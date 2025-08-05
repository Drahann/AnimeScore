#!/usr/bin/env python3
"""
豆瓣数据后处理器
在主要分析完成后，独立运行豆瓣爬虫补充数据
"""
import asyncio
import json
import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import click
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.douban_enhanced import DoubanEnhancedScraper
from src.models.anime import WebsiteName, RatingData
from src.models.config import Config, WebsiteConfig
from src.core.scoring import ScoringEngine
import aiohttp


class DoubanPostProcessor:
    """豆瓣数据后处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scoring_engine = ScoringEngine(config)
        
        # 创建豆瓣爬虫配置 - 更保守的设置
        douban_config = WebsiteConfig(
            enabled=True,
            base_url="https://movie.douban.com",
            rate_limit=15.0,  # 15秒间隔，非常保守
            timeout=60        # 更长的超时时间
        )
        
        self.douban_scraper = DoubanEnhancedScraper(WebsiteName.DOUBAN, douban_config)
        
    def find_latest_results(self, results_dir: Path) -> Optional[Path]:
        """查找最新的分析结果文件"""
        # 优先查找JSON文件
        json_files = list(results_dir.glob("anime_ranking_*.json"))

        if json_files:
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"找到最新JSON结果文件: {latest_file}")
            return latest_file

        # 如果没有JSON文件，查找CSV文件
        csv_files = list(results_dir.glob("anime_ranking_*simple.csv"))

        if csv_files:
            latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
            logger.warning(f"未找到JSON文件，使用CSV文件: {latest_file}")
            logger.warning("注意: CSV文件功能有限，建议先运行完整分析生成JSON文件")
            return latest_file

        logger.error("未找到分析结果文件 (JSON或CSV)")
        return None
    
    def load_analysis_results(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载分析结果"""
        try:
            if file_path.suffix.lower() == '.json':
                return self._load_json_results(file_path)
            elif file_path.suffix.lower() == '.csv':
                return self._load_csv_results(file_path)
            else:
                logger.error(f"不支持的文件格式: {file_path.suffix}")
                return None

        except Exception as e:
            logger.error(f"加载分析结果失败: {e}")
            return None

    def _load_json_results(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON格式的分析结果"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"成功加载JSON文件: {len(data.get('rankings', []))} 条动漫数据")
        return data

    def _load_csv_results(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载CSV格式的分析结果并转换为JSON格式"""
        logger.info("正在从CSV文件加载数据...")

        rankings = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # 基本信息
                    anime = {
                        'rank': int(row.get('排名', 0)),
                        'title': row.get('中文名', ''),
                        'title_english': row.get('日文名', ''),
                        'composite_score': float(row.get('综合评分', 0)),
                        'ratings': []
                    }

                    # 解析各网站评分数据
                    websites = ['ANILIST', 'FILMARKS', 'IMDB', 'MAL', 'DOUBAN']

                    for website in websites:
                        score_key = f"{website}_评分"
                        votes_key = f"{website}_投票数"
                        rank_key = f"{website}_排名"

                        if score_key in row and row[score_key]:
                            try:
                                rating = {
                                    'website': website.lower(),
                                    'raw_score': float(row[score_key]),
                                    'vote_count': int(row.get(votes_key, 0)) if row.get(votes_key) else 0,
                                    'site_rank': int(row[rank_key]) if row.get(rank_key) else None,
                                    'bayesian_score': float(row[score_key]),
                                    'z_score': 0.0,
                                    'weight': 1.0,
                                    'site_percentile': None,
                                    'score_distribution': {},
                                    'last_updated': datetime.now().isoformat(),
                                    'url': ''
                                }
                                anime['ratings'].append(rating)
                            except (ValueError, TypeError):
                                continue

                    # 计算统计信息
                    anime['website_count'] = len(anime['ratings'])
                    anime['total_votes'] = sum(r.get('vote_count', 0) for r in anime['ratings'])
                    anime['percentile'] = 0.0  # 会重新计算

                    rankings.append(anime)

                except Exception as e:
                    logger.warning(f"解析CSV行时出错: {e}")
                    continue

        # 构建完整的数据结构
        data = {
            'rankings': rankings,
            'analysis_info': {
                'analyzed_anime_count': len(rankings),
                'timestamp': datetime.now().isoformat(),
                'source': 'csv_import'
            }
        }

        logger.info(f"成功从CSV加载 {len(rankings)} 条动漫数据")
        return data
    
    def identify_missing_douban_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别缺少豆瓣数据的动漫"""
        missing_douban = []
        
        for anime in data.get('rankings', []):
            has_douban = False
            
            # 检查是否已有豆瓣评分
            for rating in anime.get('ratings', []):
                if rating.get('website') == 'douban':
                    has_douban = True
                    break
            
            if not has_douban:
                missing_douban.append(anime)
        
        logger.info(f"发现 {len(missing_douban)} 个动漫缺少豆瓣数据")
        return missing_douban
    
    async def search_douban_with_patience(self, session: aiohttp.ClientSession, 
                                        anime_title: str, max_attempts: int = 3) -> Optional[str]:
        """耐心搜索豆瓣ID"""
        logger.info(f"🔍 搜索豆瓣数据: {anime_title}")
        
        for attempt in range(max_attempts):
            try:
                # 尝试多种搜索策略
                strategies = [
                    lambda: self.douban_scraper.search_anime_alternative_sites(session, anime_title),
                    lambda: self.douban_scraper.search_anime_with_mobile_api(session, anime_title),
                    lambda: self.douban_scraper._try_original_search(session, anime_title)
                ]
                
                for i, strategy in enumerate(strategies):
                    logger.info(f"   尝试策略 {i+1}: {strategy.__name__ if hasattr(strategy, '__name__') else f'策略{i+1}'}")
                    
                    try:
                        results = await strategy()
                        if results:
                            douban_id = results[0].external_ids.get(WebsiteName.DOUBAN)
                            if douban_id:
                                logger.info(f"   ✅ 找到豆瓣ID: {douban_id}")
                                return douban_id
                    except Exception as e:
                        logger.warning(f"   策略 {i+1} 失败: {e}")
                        continue
                
                # 如果所有策略都失败，等待更长时间再重试
                if attempt < max_attempts - 1:
                    wait_time = 30 * (attempt + 1)  # 30秒, 60秒, 90秒
                    logger.info(f"   等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"搜索豆瓣ID时出错: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(60)  # 出错后等待1分钟
        
        logger.warning(f"❌ 无法找到豆瓣数据: {anime_title}")
        return None
    
    async def get_douban_rating_with_patience(self, session: aiohttp.ClientSession, 
                                            douban_id: str) -> Optional[RatingData]:
        """耐心获取豆瓣评分"""
        logger.info(f"📊 获取豆瓣评分: {douban_id}")
        
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                rating = await self.douban_scraper.get_anime_rating(session, douban_id)
                if rating:
                    logger.info(f"   ✅ 获取成功: {rating.raw_score} ({rating.vote_count} 票)")
                    return rating
                else:
                    logger.warning(f"   尝试 {attempt+1}/{max_attempts} 失败")
                    
            except Exception as e:
                logger.error(f"获取豆瓣评分时出错: {e}")
            
            # 逐渐增加等待时间
            if attempt < max_attempts - 1:
                wait_time = 20 * (attempt + 1)  # 20秒, 40秒, 60秒, 80秒
                logger.info(f"   等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"❌ 无法获取豆瓣评分: {douban_id}")
        return None
    
    async def process_douban_data(self, data: Dict[str, Any], 
                                max_anime: Optional[int] = None) -> Dict[str, Any]:
        """处理豆瓣数据补全"""
        missing_douban = self.identify_missing_douban_data(data)
        
        if not missing_douban:
            logger.info("所有动漫都已有豆瓣数据")
            return data
        
        # 限制处理数量
        if max_anime:
            missing_douban = missing_douban[:max_anime]
            logger.info(f"限制处理数量为 {max_anime} 个动漫")
        
        successful_additions = 0
        
        async with aiohttp.ClientSession() as session:
            logger.info("🚀 开始豆瓣数据补全...")
            
            for i, anime in enumerate(missing_douban, 1):
                anime_title = anime.get('title', '未知')
                logger.info(f"\n📺 处理 {i}/{len(missing_douban)}: {anime_title}")
                
                try:
                    # 搜索豆瓣ID
                    douban_id = await self.search_douban_with_patience(session, anime_title)
                    
                    if douban_id:
                        # 获取评分数据
                        rating_data = await self.get_douban_rating_with_patience(session, douban_id)
                        
                        if rating_data:
                            # 添加到动漫数据中
                            if 'ratings' not in anime:
                                anime['ratings'] = []
                            
                            # 转换为字典格式
                            rating_dict = {
                                'website': 'douban',
                                'raw_score': rating_data.raw_score,
                                'vote_count': rating_data.vote_count,
                                'score_distribution': rating_data.score_distribution or {},
                                'bayesian_score': rating_data.raw_score,  # 临时值，会重新计算
                                'z_score': 0.0,  # 会重新计算
                                'weight': 1.0,   # 会重新计算
                                'site_rank': None,  # 会重新计算
                                'site_percentile': None,
                                'last_updated': datetime.now().isoformat(),
                                'url': rating_data.url
                            }
                            
                            anime['ratings'].append(rating_dict)
                            anime['website_count'] = len(anime['ratings'])
                            anime['total_votes'] = sum(r.get('vote_count', 0) for r in anime['ratings'])
                            
                            successful_additions += 1
                            logger.info(f"   ✅ 成功添加豆瓣数据")
                        
                    # 在每个动漫之间添加长时间延迟
                    if i < len(missing_douban):
                        wait_time = 45  # 45秒间隔
                        logger.info(f"⏳ 等待 {wait_time} 秒...")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"处理动漫 {anime_title} 时出错: {e}")
                    continue
        
        logger.info(f"🎉 豆瓣数据补全完成: 成功添加 {successful_additions} 条数据")
        
        # 重新计算评分和排名
        if successful_additions > 0:
            logger.info("🔄 重新计算评分和排名...")
            self.recalculate_scores_and_rankings(data)
        
        return data
    
    def recalculate_scores_and_rankings(self, data: Dict[str, Any]):
        """重新计算评分和排名"""
        try:
            # 重新计算综合评分
            for anime in data['rankings']:
                if anime.get('ratings'):
                    # 使用评分引擎重新计算
                    ratings = []
                    for rating_dict in anime['ratings']:
                        rating_data = RatingData(
                            website=WebsiteName(rating_dict['website']),
                            raw_score=rating_dict['raw_score'],
                            vote_count=rating_dict['vote_count'],
                            score_distribution=rating_dict.get('score_distribution', {}),
                            last_updated=datetime.now(),
                            url=rating_dict.get('url', '')
                        )
                        ratings.append(rating_data)
                    
                    # 重新计算综合评分
                    composite_score = self.scoring_engine.calculate_composite_score(ratings)
                    anime['composite_score'] = composite_score
            
            # 重新排序
            data['rankings'].sort(key=lambda x: x.get('composite_score', 0), reverse=True)
            
            # 重新分配排名
            for i, anime in enumerate(data['rankings'], 1):
                anime['rank'] = i
                anime['percentile'] = (len(data['rankings']) - i + 1) / len(data['rankings']) * 100
            
            # 重新计算网站排名
            self.recalculate_site_rankings(data)
            
            logger.info("✅ 评分和排名重新计算完成")
            
        except Exception as e:
            logger.error(f"重新计算评分时出错: {e}")
    
    def recalculate_site_rankings(self, data: Dict[str, Any]):
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
            if len(anime_ratings) < 2:
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
    
    def save_updated_results(self, data: Dict[str, Any], original_file: Path) -> List[Path]:
        """保存更新后的结果"""
        saved_files = []
        
        # 生成新的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = original_file.stem.replace("_simple", "").replace("_detailed", "")
        
        # 保存JSON
        json_file = original_file.parent / f"{base_name}_douban_{timestamp}.json"
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            saved_files.append(json_file)
            logger.info(f"✅ 保存JSON: {json_file}")
        except Exception as e:
            logger.error(f"保存JSON失败: {e}")
        
        # 保存简化CSV
        csv_file = original_file.parent / f"{base_name}_douban_{timestamp}_simple.csv"
        try:
            self.save_simple_csv(data, csv_file)
            saved_files.append(csv_file)
            logger.info(f"✅ 保存CSV: {csv_file}")
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")
        
        return saved_files

    def save_simple_csv(self, data: Dict[str, Any], csv_path: Path):
        """保存简化版CSV"""
        # 获取所有启用的网站
        enabled_websites = set()
        for anime in data['rankings']:
            for rating in anime.get('ratings', []):
                enabled_websites.add(rating['website'])

        enabled_websites = sorted(list(enabled_websites))

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 构建表头
            headers = ['排名', '中文名', '日文名', '综合评分']

            # 添加各网站的评分、投票数和排名列
            for website in enabled_websites:
                headers.extend([
                    f"{website.upper()}_评分",
                    f"{website.upper()}_投票数",
                    f"{website.upper()}_排名"
                ])

            writer.writerow(headers)

            # 写入数据行
            for anime in data['rankings']:
                row = [
                    anime['rank'],
                    anime['title'],
                    anime.get('title_english', anime['title']),
                    anime['composite_score']
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


@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='配置文件路径')
@click.option('--input', '-i', default=None,
              help='输入的分析结果文件路径 (默认: 自动查找最新文件)')
@click.option('--max-anime', '-m', type=int, default=None,
              help='最大处理动漫数量 (用于测试)')
@click.option('--verbose', '-v', is_flag=True,
              help='启用详细日志')
def main(config, input, max_anime, verbose):
    """豆瓣数据后处理器 - 为现有分析结果补充豆瓣数据"""

    # 设置日志
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )

    logger.info("🎭 豆瓣数据后处理器启动")
    logger.info("=" * 60)

    try:
        # 加载配置
        app_config = Config.load_from_file(config)

        # 创建后处理器
        processor = DoubanPostProcessor(app_config)

        # 查找输入文件
        if input:
            input_file = Path(input)
            if not input_file.exists():
                logger.error(f"输入文件不存在: {input_file}")
                return
        else:
            results_dir = Path(app_config.storage.results_dir)
            input_file = processor.find_latest_results(results_dir)
            if not input_file:
                return

        # 加载分析结果
        data = processor.load_analysis_results(input_file)
        if not data:
            return

        # 显示当前状态
        total_anime = len(data.get('rankings', []))
        missing_douban = processor.identify_missing_douban_data(data)

        logger.info(f"📊 当前状态:")
        logger.info(f"   总动漫数: {total_anime}")
        logger.info(f"   缺少豆瓣数据: {len(missing_douban)}")

        if not missing_douban:
            logger.info("🎉 所有动漫都已有豆瓣数据，无需处理")
            return

        # 确认处理
        if max_anime:
            process_count = min(max_anime, len(missing_douban))
        else:
            process_count = len(missing_douban)

        logger.info(f"⚠️ 即将处理 {process_count} 个动漫的豆瓣数据")
        logger.info(f"⏱️ 预计耗时: {process_count * 1.5:.1f} 分钟 (每个动漫约1.5分钟)")

        if not max_anime:  # 只有在非测试模式下才询问确认
            confirm = input("\n是否继续? (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("❌ 用户取消操作")
                return

        # 开始处理
        logger.info(f"\n🚀 开始豆瓣数据补全...")

        # 运行异步处理
        updated_data = asyncio.run(processor.process_douban_data(data, max_anime))

        # 保存结果
        logger.info(f"\n💾 保存更新后的结果...")
        saved_files = processor.save_updated_results(updated_data, input_file)

        logger.info(f"\n🎉 豆瓣数据后处理完成!")
        logger.info(f"📁 生成文件:")
        for file_path in saved_files:
            logger.info(f"   - {file_path}")

        # 显示统计信息
        final_missing = processor.identify_missing_douban_data(updated_data)
        added_count = len(missing_douban) - len(final_missing)

        logger.info(f"\n📈 处理统计:")
        logger.info(f"   成功添加豆瓣数据: {added_count}")
        logger.info(f"   仍缺少豆瓣数据: {len(final_missing)}")
        logger.info(f"   成功率: {added_count/len(missing_douban)*100:.1f}%")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ 用户中断操作")
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
