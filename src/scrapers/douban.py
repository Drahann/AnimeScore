"""
豆瓣网页爬虫
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


class DoubanScraper(WebScrapingBasedScraper):
    """豆瓣网页爬虫"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        self.base_url = config.base_url or "https://movie.douban.com"
        
    def _parse_anime_type(self, douban_type: str) -> Optional[AnimeType]:
        """解析豆瓣动漫类型"""
        if '电视' in douban_type or 'TV' in douban_type:
            return AnimeType.TV
        elif '电影' in douban_type or '剧场版' in douban_type:
            return AnimeType.MOVIE
        elif 'OVA' in douban_type:
            return AnimeType.OVA
        elif 'ONA' in douban_type:
            return AnimeType.ONA
        elif '特别篇' in douban_type or '特典' in douban_type:
            return AnimeType.SPECIAL
        else:
            return AnimeType.TV  # 默认为TV
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析豆瓣日期字符串"""
        if not date_str:
            return None
        
        # 豆瓣日期格式多样，尝试多种解析方式
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2024-01-15
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 2024年1月15日
            r'(\d{4})年(\d{1,2})月',  # 2024年1月
            r'(\d{4})',  # 2024
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    groups = match.groups()
                    year = int(groups[0])
                    month = int(groups[1]) if len(groups) > 1 else 1
                    day = int(groups[2]) if len(groups) > 2 else 1
                    return date(year, month, day)
                except ValueError:
                    continue
        
        logger.warning(f"Failed to parse Douban date: {date_str}")
        return None
    
    def _extract_rating_from_page(self, html: str) -> Optional[Dict[str, Any]]:
        """从豆瓣页面提取评分信息"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找评分
        rating_element = soup.find('strong', class_='ll rating_num')
        if not rating_element:
            return None
        
        try:
            raw_score = float(rating_element.text.strip())
        except ValueError:
            return None
        
        # 查找评分人数
        vote_count = 0
        rating_people = soup.find('a', class_='rating_people')
        if rating_people:
            vote_text = rating_people.text
            vote_match = re.search(r'(\d+)', vote_text)
            if vote_match:
                vote_count = int(vote_match.group(1))
        
        # 查找评分分布
        score_distribution = {}
        rating_per = soup.find_all('span', class_='rating_per')
        if len(rating_per) == 5:
            # 豆瓣是5星制，转换为10分制
            for i, per in enumerate(rating_per):
                score = 10 - i * 2  # 5星=10分, 4星=8分, ..., 1星=2分
                percent_text = per.text.strip().replace('%', '')
                try:
                    percent = float(percent_text)
                    count = int(vote_count * percent / 100)
                    score_distribution[str(score)] = count
                except ValueError:
                    continue
        
        return {
            'score': raw_score,
            'vote_count': vote_count,
            'score_distribution': score_distribution
        }
    
    def _extract_anime_info_from_page(self, html: str, douban_id: str) -> Optional[AnimeInfo]:
        """从豆瓣页面提取动漫信息"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 标题
        title_element = soup.find('span', property='v:itemreviewed')
        title = title_element.text.strip() if title_element else ''
        
        # 基本信息
        info_element = soup.find('div', id='info')
        if not info_element:
            return None
        
        info_text = info_element.get_text()
        
        # 解析基本信息
        anime_type = None
        episodes = None
        start_date = None
        studios = []
        genres = []
        
        # 查找类型
        type_match = re.search(r'类型:\s*([^\n]+)', info_text)
        if type_match:
            type_str = type_match.group(1).strip()
            anime_type = self._parse_anime_type(type_str)
            genres = [g.strip() for g in type_str.split('/') if g.strip()]
        
        # 查找集数
        episodes_match = re.search(r'集数:\s*(\d+)', info_text)
        if episodes_match:
            episodes = int(episodes_match.group(1))
        
        # 查找首播日期
        date_match = re.search(r'首播:\s*([^\n]+)', info_text)
        if date_match:
            start_date = self._parse_date(date_match.group(1).strip())
        
        # 查找制作公司
        studio_match = re.search(r'制片国家/地区:\s*([^\n]+)', info_text)
        if studio_match:
            studios = [s.strip() for s in studio_match.group(1).split('/') if s.strip()]
        
        # 解析季度
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 简介
        synopsis = ''
        summary_element = soup.find('span', property='v:summary')
        if summary_element:
            synopsis = summary_element.get_text().strip()
        
        anime_info = AnimeInfo(
            title=title,
            anime_type=anime_type,
            episodes=episodes,
            start_date=start_date,
            season=season,
            year=year,
            studios=studios,
            genres=genres,
            external_ids={WebsiteName.DOUBAN: douban_id},
            synopsis=synopsis
        )
        
        return anime_info
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫"""
        logger.info(f"🔍 豆瓣搜索动漫: {title}")

        # 使用正确的搜索URL
        search_url = "https://search.douban.com/movie/subject_search"
        params = {
            'search_text': title,
            'cat': '1002'  # 动漫分类
        }

        response = await self._make_request(
            session, search_url, params=params, headers=self._get_default_headers()
        )

        if not response or 'text' not in response:
            logger.warning("豆瓣搜索请求失败")
            return []

        # 从JavaScript数据中提取搜索结果
        html = response['text']
        results = []

        try:
            # 查找 window.__DATA__ 中的数据
            data_match = re.search(r'window\.__DATA__\s*=\s*({.*?});', html, re.DOTALL)
            if data_match:
                import json
                data = json.loads(data_match.group(1))
                items = data.get('items', [])

                logger.debug(f"豆瓣搜索找到 {len(items)} 个结果")

                for item in items[:5]:  # 限制结果数量
                    try:
                        douban_id = str(item.get('id', ''))
                        if not douban_id:
                            continue

                        logger.debug(f"找到豆瓣ID: {douban_id}")

                        # 获取详细信息
                        anime_info = await self.get_anime_details(session, douban_id)
                        if anime_info:
                            results.append(anime_info)
                            logger.debug(f"成功获取动漫信息: {anime_info.title}")

                        # 添加延迟避免请求过快
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.warning(f"解析豆瓣搜索结果失败: {e}")
                        continue
            else:
                logger.warning("未找到豆瓣搜索数据")

        except Exception as e:
            logger.error(f"解析豆瓣搜索响应失败: {e}")

        logger.info(f"豆瓣搜索完成，找到 {len(results)} 个有效结果")
        return results
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/subject/{anime_id}/"
        
        response = await self._make_request(
            session, url, headers=self._get_default_headers()
        )
        
        if not response or 'text' not in response:
            return None
        
        try:
            return self._extract_anime_info_from_page(response['text'], anime_id)
        except Exception as e:
            logger.error(f"Failed to parse Douban anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        url = f"{self.base_url}/subject/{anime_id}/"
        
        response = await self._make_request(
            session, url, headers=self._get_default_headers()
        )
        
        if not response or 'text' not in response:
            return None
        
        rating_data = self._extract_rating_from_page(response['text'])
        if not rating_data:
            return None
        
        rating = RatingData(
            website=WebsiteName.DOUBAN,
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
        # 豆瓣没有直接的季度动漫API，这里返回空列表
        # 实际使用中可能需要通过其他方式获取季度动漫列表
        logger.info(f"Douban does not provide seasonal anime API for {season} {year}")
        return []
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据"""
        logger.info("Getting Douban site statistics...")
        
        # 豆瓣动漫评分特点的估算值
        return {
            'mean': 8.0,  # 豆瓣评分通常较高
            'std': 0.7    # 标准差中等
        }


# 注册豆瓣爬虫
ScraperFactory.register_scraper(WebsiteName.DOUBAN, DoubanScraper)
