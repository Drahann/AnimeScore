"""
测试季度工具函数
"""
import pytest
import sys
from pathlib import Path
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.anime import Season
from src.utils.season_utils import (
    get_season_from_date, get_current_season, get_season_date_range,
    parse_season_string, format_season_string, is_anime_in_season,
    get_next_season, get_previous_season
)


def test_get_season_from_date():
    """测试从日期获取季度"""
    # 冬季 (1-3月)
    assert get_season_from_date(date(2024, 1, 15)) == (Season.WINTER, 2024)
    assert get_season_from_date(date(2024, 3, 31)) == (Season.WINTER, 2024)
    
    # 春季 (4-6月)
    assert get_season_from_date(date(2024, 4, 1)) == (Season.SPRING, 2024)
    assert get_season_from_date(date(2024, 6, 30)) == (Season.SPRING, 2024)
    
    # 夏季 (7-9月)
    assert get_season_from_date(date(2024, 7, 1)) == (Season.SUMMER, 2024)
    assert get_season_from_date(date(2024, 9, 30)) == (Season.SUMMER, 2024)
    
    # 秋季 (10-12月)
    assert get_season_from_date(date(2024, 10, 1)) == (Season.FALL, 2024)
    assert get_season_from_date(date(2024, 12, 31)) == (Season.FALL, 2024)


def test_get_season_date_range():
    """测试获取季度日期范围"""
    # 测试冬季 2024
    start, end = get_season_date_range(Season.WINTER, 2024, buffer_days=0)
    assert start == date(2024, 1, 1)
    assert end == date(2024, 3, 31)
    
    # 测试带缓冲期的春季
    start, end = get_season_date_range(Season.SPRING, 2024, buffer_days=15)
    assert start == date(2024, 3, 17)  # 4月1日 - 15天
    assert end == date(2024, 7, 15)    # 6月30日 + 15天


def test_parse_season_string():
    """测试解析季度字符串"""
    # 测试 "YYYY-Q" 格式
    assert parse_season_string("2024-1") == (Season.WINTER, 2024)
    assert parse_season_string("2024-2") == (Season.SPRING, 2024)
    assert parse_season_string("2024-3") == (Season.SUMMER, 2024)
    assert parse_season_string("2024-4") == (Season.FALL, 2024)
    
    # 测试 "Season YYYY" 格式
    assert parse_season_string("Winter 2024") == (Season.WINTER, 2024)
    assert parse_season_string("Spring 2024") == (Season.SPRING, 2024)
    assert parse_season_string("Summer 2024") == (Season.SUMMER, 2024)
    assert parse_season_string("Fall 2024") == (Season.FALL, 2024)
    
    # 测试错误格式
    with pytest.raises(ValueError):
        parse_season_string("2024-5")  # 无效季度
    
    with pytest.raises(ValueError):
        parse_season_string("Invalid 2024")  # 无效季度名


def test_format_season_string():
    """测试格式化季度字符串"""
    # 测试名称格式
    assert format_season_string(Season.WINTER, 2024, "name") == "Winter 2024"
    assert format_season_string(Season.SPRING, 2024, "name") == "Spring 2024"
    
    # 测试数字格式
    assert format_season_string(Season.WINTER, 2024, "number") == "2024-1"
    assert format_season_string(Season.SUMMER, 2024, "number") == "2024-3"


def test_is_anime_in_season():
    """测试动漫是否属于指定季度"""
    # 测试正常情况
    assert is_anime_in_season(date(2024, 1, 15), Season.WINTER, 2024, 0) == True
    assert is_anime_in_season(date(2024, 4, 15), Season.WINTER, 2024, 0) == False
    
    # 测试缓冲期
    assert is_anime_in_season(date(2023, 12, 20), Season.WINTER, 2024, 15) == True
    assert is_anime_in_season(date(2024, 4, 10), Season.WINTER, 2024, 15) == True
    
    # 测试 None 日期
    assert is_anime_in_season(None, Season.WINTER, 2024, 0) == False


def test_get_next_season():
    """测试获取下一个季度"""
    assert get_next_season(Season.WINTER, 2024) == (Season.SPRING, 2024)
    assert get_next_season(Season.SPRING, 2024) == (Season.SUMMER, 2024)
    assert get_next_season(Season.SUMMER, 2024) == (Season.FALL, 2024)
    assert get_next_season(Season.FALL, 2024) == (Season.WINTER, 2025)


def test_get_previous_season():
    """测试获取上一个季度"""
    assert get_previous_season(Season.SPRING, 2024) == (Season.WINTER, 2024)
    assert get_previous_season(Season.SUMMER, 2024) == (Season.SPRING, 2024)
    assert get_previous_season(Season.FALL, 2024) == (Season.SUMMER, 2024)
    assert get_previous_season(Season.WINTER, 2024) == (Season.FALL, 2023)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
