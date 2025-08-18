# Website scrapers and API clients

# 导入所有爬虫以确保它们被注册到工厂
from .bangumi import BangumiScraper
from .mal import MALScraper
from .anilist import AniListScraper
from .douban_enhanced import DoubanEnhancedScraper  # 使用增强版豆瓣爬虫
from .imdb import IMDBScraper
from .filmarks import FilmarksScraper

# 导出基础类
from .base import BaseWebsiteScraper, APIBasedScraper, WebScrapingBasedScraper, ScraperFactory

__all__ = [
    'BaseWebsiteScraper',
    'APIBasedScraper',
    'WebScrapingBasedScraper',
    'ScraperFactory',
    'BangumiScraper',
    'MALScraper',
    'AniListScraper',
    'DoubanEnhancedScraper',  # 使用增强版豆瓣爬虫
    'IMDBScraper',
    'FilmarksScraper'
]
