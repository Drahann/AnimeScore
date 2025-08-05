"""
Bangumi API 客户端
"""
import asyncio
import aiohttp
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from loguru import logger

from .base import APIBasedScraper, ScraperFactory
from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType, AnimeStatus, Season
from ..models.config import WebsiteConfig
from ..utils.season_utils import get_season_from_date


class BangumiScraper(APIBasedScraper):
    """Bangumi API 数据获取器"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig, api_keys: Dict[str, str]):
        super().__init__(website_name, config, api_keys)
        self.base_url = config.api_base_url or "https://api.bgm.tv"
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {
            'User-Agent': 'AnimeScore/1.0 (https://github.com/your-repo/animescore)',
            'Accept': 'application/json'
        }
        
        if 'access_token' in self.api_keys:
            headers['Authorization'] = f"Bearer {self.api_keys['access_token']}"
        
        return headers
    
    def _parse_anime_type(self, bgm_type: int) -> Optional[AnimeType]:
        """解析 Bangumi 动漫类型"""
        type_mapping = {
            2: AnimeType.TV,
            6: AnimeType.MOVIE,
            3: AnimeType.OVA,
            4: AnimeType.ONA,
            5: AnimeType.SPECIAL,
            1: AnimeType.MUSIC
        }
        return type_mapping.get(bgm_type)
    
    def _parse_anime_status(self, bgm_status: int) -> Optional[AnimeStatus]:
        """解析 Bangumi 动漫状态"""
        # Bangumi 的状态码可能需要根据实际API调整
        status_mapping = {
            2: AnimeStatus.FINISHED,
            1: AnimeStatus.AIRING,
            3: AnimeStatus.NOT_YET_AIRED
        }
        return status_mapping.get(bgm_status)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # Bangumi 日期格式通常是 YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                # 尝试其他格式
                return datetime.strptime(date_str, "%Y-%m").date().replace(day=1)
            except ValueError:
                logger.warning(f"Failed to parse date: {date_str}")
                return None
    
    def _convert_to_anime_info(self, bgm_data: Dict[str, Any]) -> AnimeInfo:
        """将 Bangumi 数据转换为 AnimeInfo"""
        # 解析开始日期和季度
        start_date = self._parse_date(bgm_data.get('date'))
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 处理标题信息
        # Bangumi中：name通常是日文原名，name_cn是中文名
        japanese_name = bgm_data.get('name', '')
        chinese_name = bgm_data.get('name_cn', '')

        logger.debug(f"🇨🇳 Bangumi标题信息: 日文='{japanese_name}', 中文='{chinese_name}'")

        # 主标题优先使用中文名，如果没有则使用日文名
        main_title = chinese_name if chinese_name else japanese_name

        if chinese_name:
            logger.info(f"🇨🇳 Bangumi获取到中文标题: '{chinese_name}'")
        else:
            logger.debug(f"🇨🇳 Bangumi未获取到中文标题，使用日文: '{japanese_name}'")

        anime_info = AnimeInfo(
            title=main_title,
            title_english=None,  # Bangumi通常不提供英文标题
            title_japanese=japanese_name,
            title_chinese=chinese_name,
            alternative_titles=[],
            anime_type=self._parse_anime_type(bgm_data.get('type', 0)),
            status=self._parse_anime_status(bgm_data.get('status', 0)),
            episodes=bgm_data.get('eps_count'),
            start_date=start_date,
            season=season,
            year=year,
            external_ids={WebsiteName.BANGUMI: str(bgm_data.get('id', ''))},
            synopsis=bgm_data.get('summary', '')
        )
        
        # 处理标签
        if 'tags' in bgm_data:
            anime_info.genres = [tag.get('name', '') for tag in bgm_data['tags']]
        
        return anime_info
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫 - 改进版本，支持多种搜索策略"""
        # 构建搜索词列表
        search_terms = [title]

        # 如果标题很长，尝试简化版本
        if len(title) > 50:
            # 移除常见的季度标识
            simplified = title.replace(' 2nd Season', '').replace(' Season 2', '').replace(' Part 2', '')
            simplified = simplified.replace(' 第2期', '').replace(' 第２期', '').replace(' 第2クール', '')
            if simplified != title:
                search_terms.append(simplified)

        # 逐个尝试搜索词
        for search_term in search_terms:
            url = f"{self.base_url}/search/subject/{search_term}"
            params = {
                'type': 2,  # 动画类型
                'responseGroup': 'large'
            }

            response = await self._make_request(
                session, url, params=params, headers=self._get_auth_headers()
            )

            if response and 'list' in response and response['list']:
                results = []
                for item in response['list']:
                    try:
                        anime_info = self._convert_to_anime_info(item)
                        results.append(anime_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse Bangumi search result: {e}")
                        continue

                if results:
                    logger.debug(f"Bangumi search successful with term: '{search_term}'")
                    return results

            # 如果第一个搜索词失败，等待一下再尝试下一个
            if search_term != search_terms[-1]:
                await asyncio.sleep(0.5)

        logger.debug(f"Bangumi search failed for all terms: {search_terms}")
        return []
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/subject/{anime_id}"
        params = {'responseGroup': 'large'}
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response:
            return None
        
        try:
            return self._convert_to_anime_info(response)
        except Exception as e:
            logger.error(f"Failed to parse Bangumi anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        url = f"{self.base_url}/subject/{anime_id}"
        params = {'responseGroup': 'large'}
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response or 'rating' not in response:
            return None
        
        rating_data = response['rating']
        
        # 获取评分分布
        score_distribution = {}
        if 'count' in rating_data:
            for i in range(1, 11):
                score_distribution[str(i)] = rating_data['count'].get(str(i), 0)
        
        # Bangumi 提供标准差
        site_std = rating_data.get('std')
        
        rating = RatingData(
            website=WebsiteName.BANGUMI,
            raw_score=rating_data.get('score'),
            vote_count=rating_data.get('total'),
            score_distribution=score_distribution,
            site_mean=None,  # 需要从网站统计中获取
            site_std=site_std,
            last_updated=datetime.now(),
            url=f"https://bgm.tv/subject/{anime_id}"
        )
        
        return rating
    
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        # 注意：Bangumi的calendar API不是按季度分类的，暂时返回空列表
        # 中文标题将通过数据补全阶段的搜索功能获取
        logger.info(f"Bangumi季度API暂不支持 {season} {year}，将通过数据补全获取中文标题")
        return []

        # 原始实现（暂时注释）
        # url = f"{self.base_url}/calendar"
        # response = await self._make_request(
        #     session, url, headers=self._get_auth_headers()
        # )
        #
        # if not response:
        #     return []
        #
        # results = []
        # current_date = datetime.now().date()
        #
        # # 处理日历数据
        # for day_data in response:
        #     if 'items' not in day_data:
        #         continue
        #
        #     for item in day_data['items']:
        #         try:
        #             anime_info = self._convert_to_anime_info(item)
        #
        #             # 检查是否属于指定季度
        #             if (anime_info.year == year and
        #                 anime_info.season and
        #                 anime_info.season.value.lower() == season.lower()):
        #                 results.append(anime_info)
        #
        #         except Exception as e:
        #             logger.warning(f"Failed to parse seasonal anime: {e}")
        #             continue
        #
        # return results
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """
        获取网站统计数据
        
        注意：Bangumi 可能没有直接提供全站统计数据的API
        这里可能需要通过其他方式获取或使用预计算的值
        """
        # 这是一个示例实现，实际可能需要调整
        # 可以考虑：
        # 1. 从热门动漫列表中采样计算
        # 2. 使用预先计算好的统计数据
        # 3. 定期更新的缓存数据
        
        logger.info("Getting Bangumi site statistics...")
        
        # 临时使用估算值，实际部署时应该用真实数据
        # 可以通过分析大量动漫数据来获得更准确的统计
        return {
            'mean': 7.2,  # 估算的平均分
            'std': 0.8    # 估算的标准差
        }


# 注册 Bangumi 爬虫
ScraperFactory.register_scraper(WebsiteName.BANGUMI, BangumiScraper)
