"""
季度相关的工具函数
"""
from datetime import datetime, date, timedelta
from typing import Tuple, Optional
from ..models.anime import Season


def get_season_from_date(target_date: date) -> Tuple[Season, int]:
    """
    根据日期确定对应的动漫季度
    
    动漫季度划分：
    - Winter (冬季): 1月-3月
    - Spring (春季): 4月-6月  
    - Summer (夏季): 7月-9月
    - Fall (秋季): 10月-12月
    
    Args:
        target_date: 目标日期
        
    Returns:
        (season, year): 季度和年份
    """
    month = target_date.month
    year = target_date.year
    
    if 1 <= month <= 3:
        return Season.WINTER, year
    elif 4 <= month <= 6:
        return Season.SPRING, year
    elif 7 <= month <= 9:
        return Season.SUMMER, year
    else:  # 10-12月
        return Season.FALL, year


def get_current_season() -> Tuple[Season, int]:
    """获取当前季度"""
    return get_season_from_date(date.today())


def get_season_date_range(season: Season, year: int, buffer_days: int = 30) -> Tuple[date, date]:
    """
    获取指定季度的日期范围（包含缓冲期）
    
    Args:
        season: 季度
        year: 年份
        buffer_days: 缓冲天数（在季度开始前和结束后的天数）
        
    Returns:
        (start_date, end_date): 开始和结束日期
    """
    # 季度的标准开始和结束月份
    season_months = {
        Season.WINTER: (1, 3),
        Season.SPRING: (4, 6),
        Season.SUMMER: (7, 9),
        Season.FALL: (10, 12)
    }
    
    start_month, end_month = season_months[season]
    
    # 季度的标准开始和结束日期
    season_start = date(year, start_month, 1)
    
    # 计算季度结束日期（该月的最后一天）
    if end_month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, end_month + 1, 1)
    season_end = next_month_start - timedelta(days=1)
    
    # 应用缓冲期
    buffer_delta = timedelta(days=buffer_days)
    start_date = season_start - buffer_delta
    end_date = season_end + buffer_delta
    
    return start_date, end_date


def parse_season_string(season_str: str) -> Tuple[Season, int]:
    """
    解析季度字符串
    
    支持的格式：
    - "2024-1" (Winter 2024)
    - "2024-2" (Spring 2024)
    - "2024-3" (Summer 2024)
    - "2024-4" (Fall 2024)
    - "Winter 2024"
    - "Spring 2024"
    - "Summer 2024"
    - "Fall 2024"
    
    Args:
        season_str: 季度字符串
        
    Returns:
        (season, year): 季度和年份
        
    Raises:
        ValueError: 如果格式不正确
    """
    season_str = season_str.strip()
    
    # 处理 "YYYY-Q" 格式
    if '-' in season_str:
        try:
            year_str, quarter_str = season_str.split('-')
            year = int(year_str)
            quarter = int(quarter_str)
            
            quarter_to_season = {
                1: Season.WINTER,
                2: Season.SPRING,
                3: Season.SUMMER,
                4: Season.FALL
            }
            
            if quarter not in quarter_to_season:
                raise ValueError(f"Invalid quarter: {quarter}. Must be 1-4.")
            
            return quarter_to_season[quarter], year
            
        except ValueError as e:
            raise ValueError(f"Invalid season format '{season_str}': {e}")
    
    # 处理 "Season YYYY" 格式
    parts = season_str.split()
    if len(parts) == 2:
        season_name, year_str = parts
        try:
            year = int(year_str)
            season_name_lower = season_name.lower()
            
            name_to_season = {
                'winter': Season.WINTER,
                'spring': Season.SPRING,
                'summer': Season.SUMMER,
                'fall': Season.FALL,
                'autumn': Season.FALL  # 别名
            }
            
            if season_name_lower not in name_to_season:
                raise ValueError(f"Invalid season name: {season_name}")
            
            return name_to_season[season_name_lower], year
            
        except ValueError as e:
            raise ValueError(f"Invalid season format '{season_str}': {e}")
    
    raise ValueError(f"Unrecognized season format: '{season_str}'. "
                    f"Expected formats: 'YYYY-Q' or 'Season YYYY'")


def format_season_string(season: Season, year: int, format_type: str = "name") -> str:
    """
    格式化季度字符串
    
    Args:
        season: 季度
        year: 年份
        format_type: 格式类型 ("name" 或 "number")
        
    Returns:
        格式化的季度字符串
    """
    if format_type == "number":
        season_to_quarter = {
            Season.WINTER: 1,
            Season.SPRING: 2,
            Season.SUMMER: 3,
            Season.FALL: 4
        }
        quarter = season_to_quarter[season]
        return f"{year}-{quarter}"
    else:  # format_type == "name"
        return f"{season.value} {year}"


def is_anime_in_season(anime_start_date: Optional[date], 
                      season: Season, 
                      year: int, 
                      buffer_days: int = 30) -> bool:
    """
    判断动漫是否属于指定季度
    
    Args:
        anime_start_date: 动漫开始播放日期
        season: 目标季度
        year: 目标年份
        buffer_days: 缓冲天数
        
    Returns:
        是否属于该季度
    """
    if anime_start_date is None:
        return False
    
    season_start, season_end = get_season_date_range(season, year, buffer_days)
    return season_start <= anime_start_date <= season_end


def get_next_season(season: Season, year: int) -> Tuple[Season, int]:
    """获取下一个季度"""
    season_order = [Season.WINTER, Season.SPRING, Season.SUMMER, Season.FALL]
    current_index = season_order.index(season)
    
    if current_index == 3:  # Fall -> Winter of next year
        return Season.WINTER, year + 1
    else:
        return season_order[current_index + 1], year


def get_previous_season(season: Season, year: int) -> Tuple[Season, int]:
    """获取上一个季度"""
    season_order = [Season.WINTER, Season.SPRING, Season.SUMMER, Season.FALL]
    current_index = season_order.index(season)
    
    if current_index == 0:  # Winter -> Fall of previous year
        return Season.FALL, year - 1
    else:
        return season_order[current_index - 1], year


def get_season_anime_count_estimate(season: Season) -> int:
    """
    估算每个季度的动漫数量（用于进度显示等）
    
    这是一个粗略的估算，实际数量会有变化
    """
    # 基于历史数据的粗略估算
    base_count = {
        Season.WINTER: 45,  # 冬季通常动漫较少
        Season.SPRING: 55,  # 春季动漫较多
        Season.SUMMER: 50,  # 夏季中等
        Season.FALL: 60     # 秋季最多
    }
    
    return base_count.get(season, 50)
