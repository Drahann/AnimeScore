"""
动漫评分分析器 - 整合各网站数据并计算综合评分
"""
import asyncio
import aiohttp
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..models.anime import AnimeScore, AnimeInfo, RatingData, SeasonalAnalysis, Season, WebsiteName
from ..models.config import Config
from ..scrapers.base import ScraperFactory
from ..utils.season_utils import get_current_season, get_season_date_range, is_anime_in_season
from ..utils.anime_filter import create_default_filter
from .scoring import ScoringEngine
from .data_completion import DataCompletion


class AnimeAnalyzer:
    """动漫评分分析器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scoring_engine = ScoringEngine(config)
        self.anime_filter = create_default_filter(config)
        self.scrapers = {}
        self._initialize_scrapers()
        self.data_completion = DataCompletion(config, self.scrapers)
    
    def _initialize_scrapers(self):
        """初始化所有启用的爬虫"""
        for website_name in self.config.get_enabled_websites():
            try:
                website_enum = WebsiteName(website_name)
                website_config = self.config.get_website_config(website_name)
                api_keys = self.config.api_keys.__dict__.get(website_name, {})
                
                scraper = ScraperFactory.create_scraper(
                    website_enum, website_config, api_keys
                )
                
                if scraper:
                    self.scrapers[website_enum] = scraper
                    logger.info(f"Initialized scraper for {website_name}")
                else:
                    logger.warning(f"Failed to initialize scraper for {website_name}")
                    
            except ValueError:
                logger.error(f"Unknown website: {website_name}")
            except Exception as e:
                logger.error(f"Error initializing scraper for {website_name}: {e}")
    
    async def get_seasonal_anime_list(self, season: Season, year: int) -> List[AnimeInfo]:
        """获取指定季度的动漫列表"""
        all_anime = []
        anime_dict = {}  # 用于去重，key为标题，value为AnimeInfo
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for website_name, scraper in self.scrapers.items():
                if scraper.is_enabled():
                    task = self._get_seasonal_anime_from_scraper(
                        session, scraper, year, season.value
                    )
                    tasks.append((website_name, task))
            
            # 并发获取各网站数据
            for website_name, task in tasks:
                try:
                    anime_list = await task
                    logger.info(f"Got {len(anime_list)} anime from {website_name}")
                    
                    for anime in anime_list:
                        # 简单的去重逻辑，基于标题
                        key = anime.title.lower().strip()
                        if key not in anime_dict:
                            anime_dict[key] = anime
                        else:
                            # 合并外部ID和其他信息
                            existing = anime_dict[key]
                            logger.debug(f"🔄 合并重复动漫: {anime.title} (来自 {website_name})")
                            existing.external_ids.update(anime.external_ids)

                            # 合并标题信息
                            if anime.title_english and not existing.title_english:
                                logger.debug(f"   📝 添加英文标题: {anime.title_english}")
                                existing.title_english = anime.title_english
                            if anime.title_japanese and not existing.title_japanese:
                                logger.debug(f"   📝 添加日文标题: {anime.title_japanese}")
                                existing.title_japanese = anime.title_japanese
                            if anime.title_chinese and not existing.title_chinese:
                                logger.info(f"   🇨🇳 添加中文标题: '{existing.title}' -> '{anime.title_chinese}' (来自 {website_name})")
                                existing.title_chinese = anime.title_chinese
                            elif anime.title_chinese and existing.title_chinese:
                                logger.debug(f"   🇨🇳 中文标题已存在: {existing.title_chinese}")
                            elif not anime.title_chinese:
                                logger.debug(f"   🇨🇳 {website_name} 无中文标题")

                            # 合并图片信息
                            if anime.poster_image and not existing.poster_image:
                                logger.debug(f"   🖼️ 添加海报图片: {anime.poster_image[:50]}...")
                                existing.poster_image = anime.poster_image
                            if anime.cover_image and not existing.cover_image:
                                existing.cover_image = anime.cover_image
                            if anime.banner_image and not existing.banner_image:
                                logger.debug(f"   🖼️ 添加横幅图片: {anime.banner_image[:50]}...")
                                existing.banner_image = anime.banner_image
                            
                except Exception as e:
                    logger.error(f"Error getting seasonal anime from {website_name}: {e}")
        
        all_anime = list(anime_dict.values())

        # 去重
        deduplicated_anime = self.anime_filter.deduplicate_anime(all_anime)

        # 筛选季度新番
        filtered_anime = self.anime_filter.filter_seasonal_anime(
            deduplicated_anime, season, year, self.config.seasonal.season_buffer_days
        )

        # 按开始日期排序
        sorted_anime = self.anime_filter.sort_by_start_date(filtered_anime)

        logger.info(f"Found {len(sorted_anime)} anime for {season.value} {year} "
                   f"after filtering and sorting")

        return sorted_anime
    
    async def _get_seasonal_anime_from_scraper(self, session: aiohttp.ClientSession,
                                             scraper, year: int, season: str) -> List[AnimeInfo]:
        """从单个爬虫获取季度动漫"""
        try:
            return await scraper.get_seasonal_anime(session, year, season)
        except Exception as e:
            logger.error(f"Error in scraper {scraper.website_name}: {e}")
            return []

    def _build_search_terms(self, anime: AnimeInfo) -> List[str]:
        """构建搜索词列表（优先日文标题）- 通用方法"""
        search_terms = []

        # 1. 日文标题（最高优先级）
        if anime.title_japanese:
            search_terms.append(anime.title_japanese)
            # 去掉一些可能的修饰词
            simplified_japanese = anime.title_japanese.replace('第2期', '').replace('第２期', '').replace('2nd Season', '').strip()
            if simplified_japanese != anime.title_japanese:
                search_terms.append(simplified_japanese)

        # 2. 英文标题
        if anime.title_english:
            search_terms.append(anime.title_english)

        # 3. 别名
        if anime.alternative_titles:
            search_terms.extend(anime.alternative_titles[:2])  # 只取前2个别名

        # 4. 原始标题（罗马音）
        search_terms.append(anime.title)

        # 去重并保持顺序
        unique_search_terms = []
        for term in search_terms:
            if term and term not in unique_search_terms:
                unique_search_terms.append(term)

        return unique_search_terms

    async def improved_bangumi_search(self, session: aiohttp.ClientSession, anime_title: str, anilist_anime=None):
        """改进的Bangumi搜索 - 优先使用日文标题"""
        bangumi_scraper = self.scrapers.get(WebsiteName.BANGUMI)
        if not bangumi_scraper:
            return None

        # 如果没有AniList数据，先获取
        if not anilist_anime:
            anilist_scraper = self.scrapers.get(WebsiteName.ANILIST)
            if anilist_scraper:
                anilist_results = await anilist_scraper.search_anime(session, anime_title)
                if anilist_results:
                    anilist_anime = anilist_results[0]

        # 如果还是没有AniList数据，创建一个基本的AnimeInfo对象
        if not anilist_anime:
            anilist_anime = AnimeInfo(title=anime_title)

        # 使用通用搜索策略
        search_terms = self._build_search_terms(anilist_anime)

        # 逐个尝试搜索Bangumi
        for search_term in search_terms:
            try:
                logger.debug(f"Trying Bangumi search with term: '{search_term}'")
                bangumi_results = await bangumi_scraper.search_anime(session, search_term)

                if bangumi_results:
                    logger.info(f"✅ Bangumi search successful with term: '{search_term}'")
                    return bangumi_results[0]

            except Exception as e:
                logger.warning(f"Bangumi search error with term '{search_term}': {e}")

            # 等待间隔
            await asyncio.sleep(0.5)

        logger.debug(f"Bangumi search failed for all terms: {search_terms}")
        return None
    
    async def collect_anime_ratings(self, anime_list: List[AnimeInfo]) -> List[AnimeScore]:
        """收集动漫评分数据"""
        anime_scores = []

        async with aiohttp.ClientSession() as session:
            for anime in anime_list:
                logger.info(f"Collecting ratings for: {anime.title}")

                anime_score = AnimeScore(anime_info=anime)

                # 从各个网站收集评分
                for website_name, scraper in self.scrapers.items():
                    if not scraper.is_enabled():
                        continue

                    # 获取该网站的动漫ID
                    anime_id = anime.external_ids.get(website_name)
                    if not anime_id:
                        # 如果没有直接的ID，尝试搜索（使用优化的搜索策略）
                        anime_id = await self._search_anime_id_with_fallback(
                            session, scraper, anime
                        )
                        if anime_id:
                            anime.external_ids[website_name] = anime_id

                    if anime_id:
                        rating_data = await self._get_rating_from_scraper(
                            session, scraper, anime_id
                        )
                        if rating_data:
                            anime_score.add_or_update_rating(rating_data)

                anime_scores.append(anime_score)

        return anime_scores
    
    async def _search_anime_id(self, session: aiohttp.ClientSession,
                             scraper, title: str) -> Optional[str]:
        """搜索动漫ID"""
        try:
            search_results = await scraper.search_anime(session, title)
            if search_results:
                # 返回第一个结果的ID
                first_result = search_results[0]
                return first_result.external_ids.get(scraper.website_name)
        except Exception as e:
            logger.warning(f"Search failed for '{title}' on {scraper.website_name}: {e}")

        return None

    async def _search_anime_id_with_fallback(self, session: aiohttp.ClientSession,
                                           scraper, anime: AnimeInfo) -> Optional[str]:
        """使用多种搜索策略搜索动漫ID（优先日文标题）"""
        # 使用通用搜索策略
        search_terms = self._build_search_terms(anime)

        # 逐个尝试搜索
        for search_term in search_terms:
            try:
                logger.debug(f"Trying search term '{search_term}' on {scraper.website_name}")
                search_results = await scraper.search_anime(session, search_term)
                if search_results:
                    # 返回第一个结果的ID
                    first_result = search_results[0]
                    anime_id = first_result.external_ids.get(scraper.website_name)
                    if anime_id:
                        logger.info(f"✅ Found anime ID '{anime_id}' using search term '{search_term}' on {scraper.website_name}")

                        # 合并搜索结果中的动漫信息到原始动漫对象
                        self._merge_search_result_info(anime, first_result, scraper.website_name)

                        return anime_id
            except Exception as e:
                logger.warning(f"Search failed for '{search_term}' on {scraper.website_name}: {e}")
                continue

            # 添加延迟避免过于频繁的请求
            await asyncio.sleep(0.5)

        logger.debug(f"Search failed for all terms on {scraper.website_name}: {search_terms}")
        return None

    def _merge_search_result_info(self, original_anime: AnimeInfo, search_result: AnimeInfo, website_name: WebsiteName):
        """合并搜索结果中的动漫信息到原始动漫对象"""
        # 合并标题信息
        if search_result.title_english and not original_anime.title_english:
            logger.info(f"   📝 添加英文标题: '{original_anime.title}' -> '{search_result.title_english}' (来自 {website_name.value})")
            original_anime.title_english = search_result.title_english

        if search_result.title_japanese and not original_anime.title_japanese:
            logger.info(f"   📝 添加日文标题: '{original_anime.title}' -> '{search_result.title_japanese}' (来自 {website_name.value})")
            original_anime.title_japanese = search_result.title_japanese

        if search_result.title_chinese and not original_anime.title_chinese:
            logger.info(f"   🇨🇳 添加中文标题: '{original_anime.title}' -> '{search_result.title_chinese}' (来自 {website_name.value})")
            original_anime.title_chinese = search_result.title_chinese

        # 合并图片信息
        if search_result.poster_image and not original_anime.poster_image:
            logger.debug(f"   🖼️ 添加海报图片: {search_result.poster_image[:50]}...")
            original_anime.poster_image = search_result.poster_image

        if search_result.cover_image and not original_anime.cover_image:
            original_anime.cover_image = search_result.cover_image

        if search_result.banner_image and not original_anime.banner_image:
            logger.debug(f"   🖼️ 添加横幅图片: {search_result.banner_image[:50]}...")
            original_anime.banner_image = search_result.banner_image

        # 合并外部ID
        for ext_website, ext_id in search_result.external_ids.items():
            if ext_website not in original_anime.external_ids:
                original_anime.external_ids[ext_website] = ext_id
                logger.debug(f"   🔗 添加外部ID: {ext_website.value} -> {ext_id}")
    
    async def _get_rating_from_scraper(self, session: aiohttp.ClientSession,
                                     scraper, anime_id: str) -> Optional[RatingData]:
        """从爬虫获取评分数据"""
        try:
            rating_data = await scraper.get_anime_rating(session, anime_id)
            # 注意：site_mean和site_std将在后续的_calculate_seasonal_site_statistics中设置
            return rating_data
        except Exception as e:
            logger.error(f"Error getting rating from {scraper.website_name} "
                        f"for anime {anime_id}: {e}")
            return None
    
    def calculate_composite_scores(self, anime_scores: List[AnimeScore]) -> List[AnimeScore]:
        """计算综合评分"""
        # 首先计算季度内各网站的统计数据
        self._calculate_seasonal_site_statistics(anime_scores)

        valid_scores = []

        min_websites = self.config.model.weights.min_websites
        for anime_score in anime_scores:
            if anime_score.has_sufficient_data(min_websites):
                composite_score = self.scoring_engine.calculate_composite_score(anime_score)
                if composite_score:
                    anime_score.composite_score = composite_score
                    valid_scores.append(anime_score)
                else:
                    logger.warning(f"Failed to calculate composite score for "
                                 f"{anime_score.anime_info.title}")
            else:
                logger.info(f"Insufficient data for {anime_score.anime_info.title} "
                           f"(need {min_websites} websites)")

        # 计算网站排名
        self.scoring_engine.calculate_site_rankings(anime_scores)

        # 排名
        ranked_scores = self.scoring_engine.rank_anime_list(valid_scores)

        logger.info(f"Successfully calculated composite scores for "
                   f"{len(ranked_scores)} out of {len(anime_scores)} anime")

        return ranked_scores

    def _calculate_seasonal_site_statistics(self, anime_scores: List[AnimeScore]):
        """
        计算季度内各网站的统计数据

        根据配置决定使用季度动态统计还是固定统计数据。
        """
        # 检查配置的统计方法
        stats_config = self.config.model.site_statistics

        if stats_config.method == "fixed":
            # 使用固定统计数据
            logger.info("Using fixed site statistics as configured")
            for anime_score in anime_scores:
                for rating in anime_score.ratings:
                    self._apply_fallback_statistics(rating)
            return

        # 使用季度动态统计
        from collections import defaultdict

        # 收集各网站的评分数据
        website_scores = defaultdict(list)

        for anime_score in anime_scores:
            for rating in anime_score.ratings:
                if rating.raw_score is not None:
                    website_scores[rating.website].append(rating.raw_score)

        # 计算各网站的统计数据
        site_statistics = {}
        min_samples = stats_config.min_seasonal_samples

        for website, scores in website_scores.items():
            if len(scores) >= min_samples:
                mean, std = self.scoring_engine.calculate_site_statistics(scores)
                site_statistics[website] = {'mean': mean, 'std': std}
                logger.info(f"Calculated seasonal statistics for {website.value}: "
                           f"mean={mean:.3f}, std={std:.3f} (from {len(scores)} anime)")
            else:
                logger.warning(f"Insufficient data for {website.value}: only {len(scores)} anime "
                             f"(need {min_samples}), using fallback statistics")

        # 更新所有评分数据的统计信息
        for anime_score in anime_scores:
            for rating in anime_score.ratings:
                if rating.website in site_statistics:
                    stats = site_statistics[rating.website]
                    rating.site_mean = stats['mean']
                    rating.site_std = stats['std']
                    logger.debug(f"Updated site stats for {rating.website.value}: "
                               f"mean={stats['mean']:.3f}, std={stats['std']:.3f}")
                else:
                    # 如果没有足够的季度数据，使用回退统计数据
                    self._apply_fallback_statistics(rating)

    def _apply_fallback_statistics(self, rating: RatingData):
        """
        为没有足够季度数据的网站应用回退统计数据

        这些数据基于历史经验和网站特点，作为季度数据不足时的备选方案。
        """
        fallback_stats = {
            WebsiteName.BANGUMI: {'mean': 7.2, 'std': 0.8},
            WebsiteName.MAL: {'mean': 7.8, 'std': 0.6},
            WebsiteName.ANILIST: {'mean': 7.5, 'std': 0.9},
            WebsiteName.DOUBAN: {'mean': 8.0, 'std': 0.7},
            WebsiteName.IMDB: {'mean': 7.0, 'std': 1.0},
            WebsiteName.FILMARKS: {'mean': 7.3, 'std': 0.8}
        }

        if rating.website in fallback_stats:
            stats = fallback_stats[rating.website]
            rating.site_mean = stats['mean']
            rating.site_std = stats['std']
            logger.info(f"Applied fallback statistics for {rating.website.value}: "
                       f"mean={stats['mean']}, std={stats['std']}")
        else:
            # 通用默认值
            rating.site_mean = 7.5
            rating.site_std = 0.8
            logger.warning(f"Using generic fallback statistics for {rating.website.value}")
    
    async def analyze_season_with_completion(self, season: Optional[Season] = None,
                                           year: Optional[int] = None,
                                           enable_completion: bool = True) -> SeasonalAnalysis:
        """分析指定季度（包含数据补全）"""
        if season is None or year is None:
            season, year = get_current_season()

        logger.info(f"🎌 开始分析 {season.value} {year} (数据补全: {'启用' if enable_completion else '禁用'})")

        # 1. 获取季度动漫列表
        anime_list = await self.get_seasonal_anime_list(season, year)

        # 2. 收集评分数据（第一轮）
        anime_scores = await self.collect_anime_ratings(anime_list)
        logger.info(f"📊 第一轮收集完成，获得 {len(anime_scores)} 个动漫数据")

        # 3. 数据补全（如果启用）
        if enable_completion:
            logger.info(f"🔧 准备启动数据补全，enable_completion={enable_completion}")
            anime_scores = await self._perform_data_completion(anime_scores)
        else:
            logger.info(f"⏭️ 跳过数据补全，enable_completion={enable_completion}")

        # 4. 计算综合评分
        ranked_scores = self.calculate_composite_scores(anime_scores)

        # 5. 创建分析结果
        analysis = SeasonalAnalysis(
            season=season,
            year=year,
            anime_scores=ranked_scores,
            total_anime_count=len(anime_list),
            analyzed_anime_count=len(ranked_scores)
        )
        
        logger.info(f"🎉 分析完成: {len(ranked_scores)} 个动漫完成排名")

        return analysis

    async def analyze_season(self, season: Optional[Season] = None,
                           year: Optional[int] = None) -> SeasonalAnalysis:
        """分析指定季度（兼容性方法，默认启用数据补全）"""
        return await self.analyze_season_with_completion(season, year, enable_completion=True)

    async def _perform_data_completion(self, anime_scores: List[AnimeScore]) -> List[AnimeScore]:
        """执行数据补全"""
        logger.info("🔍 开始数据补全流程...")

        # 1. 识别缺失数据
        missing_records = self.data_completion.identify_missing_data(anime_scores)

        if not missing_records:
            logger.info("✅ 所有动漫数据完整，无需补全")
            return anime_scores

        # 2. 补全缺失数据
        completed_data, completed_anime_info = await self.data_completion.complete_missing_data(missing_records)

        if not completed_data and not completed_anime_info:
            logger.info("⚠️ 未能补全任何数据")
            return anime_scores

        # 3. 合并补全数据
        merged_scores = self.data_completion.merge_completed_data(anime_scores, completed_data, completed_anime_info)

        # 4. 重新计算网站统计（因为有新数据）
        self._recalculate_site_statistics(merged_scores)

        # 5. 输出补全摘要
        summary = self.data_completion.get_completion_summary()
        logger.info(f"📈 数据补全摘要:")
        logger.info(f"   - 需要补全的动漫: {summary.get('total_anime_with_missing_data', 0)}")
        logger.info(f"   - 搜索尝试次数: {summary.get('total_search_attempts', 0)}")
        logger.info(f"   - 成功补全次数: {summary.get('successful_completions', 0)}")
        logger.info(f"   - 补全成功率: {summary.get('success_rate', 0):.1f}%")

        return merged_scores

    def _recalculate_site_statistics(self, anime_scores: List[AnimeScore]):
        """重新计算网站统计数据"""
        logger.debug("🔄 重新计算网站统计数据...")

        # 收集所有评分数据按网站分组
        website_scores = {}

        for anime_score in anime_scores:
            for rating in anime_score.ratings:
                if rating.website not in website_scores:
                    website_scores[rating.website] = []
                website_scores[rating.website].append(rating.raw_score)

        # 重新计算每个网站的统计数据
        for website, scores in website_scores.items():
            if len(scores) >= 5:  # 至少5个样本才重新计算
                mean_score = sum(scores) / len(scores)
                variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                std_score = variance ** 0.5

                logger.debug(f"📊 {website.value}: 更新统计 (样本: {len(scores)}, 均值: {mean_score:.3f}, 标准差: {std_score:.3f})")

                # 更新所有该网站的评分数据统计
                for anime_score in anime_scores:
                    for rating in anime_score.ratings:
                        if rating.website == website:
                            rating.site_mean = mean_score
                            rating.site_std = std_score

    def get_scraper_status(self) -> Dict[str, bool]:
        """获取爬虫状态"""
        return {
            name.value: scraper.is_enabled() 
            for name, scraper in self.scrapers.items()
        }
