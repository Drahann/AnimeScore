#!/usr/bin/env python3
"""
增强版豆瓣爬虫 - 反反爬虫版本
使用多种技术绕过豆瓣的反爬虫机制
"""
import asyncio
import aiohttp
import random
import time
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from bs4 import BeautifulSoup

from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType
from ..models.config import WebsiteConfig
from .base import WebScrapingBasedScraper
from loguru import logger


class DoubanEnhancedScraper(WebScrapingBasedScraper):
    """增强版豆瓣爬虫 - 反反爬虫版本"""
    
    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        self.base_url = config.base_url or "https://movie.douban.com"
        self.session_cookies = {}
        self.last_request_time = 0
        
        # 用户代理池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
    
    def _get_random_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """获取随机化的请求头"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',  # 移除br避免Brotli问题
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if referer:
            headers['Referer'] = referer
            headers['Sec-Fetch-Site'] = 'same-origin'
        
        return headers
    
    async def _smart_delay(self):
        """智能延迟 - 模拟人类行为"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 最小间隔3-8秒，模拟人类浏览
        min_delay = random.uniform(3.0, 8.0)
        
        if time_since_last < min_delay:
            delay = min_delay - time_since_last
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()

    async def _handle_security_redirect(self, session: aiohttp.ClientSession, response) -> Optional[Dict[str, Any]]:
        """处理豆瓣安全验证重定向"""
        response_url = str(response.url)

        if 'sec.douban.com' in response_url:
            logger.warning("检测到豆瓣安全验证页面，尝试处理...")

            try:
                html = await response.text()

                # 查找自动跳转的目标URL
                redirect_match = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html)
                if redirect_match:
                    target_url = redirect_match.group(1)
                    logger.info(f"发现自动跳转目标: {target_url}")

                    # 等待一段时间模拟人类行为
                    await asyncio.sleep(random.uniform(2, 5))

                    # 访问跳转目标
                    return await self._make_enhanced_request(
                        session, target_url, referer=response_url
                    )

                # 查找表单提交
                form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', html)
                if form_match:
                    form_action = form_match.group(1)
                    logger.info(f"发现表单提交: {form_action}")

                    # 这里可以添加表单处理逻辑
                    # 暂时返回None，表示无法处理

                logger.warning("无法自动处理安全验证页面")
                return None

            except Exception as e:
                logger.error(f"处理安全验证页面时出错: {e}")
                return None

        # 不是安全验证页面，正常返回
        if response.status == 200:
            text = await response.text()
            return {"text": text, "status": response.status}

        return None
    
    async def _make_enhanced_request(self, session: aiohttp.ClientSession, 
                                   url: str, method: str = "GET",
                                   headers: Optional[Dict[str, str]] = None,
                                   params: Optional[Dict[str, Any]] = None,
                                   referer: Optional[str] = None,
                                   max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """增强版HTTP请求 - 包含反反爬虫机制"""
        
        for attempt in range(max_retries):
            try:
                # 智能延迟
                await self._smart_delay()
                
                # 获取随机化请求头
                request_headers = headers or self._get_random_headers(referer)
                
                # 添加会话cookies
                cookies = self.session_cookies.copy()
                
                timeout = aiohttp.ClientTimeout(total=30)
                
                logger.debug(f"尝试请求 {url} (第{attempt+1}次)")
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    cookies=cookies,
                    timeout=timeout,
                    ssl=False  # 忽略SSL验证
                ) as response:
                    
                    # 更新cookies
                    if response.cookies:
                        try:
                            for cookie in response.cookies:
                                if hasattr(cookie, 'key') and hasattr(cookie, 'value'):
                                    self.session_cookies[cookie.key] = cookie.value
                                else:
                                    # 处理不同的cookie格式
                                    self.session_cookies[str(cookie)] = str(cookie)
                        except Exception as e:
                            logger.debug(f"Cookie处理错误: {e}")
                    
                    logger.debug(f"响应状态码: {response.status}")

                    if response.status == 200:
                        # 检查是否被重定向到安全验证页面
                        security_result = await self._handle_security_redirect(session, response)
                        if security_result:
                            return security_result

                        # 正常处理响应
                        if 'application/json' in response.headers.get('content-type', ''):
                            return await response.json()
                        else:
                            text = await response.text()
                            return {"text": text, "status": response.status}
                    
                    elif response.status == 403:
                        logger.warning(f"403错误，可能被反爬虫检测到，尝试{attempt+1}/{max_retries}")
                        if attempt < max_retries - 1:
                            # 增加延迟时间
                            await asyncio.sleep(random.uniform(10, 20))
                            continue
                        else:
                            logger.error("多次403错误，可能需要更换策略")
                            return None
                    
                    elif response.status == 429:
                        logger.warning(f"请求频率过高，等待后重试")
                        await asyncio.sleep(random.uniform(30, 60))
                        continue
                    
                    else:
                        logger.warning(f"请求失败: {response.status} - {url}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(5, 10))
                            continue
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"请求超时: {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(5, 10))
                    continue
                return None
                
            except Exception as e:
                logger.error(f"请求异常: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(5, 10))
                    continue
                return None
        
        return None
    
    async def _init_session(self, session: aiohttp.ClientSession) -> bool:
        """初始化会话 - 获取必要的cookies"""
        logger.info("🔧 初始化豆瓣会话...")
        
        # 首先访问豆瓣首页获取基础cookies
        home_response = await self._make_enhanced_request(
            session, "https://www.douban.com", referer=None
        )
        
        if not home_response:
            logger.warning("无法访问豆瓣首页")
            return False
        
        # 访问电影首页
        movie_response = await self._make_enhanced_request(
            session, "https://movie.douban.com", referer="https://www.douban.com"
        )
        
        if not movie_response:
            logger.warning("无法访问豆瓣电影首页")
            return False
        
        logger.info("✅ 豆瓣会话初始化成功")
        return True
    
    async def search_anime_with_mobile_api(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用移动端API搜索动漫"""
        logger.info(f"📱 使用移动端API搜索: {title}")
        
        # 移动端API通常反爬虫较弱
        mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://m.douban.com/',
        }
        
        # 尝试移动端搜索API
        mobile_search_url = "https://m.douban.com/rexxar/api/v2/search"
        params = {
            'q': title,
            'type': 'movie',
            'count': 10
        }
        
        response = await self._make_enhanced_request(
            session, mobile_search_url, headers=mobile_headers, params=params,
            referer="https://m.douban.com/"
        )
        
        if response and 'items' in response:
            logger.info(f"移动端API搜索成功，找到 {len(response['items'])} 个结果")
            # 这里需要解析移动端API的响应格式
            return []  # 暂时返回空列表，需要根据实际API响应格式实现
        
        logger.warning("移动端API搜索失败")
        return []
    
    async def search_anime_with_proxy(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用代理搜索动漫"""
        logger.info(f"🌐 使用代理搜索: {title}")
        
        # 这里可以配置代理服务器
        # 注意：需要有效的代理服务器配置
        proxy_url = None  # "http://proxy-server:port"
        
        if not proxy_url:
            logger.warning("未配置代理服务器")
            return []
        
        # 使用代理的请求逻辑
        # 实际实现需要根据代理服务器配置
        return []

    async def search_anime_with_selenium(self, title: str) -> List[AnimeInfo]:
        """使用Selenium模拟浏览器搜索"""
        logger.info(f"🤖 使用Selenium搜索: {title}")

        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options

            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 随机User-Agent
            chrome_options.add_argument(f'--user-agent={random.choice(self.user_agents)}')

            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                # 访问豆瓣搜索页面
                search_url = f"https://movie.douban.com/search?q={title}"
                driver.get(search_url)

                # 等待页面加载
                wait = WebDriverWait(driver, 10)

                # 查找搜索结果
                results = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.result')))

                anime_list = []
                for result in results[:5]:  # 限制结果数量
                    try:
                        # 提取动漫信息
                        title_element = result.find_element(By.CSS_SELECTOR, '.title a')
                        anime_title = title_element.text
                        anime_url = title_element.get_attribute('href')

                        # 提取豆瓣ID
                        douban_id = re.search(r'/subject/(\d+)/', anime_url)
                        if douban_id:
                            douban_id = douban_id.group(1)

                            # 创建AnimeInfo对象
                            anime_info = AnimeInfo(
                                title=anime_title,
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )
                            anime_list.append(anime_info)

                    except Exception as e:
                        logger.warning(f"解析搜索结果失败: {e}")
                        continue

                return anime_list

            finally:
                driver.quit()

        except ImportError:
            logger.warning("Selenium未安装，无法使用浏览器模拟")
            return []
        except Exception as e:
            logger.error(f"Selenium搜索失败: {e}")
            return []

    async def search_anime_alternative_sites(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用替代网站搜索豆瓣ID"""
        logger.info(f"🔄 使用替代网站搜索豆瓣ID: {title}")

        # 可以使用其他网站的豆瓣链接来获取豆瓣ID
        # 例如：某些影评网站、聚合网站等

        # 示例：使用百度搜索豆瓣链接
        baidu_search_url = "https://www.baidu.com/s"
        params = {
            'wd': f'site:movie.douban.com {title}',
            'rn': 10
        }

        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        response = await self._make_enhanced_request(
            session, baidu_search_url, params=params, headers=headers
        )

        if response and 'text' in response:
            # 从百度搜索结果中提取豆瓣链接
            douban_links = re.findall(r'https://movie\.douban\.com/subject/(\d+)/', response['text'])

            anime_list = []
            for douban_id in douban_links[:3]:  # 限制数量
                anime_info = AnimeInfo(
                    title=title,  # 使用搜索关键词作为临时标题
                    external_ids={WebsiteName.DOUBAN: douban_id}
                )
                anime_list.append(anime_info)

            if anime_list:
                logger.info(f"通过替代网站找到 {len(anime_list)} 个豆瓣ID")
                return anime_list

        logger.warning("替代网站搜索失败")
        return []

    async def search_anime(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """搜索动漫 - 多策略尝试"""
        logger.info(f"🔍 豆瓣增强搜索: {title}")

        # 初始化会话
        if not await self._init_session(session):
            logger.warning("会话初始化失败，尝试其他方法")

        # 策略1: 尝试原始搜索方法
        try:
            results = await self._try_original_search(session, title)
            if results:
                logger.info(f"原始搜索成功，找到 {len(results)} 个结果")
                return results
        except Exception as e:
            logger.warning(f"原始搜索失败: {e}")

        # 策略2: 移动端API
        try:
            results = await self.search_anime_with_mobile_api(session, title)
            if results:
                logger.info(f"移动端API搜索成功")
                return results
        except Exception as e:
            logger.warning(f"移动端API搜索失败: {e}")

        # 策略3: 替代网站搜索
        try:
            results = await self.search_anime_alternative_sites(session, title)
            if results:
                logger.info(f"替代网站搜索成功")
                return results
        except Exception as e:
            logger.warning(f"替代网站搜索失败: {e}")

        # 策略4: Selenium (最后手段)
        try:
            results = await self.search_anime_with_selenium(title)
            if results:
                logger.info(f"Selenium搜索成功")
                return results
        except Exception as e:
            logger.warning(f"Selenium搜索失败: {e}")

        logger.error(f"所有搜索策略都失败了: {title}")
        return []

    async def _try_original_search(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """尝试原始搜索方法"""
        search_url = "https://search.douban.com/movie/subject_search"
        params = {
            'search_text': title,
            'cat': '1002'  # 动漫分类
        }

        response = await self._make_enhanced_request(
            session, search_url, params=params,
            referer="https://movie.douban.com"
        )

        if not response or 'text' not in response:
            return []

        # 解析搜索结果
        html = response['text']
        results = []

        try:
            # 查找 window.__DATA__ 中的数据
            data_match = re.search(r'window\.__DATA__\s*=\s*({.*?});', html, re.DOTALL)
            if data_match:
                data = json.loads(data_match.group(1))
                items = data.get('items', [])

                for item in items[:5]:
                    try:
                        douban_id = str(item.get('id', ''))
                        if douban_id:
                            anime_info = AnimeInfo(
                                title=item.get('title', title),
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )
                            results.append(anime_info)
                    except Exception as e:
                        logger.warning(f"解析搜索项失败: {e}")
                        continue

            return results

        except Exception as e:
            logger.error(f"解析搜索响应失败: {e}")
            return []

    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据"""
        url = f"{self.base_url}/subject/{anime_id}/"

        response = await self._make_enhanced_request(
            session, url, referer=f"{self.base_url}"
        )

        if not response or 'text' not in response:
            return None

        try:
            rating_data = self._extract_rating_from_page(response['text'])
            if not rating_data:
                return None

            rating = RatingData(
                website=WebsiteName.DOUBAN,
                raw_score=rating_data['score'],
                vote_count=rating_data['vote_count'],
                score_distribution=rating_data['score_distribution'],
                site_mean=None,
                site_std=None,
                last_updated=datetime.now(),
                url=url
            )

            return rating

        except Exception as e:
            logger.error(f"获取豆瓣评分失败 {anime_id}: {e}")
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

        return {
            'score': raw_score,
            'vote_count': vote_count,
            'score_distribution': {}
        }

    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/subject/{anime_id}/"

        response = await self._make_enhanced_request(
            session, url, referer=f"{self.base_url}"
        )

        if not response or 'text' not in response:
            return None

        try:
            return self._extract_anime_info_from_page(response['text'], anime_id)
        except Exception as e:
            logger.error(f"获取豆瓣动漫详情失败 {anime_id}: {e}")
            return None

    def _extract_anime_info_from_page(self, html: str, douban_id: str) -> Optional[AnimeInfo]:
        """从豆瓣页面提取动漫信息"""
        soup = BeautifulSoup(html, 'html.parser')

        # 标题
        title_element = soup.find('span', property='v:itemreviewed')
        title = title_element.text.strip() if title_element else ''

        # 基本信息
        info_element = soup.find('div', id='info')
        if not info_element:
            return AnimeInfo(
                title=title,
                external_ids={WebsiteName.DOUBAN: douban_id}
            )

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

        anime_info = AnimeInfo(
            title=title,
            anime_type=anime_type,
            episodes=episodes,
            start_date=start_date,
            studios=studios,
            genres=genres,
            external_ids={WebsiteName.DOUBAN: douban_id}
        )

        return anime_info

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

    async def get_seasonal_anime(self, session: aiohttp.ClientSession, season: str, year: int) -> List[AnimeInfo]:
        """获取季度动漫列表 - 豆瓣不提供此功能"""
        logger.warning("豆瓣不提供季度动漫列表功能")
        return []

    async def get_site_statistics(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """获取网站统计信息 - 豆瓣不提供此功能"""
        logger.warning("豆瓣不提供网站统计信息")
        return {}
