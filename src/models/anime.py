"""
动漫数据模型定义
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class AnimeType(str, Enum):
    """动漫类型枚举"""
    TV = "TV"
    MOVIE = "Movie"
    OVA = "OVA"
    ONA = "ONA"
    SPECIAL = "Special"
    MUSIC = "Music"


class AnimeStatus(str, Enum):
    """动漫状态枚举"""
    FINISHED = "Finished"
    AIRING = "Currently Airing"
    NOT_YET_AIRED = "Not yet aired"
    CANCELLED = "Cancelled"


class Season(str, Enum):
    """季度枚举"""
    WINTER = "Winter"
    SPRING = "Spring"
    SUMMER = "Summer"
    FALL = "Fall"


class WebsiteName(str, Enum):
    """支持的网站枚举"""
    BANGUMI = "bangumi"
    DOUBAN = "douban"
    MAL = "mal"
    ANILIST = "anilist"
    IMDB = "imdb"
    FILMARKS = "filmarks"


class RatingData(BaseModel):
    """单个网站的评分数据"""
    website: WebsiteName
    raw_score: Optional[float] = Field(None, description="原始评分")
    vote_count: Optional[int] = Field(None, description="评分人数")
    score_distribution: Optional[Dict[str, int]] = Field(None, description="分数分布，用于计算标准差")

    # 网站全局统计数据（用于标准化）
    site_mean: Optional[float] = Field(None, description="网站平均分")
    site_std: Optional[float] = Field(None, description="网站标准差")

    # 计算得出的数据
    bayesian_score: Optional[float] = Field(None, description="贝叶斯修正后的评分")
    z_score: Optional[float] = Field(None, description="标准化分数")
    weight: Optional[float] = Field(None, description="权重")

    # 排名信息
    site_rank: Optional[int] = Field(None, description="在该网站的排名")
    site_percentile: Optional[float] = Field(None, description="在该网站的百分位数")

    # 元数据
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    url: Optional[str] = Field(None, description="评分页面URL")
    
    @validator('raw_score')
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Score must be between 0 and 10')
        return v
    
    @validator('vote_count')
    def validate_vote_count(cls, v):
        if v is not None and v < 0:
            raise ValueError('Vote count must be non-negative')
        return v


class AnimeInfo(BaseModel):
    """动漫基本信息"""
    # 基本标识信息
    title: str = Field(..., description="主标题")
    title_english: Optional[str] = Field(None, description="英文标题")
    title_japanese: Optional[str] = Field(None, description="日文标题")
    title_chinese: Optional[str] = Field(None, description="中文标题")
    alternative_titles: List[str] = Field(default_factory=list, description="其他标题")
    
    # 基本属性
    anime_type: Optional[AnimeType] = Field(None, description="动漫类型")
    status: Optional[AnimeStatus] = Field(None, description="播放状态")
    episodes: Optional[int] = Field(None, description="总集数")
    duration: Optional[int] = Field(None, description="每集时长（分钟）")
    
    # 时间信息
    start_date: Optional[date] = Field(None, description="开始播放日期")
    end_date: Optional[date] = Field(None, description="结束播放日期")
    season: Optional[Season] = Field(None, description="播放季度")
    year: Optional[int] = Field(None, description="播放年份")
    
    # 制作信息
    studios: List[str] = Field(default_factory=list, description="制作公司")
    genres: List[str] = Field(default_factory=list, description="类型标签")
    source: Optional[str] = Field(None, description="原作来源")
    
    # 外部ID映射
    external_ids: Dict[WebsiteName, str] = Field(default_factory=dict, description="各网站的ID")
    
    # 描述信息
    synopsis: Optional[str] = Field(None, description="简介")

    # 媒体信息
    poster_image: Optional[str] = Field(None, description="海报图片URL")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    banner_image: Optional[str] = Field(None, description="横幅图片URL")
    
    @validator('episodes')
    def validate_episodes(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Episodes must be positive')
        return v
    
    @validator('year')
    def validate_year(cls, v):
        if v is not None and (v < 1900 or v > 2030):
            raise ValueError('Year must be reasonable')
        return v


class CompositeScore(BaseModel):
    """综合评分结果"""
    final_score: float = Field(..., description="最终综合分数")
    confidence: float = Field(..., description="置信度（0-1）")
    total_votes: int = Field(..., description="总投票数")
    website_count: int = Field(..., description="参与计算的网站数量")
    
    # 详细计算信息
    weighted_sum: float = Field(..., description="加权分数总和")
    weight_sum: float = Field(..., description="权重总和")
    
    # 排名信息（在计算完所有动漫后填入）
    rank: Optional[int] = Field(None, description="排名")
    percentile: Optional[float] = Field(None, description="百分位数")


class AnimeScore(BaseModel):
    """完整的动漫评分数据"""
    anime_info: AnimeInfo
    ratings: List[RatingData] = Field(default_factory=list, description="各网站评分数据")
    composite_score: Optional[CompositeScore] = Field(None, description="综合评分")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    def get_rating_by_website(self, website: WebsiteName) -> Optional[RatingData]:
        """根据网站名获取评分数据"""
        for rating in self.ratings:
            if rating.website == website:
                return rating
        return None
    
    def add_or_update_rating(self, rating_data: RatingData):
        """添加或更新网站评分数据"""
        existing_rating = self.get_rating_by_website(rating_data.website)
        if existing_rating:
            # 更新现有评分
            idx = self.ratings.index(existing_rating)
            self.ratings[idx] = rating_data
        else:
            # 添加新评分
            self.ratings.append(rating_data)
        
        self.updated_at = datetime.now()
    
    def has_sufficient_data(self, min_websites: int = 2) -> bool:
        """检查是否有足够的数据进行综合评分计算"""
        valid_ratings = [r for r in self.ratings if r.raw_score is not None and r.vote_count is not None]
        return len(valid_ratings) >= min_websites


class SeasonalAnalysis(BaseModel):
    """季度分析结果"""
    season: Season
    year: int
    anime_scores: List[AnimeScore] = Field(default_factory=list, description="该季度所有动漫评分")
    
    # 统计信息
    total_anime_count: int = Field(0, description="总动漫数量")
    analyzed_anime_count: int = Field(0, description="成功分析的动漫数量")
    
    # 分析时间
    analysis_date: datetime = Field(default_factory=datetime.now, description="分析时间")
    
    def get_top_anime(self, limit: int = 10) -> List[AnimeScore]:
        """获取排名前N的动漫"""
        valid_scores = [anime for anime in self.anime_scores if anime.composite_score is not None]
        sorted_scores = sorted(valid_scores, key=lambda x: x.composite_score.final_score, reverse=True)
        return sorted_scores[:limit]
    
    def get_anime_by_rank(self, rank: int) -> Optional[AnimeScore]:
        """根据排名获取动漫"""
        for anime in self.anime_scores:
            if anime.composite_score and anime.composite_score.rank == rank:
                return anime
        return None
