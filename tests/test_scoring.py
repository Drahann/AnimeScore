"""
测试评分算法
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scoring import ScoringEngine
from src.models.config import Config, ModelConfig, BayesianConfig, WeightsConfig
from src.models.anime import AnimeScore, AnimeInfo, RatingData, WebsiteName


@pytest.fixture
def config():
    """创建测试配置"""
    return Config(
        model=ModelConfig(
            bayesian=BayesianConfig(min_credible_votes=5000),
            weights=WeightsConfig(min_votes_threshold=50, use_natural_log=True),
            platform_weights={
                "bangumi": 1.0,
                "mal": 1.0,
                "douban": 1.0
            }
        )
    )


@pytest.fixture
def scoring_engine(config):
    """创建评分引擎"""
    return ScoringEngine(config)


def test_bayesian_average(scoring_engine):
    """测试贝叶斯平均计算"""
    # 测试用例：原始评分8.5，投票数1000，网站平均分7.0，最小可信投票数5000
    result = scoring_engine.calculate_bayesian_average(
        raw_score=8.5,
        vote_count=1000,
        site_mean=7.0,
        min_credible_votes=5000
    )
    
    # 期望结果：(1000 * 8.5 + 5000 * 7.0) / (1000 + 5000) = 43500 / 6000 = 7.25
    expected = (1000 * 8.5 + 5000 * 7.0) / (1000 + 5000)
    assert abs(result - expected) < 0.001


def test_z_score(scoring_engine):
    """测试Z-score标准化"""
    # 测试用例：评分8.0，网站平均分7.5，标准差0.5
    result = scoring_engine.calculate_z_score(
        score=8.0,
        site_mean=7.5,
        site_std=0.5
    )
    
    # 期望结果：(8.0 - 7.5) / 0.5 = 1.0
    expected = (8.0 - 7.5) / 0.5
    assert abs(result - expected) < 0.001


def test_weight_calculation(scoring_engine):
    """测试权重计算"""
    import math
    
    # 测试自然对数权重
    result = scoring_engine.calculate_weight(1000)
    expected = math.log(1000)
    assert abs(result - expected) < 0.001
    
    # 测试低于阈值的情况
    result = scoring_engine.calculate_weight(30)  # 低于50的阈值
    assert result == 0.0


def test_standard_deviation_calculation(scoring_engine):
    """测试从分布计算标准差"""
    # 测试用例：评分分布
    score_distribution = {
        "6": 10,
        "7": 20,
        "8": 30,
        "9": 20,
        "10": 10
    }
    mean_score = 8.0
    
    result = scoring_engine.calculate_standard_deviation_from_distribution(
        score_distribution, mean_score
    )
    
    # 手动计算期望结果
    total_votes = 90
    variance = (10 * (6-8)**2 + 20 * (7-8)**2 + 30 * (8-8)**2 + 20 * (9-8)**2 + 10 * (10-8)**2) / total_votes
    expected = variance ** 0.5
    
    assert abs(result - expected) < 0.001


def test_composite_score_calculation(scoring_engine):
    """测试综合评分计算"""
    # 创建测试动漫
    anime_info = AnimeInfo(title="测试动漫")
    anime_score = AnimeScore(anime_info=anime_info)
    
    # 添加评分数据
    rating1 = RatingData(
        website=WebsiteName.BANGUMI,
        raw_score=8.5,
        vote_count=1000,
        site_mean=7.5,
        site_std=0.8
    )
    
    rating2 = RatingData(
        website=WebsiteName.MAL,
        raw_score=8.2,
        vote_count=5000,
        site_mean=7.8,
        site_std=0.6
    )
    
    anime_score.ratings = [rating1, rating2]
    
    # 计算综合评分
    composite_score = scoring_engine.calculate_composite_score(anime_score)
    
    assert composite_score is not None
    assert composite_score.website_count == 2
    assert composite_score.total_votes == 6000
    assert composite_score.final_score > 0
    assert 0 <= composite_score.confidence <= 1


def test_ranking(scoring_engine):
    """测试排名功能"""
    # 创建多个测试动漫
    anime_list = []
    
    for i, score in enumerate([8.5, 7.2, 9.1, 6.8, 8.0]):
        anime_info = AnimeInfo(title=f"动漫{i+1}")
        anime_score = AnimeScore(anime_info=anime_info)
        
        # 添加模拟的综合评分
        from src.models.anime import CompositeScore
        anime_score.composite_score = CompositeScore(
            final_score=score,
            confidence=0.8,
            total_votes=1000,
            website_count=2,
            weighted_sum=score * 10,
            weight_sum=10
        )
        
        anime_list.append(anime_score)
    
    # 排名
    ranked_list = scoring_engine.rank_anime_list(anime_list)
    
    # 验证排名正确性
    assert len(ranked_list) == 5
    assert ranked_list[0].composite_score.rank == 1  # 最高分
    assert ranked_list[0].composite_score.final_score == 9.1
    assert ranked_list[-1].composite_score.rank == 5  # 最低分
    assert ranked_list[-1].composite_score.final_score == 6.8
    
    # 验证百分位数
    assert ranked_list[0].composite_score.percentile == 100.0
    assert ranked_list[-1].composite_score.percentile == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
