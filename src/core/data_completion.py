"""
数据补全模块
用于识别和补全动漫评分数据中的缺失信息
"""
import asyncio
import re
import aiohttp
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from ..models.anime import AnimeScore, RatingData, WebsiteName, AnimeInfo
from ..models.config import Config
from ..scrapers.base import BaseWebsiteScraper


@dataclass
class MissingDataRecord:
    """缺失数据记录"""
    anime_score: AnimeScore
    missing_websites: Set[WebsiteName]
    available_websites: Set[WebsiteName]
    
    @property
    def completion_priority(self) -> int:
        """补全优先级 - 基于已有网站数量"""
        return len(self.available_websites)


@dataclass
class SearchAttempt:
    """搜索尝试记录"""
    website: WebsiteName
    search_terms: List[str]
    success: bool
    found_data: Optional[RatingData] = None
    found_anime_info: Optional[AnimeInfo] = None


class DataCompletion:
    """数据补全引擎"""
    
    def __init__(self, config: Config, scrapers: Dict[WebsiteName, BaseWebsiteScraper]):
        self.config = config
        self.completion_config = config.data_completion
        self.scrapers = scrapers
        self.missing_data_records: List[MissingDataRecord] = []
        self.completion_attempts: Dict[str, List[SearchAttempt]] = {}
        
    def identify_missing_data(self, anime_scores: List[AnimeScore]) -> List[MissingDataRecord]:
        """识别缺失数据"""
        logger.info("🔍 开始识别缺失数据...")
        
        missing_records = []
        enabled_websites = self._get_enabled_websites()
        
        for anime_score in anime_scores:
            # 获取当前动漫已有的网站数据
            available_websites = {rating.website for rating in anime_score.ratings}
            
            # 找出缺失的网站
            missing_websites = enabled_websites - available_websites

            # 检查是否满足最小现有网站数要求
            if (missing_websites and
                len(available_websites) >= self.completion_config.min_existing_websites):
                record = MissingDataRecord(
                    anime_score=anime_score,
                    missing_websites=missing_websites,
                    available_websites=available_websites
                )
                missing_records.append(record)
        
        # 按优先级排序 - 已有网站数多的优先补全
        missing_records.sort(key=lambda x: x.completion_priority, reverse=True)
        
        logger.info(f"📊 识别到 {len(missing_records)} 个动漫需要数据补全")
        logger.info(f"📈 平均缺失网站数: {sum(len(r.missing_websites) for r in missing_records) / len(missing_records):.1f}")
        
        self.missing_data_records = missing_records
        return missing_records
    
    async def complete_missing_data(self, missing_records: List[MissingDataRecord]) -> Tuple[Dict[str, List[RatingData]], Dict[str, List[AnimeInfo]]]:
        """补全缺失数据"""
        logger.info(f"🔄 开始补全 {len(missing_records)} 个动漫的缺失数据...")

        completed_data = {}
        completed_anime_info = {}
        total_attempts = 0
        successful_completions = 0
        
        for i, record in enumerate(missing_records, 1):
            anime_title = record.anime_score.anime_info.title
            logger.info(f"📝 [{i}/{len(missing_records)}] 补全动漫: {anime_title}")
            
            anime_completed_data = []
            anime_completed_info = []

            for website in record.missing_websites:
                if website not in self.scrapers:
                    continue

                scraper = self.scrapers[website]
                search_terms = self._generate_search_terms(record.anime_score)

                logger.debug(f"🔍 在 {website.value} 搜索: {search_terms}")

                # 尝试搜索
                attempt = await self._attempt_search(scraper, website, search_terms, anime_title)
                total_attempts += 1

                # 记录搜索尝试
                if anime_title not in self.completion_attempts:
                    self.completion_attempts[anime_title] = []
                self.completion_attempts[anime_title].append(attempt)

                if attempt.success and attempt.found_data:
                    anime_completed_data.append(attempt.found_data)
                    successful_completions += 1
                    logger.info(f"✅ 在 {website.value} 找到数据: {attempt.found_data.raw_score}")

                    # 保存AnimeInfo（如果有的话）
                    if attempt.found_anime_info:
                        anime_completed_info.append(attempt.found_anime_info)
                        logger.debug(f"✅ 在 {website.value} 找到动漫信息: {attempt.found_anime_info.title}")
                else:
                    logger.debug(f"❌ 在 {website.value} 未找到数据")

            if anime_completed_data:
                completed_data[anime_title] = anime_completed_data
            if anime_completed_info:
                completed_anime_info[anime_title] = anime_completed_info
        
        success_rate = (successful_completions / total_attempts * 100) if total_attempts > 0 else 0
        logger.info(f"🎉 数据补全完成!")
        logger.info(f"📊 总尝试: {total_attempts}, 成功: {successful_completions}, 成功率: {success_rate:.1f}%")

        return completed_data, completed_anime_info
    
    def _get_enabled_websites(self) -> Set[WebsiteName]:
        """获取启用的网站列表"""
        enabled_websites = set()
        
        for website_name, website_config in self.config.websites.items():
            if website_config.enabled:
                try:
                    website_enum = WebsiteName(website_name)
                    enabled_websites.add(website_enum)
                except ValueError:
                    continue
        
        return enabled_websites
    
    def _generate_search_terms(self, anime_score: AnimeScore) -> List[str]:
        """生成多种搜索词（优先日文标题）"""
        anime_info = anime_score.anime_info
        search_terms = []

        # 1. 日文标题（最高优先级）
        if anime_info.title_japanese:
            search_terms.append(anime_info.title_japanese)
            # 去掉一些可能的修饰词
            simplified_japanese = anime_info.title_japanese.replace('第2期', '').replace('第２期', '').replace('2nd Season', '').strip()
            if simplified_japanese != anime_info.title_japanese:
                search_terms.append(simplified_japanese)

        # 2. 英文标题
        if anime_info.title_english and anime_info.title_english != anime_info.title:
            search_terms.append(anime_info.title_english)

        # 3. 别名
        if anime_info.alternative_titles:
            search_terms.extend(anime_info.alternative_titles[:2])  # 只取前2个别名

        # 4. 原始标题（罗马音）
        if anime_info.title:
            search_terms.append(anime_info.title)

        # 5. 简化标题（去除季数、特殊符号等）
        if anime_info.title:
            simplified = self._simplify_title(anime_info.title)
            if simplified and simplified not in search_terms:
                search_terms.append(simplified)

        # 6. 去除括号内容
        if anime_info.title:
            no_brackets = re.sub(r'\([^)]*\)', '', anime_info.title).strip()
            if no_brackets and no_brackets not in search_terms:
                search_terms.append(no_brackets)

        # 去重并保持顺序
        unique_search_terms = []
        for term in search_terms:
            if term and term not in unique_search_terms:
                unique_search_terms.append(term)

        return unique_search_terms[:5]  # 限制最多5个搜索词
    
    def _simplify_title(self, title: str) -> str:
        """简化标题"""
        # 去除常见的特殊符号和后缀
        simplified = title
        
        # 去除常见后缀
        suffixes_to_remove = [
            r'\s*2nd Season$', r'\s*Season 2$', r'\s*S2$',
            r'\s*3rd Season$', r'\s*Season 3$', r'\s*S3$',
            r'\s*4th Season$', r'\s*Season 4$', r'\s*S4$',
            r'\s*Part 2$', r'\s*Part II$',
            r'\s*\(2025\)$', r'\s*\(2024\)$', r'\s*\(2023\)$',
            r'\s*OVA$', r'\s*ONA$', r'\s*Special$',
            r'\s*Movie$', r'\s*Film$'
        ]
        
        for suffix in suffixes_to_remove:
            simplified = re.sub(suffix, '', simplified, flags=re.IGNORECASE)
        
        # 去除多余空格
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        return simplified if simplified != title else ""
    
    def _remove_season_info(self, title: str) -> str:
        """去除季数信息"""
        # 去除各种季数表示
        season_patterns = [
            r'\s*2nd Season', r'\s*Season 2', r'\s*S2',
            r'\s*3rd Season', r'\s*Season 3', r'\s*S3', 
            r'\s*4th Season', r'\s*Season 4', r'\s*S4',
            r'\s*Part 2', r'\s*Part II', r'\s*Part III',
            r'\s*続編', r'\s*第二季', r'\s*第2季'
        ]
        
        result = title
        for pattern in season_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        return result.strip() if result.strip() != title else ""
    
    async def _attempt_search(self, scraper: BaseWebsiteScraper, website: WebsiteName,
                            search_terms: List[str], anime_title: str) -> SearchAttempt:
        """尝试搜索动漫数据"""
        attempt = SearchAttempt(
            website=website,
            search_terms=search_terms,
            success=False
        )

        try:
            async with aiohttp.ClientSession() as session:
                for term in search_terms:
                    try:
                        # 搜索动漫
                        search_results = await scraper.search_anime(session, term)

                        if search_results:
                            # 取第一个结果获取详细信息
                            anime_data = search_results[0]

                            # 从AnimeInfo中获取对应网站的ID
                            anime_id = anime_data.external_ids.get(website)
                            if not anime_id:
                                # 如果没有external_id，尝试使用其他ID字段
                                if website == WebsiteName.MAL and hasattr(anime_data, 'mal_id'):
                                    anime_id = str(anime_data.mal_id)
                                elif website == WebsiteName.ANILIST and hasattr(anime_data, 'anilist_id'):
                                    anime_id = str(anime_data.anilist_id)
                                elif website == WebsiteName.BANGUMI and hasattr(anime_data, 'bangumi_id'):
                                    anime_id = str(anime_data.bangumi_id)

                            if anime_id:
                                # 获取评分数据
                                rating_data = await scraper.get_anime_rating(session, anime_id)

                                if rating_data:
                                    attempt.success = True
                                    attempt.found_data = rating_data
                                    attempt.found_anime_info = anime_data  # 保存AnimeInfo
                                    logger.debug(f"✅ 搜索成功: {term} -> {rating_data.raw_score}")
                                    return attempt
                                else:
                                    logger.debug(f"⚠️ 找到动漫但无法获取评分数据: {anime_id}")
                            else:
                                logger.debug(f"⚠️ 找到动漫但缺少ID信息: {anime_data.title}")

                    except Exception as e:
                        logger.debug(f"❌ 搜索词 '{term}' 失败: {e}")
                        continue

        except Exception as e:
            logger.warning(f"⚠️ 搜索 {anime_title} 在 {website.value} 时出错: {e}")

        return attempt
    
    def merge_completed_data(self, original_scores: List[AnimeScore],
                           completed_data: Dict[str, List[RatingData]],
                           completed_anime_info: Dict[str, List[AnimeInfo]]) -> List[AnimeScore]:
        """将补全的数据合并到原始结果中"""
        logger.info("🔄 合并补全数据到原始结果...")

        merged_count = 0
        merged_info_count = 0

        for anime_score in original_scores:
            anime_title = anime_score.anime_info.title

            # 合并评分数据
            if anime_title in completed_data:
                for rating_data in completed_data[anime_title]:
                    # 检查是否已存在该网站的数据
                    existing_websites = {r.website for r in anime_score.ratings}

                    if rating_data.website not in existing_websites:
                        anime_score.ratings.append(rating_data)
                        merged_count += 1
                        logger.debug(f"✅ 为 {anime_title} 添加 {rating_data.website.value} 数据")

            # 合并动漫信息
            if anime_title in completed_anime_info:
                for anime_info in completed_anime_info[anime_title]:
                    # 合并标题信息
                    if anime_info.title_english and not anime_score.anime_info.title_english:
                        logger.info(f"   📝 添加英文标题: '{anime_title}' -> '{anime_info.title_english}' (来自 {list(anime_info.external_ids.keys())[0].value if anime_info.external_ids else '未知'})")
                        anime_score.anime_info.title_english = anime_info.title_english
                        merged_info_count += 1

                    if anime_info.title_japanese and not anime_score.anime_info.title_japanese:
                        logger.info(f"   📝 添加日文标题: '{anime_title}' -> '{anime_info.title_japanese}' (来自 {list(anime_info.external_ids.keys())[0].value if anime_info.external_ids else '未知'})")
                        anime_score.anime_info.title_japanese = anime_info.title_japanese
                        merged_info_count += 1

                    if anime_info.title_chinese and not anime_score.anime_info.title_chinese:
                        website_name = list(anime_info.external_ids.keys())[0].value if anime_info.external_ids else '未知'
                        logger.info(f"   🇨🇳 添加中文标题: '{anime_title}' -> '{anime_info.title_chinese}' (来自 {website_name})")
                        anime_score.anime_info.title_chinese = anime_info.title_chinese
                        merged_info_count += 1

                    # 合并图片信息
                    if anime_info.poster_image and not anime_score.anime_info.poster_image:
                        logger.debug(f"   🖼️ 添加海报图片: {anime_info.poster_image[:50]}...")
                        anime_score.anime_info.poster_image = anime_info.poster_image
                        merged_info_count += 1

                    if anime_info.cover_image and not anime_score.anime_info.cover_image:
                        anime_score.anime_info.cover_image = anime_info.cover_image
                        merged_info_count += 1

                    if anime_info.banner_image and not anime_score.anime_info.banner_image:
                        logger.debug(f"   🖼️ 添加横幅图片: {anime_info.banner_image[:50]}...")
                        anime_score.anime_info.banner_image = anime_info.banner_image
                        merged_info_count += 1

                    # 合并外部ID
                    for website, external_id in anime_info.external_ids.items():
                        if website not in anime_score.anime_info.external_ids:
                            anime_score.anime_info.external_ids[website] = external_id
                            logger.debug(f"   🔗 添加外部ID: {website.value} -> {external_id}")
                            merged_info_count += 1

        logger.info(f"🎉 成功合并 {merged_count} 条评分数据和 {merged_info_count} 条动漫信息")
        return original_scores
    
    def get_completion_summary(self) -> Dict:
        """获取补全过程摘要"""
        if not self.missing_data_records:
            return {}
        
        total_missing = len(self.missing_data_records)
        total_attempts = sum(len(attempts) for attempts in self.completion_attempts.values())
        successful_attempts = sum(
            1 for attempts in self.completion_attempts.values() 
            for attempt in attempts if attempt.success
        )
        
        return {
            "total_anime_with_missing_data": total_missing,
            "total_search_attempts": total_attempts,
            "successful_completions": successful_attempts,
            "success_rate": (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0,
            "completion_details": {
                anime_title: [
                    {
                        "website": attempt.website.value,
                        "search_terms": attempt.search_terms,
                        "success": attempt.success,
                        "found_score": attempt.found_data.raw_score if attempt.found_data else None
                    }
                    for attempt in attempts
                ]
                for anime_title, attempts in self.completion_attempts.items()
            }
        }
