"""
配置管理模型
"""
from typing import Dict, Optional, List
from pydantic import BaseModel, Field, validator
from pathlib import Path
import yaml
import os


class APIKeys(BaseModel):
    """API密钥配置"""
    bangumi: Dict[str, str] = Field(default_factory=dict)
    mal: Dict[str, str] = Field(default_factory=dict)
    anilist: Dict[str, str] = Field(default_factory=dict)


class WebsiteConfig(BaseModel):
    """单个网站配置"""
    enabled: bool = True
    api_base_url: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: float = Field(1.0, description="请求间隔（秒）")
    timeout: int = Field(30, description="请求超时（秒）")
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v < 0:
            raise ValueError('Rate limit must be non-negative')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v


class BayesianConfig(BaseModel):
    """贝叶斯平均配置"""
    min_credible_votes: int = Field(5000, description="最小可信投票数（M参数）")
    
    @validator('min_credible_votes')
    def validate_min_credible_votes(cls, v):
        if v <= 0:
            raise ValueError('Min credible votes must be positive')
        return v


class WeightsConfig(BaseModel):
    """权重计算配置"""
    min_votes_threshold: int = Field(50, description="最小投票数阈值")
    min_websites: int = Field(2, description="最小网站数量要求")
    use_natural_log: bool = Field(True, description="是否使用自然对数")

    @validator('min_votes_threshold')
    def validate_min_votes_threshold(cls, v):
        if v < 0:
            raise ValueError('Min votes threshold must be non-negative')
        return v

    @validator('min_websites')
    def validate_min_websites(cls, v):
        if v < 1:
            raise ValueError('Min websites must be at least 1')
        return v


class SiteStatisticsConfig(BaseModel):
    """网站统计数据配置"""
    method: str = Field("seasonal", description="统计方法：seasonal 或 fixed")
    min_seasonal_samples: int = Field(5, description="季度统计最小样本数")

    @validator('method')
    def validate_method(cls, v):
        if v not in ['seasonal', 'fixed']:
            raise ValueError('Method must be either "seasonal" or "fixed"')
        return v

    @validator('min_seasonal_samples')
    def validate_min_samples(cls, v):
        if v < 1:
            raise ValueError('Min seasonal samples must be positive')
        return v


class ModelConfig(BaseModel):
    """数学模型配置"""
    bayesian: BayesianConfig = Field(default_factory=BayesianConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    platform_weights: Dict[str, float] = Field(default_factory=lambda: {
        "bangumi": 1.0,
        "douban": 1.0,
        "mal": 1.0,
        "anilist": 1.0,
        "imdb": 0.8,
        "filmarks": 0.9
    })
    site_statistics: SiteStatisticsConfig = Field(default_factory=SiteStatisticsConfig)
    
    @validator('platform_weights')
    def validate_platform_weights(cls, v):
        for platform, weight in v.items():
            if weight < 0:
                raise ValueError(f'Platform weight for {platform} must be non-negative')
        return v


class SeasonalConfig(BaseModel):
    """季度配置"""
    current_season: Optional[str] = Field(None, description="当前季度，格式：YYYY-Q")
    season_buffer_days: int = Field(30, description="季度缓冲天数")
    min_episodes: int = Field(1, description="最小集数")
    
    @validator('season_buffer_days')
    def validate_season_buffer_days(cls, v):
        if v < 0:
            raise ValueError('Season buffer days must be non-negative')
        return v
    
    @validator('min_episodes')
    def validate_min_episodes(cls, v):
        if v < 0:
            raise ValueError('Min episodes must be non-negative')
        return v


class DataCompletionConfig(BaseModel):
    """数据补全配置"""
    enabled: bool = Field(True, description="是否启用数据补全")
    max_retry_per_anime: int = Field(3, description="每个动漫每个网站的最大重试次数")
    search_timeout: int = Field(30, description="搜索超时时间（秒）")
    use_alternative_names: bool = Field(True, description="是否使用备选名称搜索")
    parallel_searches: int = Field(5, description="并行搜索数量")
    min_existing_websites: int = Field(1, description="尝试补全的最小现有网站数")
    priority_websites: List[str] = Field(
        default_factory=lambda: ["bangumi", "mal", "anilist"],
        description="优先补全的网站列表"
    )

    @validator('max_retry_per_anime')
    def validate_max_retry(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Max retry per anime must be between 1 and 10')
        return v

    @validator('search_timeout')
    def validate_search_timeout(cls, v):
        if v < 5 or v > 120:
            raise ValueError('Search timeout must be between 5 and 120 seconds')
        return v

    @validator('parallel_searches')
    def validate_parallel_searches(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Parallel searches must be between 1 and 20')
        return v

    @validator('min_existing_websites')
    def validate_min_existing_websites(cls, v):
        if v < 0:
            raise ValueError('Min existing websites must be non-negative')
        return v


class StorageConfig(BaseModel):
    """存储配置"""
    cache_dir: str = Field("data/cache", description="缓存目录")
    results_dir: str = Field("data/results", description="结果目录")
    cache_expiration: int = Field(24, description="缓存过期时间（小时）")
    export_formats: List[str] = Field(default_factory=lambda: ["json", "csv", "xlsx"])
    
    @validator('cache_expiration')
    def validate_cache_expiration(cls, v):
        if v <= 0:
            raise ValueError('Cache expiration must be positive')
        return v


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field("INFO", description="日志级别")
    file: str = Field("data/logs/animescore.log", description="日志文件路径")
    max_file_size: str = Field("10MB", description="最大文件大小")
    backup_count: int = Field(5, description="备份文件数量")
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()


class Config(BaseModel):
    """主配置类"""
    api_keys: APIKeys = Field(default_factory=APIKeys)
    websites: Dict[str, WebsiteConfig] = Field(default_factory=dict)
    model: ModelConfig = Field(default_factory=ModelConfig)
    seasonal: SeasonalConfig = Field(default_factory=SeasonalConfig)
    data_completion: DataCompletionConfig = Field(default_factory=DataCompletionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def load_from_file(cls, config_path: str = "config/config.yaml") -> "Config":
        """从YAML文件加载配置"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            # 如果配置文件不存在，尝试从示例文件复制
            example_file = Path("config/config.example.yaml")
            if example_file.exists():
                raise FileNotFoundError(
                    f"Configuration file {config_path} not found. "
                    f"Please copy {example_file} to {config_path} and configure it."
                )
            else:
                raise FileNotFoundError(f"Configuration file {config_path} not found.")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: str = "config/config.yaml"):
        """保存配置到YAML文件"""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, allow_unicode=True)
    
    def get_website_config(self, website_name: str) -> Optional[WebsiteConfig]:
        """获取指定网站的配置"""
        return self.websites.get(website_name)
    
    def is_website_enabled(self, website_name: str) -> bool:
        """检查网站是否启用"""
        website_config = self.get_website_config(website_name)
        return website_config is not None and website_config.enabled
    
    def get_enabled_websites(self) -> List[str]:
        """获取所有启用的网站列表"""
        return [name for name, config in self.websites.items() if config.enabled]
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.storage.cache_dir,
            self.storage.results_dir,
            Path(self.logging.file).parent
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
