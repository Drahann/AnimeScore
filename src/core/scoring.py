"""
核心评分算法实现
包含Z-score标准化、贝叶斯平均、加权计算等功能
"""
import math
import numpy as np
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..models.anime import AnimeScore, RatingData, CompositeScore, WebsiteName
from ..models.config import Config


class ScoringEngine:
    """评分计算引擎"""
    
    def __init__(self, config: Config):
        self.config = config
        self.model_config = config.model
    
    def calculate_bayesian_average(self, raw_score: float, vote_count: int, 
                                 site_mean: float, min_credible_votes: Optional[int] = None) -> float:
        """
        计算贝叶斯平均分
        
        公式: S' = (N * S + M * μ) / (N + M)
        其中:
        - S: 原始评分
        - N: 投票数
        - M: 最小可信投票数
        - μ: 网站平均分
        """
        if min_credible_votes is None:
            min_credible_votes = self.model_config.bayesian.min_credible_votes
        
        bayesian_score = (
            (vote_count * raw_score + min_credible_votes * site_mean) /
            (vote_count + min_credible_votes)
        )
        
        logger.debug(f"Bayesian average: {raw_score} -> {bayesian_score} "
                    f"(votes: {vote_count}, site_mean: {site_mean}, M: {min_credible_votes})")
        
        return bayesian_score
    
    def calculate_z_score(self, score: float, site_mean: float, site_std: float) -> float:
        """
        计算Z-score标准化分数
        
        公式: Z = (S - μ) / σ
        其中:
        - S: 评分
        - μ: 网站平均分
        - σ: 网站标准差
        """
        if site_std == 0:
            logger.warning(f"Standard deviation is 0 for site mean {site_mean}, returning 0")
            return 0.0
        
        z_score = (score - site_mean) / site_std
        
        logger.debug(f"Z-score: {score} -> {z_score} "
                    f"(mean: {site_mean}, std: {site_std})")
        
        return z_score
    
    def calculate_weight(self, vote_count: int) -> float:
        """
        计算权重
        
        使用对数函数: W = ln(N) 或 log10(N)
        """
        if vote_count < self.model_config.weights.min_votes_threshold:
            return 0.0
        
        if self.model_config.weights.use_natural_log:
            weight = math.log(vote_count)
        else:
            weight = math.log10(vote_count)
        
        logger.debug(f"Weight calculation: {vote_count} votes -> {weight}")
        
        return weight
    
    def calculate_standard_deviation_from_distribution(self, 
                                                     score_distribution: Dict[str, int],
                                                     mean_score: float) -> float:
        """
        从评分分布计算标准差
        
        Args:
            score_distribution: 评分分布，如 {"1": 10, "2": 20, ...}
            mean_score: 平均分
        """
        total_votes = sum(score_distribution.values())
        if total_votes == 0:
            return 0.0
        
        # 计算方差
        variance = 0.0
        for score_str, count in score_distribution.items():
            try:
                score = float(score_str)
                variance += count * (score - mean_score) ** 2
            except ValueError:
                logger.warning(f"Invalid score in distribution: {score_str}")
                continue
        
        variance /= total_votes
        std_dev = math.sqrt(variance)
        
        logger.debug(f"Calculated std dev: {std_dev} from distribution with {total_votes} total votes")
        
        return std_dev
    
    def process_rating_data(self, rating: RatingData) -> RatingData:
        """
        处理单个评分数据，计算Z-score和权重（不使用贝叶斯平均）
        """
        if rating.raw_score is None or rating.vote_count is None:
            logger.warning(f"Missing raw_score or vote_count for {rating.website}")
            return rating

        # 如果没有网站统计数据，无法进行标准化
        if rating.site_mean is None or rating.site_std is None:
            logger.warning(f"Missing site statistics for {rating.website}")
            return rating

        # 不使用贝叶斯平均，直接使用原始评分
        rating.bayesian_score = rating.raw_score

        # 计算Z-score（使用原始评分）
        rating.z_score = self.calculate_z_score(
            rating.raw_score, rating.site_mean, rating.site_std
        )

        # 计算权重
        rating.weight = self.calculate_weight(rating.vote_count)

        # 应用平台权重
        platform_weight = self.model_config.platform_weights.get(rating.website.value, 1.0)
        rating.weight *= platform_weight

        logger.debug(f"Processed rating for {rating.website}: "
                    f"raw={rating.raw_score}, z_score={rating.z_score}, weight={rating.weight}")

        return rating
    
    def calculate_composite_score(self, anime_score: AnimeScore) -> Optional[CompositeScore]:
        """
        计算动漫的综合评分
        
        公式: C = Σ(Z_i * W_i) / Σ(W_i)
        """
        valid_ratings = []
        
        # 处理所有评分数据
        for rating in anime_score.ratings:
            processed_rating = self.process_rating_data(rating)
            
            # 只包含有效的评分数据
            if (processed_rating.z_score is not None and 
                processed_rating.weight is not None and 
                processed_rating.weight > 0):
                valid_ratings.append(processed_rating)
        
        min_websites = self.config.model.weights.min_websites
        if len(valid_ratings) < min_websites:
            logger.warning(f"Insufficient valid ratings for {anime_score.anime_info.title}: "
                          f"only {len(valid_ratings)} valid ratings (need {min_websites})")
            return None
        
        # 计算加权平均
        weighted_sum = sum(rating.z_score * rating.weight for rating in valid_ratings)
        weight_sum = sum(rating.weight for rating in valid_ratings)
        
        if weight_sum == 0:
            logger.warning(f"Total weight is 0 for {anime_score.anime_info.title}")
            return None
        
        final_score = weighted_sum / weight_sum
        
        # 计算置信度（基于参与网站数量和总投票数）
        total_votes = sum(rating.vote_count for rating in valid_ratings if rating.vote_count)
        website_count = len(valid_ratings)
        
        # 简单的置信度计算：基于网站数量和投票数
        confidence = min(1.0, (website_count / 6.0) * (math.log10(total_votes + 1) / 6.0))
        
        composite_score = CompositeScore(
            final_score=final_score,
            confidence=confidence,
            total_votes=total_votes,
            website_count=website_count,
            weighted_sum=weighted_sum,
            weight_sum=weight_sum
        )
        
        logger.info(f"Calculated composite score for {anime_score.anime_info.title}: "
                   f"{final_score:.3f} (confidence: {confidence:.3f}, "
                   f"websites: {website_count}, votes: {total_votes})")
        
        return composite_score
    
    def rank_anime_list(self, anime_list: List[AnimeScore]) -> List[AnimeScore]:
        """
        对动漫列表进行排名
        """
        # 过滤出有综合评分的动漫
        valid_anime = [anime for anime in anime_list if anime.composite_score is not None]

        # 按综合评分降序排序
        sorted_anime = sorted(valid_anime, key=lambda x: x.composite_score.final_score, reverse=True)

        # 分配排名和百分位数
        total_count = len(sorted_anime)
        for i, anime in enumerate(sorted_anime):
            rank = i + 1
            percentile = (total_count - rank + 1) / total_count * 100

            anime.composite_score.rank = rank
            anime.composite_score.percentile = percentile

        logger.info(f"Ranked {total_count} anime with valid composite scores")

        return sorted_anime

    def calculate_site_rankings(self, anime_list: List[AnimeScore]):
        """
        计算每个动漫在各个网站的排名
        """
        from collections import defaultdict

        # 按网站分组收集评分数据
        website_anime_scores = defaultdict(list)

        for anime_score in anime_list:
            for rating in anime_score.ratings:
                if rating.raw_score is not None:
                    website_anime_scores[rating.website].append({
                        'anime_score': anime_score,
                        'rating': rating,
                        'score': rating.raw_score
                    })

        # 为每个网站计算排名
        for website, anime_ratings in website_anime_scores.items():
            if len(anime_ratings) < 2:  # 至少需要2个动漫才能排名
                continue

            # 按评分降序排序
            sorted_ratings = sorted(anime_ratings, key=lambda x: x['score'], reverse=True)
            total_count = len(sorted_ratings)

            # 分配排名
            for i, item in enumerate(sorted_ratings):
                rank = i + 1
                percentile = (total_count - rank + 1) / total_count * 100

                # 更新评分数据中的排名信息
                item['rating'].site_rank = rank
                item['rating'].site_percentile = percentile

            logger.debug(f"Calculated rankings for {total_count} anime on {website.value}")

        logger.info(f"Calculated site rankings for {len(website_anime_scores)} websites")
    
    def calculate_site_statistics(self, all_scores: List[float]) -> Tuple[float, float]:
        """
        计算网站的平均分和标准差
        
        Args:
            all_scores: 网站上所有动漫的评分列表
            
        Returns:
            (mean, std): 平均分和标准差
        """
        if not all_scores:
            return 0.0, 0.0
        
        scores_array = np.array(all_scores)
        mean = np.mean(scores_array)
        std = np.std(scores_array, ddof=1)  # 使用样本标准差
        
        logger.info(f"Calculated site statistics: mean={mean:.3f}, std={std:.3f} "
                   f"from {len(all_scores)} scores")
        
        return float(mean), float(std)
