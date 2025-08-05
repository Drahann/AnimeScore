"""
IMDB 网页爬虫
"""
import aiohttp
import asyncio
import re
import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger

from .base import WebScrapingBasedScraper, ScraperFactory
from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType, AnimeStatus, Season
from ..models.config import WebsiteConfig
from ..utils.season_utils import get_season_from_date


class IMDBScraper(WebScrapingBasedScraper):
    """IMDB 网页爬虫"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        self.base_url = config.base_url or "https://www.imdb.com"
        
    def _parse_anime_type(self, imdb_type: str) -> Optional[AnimeType]:
        """解析IMDB类型"""
        if 'TV Series' in imdb_type or 'TV Mini Series' in imdb_type:
            return AnimeType.TV
        elif 'Movie' in imdb_type:
            return AnimeType.MOVIE
        elif 'TV Special' in imdb_type:
            return AnimeType.SPECIAL
        else:
            return AnimeType.TV
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析IMDB日期"""
        if not date_str:
            return None
        
        try:
            # IMDB日期格式通常是 "15 January 2024"
            return datetime.strptime(date_str.strip(), "%d %B %Y").date()
        except ValueError:
            try:
                # 尝试其他格式
                return datetime.strptime(date_str.strip(), "%Y").date().replace(month=1, day=1)
            except ValueError:
                logger.warning(f"Failed to parse IMDB date: {date_str}")
                return None
    
    def _extract_json_ld_data(self, html: str) -> Optional[Dict[str, Any]]:
        """提取页面中的JSON-LD结构化数据"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找JSON-LD脚本标签
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Movie', 'TVSeries']:
                    return data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ['Movie', 'TVSeries']:
                            return item
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _extract_rating_from_page(self, html: str) -> Optional[Dict[str, Any]]:
        """从IMDB页面提取评分信息"""
        # 首先尝试从JSON-LD结构化数据中提取
        json_data = self._extract_json_ld_data(html)
        if json_data and 'aggregateRating' in json_data:
            rating_info = json_data['aggregateRating']
            try:
                raw_score = float(rating_info.get('ratingValue', 0))
                vote_count = int(rating_info.get('ratingCount', 0))

                if raw_score > 0 and vote_count > 0:
                    logger.debug(f"从JSON-LD提取评分: {raw_score}, 投票数: {vote_count}")
                    return {
                        'score': raw_score,
                        'vote_count': vote_count,
                        'score_distribution': {}  # IMDB不提供详细分布
                    }
            except (ValueError, TypeError) as e:
                logger.warning(f"解析JSON-LD评分数据失败: {e}")

        # 如果JSON-LD失败，尝试从HTML元素中提取
        soup = BeautifulSoup(html, 'html.parser')

        # 查找评分 - 尝试多种选择器
        rating_selectors = [
            'span[data-testid="hero-rating-bar__aggregate-rating__score"]',
            'span.sc-bde20123-1',
            '.rating-bar__base-button .ipc-button__text',
            '.AggregateRatingButton__RatingScore',
            '.ratingValue strong span'
        ]

        raw_score = None
        for selector in rating_selectors:
            rating_element = soup.select_one(selector)
            if rating_element:
                try:
                    rating_text = rating_element.text.strip()
                    raw_score = float(rating_text.split('/')[0])
                    logger.debug(f"从HTML元素提取评分: {raw_score} (选择器: {selector})")
                    break
                except (ValueError, IndexError):
                    continue

        if raw_score is None:
            logger.warning("未能从页面提取评分信息")
            return None

        # 查找投票数
        vote_count = 0
        vote_selectors = [
            'div[data-testid="hero-rating-bar__aggregate-rating__vote-count"]',
            'div.sc-bde20123-3',
            '.rating-bar__base-button .ipc-button__text',
            '.AggregateRatingButton__TotalRatingAmount'
        ]

        for selector in vote_selectors:
            vote_element = soup.select_one(selector)
            if vote_element:
                vote_text = vote_element.text
                # 提取数字，可能包含K、M等单位
                vote_match = re.search(r'([\d.]+)([KM]?)', vote_text)
                if vote_match:
                    number = float(vote_match.group(1))
                    unit = vote_match.group(2)
                    if unit == 'K':
                        vote_count = int(number * 1000)
                    elif unit == 'M':
                        vote_count = int(number * 1000000)
                    else:
                        vote_count = int(number)
                    logger.debug(f"从HTML元素提取投票数: {vote_count} (选择器: {selector})")
                    break

        return {
            'score': raw_score,
            'vote_count': vote_count,
            'score_distribution': {}  # IMDB不提供详细分布
        }
    
    def _extract_anime_info_from_page(self, html: str, imdb_id: str) -> Optional[AnimeInfo]:
        """从IMDB页面提取动漫信息"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试从JSON-LD获取结构化数据
        json_data = self._extract_json_ld_data(html)
        
        # 标题
        title = ''
        if json_data:
            title = json_data.get('name', '')
        
        if not title:
            title_element = soup.find('h1', {'data-testid': 'hero__pageTitle'})
            if title_element:
                title = title_element.text.strip()
        
        # 类型
        anime_type = None
        if json_data:
            imdb_type = json_data.get('@type', '')
            anime_type = self._parse_anime_type(imdb_type)
        
        # 日期
        start_date = None
        if json_data and 'datePublished' in json_data:
            start_date = self._parse_date(json_data['datePublished'])
        
        # 解析季度
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 类型标签
        genres = []
        if json_data and 'genre' in json_data:
            if isinstance(json_data['genre'], list):
                genres = json_data['genre']
            elif isinstance(json_data['genre'], str):
                genres = [json_data['genre']]
        
        # 简介
        synopsis = ''
        if json_data and 'description' in json_data:
            synopsis = json_data['description']
        
        anime_info = AnimeInfo(
            title=title,
            anime_type=anime_type,
            start_date=start_date,
            season=season,
            year=year,
            genres=genres,
            external_ids={WebsiteName.IMDB: imdb_id},
            synopsis=synopsis
        )
        
        return anime_info
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫"""
        logger.info(f"🔍 IMDB搜索动漫: {title}")

        search_url = f"{self.base_url}/find"
        params = {
            'q': title,
            's': 'tt',  # 搜索标题
            'ttype': 'tv'  # 限制为TV内容
        }

        response = await self._make_request(
            session, search_url, params=params, headers=self._get_default_headers()
        )

        if not response or 'text' not in response:
            logger.warning("IMDB搜索请求失败")
            return []

        soup = BeautifulSoup(response['text'], 'html.parser')
        results = []

        # 使用正确的选择器解析搜索结果
        result_selectors = [
            '.find-title-result',
            '.ipc-metadata-list-summary-item',
            'tr.findResult'
        ]

        result_items = []
        for selector in result_selectors:
            items = soup.select(selector)
            if items:
                logger.debug(f"使用选择器 {selector} 找到 {len(items)} 个结果")
                result_items = items
                break

        if not result_items:
            logger.warning("未找到搜索结果")
            return []

        for item in result_items[:5]:  # 限制结果数量
            try:
                # 查找链接
                link_element = item.find('a')
                if not link_element:
                    continue

                href = link_element.get('href', '')
                imdb_id_match = re.search(r'/title/(tt\d+)/', href)
                if not imdb_id_match:
                    continue

                imdb_id = imdb_id_match.group(1)
                logger.debug(f"找到IMDB ID: {imdb_id}")

                # 获取详细信息
                anime_info = await self.get_anime_details(session, imdb_id)
                if anime_info:
                    results.append(anime_info)
                    logger.debug(f"成功获取动漫信息: {anime_info.title}")

                # 添加延迟避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"解析IMDB搜索结果失败: {e}")
                continue

        logger.info(f"IMDB搜索完成，找到 {len(results)} 个有效结果")
        return results
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/title/{anime_id}/"
        
        response = await self._make_request(
            session, url, headers=self._get_default_headers()
        )
        
        if not response or 'text' not in response:
            return None
        
        try:
            return self._extract_anime_info_from_page(response['text'], anime_id)
        except Exception as e:
            logger.error(f"Failed to parse IMDB anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        url = f"{self.base_url}/title/{anime_id}/"
        
        response = await self._make_request(
            session, url, headers=self._get_default_headers()
        )
        
        if not response or 'text' not in response:
            return None
        
        rating_data = self._extract_rating_from_page(response['text'])
        if not rating_data:
            return None
        
        rating = RatingData(
            website=WebsiteName.IMDB,
            raw_score=rating_data['score'],
            vote_count=rating_data['vote_count'],
            score_distribution=rating_data['score_distribution'],
            site_mean=None,  # 需要从网站统计中获取
            site_std=None,   # 需要计算
            last_updated=datetime.now(),
            url=url
        )
        
        return rating
    
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        # IMDB没有直接的季度动漫API
        logger.info(f"IMDB does not provide seasonal anime API for {season} {year}")
        return []
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据"""
        logger.info("Getting IMDB site statistics...")
        
        # IMDB评分特点的估算值
        return {
            'mean': 7.0,  # IMDB平均分相对较低
            'std': 1.2    # 标准差较大
        }


# 注册IMDB爬虫
ScraperFactory.register_scraper(WebsiteName.IMDB, IMDBScraper)
