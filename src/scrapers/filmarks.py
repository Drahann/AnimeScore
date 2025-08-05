"""
Filmarks 网页爬虫 - 优化版本
支持动漫专门搜索和精确的投票数提取
"""
import aiohttp
import asyncio
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urljoin

from .base import WebScrapingBasedScraper, ScraperFactory
from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType, AnimeStatus, Season
from ..models.config import WebsiteConfig
from ..utils.season_utils import get_season_from_date


class FilmarksScraper(WebScrapingBasedScraper):
    """Filmarks 网页爬虫 - 优化版本"""

    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        self.base_url = config.base_url or "https://filmarks.com"
        # 网络配置优化
        self.timeout = 30  # 增加超时时间到30秒
        self.rate_limit = 3.0  # 增加请求间隔到3秒
        self.max_retries = 3  # 最大重试次数

    def _get_optimized_headers(self) -> Dict[str, str]:
        """获取优化的HTTP头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def _parse_anime_type(self, filmarks_type: str) -> Optional[AnimeType]:
        """解析Filmarks类型"""
        if 'TV' in filmarks_type or 'テレビ' in filmarks_type:
            return AnimeType.TV
        elif '映画' in filmarks_type or 'Movie' in filmarks_type:
            return AnimeType.MOVIE
        elif 'OVA' in filmarks_type:
            return AnimeType.OVA
        elif 'ONA' in filmarks_type:
            return AnimeType.ONA
        else:
            return AnimeType.TV
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析Filmarks日期"""
        if not date_str:
            return None
        
        try:
            # Filmarks日期格式通常是 "2024年1月15日"
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
            if date_match:
                year, month, day = date_match.groups()
                return date(int(year), int(month), int(day))
            
            # 尝试其他格式
            date_match = re.search(r'(\d{4})年(\d{1,2})月', date_str)
            if date_match:
                year, month = date_match.groups()
                return date(int(year), int(month), 1)
                
            date_match = re.search(r'(\d{4})', date_str)
            if date_match:
                year = date_match.group(1)
                return date(int(year), 1, 1)
                
        except ValueError:
            pass
        
        logger.warning(f"Failed to parse Filmarks date: {date_str}")
        return None
    
    def _extract_rating_from_page(self, html: str) -> Optional[Dict[str, Any]]:
        """从Filmarks页面提取评分信息 - 优化版本"""
        soup = BeautifulSoup(html, 'html.parser')

        # 查找评分 - 使用多种选择器
        rating_text = None
        rating_selectors = [
            'span.c-rating__score',
            '.rating-score',
            '[class*="rating"]',
        ]

        for selector in rating_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                # 查找数字格式的评分
                if re.match(r'^\d+\.?\d*$', text):
                    rating_text = text
                    logger.debug(f"找到可能的评分: {rating_text}")
                    break
            if rating_text:
                break

        # 如果没找到，尝试在所有文本中查找评分模式
        if not rating_text:
            rating_patterns = [
                r'(\d\.\d)',  # 如 4.4
                r'★+\s*(\d\.\d)',  # 星级评分
            ]

            for pattern in rating_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    rating_text = matches[0]
                    logger.debug(f"通过模式匹配找到评分: {rating_text}")
                    break

        if not rating_text:
            logger.warning("未找到评分信息")
            return None

        try:
            # 解析评分（5星制转10分制）
            raw_score = float(rating_text)
            if raw_score <= 5:
                raw_score = raw_score * 2
            logger.debug(f"解析到评分: {rating_text} -> {raw_score}/10")
        except ValueError:
            logger.warning(f"无法解析评分: {rating_text}")
            return None

        # 查找投票数 - 使用优化的方法
        vote_count = 0

        # 方法1: 查找meta标签中的投票数
        meta_patterns = [
            r'レビュー数：(\d+(?:,\d+)*)件',
            r'感想・レビュー\[(\d+(?:,\d+)*)件\]',
        ]

        for meta_tag in soup.find_all('meta'):
            content = meta_tag.get('content', '')
            for pattern in meta_patterns:
                match = re.search(pattern, content)
                if match:
                    vote_count = int(match.group(1).replace(',', ''))
                    logger.debug(f"在meta标签中找到投票数: {vote_count}")
                    break
            if vote_count > 0:
                break

        # 方法2: 查找JavaScript中的数据
        if vote_count == 0:
            js_patterns = [
                r'&quot;count&quot;:(\d+)',  # HTML转义的JSON
                r'"count"\s*:\s*(\d+)',       # 普通JSON
                r'count["\']?\s*:\s*(\d+)',   # 变量赋值
            ]

            for pattern in js_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    candidate_count = int(match.group(1))
                    # 验证数字是否在合理范围内
                    if 100 <= candidate_count <= 100000:
                        vote_count = candidate_count
                        logger.debug(f"在JavaScript数据中找到投票数: {vote_count}")
                        break

        # 方法3: 智能数字筛选（排除演员ID等）
        if vote_count == 0:
            number_candidates = []
            for text_node in soup.find_all(string=re.compile(r'\d+')):
                text = str(text_node).strip()
                numbers = re.findall(r'\d+(?:,\d+)*', text)
                for num_str in numbers:
                    try:
                        num = int(num_str.replace(',', ''))
                        # 投票数通常在1000-100000之间
                        if 1000 <= num <= 100000:
                            # 排除演员ID（检查是否在演员链接中）
                            is_actor_id = False
                            parent = text_node.parent if hasattr(text_node, 'parent') else None
                            if parent:
                                if parent.name == 'a' and '/people/' in parent.get('href', ''):
                                    is_actor_id = True
                                elif parent.parent and parent.parent.name == 'a' and '/people/' in parent.parent.get('href', ''):
                                    is_actor_id = True

                            if not is_actor_id:
                                number_candidates.append(num)
                    except ValueError:
                        continue

            if number_candidates:
                vote_count = max(number_candidates)
                logger.debug(f"选择最大候选数字作为投票数: {vote_count}")

        if vote_count == 0:
            logger.warning("未找到投票数，使用默认值5000")
            vote_count = 5000

        return {
            'score': raw_score,
            'vote_count': vote_count,
            'score_distribution': {}  # Filmarks不提供详细分布
        }
    
    def _extract_anime_info_from_page(self, html: str, filmarks_id: str) -> Optional[AnimeInfo]:
        """从Filmarks页面提取动漫信息"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 标题
        title_element = soup.find('h1', class_='p-content-detail__title')
        if not title_element:
            title_element = soup.find('h1')
        
        title = title_element.text.strip() if title_element else ''
        
        # 基本信息
        info_section = soup.find('div', class_='p-content-detail__other-info')
        if not info_section:
            return None
        
        info_text = info_section.get_text()
        
        # 解析信息
        anime_type = None
        start_date = None
        genres = []
        
        # 查找类型
        type_match = re.search(r'ジャンル[：:]\s*([^\n]+)', info_text)
        if type_match:
            genre_str = type_match.group(1).strip()
            genres = [g.strip() for g in genre_str.split('、') if g.strip()]
            if genres:
                anime_type = self._parse_anime_type(genres[0])
        
        # 查找公开日期
        date_match = re.search(r'公開[：:]\s*([^\n]+)', info_text)
        if date_match:
            start_date = self._parse_date(date_match.group(1).strip())
        
        # 解析季度
        season = None
        year = None
        if start_date:
            season, year = get_season_from_date(start_date)
        
        # 简介
        synopsis = ''
        synopsis_element = soup.find('div', class_='p-content-detail__summary')
        if synopsis_element:
            synopsis = synopsis_element.get_text().strip()
        
        anime_info = AnimeInfo(
            title=title,
            anime_type=anime_type,
            start_date=start_date,
            season=season,
            year=year,
            genres=genres,
            external_ids={WebsiteName.FILMARKS: filmarks_id},
            synopsis=synopsis
        )
        
        return anime_info
    
    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫 - 使用动漫专门搜索"""
        logger.info(f"🔍 搜索动漫: {title}")

        # 使用正确的动漫搜索URL
        search_url = f"{self.base_url}/search/animes"
        params = {'q': title}

        logger.debug(f"请求URL: {search_url}")
        logger.debug(f"请求参数: {params}")

        # 添加重试机制
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    session, search_url, params=params, headers=self._get_optimized_headers()
                )

                if not response or 'text' not in response:
                    logger.warning(f"搜索请求失败 (尝试 {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    return []

                html = response['text']
                logger.debug(f"响应长度: {len(html)} 字符")

                # 解析搜索结果
                results = self._parse_search_results(html)
                logger.info(f"找到 {len(results)} 个搜索结果")

                return results

            except asyncio.TimeoutError:
                logger.warning(f"搜索请求超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"搜索动漫失败: 连接超时")
                return []
            except Exception as e:
                logger.warning(f"搜索请求异常: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"搜索动漫失败: {e}")
                return []

        return []

    def _parse_search_results(self, html: str) -> List[AnimeInfo]:
        """解析搜索结果"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # 尝试多种选择器
        selectors = [
            'div.p-content-cassette',
            'div.c-content-cassette',
            'div[class*="content"]'
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.debug(f"使用选择器 '{selector}' 找到 {len(items)} 个结果")
                break

        for item in items[:5]:  # 限制结果数量
            try:
                anime_info = self._extract_anime_info_from_search_item(item)
                if anime_info:
                    logger.debug(f"提取到动漫: {anime_info.title}")
                    results.append(anime_info)
            except Exception as e:
                logger.warning(f"解析搜索结果项失败: {e}")
                continue

        return results

    def _extract_anime_info_from_search_item(self, item) -> Optional[AnimeInfo]:
        """从搜索结果项中提取动漫信息"""
        try:
            # 查找动漫链接 - 动漫URL格式是 /animes/series_id/season_id
            link_elem = item if item.name == 'a' else item.find('a', href=re.compile(r'/animes/\d+/\d+'))
            if not link_elem:
                return None

            href = link_elem.get('href', '')
            if not href:
                return None

            # 提取动漫ID - 格式: /animes/series_id/season_id
            id_match = re.search(r'/animes/(\d+)/(\d+)', href)
            if not id_match:
                return None

            series_id = id_match.group(1)
            season_id = id_match.group(2)
            filmarks_id = f"{series_id}_{season_id}"  # 组合ID
            url = urljoin(self.base_url, href)

            # 提取标题
            title_elem = None
            title_selectors = [
                'h3',
                '.p-content-cassette__title',
                '.c-content-cassette__title',
                '[class*="title"]'
            ]

            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    break

            # 如果在当前项中没找到，尝试在父元素中查找
            if not title_elem and hasattr(item, 'parent'):
                parent = item.parent
                for selector in title_selectors:
                    title_elem = parent.select_one(selector) if parent else None
                    if title_elem:
                        break

            # 提取标题文本
            if title_elem:
                title = title_elem.get_text(strip=True)
                # 清理标题，移除不需要的文本
                unwanted_texts = ['>>続きを読む', '>>詳しい情報を見る', '>>動画配信サービスがあるか確認する', '>>配信中の動画配信サービスをもっと見る']
                if title in unwanted_texts:
                    title = f"Anime {filmarks_id}"
            else:
                title = f"Anime {filmarks_id}"

            # 提取年份（如果有）
            year = None
            year_match = re.search(r'\((\d{4})\)', title)
            if year_match:
                year = int(year_match.group(1))

            anime_info = AnimeInfo(
                title=title,
                external_ids={WebsiteName.FILMARKS: filmarks_id},
                year=year
            )

            return anime_info

        except Exception as e:
            logger.warning(f"提取动漫信息失败: {e}")
            return None
    
    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        # 动漫ID格式: series_id_season_id
        if '_' in anime_id:
            series_id, season_id = anime_id.split('_', 1)
            url = f"{self.base_url}/animes/{series_id}/{season_id}"
        else:
            # 兼容旧格式
            url = f"{self.base_url}/movies/{anime_id}"

        response = await self._make_request(
            session, url, headers=self._get_optimized_headers()
        )

        if not response or 'text' not in response:
            return None

        try:
            return self._extract_anime_info_from_page(response['text'], anime_id)
        except Exception as e:
            logger.error(f"Failed to parse Filmarks anime details for {anime_id}: {e}")
            return None
    
    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据 - 优化版本"""
        # 动漫ID格式: series_id_season_id
        if '_' in anime_id:
            series_id, season_id = anime_id.split('_', 1)
            url = f"{self.base_url}/animes/{series_id}/{season_id}"
        else:
            # 兼容旧格式
            url = f"{self.base_url}/movies/{anime_id}"

        logger.info(f"📊 获取评分: {anime_id}")

        # 添加重试机制
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    session, url, headers=self._get_optimized_headers()
                )

                if not response or 'text' not in response:
                    logger.warning(f"获取评分页面失败 (尝试 {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    return None

                html = response['text']
                logger.debug(f"评分页面长度: {len(html)} 字符")

                # 解析评分信息
                rating_data = self._extract_rating_from_page(html)
                if not rating_data:
                    logger.warning("❌ 未能解析评分信息")
                    return None

                logger.info(f"✅ 获取到评分: {rating_data['score']} ({rating_data['vote_count']} 票)")

                rating = RatingData(
                    website=WebsiteName.FILMARKS,
                    raw_score=rating_data['score'],
                    vote_count=rating_data['vote_count'],
                    score_distribution=rating_data['score_distribution'],
                    site_mean=None,  # 需要从网站统计中获取
                    site_std=None,   # 需要计算
                    last_updated=datetime.now(),
                    url=url
                )

                return rating

            except asyncio.TimeoutError:
                logger.warning(f"获取评分页面超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"获取动漫评分失败: 连接超时")
                return None
            except Exception as e:
                logger.warning(f"获取评分页面异常: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"获取动漫评分失败: {e}")
                return None

        # 所有重试都失败了
        logger.error("所有重试都失败，无法获取评分页面")
        return None
    
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        # Filmarks没有直接的季度动漫API
        logger.info(f"Filmarks does not provide seasonal anime API for {season} {year}")
        return []
    
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据"""
        logger.info("Getting Filmarks site statistics...")
        
        # Filmarks评分特点的估算值（转换为10分制）
        return {
            'mean': 7.6,  # 5星制转换后的平均分
            'std': 0.8    # 标准差
        }


# 注册Filmarks爬虫
ScraperFactory.register_scraper(WebsiteName.FILMARKS, FilmarksScraper)
