"""
AniList GraphQL API 客户端
"""
import aiohttp
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from loguru import logger

from .base import APIBasedScraper, ScraperFactory
from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType, AnimeStatus, Season
from ..models.config import WebsiteConfig
from ..utils.season_utils import get_season_from_date


class AniListScraper(APIBasedScraper):
    """AniList GraphQL API 数据获取器"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig, api_keys: Dict[str, str]):
        super().__init__(website_name, config, api_keys)
        self.base_url = config.api_base_url or "https://graphql.anilist.co"
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AnimeScore/1.0'
        }
        
        # AniList 基础功能无需认证
        if 'access_token' in self.api_keys:
            headers['Authorization'] = f"Bearer {self.api_keys['access_token']}"
        
        return headers
    
    def _parse_anime_type(self, anilist_format: str) -> Optional[AnimeType]:
        """解析 AniList 动漫类型"""
        type_mapping = {
            'TV': AnimeType.TV,
            'MOVIE': AnimeType.MOVIE,
            'OVA': AnimeType.OVA,
            'ONA': AnimeType.ONA,
            'SPECIAL': AnimeType.SPECIAL,
            'MUSIC': AnimeType.MUSIC
        }
        return type_mapping.get(anilist_format)
    
    def _parse_anime_status(self, anilist_status: str) -> Optional[AnimeStatus]:
        """解析 AniList 动漫状态"""
        status_mapping = {
            'FINISHED': AnimeStatus.FINISHED,
            'RELEASING': AnimeStatus.AIRING,
            'NOT_YET_RELEASED': AnimeStatus.NOT_YET_AIRED,
            'CANCELLED': AnimeStatus.CANCELLED
        }
        return status_mapping.get(anilist_status)
    
    def _parse_date(self, date_obj: Dict[str, int]) -> Optional[date]:
        """解析 AniList 日期对象"""
        if not date_obj or not date_obj.get('year'):
            return None
        
        try:
            year = date_obj['year']
            month = date_obj.get('month', 1)
            day = date_obj.get('day', 1)
            return date(year, month, day)
        except ValueError:
            logger.warning(f"Failed to parse AniList date: {date_obj}")
            return None
    
    def _convert_to_anime_info(self, anilist_data: Dict[str, Any]) -> AnimeInfo:
        """将 AniList 数据转换为 AnimeInfo"""
        # 解析开始日期和季度
        start_date = None
        if 'startDate' in anilist_data:
            start_date = self._parse_date(anilist_data['startDate'])
        
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 解析结束日期
        end_date = None
        if 'endDate' in anilist_data:
            end_date = self._parse_date(anilist_data['endDate'])
        
        # 处理标题
        title_data = anilist_data.get('title', {})
        
        # 处理图片信息
        cover_image = None
        poster_image = None
        banner_image = None

        if 'coverImage' in anilist_data:
            cover_data = anilist_data['coverImage']
            # 优先使用large，然后medium
            cover_image = cover_data.get('large') or cover_data.get('medium')
            poster_image = cover_image  # AniList的coverImage就是海报

        if 'bannerImage' in anilist_data:
            banner_image = anilist_data['bannerImage']

        anime_info = AnimeInfo(
            title=title_data.get('romaji', '') or title_data.get('english', ''),
            title_english=title_data.get('english', ''),
            title_japanese=title_data.get('native', ''),
            alternative_titles=anilist_data.get('synonyms', []),
            anime_type=self._parse_anime_type(anilist_data.get('format', '')),
            status=self._parse_anime_status(anilist_data.get('status', '')),
            episodes=anilist_data.get('episodes'),
            duration=anilist_data.get('duration'),
            start_date=start_date,
            end_date=end_date,
            season=season,
            year=year,
            external_ids={WebsiteName.ANILIST: str(anilist_data.get('id', ''))},
            synopsis=anilist_data.get('description', ''),
            poster_image=poster_image,
            cover_image=cover_image,
            banner_image=banner_image
        )
        
        # 处理制作公司
        if 'studios' in anilist_data and 'nodes' in anilist_data['studios']:
            anime_info.studios = [studio.get('name', '') for studio in anilist_data['studios']['nodes']]
        
        # 处理类型标签
        if 'genres' in anilist_data:
            anime_info.genres = anilist_data['genres']
        
        # 处理来源
        if 'source' in anilist_data:
            anime_info.source = anilist_data['source']
        
        return anime_info
    
    async def _graphql_request(self, session: aiohttp.ClientSession, query: str, variables: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """发起 GraphQL 请求"""
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = await self._make_request(
            session, self.base_url, method="POST", 
            headers=self._get_auth_headers(), json_data=payload
        )
        
        if response and 'data' in response:
            return response['data']
        elif response and 'errors' in response:
            logger.error(f"AniList GraphQL errors: {response['errors']}")
        
        return None
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫"""
        query = """
        query ($search: String) {
            Page(page: 1, perPage: 10) {
                media(search: $search, type: ANIME) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    synonyms
                    format
                    status
                    episodes
                    duration
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    description
                    genres
                    studios {
                        nodes {
                            name
                        }
                    }
                    source
                    averageScore
                    coverImage {
                        large
                        medium
                        color
                    }
                    bannerImage
                }
            }
        }
        """
        
        variables = {'search': title}
        data = await self._graphql_request(session, query, variables)
        
        if not data or 'Page' not in data or 'media' not in data['Page']:
            return []
        
        results = []
        for item in data['Page']['media']:
            try:
                anime_info = self._convert_to_anime_info(item)
                results.append(anime_info)
            except Exception as e:
                logger.warning(f"Failed to parse AniList search result: {e}")
                continue
        
        return results
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                synonyms
                format
                status
                episodes
                duration
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                description
                genres
                studios {
                    nodes {
                        name
                    }
                }
                source
                averageScore
                coverImage {
                    large
                    medium
                    color
                }
                bannerImage
                stats {
                    scoreDistribution {
                        score
                        amount
                    }
                }
            }
        }
        """
        
        variables = {'id': int(anime_id)}
        data = await self._graphql_request(session, query, variables)
        
        if not data or 'Media' not in data:
            return None
        
        try:
            return self._convert_to_anime_info(data['Media'])
        except Exception as e:
            logger.error(f"Failed to parse AniList anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                averageScore
                stats {
                    scoreDistribution {
                        score
                        amount
                    }
                }
            }
        }
        """
        
        variables = {'id': int(anime_id)}
        data = await self._graphql_request(session, query, variables)
        
        if not data or 'Media' not in data:
            return None
        
        media = data['Media']
        average_score = media.get('averageScore')
        
        if average_score is None:
            return None
        
        # AniList 使用 0-100 分制，转换为 0-10 分制
        raw_score = average_score / 10.0
        
        # 获取评分分布
        score_distribution = {}
        total_votes = 0
        
        if 'stats' in media and 'scoreDistribution' in media['stats']:
            for dist in media['stats']['scoreDistribution']:
                score = dist['score'] // 10  # 转换为 1-10 分制
                amount = dist['amount']
                score_distribution[str(score)] = amount
                total_votes += amount
        
        rating = RatingData(
            website=WebsiteName.ANILIST,
            raw_score=raw_score,
            vote_count=total_votes,
            score_distribution=score_distribution,
            site_mean=None,  # 需要从网站统计中获取
            site_std=None,   # 需要计算
            last_updated=datetime.now(),
            url=f"https://anilist.co/anime/{anime_id}"
        )
        
        return rating
    
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        # AniList 季度映射
        season_mapping = {
            'Winter': 'WINTER',
            'Spring': 'SPRING',
            'Summer': 'SUMMER', 
            'Fall': 'FALL'
        }
        
        anilist_season = season_mapping.get(season, season.upper())
        
        query = """
        query ($year: Int, $season: MediaSeason) {
            Page(page: 1, perPage: 50) {
                media(seasonYear: $year, season: $season, type: ANIME, sort: SCORE_DESC) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    synonyms
                    format
                    status
                    episodes
                    duration
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    description
                    genres
                    studios {
                        nodes {
                            name
                        }
                    }
                    source
                    averageScore
                    coverImage {
                        large
                        medium
                        color
                    }
                    bannerImage
                }
            }
        }
        """
        
        variables = {'year': year, 'season': anilist_season}
        data = await self._graphql_request(session, query, variables)
        
        if not data or 'Page' not in data or 'media' not in data['Page']:
            return []
        
        results = []
        for item in data['Page']['media']:
            try:
                anime_info = self._convert_to_anime_info(item)
                results.append(anime_info)
            except Exception as e:
                logger.warning(f"Failed to parse AniList seasonal anime: {e}")
                continue
        
        return results
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据"""
        logger.info("Getting AniList site statistics...")
        
        # AniList 使用 0-100 分制，转换后的统计
        return {
            'mean': 7.5,  # 转换为 10 分制后的平均分
            'std': 0.9    # 相对较大的标准差
        }


# 注册 AniList 爬虫
ScraperFactory.register_scraper(WebsiteName.ANILIST, AniListScraper)
