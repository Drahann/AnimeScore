"""
MyAnimeList 简化API客户端 - 只使用Client ID，无需OAuth2
"""
import aiohttp
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from loguru import logger

from .base import APIBasedScraper, ScraperFactory
from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType, AnimeStatus, Season
from ..models.config import WebsiteConfig
from ..utils.season_utils import get_season_from_date


class SimpleMALScraper(APIBasedScraper):
    """简化的MyAnimeList API数据获取器，只使用Client ID"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig, api_keys: Dict[str, str]):
        super().__init__(website_name, config, api_keys)
        self.base_url = config.api_base_url or "https://api.myanimelist.net/v2"
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头 - 只使用Client ID"""
        headers = {
            'User-Agent': 'AnimeScore/1.0',
            'Accept': 'application/json'
        }

        # 只使用 client_id，不需要 OAuth2
        if 'client_id' in self.api_keys:
            headers['X-MAL-CLIENT-ID'] = self.api_keys['client_id']
        else:
            logger.warning("MAL Client ID not found in API keys")

        return headers
    
    def _parse_anime_type(self, mal_type: str) -> Optional[AnimeType]:
        """解析 MAL 动漫类型"""
        type_mapping = {
            'tv': AnimeType.TV,
            'movie': AnimeType.MOVIE,
            'ova': AnimeType.OVA,
            'ona': AnimeType.ONA,
            'special': AnimeType.SPECIAL,
            'music': AnimeType.MUSIC
        }
        return type_mapping.get(mal_type.lower())
    
    def _parse_anime_status(self, mal_status: str) -> Optional[AnimeStatus]:
        """解析 MAL 动漫状态"""
        status_mapping = {
            'finished_airing': AnimeStatus.FINISHED,
            'currently_airing': AnimeStatus.AIRING,
            'not_yet_aired': AnimeStatus.NOT_YET_AIRED
        }
        return status_mapping.get(mal_status)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Failed to parse MAL date: {date_str}")
            return None
    
    def _convert_to_anime_info(self, mal_data: Dict[str, Any]) -> AnimeInfo:
        """将 MAL 数据转换为 AnimeInfo"""
        # 解析开始日期和季度
        start_date = None
        if 'start_date' in mal_data:
            start_date = self._parse_date(mal_data['start_date'])
        
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 解析结束日期
        end_date = None
        if 'end_date' in mal_data:
            end_date = self._parse_date(mal_data['end_date'])
        
        # 处理episodes字段，确保为正数或None
        episodes = mal_data.get('num_episodes')
        if episodes is not None and episodes <= 0:
            episodes = None

        anime_info = AnimeInfo(
            title=mal_data.get('title', ''),
            title_english=mal_data.get('alternative_titles', {}).get('en', ''),
            title_japanese=mal_data.get('alternative_titles', {}).get('ja', ''),
            alternative_titles=mal_data.get('alternative_titles', {}).get('synonyms', []),
            anime_type=self._parse_anime_type(mal_data.get('media_type', '')),
            status=self._parse_anime_status(mal_data.get('status', '')),
            episodes=episodes,
            start_date=start_date,
            end_date=end_date,
            season=season,
            year=year,
            external_ids={WebsiteName.MAL: str(mal_data.get('id', ''))},
            synopsis=mal_data.get('synopsis', '')
        )
        
        # 处理制作公司
        if 'studios' in mal_data:
            anime_info.studios = [studio.get('name', '') for studio in mal_data['studios']]
        
        # 处理类型标签
        if 'genres' in mal_data:
            anime_info.genres = [genre.get('name', '') for genre in mal_data['genres']]
        
        # 处理来源
        if 'source' in mal_data:
            anime_info.source = mal_data['source']
        
        return anime_info
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫"""
        url = f"{self.base_url}/anime"
        params = {
            'q': title,
            'limit': 10,
            'fields': 'id,title,alternative_titles,start_date,end_date,synopsis,mean,media_type,status,genres,studios,source,num_episodes'
        }
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response or 'data' not in response:
            return []
        
        results = []
        for item in response['data']:
            try:
                anime_info = self._convert_to_anime_info(item['node'])
                results.append(anime_info)
            except Exception as e:
                logger.warning(f"Failed to parse MAL search result: {e}")
                continue
        
        return results
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/anime/{anime_id}"
        params = {
            'fields': 'id,title,alternative_titles,start_date,end_date,synopsis,mean,media_type,status,genres,studios,source,num_episodes,num_scoring_users'
        }
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response:
            return None
        
        try:
            return self._convert_to_anime_info(response)
        except Exception as e:
            logger.error(f"Failed to parse MAL anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        url = f"{self.base_url}/anime/{anime_id}"
        params = {
            'fields': 'mean,num_scoring_users'
        }
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response:
            return None
        
        # MAL 评分数据
        mean_score = response.get('mean')
        num_users = response.get('num_scoring_users')
        
        if mean_score is None or num_users is None:
            logger.debug(f"MAL anime {anime_id} has no rating data")
            return None
        
        rating = RatingData(
            website=WebsiteName.MAL,
            raw_score=mean_score,
            vote_count=num_users,
            score_distribution={},
            site_mean=None,  # 需要从网站统计中获取
            site_std=None,   # 需要计算
            last_updated=datetime.now(),
            url=f"https://myanimelist.net/anime/{anime_id}"
        )
        
        return rating
    
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        # MAL 季度动漫API
        season_mapping = {
            'Winter': 'winter',
            'Spring': 'spring', 
            'Summer': 'summer',
            'Fall': 'fall'
        }
        
        mal_season = season_mapping.get(season, season.lower())
        url = f"{self.base_url}/anime/season/{year}/{mal_season}"
        params = {
            'sort': 'anime_score',
            'limit': 100,
            'fields': 'id,title,alternative_titles,start_date,end_date,synopsis,mean,media_type,status,genres,studios,source,num_episodes'
        }
        
        response = await self._make_request(
            session, url, params=params, headers=self._get_auth_headers()
        )
        
        if not response or 'data' not in response:
            return []
        
        results = []
        for item in response['data']:
            try:
                anime_info = self._convert_to_anime_info(item['node'])
                results.append(anime_info)
            except Exception as e:
                logger.warning(f"Failed to parse MAL seasonal anime: {e}")
                continue
        
        return results
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据"""
        # MAL 没有直接提供全站统计数据的API
        # 这里使用基于经验的估算值
        logger.info("Getting MAL site statistics...")
        
        # 基于MAL评分特点的估算值
        return {
            'mean': 7.8,  # MAL平均分通常较高
            'std': 0.6    # MAL评分相对集中
        }


# 注册简化版 MAL 爬虫
ScraperFactory.register_scraper(WebsiteName.MAL, SimpleMALScraper)
