#!/usr/bin/env python3
"""
增强版豆瓣爬虫 - 终极反反爬虫版本
使用多种先进技术绕过豆瓣的反爬虫机制
"""
import asyncio
import aiohttp
import random
import time
import json
import re
import hashlib
import base64
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from datetime import datetime, date
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote, unquote

from ..models.anime import AnimeInfo, RatingData, WebsiteName, AnimeType
from ..models.config import WebsiteConfig
from .base import WebScrapingBasedScraper
from loguru import logger

class DoubanEnhancedScraper(WebScrapingBasedScraper):
    """增强版豆瓣爬虫 - 终极反反爬虫版本"""

    def __init__(self, website_name: WebsiteName, config: WebsiteConfig):
        super().__init__(website_name, config)
        self.base_url = config.base_url or "https://movie.douban.com"
        self.session_cookies = {}
        self.last_request_time = 0
        self.session_id = self._generate_session_id()
        self.request_count = 0
        self.failed_attempts = 0
        self.current_user_agent = None
        self.current_browser_type = None
        self.session_start_time = time.time()

        # 更真实的用户代理池 - 2025年最新版本，包含更多变体
        self.user_agents = [
            # Chrome Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',

            # Chrome macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',

            # Firefox Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',

            # Safari macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',

            # Edge Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',

            # Chrome Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0',
        ]

        # 代理池配置
        self.proxy_pool = []
        self.current_proxy_index = 0
        self.proxy_failure_count = {}

        # TLS指纹伪装
        self.tls_versions = ['TLSv1.2', 'TLSv1.3']

        # 增强的浏览器指纹伪装
        self.browser_fingerprints = {
            'chrome': {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept_encoding': 'gzip, deflate, br, zstd',
                'accept_language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'sec_ch_ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
                'sec_ch_ua_platform_version': '"15.0.0"',
                'sec_fetch_dest': 'document',
                'sec_fetch_mode': 'navigate',
                'sec_fetch_site': 'none',
                'sec_fetch_user': '?1',
                'upgrade_insecure_requests': '1',
                'cache_control': 'max-age=0'
            },
            'firefox': {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'upgrade_insecure_requests': '1',
                'te': 'trailers'
            },
            'safari': {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'zh-CN,zh-Hans;q=0.9,en;q=0.8',
                'upgrade_insecure_requests': '1'
            },
            'edge': {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'sec_ch_ua': '"Microsoft Edge";v="122", "Chromium";v="122", "Not(A:Brand";v="24"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
                'sec_fetch_dest': 'document',
                'sec_fetch_mode': 'navigate',
                'sec_fetch_site': 'none',
                'sec_fetch_user': '?1',
                'upgrade_insecure_requests': '1'
            }
        }

        # 屏幕分辨率池（用于生成更真实的指纹）
        self.screen_resolutions = [
            '1920x1080', '1366x768', '1536x864', '1440x900', '1280x720',
            '2560x1440', '3840x2160', '1680x1050', '1600x900', '1024x768'
        ]

        # 时区列表
        self.timezones = [
            'Asia/Shanghai', 'Asia/Beijing', 'Asia/Hong_Kong', 'Asia/Taipei'
        ]

    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        return hashlib.md5(f"{timestamp}_{random_str}".encode()).hexdigest()[:16]

    def _get_next_proxy(self) -> Optional[str]:
        """获取下一个代理"""
        if not self.proxy_pool:
            return None

        proxy = self.proxy_pool[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_pool)
        return proxy

    def _detect_browser_type(self, user_agent: str) -> str:
        """根据User-Agent检测浏览器类型"""
        if 'Edg/' in user_agent:
            return 'edge'
        elif 'Chrome' in user_agent and 'Safari' in user_agent and 'Edg' not in user_agent:
            return 'chrome'
        elif 'Firefox' in user_agent:
            return 'firefox'
        elif 'Safari' in user_agent and 'Chrome' not in user_agent:
            return 'safari'
        else:
            return 'chrome'  # 默认

    def _select_consistent_user_agent(self) -> str:
        """选择一个一致的User-Agent并保持会话期间不变"""
        if not self.current_user_agent:
            self.current_user_agent = random.choice(self.user_agents)
            self.current_browser_type = self._detect_browser_type(self.current_user_agent)
            logger.debug(f"🎭 选择浏览器类型: {self.current_browser_type}")
        return self.current_user_agent

    def _generate_browser_fingerprint(self) -> Dict[str, str]:
        """生成一致的浏览器指纹"""
        if not self.current_browser_type:
            self._select_consistent_user_agent()

        fingerprint = self.browser_fingerprints[self.current_browser_type].copy()

        # 根据User-Agent动态调整某些头部
        if self.current_browser_type == 'chrome':
            # 从User-Agent中提取Chrome版本
            chrome_version_match = re.search(r'Chrome/(\d+)', self.current_user_agent)
            if chrome_version_match:
                version = chrome_version_match.group(1)
                fingerprint['sec_ch_ua'] = f'"Chromium";v="{version}", "Not(A:Brand";v="24", "Google Chrome";v="{version}"'

            # 检测操作系统
            if 'Windows NT 11.0' in self.current_user_agent:
                fingerprint['sec_ch_ua_platform'] = '"Windows"'
                fingerprint['sec_ch_ua_platform_version'] = '"13.0.0"'
            elif 'Windows NT 10.0' in self.current_user_agent:
                fingerprint['sec_ch_ua_platform'] = '"Windows"'
                fingerprint['sec_ch_ua_platform_version'] = '"10.0.0"'
            elif 'Macintosh' in self.current_user_agent:
                fingerprint['sec_ch_ua_platform'] = '"macOS"'
                fingerprint['sec_ch_ua_platform_version'] = '"14.2.1"'
            elif 'Linux' in self.current_user_agent:
                fingerprint['sec_ch_ua_platform'] = '"Linux"'
                fingerprint['sec_ch_ua_platform_version'] = '""'

        elif self.current_browser_type == 'edge':
            # Edge特殊处理
            edge_version_match = re.search(r'Edg/(\d+)', self.current_user_agent)
            if edge_version_match:
                version = edge_version_match.group(1)
                fingerprint['sec_ch_ua'] = f'"Microsoft Edge";v="{version}", "Chromium";v="{version}", "Not(A:Brand";v="24"'

        return fingerprint

    def _get_realistic_headers(self, referer: Optional[str] = None,
                              is_ajax: bool = False,
                              is_image: bool = False) -> Dict[str, str]:
        """获取更真实的请求头"""
        user_agent = self._select_consistent_user_agent()
        fingerprint = self._generate_browser_fingerprint()

        headers = {
            'User-Agent': user_agent,
            'Accept': fingerprint['accept'],
            'Accept-Language': fingerprint['accept_language'],
            'Accept-Encoding': fingerprint['accept_encoding'],
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': fingerprint.get('upgrade_insecure_requests', '1'),
        }

        # 根据请求类型调整Accept头
        if is_ajax:
            headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
            headers['X-Requested-With'] = 'XMLHttpRequest'
        elif is_image:
            headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'

        # Chrome/Edge特有的安全头
        if self.current_browser_type in ['chrome', 'edge']:
            sec_headers = {
                'sec-ch-ua': fingerprint.get('sec_ch_ua', ''),
                'sec-ch-ua-mobile': fingerprint.get('sec_ch_ua_mobile', '?0'),
                'sec-ch-ua-platform': fingerprint.get('sec_ch_ua_platform', '"Windows"'),
            }

            # 添加平台版本（如果有）
            if 'sec_ch_ua_platform_version' in fingerprint:
                sec_headers['sec-ch-ua-platform-version'] = fingerprint['sec_ch_ua_platform_version']

            # 根据请求类型设置Fetch头
            if is_ajax:
                sec_headers.update({
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin' if referer else 'cross-site',
                })
            elif is_image:
                sec_headers.update({
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'same-origin' if referer else 'cross-site',
                })
            else:
                sec_headers.update({
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
                    'Sec-Fetch-User': '?1',
                })

            headers.update(sec_headers)

        # 添加Referer
        if referer:
            headers['Referer'] = referer

        # 随机添加一些真实浏览器会有的头
        random_headers = {}

        if random.random() < 0.4:  # 40%概率添加Cache-Control
            cache_controls = ['no-cache', 'max-age=0', 'no-store', 'must-revalidate']
            random_headers['Cache-Control'] = random.choice(cache_controls)

        if random.random() < 0.3:  # 30%概率添加Pragma
            random_headers['Pragma'] = 'no-cache'

        if random.random() < 0.2:  # 20%概率添加Purpose
            random_headers['Purpose'] = 'prefetch'

        if random.random() < 0.15:  # 15%概率添加Priority
            priorities = ['u=0, i', 'u=1, i', 'u=2, i', 'u=3, i']
            random_headers['Priority'] = random.choice(priorities)

        # Firefox特有头
        if self.current_browser_type == 'firefox' and 'te' in fingerprint:
            random_headers['TE'] = fingerprint['te']

        headers.update(random_headers)

        # 移除None值和空值
        return {k: v for k, v in headers.items() if v is not None and v != ''}

    def _generate_realistic_cookies(self) -> Dict[str, str]:
        """生成更真实的Cookie"""
        cookies = {}
        current_time = int(time.time())

        # 豆瓣基础cookies
        cookies['bid'] = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=11))

        # Google Analytics cookies (豆瓣使用GA)
        ga_client_id = f"{random.randint(1000000000, 9999999999)}.{current_time - random.randint(86400, 31536000)}"
        cookies['_ga'] = f"GA1.2.{ga_client_id}"
        cookies['_gid'] = f"GA1.2.{random.randint(1000000000, 9999999999)}.{current_time - random.randint(0, 86400)}"

        # 传统UTM cookies
        session_start = current_time - random.randint(0, 3600)
        cookies['__utma'] = f"30149280.{ga_client_id}.{session_start}.{session_start}.{current_time}.1"
        cookies['__utmb'] = f"30149280.{random.randint(1, 10)}.10.{current_time}"
        cookies['__utmc'] = "30149280"
        cookies['__utmz'] = f"30149280.{session_start}.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)"

        # 豆瓣特有cookies
        if random.random() < 0.7:  # 70%概率
            cookies['ll'] = f'"{random.randint(100000, 999999)}"'

        if random.random() < 0.6:  # 60%概率
            cookies['dbcl2'] = f'"{random.randint(100000000, 999999999)}:{self.session_id}"'

        if random.random() < 0.5:  # 50%概率
            cookies['_pk_id.100001.8cb4'] = f"{random.randint(1000000000, 9999999999)}.{current_time}"
            cookies['_pk_ses.100001.8cb4'] = "1"

        if random.random() < 0.4:  # 40%概率
            cookies['ap_v'] = '0,6.0'

        if random.random() < 0.3:  # 30%概率
            cookies['viewed'] = f'"{random.randint(10000000, 99999999)}"'

        # 添加一些随机的技术cookies
        if random.random() < 0.2:  # 20%概率
            cookies['_vwo_uuid_v2'] = f"{random.randint(100000000, 999999999)}:{random.randint(100, 999)}"

        if random.random() < 0.15:  # 15%概率
            cookies['__gads'] = f"ID={random.randint(100000000000000000, 999999999999999999)}:T={current_time}:RT={current_time}:S=ALNI_M{random.randint(100000000000000000, 999999999999999999)}"

        # 会话相关cookies
        cookies['_douban_session'] = self.session_id

        return cookies

    def _update_session_cookies(self, response_cookies) -> None:
        """更新会话cookies"""
        if not response_cookies:
            return

        try:
            for cookie in response_cookies:
                if hasattr(cookie, 'key') and hasattr(cookie, 'value'):
                    key, value = cookie.key, cookie.value
                elif hasattr(cookie, 'name') and hasattr(cookie, 'value'):
                    key, value = cookie.name, cookie.value
                else:
                    continue

                # 只保存重要的cookies
                important_cookies = [
                    'bid', 'dbcl2', 'll', '_ga', '_gid', '__utma', '__utmb',
                    '__utmc', '__utmz', 'viewed', '_pk_id.100001.8cb4',
                    '_pk_ses.100001.8cb4', 'ap_v', '_douban_session'
                ]

                if key in important_cookies or key.startswith('_'):
                    self.session_cookies[key] = value
                    logger.debug(f"🍪 更新Cookie: {key}")

        except Exception as e:
            logger.debug(f"Cookie更新错误: {e}")
    
    async def _adaptive_delay(self):
        """增强的自适应延迟策略"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        session_duration = current_time - self.session_start_time

        # 1. 基础延迟计算（指数退避）
        if self.failed_attempts == 0:
            base_delay = 3.0  # 成功时的基础延迟
        else:
            # 指数退避：2^n * 基础延迟，最大120秒
            base_delay = min(120.0, 5.0 * (2 ** min(self.failed_attempts - 1, 5)))

        # 2. 会话时长调整（模拟用户疲劳）
        if session_duration > 1800:  # 30分钟后
            base_delay *= 1.3
        elif session_duration > 3600:  # 1小时后
            base_delay *= 1.6

        # 3. 请求频率控制
        requests_per_minute = self.request_count / max(session_duration / 60, 1)
        if requests_per_minute > 10:  # 每分钟超过10个请求
            base_delay *= 2.0
            logger.warning(f"🚨 请求频率过高 ({requests_per_minute:.1f}/min)，增加延迟")
        elif requests_per_minute > 6:  # 每分钟超过6个请求
            base_delay *= 1.5

        # 4. 时段感知延迟
        current_hour = datetime.now().hour
        time_factor = self._get_time_factor(current_hour)
        base_delay *= time_factor

        # 5. 添加人类行为随机性
        human_factor = random.uniform(0.8, 1.4)
        if random.random() < 0.1:  # 10%概率的"思考"时间
            human_factor *= random.uniform(2.0, 4.0)
            logger.debug("🤔 模拟用户思考时间")

        final_delay = base_delay * human_factor

        # 6. 特殊情况处理
        if self.request_count > 0:
            # 每20个请求后的长休息（缩短为15-30秒）
            if self.request_count % 20 == 0:
                final_delay += random.uniform(15, 30)
                logger.info(f"� 长休息时间: +{final_delay - base_delay * human_factor:.1f}秒")
                logger.warning("⚠️ 长休息后将重置会话状态以避免被持续标记")

            # 每50个请求后的超长休息（缩短为60-120秒）
            elif self.request_count % 50 == 0:
                final_delay += random.uniform(60, 120)
                logger.info(f"🛌 超长休息时间: +{final_delay - base_delay * human_factor:.1f}秒")
                logger.warning("⚠️ 超长休息后将重置会话状态以避免被持续标记")

        # 7. 执行延迟
        if time_since_last < final_delay:
            actual_delay = final_delay - time_since_last
            logger.debug(f"⏳ 智能延迟 {actual_delay:.1f}秒 (失败:{self.failed_attempts}, 频率:{requests_per_minute:.1f}/min)")

            # 分段延迟，模拟用户可能的中断
            if actual_delay > 30:
                await self._segmented_delay(actual_delay)
            else:
                await asyncio.sleep(actual_delay)

        self.last_request_time = time.time()
        self.request_count += 1

    def _get_time_factor(self, hour: int) -> float:
        """根据时间段返回延迟因子"""
        if 2 <= hour <= 6:  # 深夜
            return 0.7  # 减少延迟，模拟夜猫子
        elif 7 <= hour <= 9:  # 早高峰
            return 1.3  # 增加延迟，网络繁忙
        elif 10 <= hour <= 11:  # 上午工作时间
            return 1.1
        elif 12 <= hour <= 14:  # 午休时间
            return 0.9  # 稍微减少
        elif 15 <= hour <= 17:  # 下午工作时间
            return 1.2
        elif 18 <= hour <= 20:  # 晚高峰
            return 1.4  # 最繁忙时段
        elif 21 <= hour <= 23:  # 晚上休闲时间
            return 1.0  # 正常
        else:  # 0-1点
            return 0.8

    async def _segmented_delay(self, total_delay: float):
        """分段延迟，模拟用户可能的中断行为"""
        remaining = total_delay
        is_long_delay = total_delay > 60  # 判断是否为长延迟

        while remaining > 0:
            # 随机选择一个延迟段
            segment = min(remaining, random.uniform(5, 15))
            await asyncio.sleep(segment)
            remaining -= segment

            # 小概率的"用户回来"检查
            if remaining > 10 and random.random() < 0.05:
                logger.debug("👀 模拟用户中途检查")
                await asyncio.sleep(random.uniform(1, 3))

        # 长延迟后重置会话状态以避免被持续标记
        if is_long_delay:
            self._reset_session_state()
            logger.info("🔄 长延迟后已重置会话状态，避免持续标记")

    def _should_rotate_session(self) -> bool:
        """智能判断是否需要轮换会话"""
        current_time = time.time()
        session_duration = current_time - self.session_start_time

        # 1. 失败次数过多时轮换
        if self.failed_attempts >= 3:
            logger.info(f"🔄 失败次数过多 ({self.failed_attempts})，轮换会话")
            return True

        # 2. 请求次数过多时轮换
        if self.request_count >= 80:  # 增加到80个请求
            logger.info(f"🔄 请求次数过多 ({self.request_count})，轮换会话")
            return True

        # 3. 会话时间过长时轮换
        if session_duration > 7200:  # 2小时
            logger.info(f"🔄 会话时间过长 ({session_duration/3600:.1f}小时)，轮换会话")
            return True

        # 4. 随机轮换（模拟用户关闭重开浏览器）
        if session_duration > 1800 and random.random() < 0.03:  # 30分钟后3%概率
            logger.info("🔄 随机轮换会话（模拟用户行为）")
            return True

        # 5. 检测到可能的检测时轮换
        if self.failed_attempts >= 2 and self.request_count > 20:
            logger.info("🔄 检测到可能的反爬虫检测，轮换会话")
            return True

        return False

    def _reset_session_state(self):
        """重置会话状态"""
        old_session_id = self.session_id[:8]
        self.session_id = self._generate_session_id()
        self.session_cookies = {}
        self.request_count = 0
        self.failed_attempts = max(0, self.failed_attempts - 2)  # 减少失败计数
        self.session_start_time = time.time()
        self.current_user_agent = None  # 重置User-Agent
        self.current_browser_type = None

        logger.info(f"🔄 会话已重置 ({old_session_id}... -> {self.session_id[:8]}...)")

        # 重置后的短暂延迟
        return random.uniform(5, 15)

    def _extract_anti_csrf_token(self, html: str) -> Optional[str]:
        """提取反CSRF令牌"""
        # 查找常见的CSRF token
        patterns = [
            r'name=["\']_token["\'] value=["\']([^"\']+)["\']',
            r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']',
            r'window\.__csrf_token__\s*=\s*["\']([^"\']+)["\']',
            r'data-csrf-token=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None

    async def _handle_security_challenge(self, session: aiohttp.ClientSession,
                                       response, original_url: str) -> Optional[Dict[str, Any]]:
        """处理豆瓣安全挑战"""
        response_url = str(response.url)

        # 检测各种安全验证页面
        security_indicators = [
            'sec.douban.com',
            'verify.douban.com',
            'captcha',
            '安全验证',
            '请输入验证码',
            'robot',
            'blocked'
        ]

        html = await response.text()
        is_security_page = any(indicator in response_url or indicator in html
                              for indicator in security_indicators)

        if is_security_page:
            logger.warning(f"🚨 检测到安全验证页面: {response_url}")

            # 策略1: 查找自动跳转
            redirect_patterns = [
                r'location\.href\s*=\s*["\']([^"\']+)["\']',
                r'window\.location\s*=\s*["\']([^"\']+)["\']',
                r'document\.location\s*=\s*["\']([^"\']+)["\']',
                r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][^;]*;\s*url=([^"\']+)["\']'
            ]

            for pattern in redirect_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    target_url = match.group(1)
                    if target_url.startswith('/'):
                        target_url = 'https://www.douban.com' + target_url

                    logger.info(f"🔄 发现自动跳转: {target_url}")

                    # 模拟人类等待时间
                    await asyncio.sleep(random.uniform(3, 8))

                    return await self._make_ultimate_request(
                        session, target_url, referer=response_url
                    )

            # 策略2: 查找验证表单
            form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', html)
            if form_match:
                form_action = form_match.group(1)
                logger.info(f"📝 发现验证表单: {form_action}")

                # 尝试提取并处理表单
                csrf_token = self._extract_anti_csrf_token(html)
                if csrf_token:
                    logger.info(f"🔑 提取到CSRF令牌: {csrf_token[:8]}...")
                    # 这里可以实现自动表单提交逻辑

            # 策略3: 等待后重试原始URL
            logger.info("⏳ 等待后重试原始请求...")
            await asyncio.sleep(random.uniform(30, 60))

            # 重置会话状态
            self._reset_session_state()

            return await self._make_ultimate_request(
                session, original_url, referer="https://www.douban.com"
            )

        # 正常响应
        if response.status == 200:
            return {"text": html, "status": response.status}

        return None
    
    async def _make_ultimate_request(self, session: aiohttp.ClientSession,
                                   url: str, method: str = "GET",
                                   headers: Optional[Dict[str, str]] = None,
                                   params: Optional[Dict[str, Any]] = None,
                                   data: Optional[Dict[str, Any]] = None,
                                   referer: Optional[str] = None,
                                   is_ajax: bool = False,
                                   max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """终极HTTP请求 - 包含最先进的反反爬虫机制"""

        # 检查是否需要轮换会话
        if self._should_rotate_session():
            self._reset_session_state()

        for attempt in range(max_retries):
            try:
                # 自适应延迟
                await self._adaptive_delay()

                # 获取真实的请求头
                request_headers = headers or self._get_realistic_headers(referer, is_ajax)

                # 合并会话cookies和生成的cookies
                cookies = self.session_cookies.copy()
                if not cookies:  # 如果没有会话cookies，生成一些基础cookies
                    cookies.update(self._generate_realistic_cookies())

                # 获取代理（如果配置了）
                proxy = self._get_next_proxy()

                # 配置超时
                timeout = aiohttp.ClientTimeout(
                    total=60,  # 总超时时间
                    connect=30,  # 连接超时
                    sock_read=30  # 读取超时
                )

                logger.debug(f"🌐 请求 {url} (第{attempt+1}/{max_retries}次, 会话: {self.session_id[:8]})")

                # 构建请求参数
                request_kwargs = {
                    'method': method,
                    'url': url,
                    'headers': request_headers,
                    'cookies': cookies,
                    'timeout': timeout,
                    'ssl': False,  # 忽略SSL验证
                    'allow_redirects': True,
                    'max_redirects': 5
                }

                # 添加参数和数据
                if params:
                    request_kwargs['params'] = params
                if data:
                    if method.upper() == 'POST':
                        request_kwargs['data'] = data
                    else:
                        request_kwargs['json'] = data

                # 添加代理
                if proxy:
                    request_kwargs['proxy'] = proxy
                    logger.debug(f"🌐 使用代理: {proxy}")

                async with session.request(**request_kwargs) as response:

                    # 更新cookies
                    if response.cookies:
                        self._update_session_cookies(response.cookies)

                    logger.debug(f"📊 响应: {response.status} {response.reason} (大小: {response.headers.get('content-length', 'unknown')})")

                    # 成功响应
                    if response.status == 200:
                        # 检查安全挑战
                        result = await self._handle_security_challenge(session, response, url)
                        if result:
                            self.failed_attempts = 0  # 重置失败计数
                            return result

                    # 增强的错误状态处理
                    elif response.status == 403:
                        self.failed_attempts += 1
                        logger.warning(f"🚫 403 Forbidden (失败次数: {self.failed_attempts})")

                        # 检查响应内容以确定具体原因
                        try:
                            response_text = await response.text()
                            if '验证码' in response_text or 'captcha' in response_text.lower():
                                logger.error("🤖 检测到验证码要求，需要人工干预")
                                return None
                            elif 'blocked' in response_text.lower() or '封禁' in response_text:
                                logger.error("🚫 IP可能被封禁")
                                # 尝试更长的等待时间
                                wait_time = min(600, 120 * (attempt + 1))
                            else:
                                wait_time = min(180, 30 * (attempt + 1))
                        except:
                            wait_time = min(120, 20 * (attempt + 1))

                        if attempt < max_retries - 1:
                            logger.info(f"⏳ 403错误，等待 {wait_time} 秒后重试...")
                            await asyncio.sleep(wait_time)

                            # 强制轮换会话
                            reset_delay = self._reset_session_state()
                            await asyncio.sleep(reset_delay)
                            continue

                    elif response.status == 429:
                        self.failed_attempts += 1
                        logger.warning(f"🐌 429 Too Many Requests (失败次数: {self.failed_attempts})")

                        # 从响应头获取重试时间
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                wait_time = int(retry_after)
                            except ValueError:
                                wait_time = 300
                        else:
                            # 指数退避，最多等待10分钟
                            wait_time = min(600, 60 * (2 ** attempt))

                        logger.info(f"⏳ 频率限制，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)

                        # 429错误后也轮换会话
                        if attempt == max_retries // 2:
                            reset_delay = self._reset_session_state()
                            await asyncio.sleep(reset_delay)
                        continue

                    elif response.status == 418:  # I'm a teapot - 有些网站用这个表示反爬虫
                        self.failed_attempts += 1
                        logger.warning("🫖 418 I'm a teapot - 可能触发反爬虫机制")
                        if attempt < max_retries - 1:
                            wait_time = random.uniform(300, 600)  # 5-10分钟
                            logger.info(f"⏳ 等待 {wait_time:.0f} 秒后重试...")
                            await asyncio.sleep(wait_time)
                            reset_delay = self._reset_session_state()
                            await asyncio.sleep(reset_delay)
                            continue

                    elif response.status in [301, 302, 303, 307, 308]:
                        # 增强的重定向处理
                        location = response.headers.get('Location')
                        if location:
                            # 检查重定向是否是安全验证页面
                            if any(keyword in location.lower() for keyword in ['verify', 'captcha', 'security', 'robot']):
                                logger.warning(f"🔒 重定向到安全验证页面: {location}")
                                # 尝试处理安全验证
                                return await self._handle_security_challenge(session, response, url)
                            else:
                                logger.info(f"🔄 重定向到: {location}")
                                return await self._make_ultimate_request(
                                    session, location, method='GET', referer=url
                                )

                    elif response.status == 404:
                        logger.warning(f"🔍 404 Not Found: {url}")
                        return None  # 404通常不需要重试

                    elif response.status in [502, 503, 504]:
                        logger.warning(f"🔧 服务器错误: {response.status}")
                        if attempt < max_retries - 1:
                            # 服务器错误使用较短的等待时间
                            wait_time = random.uniform(10, 30) * (attempt + 1)
                            logger.info(f"⏳ 服务器错误，等待 {wait_time:.1f} 秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue

                    elif response.status >= 500:
                        logger.warning(f"🔧 其他服务器错误: {response.status}")
                        if attempt < max_retries - 1:
                            wait_time = random.uniform(15, 45)
                            await asyncio.sleep(wait_time)
                            continue

                    else:
                        logger.warning(f"❌ 未知状态码: {response.status} {response.reason}")
                        if attempt < max_retries - 1:
                            wait_time = random.uniform(5, 15)
                            await asyncio.sleep(wait_time)
                            continue

            except asyncio.TimeoutError:
                self.failed_attempts += 1
                logger.warning(f"⏰ 请求超时 (第{attempt+1}次，总失败:{self.failed_attempts})")
                if attempt < max_retries - 1:
                    # 超时后增加等待时间
                    wait_time = random.uniform(15, 30) * (attempt + 1)
                    logger.info(f"⏳ 超时重试，等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)
                    continue

            except aiohttp.ClientConnectorError as e:
                self.failed_attempts += 1
                logger.error(f"🔌 连接错误: {e}")
                if attempt < max_retries - 1:
                    # 连接错误可能是网络问题，等待更长时间
                    wait_time = random.uniform(30, 60) * (attempt + 1)
                    logger.info(f"⏳ 连接错误重试，等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)

                    # 连接错误时轮换会话
                    if attempt >= max_retries // 2:
                        reset_delay = self._reset_session_state()
                        await asyncio.sleep(reset_delay)
                    continue

            except aiohttp.ClientResponseError as e:
                self.failed_attempts += 1
                logger.error(f"📡 响应错误: {e.status} {e.message}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(10, 25)
                    await asyncio.sleep(wait_time)
                    continue

            except aiohttp.ClientError as e:
                self.failed_attempts += 1
                logger.error(f"🌐 客户端错误: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(10, 20)
                    await asyncio.sleep(wait_time)
                    continue

            except json.JSONDecodeError as e:
                logger.error(f"📄 JSON解析错误: {e}")
                # JSON错误通常不需要重试
                return None

            except UnicodeDecodeError as e:
                logger.error(f"🔤 编码错误: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(5, 10))
                    continue

            except Exception as e:
                self.failed_attempts += 1
                logger.error(f"💥 未知错误: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(15, 30)
                    await asyncio.sleep(wait_time)
                    continue

        logger.error(f"❌ 所有重试都失败了: {url}")
        return None
    
    async def _init_session_carefully(self, session: aiohttp.ClientSession) -> bool:
        """谨慎初始化会话 - 模拟真实用户行为"""
        logger.info("🔧 正在初始化豆瓣会话...")

        try:
            # 步骤1: 访问豆瓣首页
            logger.debug("📱 访问豆瓣首页...")
            home_response = await self._make_ultimate_request(
                session, "https://www.douban.com"
            )

            if not home_response:
                logger.warning("❌ 无法访问豆瓣首页")
                return False

            # 模拟用户浏览行为 - 短暂停留
            await asyncio.sleep(random.uniform(2, 5))

            # 步骤2: 访问电影首页
            logger.debug("🎬 访问豆瓣电影首页...")
            movie_response = await self._make_ultimate_request(
                session, "https://movie.douban.com",
                referer="https://www.douban.com"
            )

            if not movie_response:
                logger.warning("❌ 无法访问豆瓣电影首页")
                return False

            # 模拟用户浏览行为 - 查看页面内容
            await asyncio.sleep(random.uniform(3, 7))

            # 步骤3: 访问搜索页面（预热）
            logger.debug("🔍 预热搜索功能...")
            search_page_response = await self._make_ultimate_request(
                session, "https://search.douban.com/movie/subject_search",
                referer="https://movie.douban.com"
            )

            if search_page_response:
                logger.debug("✅ 搜索页面预热成功")

            # 检查是否获得了有效的cookies
            if len(self.session_cookies) > 0:
                logger.info(f"✅ 会话初始化成功 (获得 {len(self.session_cookies)} 个cookies)")
                return True
            else:
                logger.warning("⚠️ 会话初始化完成，但未获得cookies")
                return True  # 仍然继续，可能不需要cookies

        except Exception as e:
            logger.error(f"❌ 会话初始化失败: {e}")
            return False
    
    async def search_anime_with_mobile_api(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用移动端API搜索动漫"""
        logger.info(f"📱 使用移动端API搜索: {title}")

        try:
            # 更丰富的移动端User-Agent池
            mobile_agents = [
                # iPhone Safari
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1',

                # Android Chrome
                'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 12; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',

                # Android Firefox
                'Mozilla/5.0 (Mobile; rv:123.0) Gecko/123.0 Firefox/123.0',
                'Mozilla/5.0 (Android 14; Mobile; rv:122.0) Gecko/122.0 Firefox/122.0',

                # 微信内置浏览器
                'Mozilla/5.0 (Linux; Android 12; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.47.2560(0x28002F30) Process/tools WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
            ]

            # 随机选择一个移动端User-Agent
            mobile_ua = random.choice(mobile_agents)

            mobile_headers = {
                'User-Agent': mobile_ua,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.douban.com/',
                'Origin': 'https://m.douban.com',
                'X-Requested-With': 'XMLHttpRequest',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }

            # 如果是微信浏览器，添加特殊头
            if 'MicroMessenger' in mobile_ua:
                mobile_headers['X-Requested-With'] = 'com.tencent.mm'

            # 扩展的移动端API端点
            api_endpoints = [
                {
                    'url': 'https://m.douban.com/rexxar/api/v2/search',
                    'params': {'q': title, 'type': 'movie', 'count': 10, 'start': 0}
                },
                {
                    'url': 'https://m.douban.com/j/search',
                    'params': {'q': title, 'cat': '1002', 'start': 0}
                },
                {
                    'url': 'https://frodo.douban.com/api/v2/search/movie',
                    'params': {'q': title, 'count': 10, 'start': 0}
                },
                {
                    'url': 'https://m.douban.com/search/',
                    'params': {'query': title, 'type': 'movie'}
                },
                {
                    'url': 'https://movie.douban.com/j/subject_suggest',
                    'params': {'q': title}
                }
            ]

            for endpoint in api_endpoints:
                try:
                    api_url = endpoint['url']
                    params = endpoint['params']

                    logger.debug(f"🔍 尝试移动端API: {api_url}")

                    response = await self._make_ultimate_request(
                        session, api_url,
                        headers=mobile_headers,
                        params=params,
                        referer="https://m.douban.com/",
                        is_ajax=True
                    )

                    if response:
                        results = self._parse_mobile_api_response(response, title)
                        if results:
                            logger.info(f"✅ 移动端API搜索成功，找到 {len(results)} 个结果")
                            return results

                    # 短暂延迟后尝试下一个API
                    await asyncio.sleep(random.uniform(2, 5))

                except Exception as e:
                    logger.debug(f"移动端API {api_url} 失败: {e}")
                    continue

            logger.warning("❌ 所有移动端API都失败了")
            return []

        except Exception as e:
            logger.error(f"移动端API搜索异常: {e}")
            return []

    def _parse_mobile_api_response(self, response: Dict[str, Any], search_title: str) -> List[AnimeInfo]:
        """解析移动端API响应"""
        results = []

        try:
            # 尝试不同的响应格式
            items = None

            if isinstance(response, dict):
                # 标准格式
                if 'items' in response:
                    items = response['items']
                elif 'subjects' in response:
                    items = response['subjects']
                elif 'data' in response and isinstance(response['data'], list):
                    items = response['data']
                elif isinstance(response.get('text'), str):
                    # HTML响应，尝试解析
                    return self._parse_mobile_html_response(response['text'], search_title)

            if items and isinstance(items, list):
                for item in items[:5]:  # 限制结果数量
                    try:
                        douban_id = str(item.get('id', ''))
                        title_text = item.get('title', item.get('name', item.get('subject', {}).get('title', '')))

                        # 提取更多信息
                        year = item.get('year', item.get('pubdate', ''))
                        rating = item.get('rating', item.get('rate', ''))

                        if douban_id and title_text:
                            anime_info = AnimeInfo(
                                title=title_text,
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )

                            # 如果有年份信息，添加到对象中
                            if year:
                                try:
                                    anime_info.year = int(str(year)[:4])
                                except:
                                    pass

                            results.append(anime_info)

                    except Exception as e:
                        logger.debug(f"解析移动端API结果项失败: {e}")
                        continue

        except Exception as e:
            logger.debug(f"解析移动端API响应失败: {e}")

        return results

    def _parse_mobile_html_response(self, html: str, search_title: str) -> List[AnimeInfo]:
        """解析移动端HTML响应"""
        results = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 查找搜索结果
            result_items = soup.find_all(['div', 'li'], class_=re.compile(r'result|item|subject'))

            for item in result_items[:5]:
                try:
                    # 查找链接
                    link = item.find('a', href=re.compile(r'/subject/\d+'))
                    if link:
                        href = link.get('href', '')
                        douban_id_match = re.search(r'/subject/(\d+)', href)

                        if douban_id_match:
                            douban_id = douban_id_match.group(1)
                            title_text = link.get_text(strip=True) or link.get('title', '')

                            if title_text:
                                anime_info = AnimeInfo(
                                    title=title_text,
                                    external_ids={WebsiteName.DOUBAN: douban_id}
                                )
                                results.append(anime_info)

                except Exception as e:
                    logger.debug(f"解析HTML结果项失败: {e}")
                    continue

        except Exception as e:
            logger.debug(f"解析HTML响应失败: {e}")

        return results
    
    async def search_anime_with_proxy(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用代理搜索动漫"""
        logger.info(f"🌐 使用代理搜索: {title}")

        # 代理服务器配置（可以从配置文件读取）
        proxy_configs = [
            # 示例代理配置，实际使用时需要替换为真实的代理
            # {"http": "http://proxy1:port", "https": "https://proxy1:port"},
            # {"http": "http://proxy2:port", "https": "https://proxy2:port"},
        ]

        if not proxy_configs:
            logger.warning("未配置代理服务器")
            return []

        for proxy_config in proxy_configs:
            try:
                logger.debug(f"🔄 尝试代理: {proxy_config}")

                # 使用代理的特殊请求头
                proxy_headers = self._get_realistic_headers()
                proxy_headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

                search_url = "https://search.douban.com/movie/subject_search"
                params = {
                    'search_text': title,
                    'cat': '1002'
                }

                # 创建带代理的连接器
                connector = aiohttp.TCPConnector(ssl=False)
                timeout = aiohttp.ClientTimeout(total=60)

                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                ) as proxy_session:

                    async with proxy_session.get(
                        search_url,
                        params=params,
                        headers=proxy_headers,
                        proxy=proxy_config.get('http')
                    ) as response:

                        if response.status == 200:
                            html = await response.text()
                            results = self._parse_search_results(html, title)
                            if results:
                                logger.info(f"✅ 代理搜索成功，找到 {len(results)} 个结果")
                                return results

                await asyncio.sleep(random.uniform(3, 8))

            except Exception as e:
                logger.debug(f"代理 {proxy_config} 失败: {e}")
                continue

        logger.warning("❌ 所有代理都失败了")
        return []

    def _parse_search_results(self, html: str, search_title: str) -> List[AnimeInfo]:
        """解析搜索结果HTML"""
        results = []

        try:
            # 尝试从JavaScript数据中提取
            data_match = re.search(r'window\.__DATA__\s*=\s*({.*?});', html, re.DOTALL)
            if data_match:
                import json
                data = json.loads(data_match.group(1))
                items = data.get('items', [])

                # 添加详细的调试信息
                logger.debug(f"   📊 JavaScript数据解析成功")
                logger.debug(f"      总数: {data.get('count', 0)}")
                logger.debug(f"      错误信息: {data.get('error_info', '无')}")
                logger.debug(f"      结果项数: {len(items)}")
                logger.debug(f"      搜索文本: {data.get('text', '未知')}")

                if len(items) == 0:
                    error_info = data.get('error_info', '')
                    if '频繁' in error_info or '限制' in error_info:
                        logger.error(f"   🚫 豆瓣频率限制: {error_info}")
                        logger.warning(f"   💡 建议等待30分钟后再尝试搜索")
                        # 抛出特定异常，让上层切换策略
                        raise Exception(f"豆瓣频率限制: {error_info}")
                    else:
                        logger.warning(f"   ⚠️ 豆瓣返回0个搜索结果")
                    logger.debug(f"      完整数据: {data}")
                    return []

                for item in items[:5]:
                    try:
                        douban_id = str(item.get('id', ''))
                        title_text = item.get('title', '')

                        if douban_id and title_text:
                            anime_info = AnimeInfo(
                                title=title_text,
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )
                            results.append(anime_info)
                            logger.debug(f"      ✅ 解析成功: {title_text} (ID: {douban_id})")
                    except Exception as e:
                        logger.debug(f"解析搜索结果项失败: {e}")
                        continue
            else:
                logger.warning(f"   ⚠️ 未找到JavaScript数据 window.__DATA__")
                # 保存HTML用于调试
                import time
                debug_file = f"debug_no_data_{int(time.time())}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.debug(f"      HTML已保存到: {debug_file}")

            # 如果JavaScript解析失败，尝试HTML解析
            if not results:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                result_items = soup.find_all('div', class_='result')
                for item in result_items[:5]:
                    try:
                        link = item.find('a', href=re.compile(r'/subject/\d+'))
                        if link:
                            href = link.get('href', '')
                            douban_id_match = re.search(r'/subject/(\d+)', href)

                            if douban_id_match:
                                douban_id = douban_id_match.group(1)
                                title_text = link.get_text(strip=True)

                                if title_text:
                                    anime_info = AnimeInfo(
                                        title=title_text,
                                        external_ids={WebsiteName.DOUBAN: douban_id}
                                    )
                                    results.append(anime_info)
                    except Exception as e:
                        logger.debug(f"解析HTML结果项失败: {e}")
                        continue

        except Exception as e:
            logger.debug(f"解析搜索结果失败: {e}")

        return results

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

        # 多种替代搜索策略
        strategies = [
            self._search_via_search_engines,
            self._search_via_mirror_sites,
            self._search_via_api_aggregators,
        ]

        for strategy in strategies:
            try:
                results = await strategy(session, title)
                if results:
                    logger.info(f"✅ 替代网站搜索成功，找到 {len(results)} 个结果")
                    return results

                # 策略间延迟
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.debug(f"替代搜索策略失败: {e}")
                continue

        logger.warning("❌ 所有替代网站搜索都失败了")
        return []

    async def _search_via_search_engines(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """通过搜索引擎搜索豆瓣链接"""
        search_engines = [
            {
                'name': 'Bing',
                'url': 'https://www.bing.com/search',
                'params': {'q': f'site:movie.douban.com {title}', 'count': 10}
            },
            {
                'name': 'DuckDuckGo',
                'url': 'https://duckduckgo.com/html/',
                'params': {'q': f'site:movie.douban.com {title}'}
            },
            {
                'name': 'Yandex',
                'url': 'https://yandex.com/search/',
                'params': {'text': f'site:movie.douban.com {title}'}
            }
        ]

        for engine in search_engines:
            try:
                logger.debug(f"🔍 尝试 {engine['name']} 搜索")

                headers = self._get_realistic_headers()
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

                response = await self._make_ultimate_request(
                    session, engine['url'],
                    params=engine['params'],
                    headers=headers
                )

                if response and 'text' in response:
                    # 提取豆瓣链接
                    douban_links = re.findall(
                        r'https?://movie\.douban\.com/subject/(\d+)/?',
                        response['text']
                    )

                    if douban_links:
                        results = []
                        for douban_id in douban_links[:3]:  # 限制数量
                            anime_info = AnimeInfo(
                                title=title,
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )
                            results.append(anime_info)

                        if results:
                            logger.info(f"✅ {engine['name']} 找到 {len(results)} 个豆瓣ID")
                            return results

                await asyncio.sleep(random.uniform(3, 7))

            except Exception as e:
                logger.debug(f"{engine['name']} 搜索失败: {e}")
                continue

        return []

    async def _search_via_mirror_sites(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """通过镜像站点搜索"""
        # 豆瓣镜像站点（注意：这些可能不稳定，需要定期更新）
        mirror_sites = [
            # 示例镜像站点，实际使用时需要替换为真实可用的镜像
            # "https://douban-mirror1.com",
            # "https://douban-mirror2.com",
        ]

        if not mirror_sites:
            logger.debug("未配置镜像站点")
            return []

        for mirror_url in mirror_sites:
            try:
                logger.debug(f"🪞 尝试镜像站点: {mirror_url}")

                search_url = f"{mirror_url}/search"
                params = {'q': title, 'cat': '1002'}

                headers = self._get_realistic_headers()

                response = await self._make_ultimate_request(
                    session, search_url,
                    params=params,
                    headers=headers
                )

                if response and 'text' in response:
                    results = self._parse_search_results(response['text'], title)
                    if results:
                        logger.info(f"✅ 镜像站点找到 {len(results)} 个结果")
                        return results

                await asyncio.sleep(random.uniform(3, 8))

            except Exception as e:
                logger.debug(f"镜像站点 {mirror_url} 失败: {e}")
                continue

        return []

    async def _search_via_api_aggregators(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """通过API聚合服务搜索"""
        # 第三方API聚合服务（需要API密钥）
        aggregators = [
            # 示例API聚合服务
            # {
            #     'name': 'RapidAPI',
            #     'url': 'https://douban-api.rapidapi.com/search',
            #     'headers': {'X-RapidAPI-Key': 'your-api-key'}
            # }
        ]

        if not aggregators:
            logger.debug("未配置API聚合服务")
            return []

        for aggregator in aggregators:
            try:
                logger.debug(f"🔗 尝试API聚合: {aggregator['name']}")

                headers = self._get_realistic_headers()
                headers.update(aggregator.get('headers', {}))

                params = {'q': title, 'type': 'movie'}

                response = await self._make_ultimate_request(
                    session, aggregator['url'],
                    params=params,
                    headers=headers,
                    is_ajax=True
                )

                if response:
                    results = self._parse_mobile_api_response(response, title)
                    if results:
                        logger.info(f"✅ API聚合找到 {len(results)} 个结果")
                        return results

                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.debug(f"API聚合 {aggregator['name']} 失败: {e}")
                continue

        return []

    def _build_optimized_search_terms(self, title: str, anime_info: Optional['AnimeInfo'] = None) -> List[str]:
        """构建优化的搜索词：优先中文名，然后日文名（不使用简化标题）"""
        search_terms = []

        # 如果有AnimeInfo对象，优先使用其中的标题信息
        if anime_info:
            # 1. 中文标题（最高优先级）
            if anime_info.title_chinese:
                search_terms.append(anime_info.title_chinese)
                logger.info(f"   🇨🇳 使用中文标题: {anime_info.title_chinese}")

            # 2. 日文标题（第二优先级）
            if anime_info.title_japanese:
                search_terms.append(anime_info.title_japanese)
                logger.info(f"   🇯🇵 使用日文标题: {anime_info.title_japanese}")

        # 3. 如果没有中文和日文标题，使用原始标题作为备用
        if not search_terms:
            search_terms.append(title)
            logger.info(f"   📝 使用原始标题: {title}")

        # 确保最多2个搜索词：中文 + 日文（不包含简化版本）
        final_terms = search_terms[:2]
        logger.info(f"   ✅ 最终搜索词: {final_terms}")

        return final_terms

    async def search_anime(self, session: aiohttp.ClientSession, title: str, anime_info: Optional['AnimeInfo'] = None) -> List[AnimeInfo]:
        """搜索动漫 - 多策略自动切换：主页面搜索 → 移动端API → 备用方法"""
        logger.info(f"🔍 豆瓣优化搜索开始: {title}")

        # 构建搜索词：优先日文，然后中文，最后英文
        search_terms = self._build_optimized_search_terms(title, anime_info)
        logger.info(f"🔤 搜索词策略: {search_terms}")

        # 搜索策略：只使用移动端API（稳定且有完整评分数据）
        logger.debug(f"🚀 使用移动端API策略（唯一策略）")

        # 按优先级尝试每个搜索词
        for i, term in enumerate(search_terms, 1):
            logger.info(f"🎯 [{i}/{len(search_terms)}] 搜索词: '{term}' (策略: 移动端API)")

            try:
                # 使用移动端API搜索
                results = await self._search_with_mobile_api_v2(session, term)

                if results:
                    # 验证搜索结果
                    validated_results = self._validate_search_results(results, term)
                    if validated_results:
                        logger.success(f"✅ 移动端API搜索成功! 找到 {len(validated_results)} 个有效结果")
                        return validated_results

                # 如果没找到结果，尝试下一个搜索词
                if i < len(search_terms):
                    logger.info("⏳ 等待5秒后尝试下一个搜索词...")
                    await asyncio.sleep(5)

            except Exception as e:
                error_msg = str(e).lower()
                if '频繁' in error_msg or '限制' in error_msg or 'rate' in error_msg:
                    logger.warning(f"🚫 移动端API遇到频率限制，停止搜索")
                    break
                else:
                    logger.warning(f"❌ 移动端API搜索词 '{term}' 失败: {e}")
                    # 继续尝试下一个搜索词
                    if i < len(search_terms):
                        await asyncio.sleep(5)

        logger.warning(f"❌ 移动端API搜索未找到结果，跳过: {title}")
        return []




    async def _search_with_homepage_form(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用主页面搜索表单 - 模拟表单提交"""
        logger.info(f"🎯 主页面表单搜索: {title}")

        try:
            # 使用发现的搜索URL
            search_urls = [
                f"https://movie.douban.com/subject_search?search_text={title}",
                f"https://movie.douban.com/search?q={title}",
                f"https://search.douban.com/movie/subject_search?search_text={title}",
            ]

            for search_url in search_urls:
                try:
                    logger.debug(f"   🔗 尝试URL: {search_url}")

                    response = await self._make_ultimate_request(
                        session, search_url,
                        referer="https://movie.douban.com/"
                    )

                    if response and 'text' in response:
                        results = self._parse_search_results(response['text'], title)
                        if results:
                            logger.success(f"✅ 主页面搜索成功，找到 {len(results)} 个结果")
                            return results

                    # 短暂延迟后尝试下一个URL
                    await asyncio.sleep(random.uniform(2, 4))

                except Exception as e:
                    logger.debug(f"搜索URL失败 {search_url}: {e}")
                    continue

            return []

        except Exception as e:
            logger.error(f"主页面搜索失败: {e}")
            return []

    async def _search_with_mobile_api_v2(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用移动端API v2 - 基于新发现的接口"""
        logger.info(f"📱 移动端API v2搜索: {title}")

        try:
            # 使用发现的移动端API
            api_url = "https://m.douban.com/rexxar/api/v2/search"
            params = {
                'q': title,
                'type': 'movie',
                'count': 10
            }

            # 移动端请求头
            mobile_headers = self._get_realistic_headers(
                referer="https://m.douban.com/",
                is_ajax=True
            )

            # 使用移动端User-Agent
            mobile_agents = [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            ]
            mobile_headers['User-Agent'] = random.choice(mobile_agents)

            response = await self._make_ultimate_request(
                session, api_url,
                params=params,
                headers=mobile_headers,
                referer="https://m.douban.com/",
                is_ajax=True
            )

            if not response:
                return []

            # 解析响应
            if isinstance(response, dict) and 'text' in response:
                import json
                try:
                    data = json.loads(response['text'])
                except json.JSONDecodeError:
                    return []
            else:
                data = response

            if not isinstance(data, dict):
                return []

            # 提取搜索结果
            subjects = data.get('subjects', {})
            items = subjects.get('items', []) if isinstance(subjects, dict) else []

            # 分类处理结果：按类型优先级排序
            anime_movie_results = []    # 电影类型
            anime_drama_results = []    # 剧集类型
            other_results = []          # 其他类型

            for item in items[:10]:  # 处理更多结果
                try:
                    if not isinstance(item, dict):
                        continue

                    target = item.get('target', {})
                    target_type = item.get('target_type', '')
                    type_name = item.get('type_name', '')

                    if isinstance(target, dict):
                        douban_id = str(target.get('id', ''))
                        title_text = target.get('title', '')
                        card_subtitle = target.get('card_subtitle', '')

                        if douban_id and title_text:
                            # 提取年份信息
                            year_str = target.get('year', '')
                            release_year = None
                            if year_str and year_str.isdigit():
                                release_year = int(year_str)

                            anime_info = AnimeInfo(
                                title=title_text,
                                external_ids={WebsiteName.DOUBAN: douban_id},
                                year=int(year_str) if year_str and year_str.isdigit() else None
                            )

                            # 提取评分数据
                            rating_info = target.get('rating', {})
                            if isinstance(rating_info, dict):
                                raw_score = rating_info.get('value', 0)
                                vote_count = rating_info.get('count', 0)

                                # 检查是否有有效的评分
                                if raw_score and raw_score > 0 and vote_count > 0:
                                    # 创建评分数据对象
                                    from ..models.anime import RatingData
                                    rating_data = RatingData(
                                        website=WebsiteName.DOUBAN,
                                        raw_score=float(raw_score),
                                        vote_count=int(vote_count)
                                    )

                                    anime_info._rating_data = rating_data
                                    logger.debug(f"   ✅ 找到: {title_text} (ID: {douban_id}, 类型: {target_type}) - 评分: {raw_score}, 投票: {vote_count:,}")
                                else:
                                    # 检查无评分原因
                                    null_reason = target.get('null_rating_reason', '')
                                    if null_reason:
                                        logger.debug(f"   ✅ 找到: {title_text} (ID: {douban_id}, 类型: {target_type}) - 无评分: {null_reason}")
                                    else:
                                        logger.debug(f"   ✅ 找到: {title_text} (ID: {douban_id}, 类型: {target_type}) - 无评分数据")
                            else:
                                logger.debug(f"   ✅ 找到: {title_text} (ID: {douban_id}, 类型: {target_type}) - 无评分信息")

                            # 按类型分类，优先movie和drama类型（动漫通常是这两种）
                            if target_type == 'movie':
                                anime_movie_results.append((anime_info, year_str))
                            elif target_type == 'drama':
                                anime_drama_results.append((anime_info, year_str))
                            else:
                                other_results.append((anime_info, year_str))

                except Exception as e:
                    logger.debug(f"解析移动端API结果项失败: {e}")
                    continue

            # 合并所有结果并按优先级排序：电影 > 剧集 > 其他类型
            all_results = anime_movie_results + anime_drama_results + other_results

            # 提取AnimeInfo对象（去掉年份信息）
            results = [item[0] for item in all_results]

            # 记录分类统计
            logger.debug(f"   📊 结果分类: 电影={len(anime_movie_results)}, 剧集={len(anime_drama_results)}, 其他={len(other_results)}")

            if results:
                logger.success(f"✅ 移动端API v2搜索成功，找到 {len(results)} 个结果")

            return results

        except Exception as e:
            logger.error(f"移动端API v2搜索失败: {e}")
            return []

    def _is_anime_related(self, card_subtitle: str, title: str, type_name: str) -> bool:
        """判断是否为动漫相关内容"""
        try:
            # 动漫关键词
            anime_keywords = [
                '动画', '动漫', '番剧', '漫画',
                '奇幻', '冒险', '魔法', '异世界',
                '机甲', '热血', '校园', '恋爱',
                '治愈', '日常', '搞笑', '悬疑'
            ]

            # 动漫制作公司/导演关键词
            anime_studios = [
                '宫崎骏', '新海诚', '今敏', '押井守',
                '吉卜力', '京都动画', 'MAPPA', 'WIT',
                '东映', '骨头社', 'A-1', 'P.A.WORKS'
            ]

            # 检查card_subtitle
            if card_subtitle:
                subtitle_lower = card_subtitle.lower()
                for keyword in anime_keywords:
                    if keyword in card_subtitle:
                        return True
                for studio in anime_studios:
                    if studio in card_subtitle:
                        return True

            # 检查标题
            if title:
                title_lower = title.lower()
                # 常见动漫标题模式
                anime_title_patterns = [
                    '第', '季', 'OVA', 'OAD', '剧场版',
                    '之', '物语', '传说', '战记'
                ]
                for pattern in anime_title_patterns:
                    if pattern in title:
                        return True

            # 检查type_name
            if type_name and '动画' in type_name:
                return True

            return False

        except Exception as e:
            logger.debug(f"动漫相关性判断失败: {e}")
            return False

    async def _search_with_backup_urls(self, session: aiohttp.ClientSession, title: str) -> List[AnimeInfo]:
        """使用备用搜索URL"""
        logger.info(f"🔄 备用URL搜索: {title}")

        try:
            # 其他发现的搜索URL
            backup_urls = [
                f"https://www.douban.com/search?q={title}&cat=1002",
            ]

            for url in backup_urls:
                try:
                    logger.debug(f"   🔗 尝试备用URL: {url}")

                    response = await self._make_ultimate_request(
                        session, url,
                        referer="https://www.douban.com/"
                    )

                    if response and 'text' in response:
                        results = self._parse_search_results(response['text'], title)
                        if results:
                            logger.success(f"✅ 备用URL搜索成功，找到 {len(results)} 个结果")
                            return results

                    await asyncio.sleep(random.uniform(2, 4))

                except Exception as e:
                    logger.debug(f"备用URL失败 {url}: {e}")
                    continue

            return []

        except Exception as e:
            logger.error(f"备用URL搜索失败: {e}")
            return []

    async def _make_enhanced_request(self, session: aiohttp.ClientSession, url: str,
                                   method: str = "GET", headers: Optional[Dict[str, str]] = None,
                                   params: Optional[Dict[str, Any]] = None,
                                   referer: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """增强的请求方法，兼容旧接口"""
        return await self._make_ultimate_request(
            session, url, method=method, headers=headers,
            params=params, referer=referer
        )

    def _prepare_search_terms(self, title: str) -> List[str]:
        """准备多种搜索词变体"""
        terms = [title]  # 原始标题

        # 去除常见后缀
        suffixes_to_remove = [
            '第二季', '第2季', '第三季', '第3季', '第四季', '第4季',
            'Season 2', 'Season 3', 'Season 4', 'S2', 'S3', 'S4',
            '2nd Season', '3rd Season', '4th Season',
            'II', 'III', 'IV', '续', '新作', '完结篇', '最终季'
        ]

        for suffix in suffixes_to_remove:
            if suffix in title:
                simplified = title.replace(suffix, '').strip()
                if simplified and simplified not in terms:
                    terms.append(simplified)

        # 去除括号内容
        import re
        no_brackets = re.sub(r'[（(].*?[）)]', '', title).strip()
        if no_brackets and no_brackets not in terms:
            terms.append(no_brackets)

        # 只保留前3个最有可能的搜索词
        return terms[:3]

    def _validate_search_results(self, results: List[AnimeInfo], original_title: str) -> List[AnimeInfo]:
        """验证搜索结果的质量"""
        if not results:
            return []

        validated = []
        original_lower = original_title.lower()

        for result in results:
            # 基本验证：必须有豆瓣ID
            douban_id = result.external_ids.get(WebsiteName.DOUBAN)
            if not douban_id:
                continue

            # 标题相似性验证
            result_title = result.title.lower()

            # 检查是否包含非拉丁字符（如日文、中文）
            has_non_latin = any(ord(c) > 127 for c in original_title)

            # 对于非拉丁字符，放宽验证条件
            if has_non_latin:
                # 对于日文等字符，只要找到结果就认为有效
                # 因为豆瓣的搜索算法已经做了匹配
                validated.append(result)
                logger.debug(f"   ✅ 非拉丁字符标题验证通过: {result.title}")
            else:
                # 拉丁字符使用严格的相似性检查
                if (original_lower in result_title or
                    result_title in original_lower or
                    self._calculate_similarity(original_lower, result_title) > 0.6):
                    validated.append(result)
                    logger.debug(f"   ✅ 拉丁字符标题验证通过: {result.title}")
                else:
                    logger.debug(f"   ❌ 标题相似性不足: {original_title} vs {result.title}")

        logger.debug(f"   📊 验证结果: {len(results)} -> {len(validated)}")
        return validated[:5]  # 最多返回5个结果

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简单版本）"""
        if not str1 or not str2:
            return 0.0

        # 计算最长公共子序列长度
        len1, len2 = len(str1), len(str2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        lcs_length = dp[len1][len2]
        return lcs_length / max(len1, len2)

    async def _search_with_selenium_wrapper(self, title: str) -> List[AnimeInfo]:
        """Selenium搜索包装器"""
        try:
            return await self.search_anime_with_selenium(title)
        except Exception as e:
            logger.warning(f"Selenium包装器错误: {e}")
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

                # 添加详细的调试信息
                logger.debug(f"   📊 JavaScript数据解析成功")
                logger.debug(f"      总数: {data.get('count', 0)}")
                logger.debug(f"      错误信息: {data.get('error_info', '无')}")
                logger.debug(f"      结果项数: {len(items)}")
                logger.debug(f"      搜索文本: {data.get('text', '未知')}")

                if len(items) == 0:
                    logger.warning(f"   ⚠️ 豆瓣返回0个搜索结果")
                    logger.debug(f"      完整数据: {data}")
                    return []

                for item in items[:5]:
                    try:
                        douban_id = str(item.get('id', ''))
                        if douban_id:
                            anime_info = AnimeInfo(
                                title=item.get('title', title),
                                external_ids={WebsiteName.DOUBAN: douban_id}
                            )
                            results.append(anime_info)
                            logger.debug(f"      ✅ 解析成功: {item.get('title', title)} (ID: {douban_id})")
                    except Exception as e:
                        logger.warning(f"解析搜索项失败: {e}")
                        continue
            else:
                logger.warning(f"   ⚠️ 未找到JavaScript数据 window.__DATA__")
                # 保存HTML用于调试
                import time
                debug_file = f"debug_no_data_{int(time.time())}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.debug(f"      HTML已保存到: {debug_file}")

            return results

        except Exception as e:
            logger.error(f"解析搜索响应失败: {e}")
            return []

    async def get_anime_rating(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """获取动漫评分数据 - 优先使用移动端API"""

        # 首先尝试使用移动端API获取评分（更快更准确）
        try:
            rating_data = await self._get_rating_from_mobile_api(session, anime_id)
            if rating_data:
                logger.debug(f"✅ 通过移动端API获取评分: {anime_id}")
                return rating_data
        except Exception as e:
            logger.debug(f"移动端API获取评分失败: {e}")

        # 备用方案：从页面HTML提取评分
        logger.debug(f"🔄 使用页面解析获取评分: {anime_id}")
        url = f"{self.base_url}/subject/{anime_id}/"

        response = await self._make_ultimate_request(
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

    async def _get_rating_from_mobile_api(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[RatingData]:
        """通过移动端API获取评分数据"""
        try:
            # 构造移动端API URL
            api_url = f"https://m.douban.com/rexxar/api/v2/subject/{anime_id}"

            # 移动端请求头
            mobile_headers = self._get_realistic_headers(
                referer="https://m.douban.com/",
                is_ajax=True
            )
            mobile_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1'

            response = await self._make_ultimate_request(
                session, api_url,
                headers=mobile_headers,
                referer="https://m.douban.com/",
                is_ajax=True
            )

            if not response:
                return None

            # 解析JSON响应
            if isinstance(response, dict) and 'text' in response:
                import json
                try:
                    data = json.loads(response['text'])
                except json.JSONDecodeError:
                    return None
            else:
                data = response

            if not isinstance(data, dict):
                return None

            # 提取评分数据
            rating_info = data.get('rating', {})
            if not isinstance(rating_info, dict):
                return None

            raw_score = rating_info.get('value', 0)
            vote_count = rating_info.get('count', 0)

            if raw_score <= 0:
                return None

            # 创建RatingData对象
            rating = RatingData(
                website=WebsiteName.DOUBAN,
                raw_score=float(raw_score),
                vote_count=int(vote_count),
                score_distribution={},  # 移动端API通常不提供详细分布
                site_mean=None,
                site_std=None,
                last_updated=datetime.now(),
                url=f"https://movie.douban.com/subject/{anime_id}/"
            )

            return rating

        except Exception as e:
            logger.debug(f"移动端API获取评分异常: {e}")
            return None

    def _extract_rating_from_page(self, html: str) -> Optional[Dict[str, Any]]:
        """从豆瓣页面提取评分信息 - 增强版"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 多种方式查找评分
            raw_score = None
            vote_count = 0
            score_distribution = {}

            # 方法1: 标准评分元素
            rating_element = soup.find('strong', class_='ll rating_num')
            if rating_element:
                try:
                    raw_score = float(rating_element.text.strip())
                except ValueError:
                    pass

            # 方法2: 备用评分元素
            if raw_score is None:
                rating_selectors = [
                    'span.rating_num',
                    '.rating_num strong',
                    '[property="v:average"]',
                    '.rating-info .rating_num'
                ]

                for selector in rating_selectors:
                    element = soup.select_one(selector)
                    if element:
                        try:
                            raw_score = float(element.text.strip())
                            break
                        except ValueError:
                            continue

            # 方法3: 从JSON数据中提取
            if raw_score is None:
                json_match = re.search(r'"rating":\s*{\s*"average":\s*([0-9.]+)', html)
                if json_match:
                    try:
                        raw_score = float(json_match.group(1))
                    except ValueError:
                        pass

            if raw_score is None:
                logger.debug("未找到评分信息")
                return None

            # 查找评分人数 - 多种方式
            vote_selectors = [
                'a.rating_people',
                '.rating_people',
                '[property="v:votes"]',
                '.rating-info .rating_people'
            ]

            for selector in vote_selectors:
                element = soup.select_one(selector)
                if element:
                    vote_text = element.text
                    # 支持不同格式的数字
                    vote_patterns = [
                        r'(\d+)人评价',
                        r'(\d+)\s*人',
                        r'(\d+)',
                        r'(\d+(?:,\d+)*)'  # 支持逗号分隔的数字
                    ]

                    for pattern in vote_patterns:
                        vote_match = re.search(pattern, vote_text)
                        if vote_match:
                            try:
                                vote_str = vote_match.group(1).replace(',', '')
                                vote_count = int(vote_str)
                                break
                            except ValueError:
                                continue

                    if vote_count > 0:
                        break

            # 提取评分分布
            score_distribution = self._extract_score_distribution(soup, vote_count)

            return {
                'score': raw_score,
                'vote_count': vote_count,
                'score_distribution': score_distribution
            }

        except Exception as e:
            logger.error(f"提取评分信息失败: {e}")
            return None

    def _extract_score_distribution(self, soup: BeautifulSoup, total_votes: int) -> Dict[str, int]:
        """提取评分分布"""
        distribution = {}

        try:
            # 查找评分分布元素
            rating_per_elements = soup.find_all('span', class_='rating_per')

            if len(rating_per_elements) == 5:
                # 豆瓣是5星制，转换为10分制
                star_labels = ['5星', '4星', '3星', '2星', '1星']
                score_values = [10, 8, 6, 4, 2]  # 对应的10分制分数

                for i, (element, score) in enumerate(zip(rating_per_elements, score_values)):
                    try:
                        percent_text = element.text.strip().replace('%', '')
                        percent = float(percent_text)
                        count = int(total_votes * percent / 100) if total_votes > 0 else 0
                        distribution[str(score)] = count
                    except (ValueError, TypeError):
                        continue

            # 备用方法：从CSS或其他元素提取
            if not distribution:
                # 查找其他可能的分布数据
                distribution_elements = soup.select('.rating_betterthan, .rating_distribution')
                for element in distribution_elements:
                    # 尝试解析不同格式的分布数据
                    text = element.get_text()
                    # 这里可以添加更多解析逻辑
                    pass

        except Exception as e:
            logger.debug(f"提取评分分布失败: {e}")

        return distribution

    async def get_anime_details(self, session: aiohttp.ClientSession, anime_id: str) -> Optional[AnimeInfo]:
        """获取动漫详细信息"""
        url = f"{self.base_url}/subject/{anime_id}/"

        response = await self._make_ultimate_request(
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

# 注册豆瓣增强爬虫到工厂
from .base import ScraperFactory
ScraperFactory.register_scraper(WebsiteName.DOUBAN, DoubanEnhancedScraper)
