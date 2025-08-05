"""
动漫筛选和过滤工具
"""
from datetime import date, datetime
from typing import List, Optional, Set
from loguru import logger

from ..models.anime import AnimeInfo, AnimeType, AnimeStatus, Season
from .season_utils import is_anime_in_season, get_season_date_range


class AnimeFilter:
    """动漫筛选器"""
    
    def __init__(self, min_episodes: int = 1, 
                 excluded_types: Optional[Set[AnimeType]] = None,
                 excluded_statuses: Optional[Set[AnimeStatus]] = None):
        self.min_episodes = min_episodes
        self.excluded_types = excluded_types or set()
        self.excluded_statuses = excluded_statuses or set()
    
    def filter_seasonal_anime(self, anime_list: List[AnimeInfo], 
                            season: Season, year: int, 
                            buffer_days: int = 30) -> List[AnimeInfo]:
        """筛选季度新番"""
        filtered = []
        
        for anime in anime_list:
            if self._is_valid_seasonal_anime(anime, season, year, buffer_days):
                filtered.append(anime)
        
        logger.info(f"Filtered {len(filtered)} anime from {len(anime_list)} "
                   f"for {season.value} {year}")
        
        return filtered
    
    def _is_valid_seasonal_anime(self, anime: AnimeInfo, 
                               season: Season, year: int, 
                               buffer_days: int) -> bool:
        """检查动漫是否为有效的季度新番"""
        
        # 1. 检查动漫类型
        if anime.anime_type in self.excluded_types:
            logger.debug(f"Excluded {anime.title}: type {anime.anime_type}")
            return False
        
        # 2. 检查动漫状态
        if anime.status in self.excluded_statuses:
            logger.debug(f"Excluded {anime.title}: status {anime.status}")
            return False
        
        # 3. 检查集数
        if anime.episodes is not None and anime.episodes < self.min_episodes:
            logger.debug(f"Excluded {anime.title}: episodes {anime.episodes} < {self.min_episodes}")
            return False
        
        # 4. 检查是否属于指定季度
        if not is_anime_in_season(anime.start_date, season, year, buffer_days):
            logger.debug(f"Excluded {anime.title}: not in {season.value} {year}")
            return False
        
        # 5. 额外的质量检查
        if not self._quality_check(anime):
            return False
        
        return True
    
    def _quality_check(self, anime: AnimeInfo) -> bool:
        """额外的质量检查"""
        
        # 检查标题是否有效
        if not anime.title or len(anime.title.strip()) == 0:
            logger.debug(f"Excluded anime: empty title")
            return False
        
        # 检查标题长度（过滤明显错误的数据）
        if len(anime.title) > 200:
            logger.debug(f"Excluded {anime.title}: title too long")
            return False
        
        return True
    
    def deduplicate_anime(self, anime_list: List[AnimeInfo]) -> List[AnimeInfo]:
        """去重动漫列表"""
        seen_titles = set()
        seen_ids = {}
        deduplicated = []
        
        for anime in anime_list:
            # 标准化标题用于比较
            normalized_title = self._normalize_title(anime.title)
            
            # 检查是否已经见过相同标题
            if normalized_title in seen_titles:
                # 尝试合并外部ID
                existing_anime = self._find_anime_by_title(deduplicated, normalized_title)
                if existing_anime:
                    existing_anime.external_ids.update(anime.external_ids)
                    # 合并其他信息
                    self._merge_anime_info(existing_anime, anime)
                continue
            
            # 检查外部ID是否重复
            duplicate_found = False
            for website, anime_id in anime.external_ids.items():
                if website in seen_ids and seen_ids[website] == anime_id:
                    duplicate_found = True
                    break
            
            if duplicate_found:
                continue
            
            # 添加到结果列表
            seen_titles.add(normalized_title)
            for website, anime_id in anime.external_ids.items():
                seen_ids[website] = anime_id
            
            deduplicated.append(anime)
        
        logger.info(f"Deduplicated {len(anime_list)} -> {len(deduplicated)} anime")
        return deduplicated
    
    def _normalize_title(self, title: str) -> str:
        """标准化标题用于比较"""
        # 移除特殊字符，转换为小写，移除多余空格
        import re
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _find_anime_by_title(self, anime_list: List[AnimeInfo], 
                           normalized_title: str) -> Optional[AnimeInfo]:
        """根据标准化标题查找动漫"""
        for anime in anime_list:
            if self._normalize_title(anime.title) == normalized_title:
                return anime
        return None
    
    def _merge_anime_info(self, existing: AnimeInfo, new: AnimeInfo):
        """合并动漫信息"""
        logger.debug(f"🔄 合并动漫信息: {existing.title}")

        # 合并标题
        if new.title_english and not existing.title_english:
            logger.debug(f"   📝 添加英文标题: {new.title_english}")
            existing.title_english = new.title_english

        if new.title_japanese and not existing.title_japanese:
            logger.debug(f"   📝 添加日文标题: {new.title_japanese}")
            existing.title_japanese = new.title_japanese

        if new.title_chinese and not existing.title_chinese:
            logger.info(f"   🇨🇳 添加中文标题: '{existing.title}' -> '{new.title_chinese}'")
            existing.title_chinese = new.title_chinese
        elif new.title_chinese and existing.title_chinese:
            logger.debug(f"   🇨🇳 中文标题已存在: {existing.title_chinese}")
        elif not new.title_chinese:
            logger.debug(f"   🇨🇳 新数据无中文标题: {new.title}")
        
        # 合并其他标题
        for alt_title in new.alternative_titles:
            if alt_title not in existing.alternative_titles:
                existing.alternative_titles.append(alt_title)
        
        # 合并类型标签
        for genre in new.genres:
            if genre not in existing.genres:
                existing.genres.append(genre)
        
        # 合并制作公司
        for studio in new.studios:
            if studio not in existing.studios:
                existing.studios.append(studio)
        
        # 更新缺失的字段
        if new.anime_type and not existing.anime_type:
            existing.anime_type = new.anime_type
        
        if new.status and not existing.status:
            existing.status = new.status
        
        if new.episodes and not existing.episodes:
            existing.episodes = new.episodes
        
        if new.start_date and not existing.start_date:
            existing.start_date = new.start_date
        
        if new.synopsis and not existing.synopsis:
            existing.synopsis = new.synopsis

        # 合并图片信息
        if new.poster_image and not existing.poster_image:
            existing.poster_image = new.poster_image

        if new.cover_image and not existing.cover_image:
            existing.cover_image = new.cover_image

        if new.banner_image and not existing.banner_image:
            existing.banner_image = new.banner_image
    
    def filter_by_popularity(self, anime_list: List[AnimeInfo], 
                           min_external_ids: int = 2) -> List[AnimeInfo]:
        """根据流行度筛选（基于外部ID数量）"""
        filtered = []
        
        for anime in anime_list:
            if len(anime.external_ids) >= min_external_ids:
                filtered.append(anime)
        
        logger.info(f"Popularity filter: {len(filtered)} anime with >= {min_external_ids} external IDs")
        return filtered
    
    def sort_by_start_date(self, anime_list: List[AnimeInfo]) -> List[AnimeInfo]:
        """按开始日期排序"""
        def sort_key(anime):
            if anime.start_date:
                return anime.start_date
            else:
                # 没有日期的放在最后
                return date.max
        
        return sorted(anime_list, key=sort_key)


def create_default_filter(config) -> AnimeFilter:
    """创建默认的动漫筛选器"""
    # 默认排除的类型（可以根据需要调整）
    excluded_types = {
        AnimeType.MUSIC  # 通常排除音乐类
    }
    
    # 默认排除的状态
    excluded_statuses = {
        AnimeStatus.CANCELLED  # 排除已取消的动漫
    }
    
    return AnimeFilter(
        min_episodes=config.seasonal.min_episodes,
        excluded_types=excluded_types,
        excluded_statuses=excluded_statuses
    )
