"""
基础爬虫和API客户端类
"""
import asyncio
import aiohttp
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from loguru import logger

from ..models.anime import AnimeInfo, RatingData, WebsiteName
from ..models.config import WebsiteConfig


class BaseWebsiteScraper(ABC):
    """网站数据获取基类"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        self.website_name = website_name
        self.config = config
        self.last_request_time = 0
        
    async def _rate_limit(self):
        """实现请求频率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.config.rate_limit:
            sleep_time = self.config.rate_limit - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, session: aiohttp.ClientSession, 
                          url: str, method: str = "GET", 
                          headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None,
                          json_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """发起HTTP请求"""
        await self._rate_limit()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout
            ) as response:
                
                if response.status == 200:
                    if 'application/json' in response.headers.get('content-type', ''):
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"text": text}
                else:
                    logger.warning(f"Request failed: {response.status} - {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error for {url}: {e}")
            return None
    
    @abstractmethod
    async def search_anime(self, session: aiohttp.ClientSession, 
                          title: str) -> List[AnimeInfo]:
        """搜索动漫"""
        pass
    
    @abstractmethod
    async def get_anime_details(self, session: aiohttp.ClientSession, 
                               anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        pass
    
    @abstractmethod
    async def get_anime_rating(self, session: aiohttp.ClientSession, 
                              anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        pass
    
    @abstractmethod
    async def get_seasonal_anime(self, session: aiohttp.ClientSession, 
                                year: int, season: str) -> List[AnimeInfo]:
        """获取季度动漫列表"""
        pass
    
    @abstractmethod
    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Optional[Dict[str, float]]:
        """获取网站统计数据（平均分、标准差等）"""
        pass
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enabled


class APIBasedScraper(BaseWebsiteScraper):
    """基于API的数据获取器基类"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig, api_keys: Dict[str, str]):
        super().__init__(website_name, config)
        self.api_keys = api_keys
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        return {}


class WebScrapingBasedScraper(BaseWebsiteScraper):
    """基于网页爬虫的数据获取器基类"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        
    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }


class ScraperFactory:
    """爬虫工厂类"""
    
    _scrapers = {}
    
    @classmethod
    def register_scraper(cls, website_name: WebsiteName, scraper_class):
        """注册爬虫类"""
        cls._scrapers[website_name] = scraper_class
    
    @classmethod
    def create_scraper(cls, website_name: WebsiteName, 
                      config: WebsiteConfig, 
                      api_keys: Optional[Dict[str, str]] = None) -> Optional[BaseWebsiteScraper]:
        """创建爬虫实例"""
        if website_name not in cls._scrapers:
            logger.error(f"No scraper registered for {website_name}")
            return None
        
        scraper_class = cls._scrapers[website_name]
        
        try:
            # 检查是否需要API密钥
            if issubclass(scraper_class, APIBasedScraper):
                if not api_keys:
                    logger.error(f"API keys required for {website_name}")
                    return None
                return scraper_class(website_name, config, api_keys)
            else:
                return scraper_class(website_name, config)
        except Exception as e:
            logger.error(f"Failed to create scraper for {website_name}: {e}")
            return None
    
    @classmethod
    def get_available_scrapers(cls) -> List[WebsiteName]:
        """获取可用的爬虫列表"""
        return list(cls._scrapers.keys())
