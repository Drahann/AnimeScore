#!/usr/bin/env python3
"""
项目初始化脚本
"""
import sys
import shutil
from pathlib import Path
import click
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_directories():
    """创建必要的目录"""
    directories = [
        "data/cache",
        "data/results", 
        "data/logs",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


def setup_config():
    """设置配置文件"""
    config_file = Path("config/config.yaml")
    example_file = Path("config/config.example.yaml")
    
    if not config_file.exists() and example_file.exists():
        shutil.copy(example_file, config_file)
        logger.info(f"Created config file: {config_file}")
        logger.warning("Please edit config/config.yaml to add your API keys and preferences")
    elif config_file.exists():
        logger.info("Config file already exists")
    else:
        logger.error("Example config file not found!")


def check_dependencies():
    """检查依赖包"""
    # 包名映射：pip包名 -> import名
    package_mapping = {
        "requests": "requests",
        "pandas": "pandas",
        "numpy": "numpy",
        "scipy": "scipy",
        "beautifulsoup4": "bs4",  # 修复：beautifulsoup4 导入时是 bs4
        "lxml": "lxml",
        "pydantic": "pydantic",
        "click": "click",
        "aiohttp": "aiohttp",
        "loguru": "loguru",
        "PyYAML": "yaml"  # 修复：PyYAML 导入时是 yaml
    }

    missing_packages = []

    for pip_name, import_name in package_mapping.items():
        try:
            __import__(import_name)
            logger.info(f"✓ {pip_name}")
        except ImportError:
            missing_packages.append(pip_name)
            logger.warning(f"✗ {pip_name} (missing)")

    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.info("Please run: pip install -r requirements.txt")
        return False
    else:
        logger.info("All required packages are installed!")
        return True


def test_basic_functionality():
    """测试基本功能"""
    try:
        from src.models.config import Config
        from src.models.anime import AnimeInfo, Season
        from src.core.scoring import ScoringEngine
        from src.utils.season_utils import get_current_season
        
        logger.info("✓ All modules imported successfully")
        
        # 测试配置加载
        try:
            config = Config.load_from_file("config/config.yaml")
            logger.info("✓ Configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Configuration loading failed: {e}")
            return False
        
        # 测试评分引擎
        scoring_engine = ScoringEngine(config)
        logger.info("✓ Scoring engine created successfully")
        
        # 测试季度工具
        season, year = get_current_season()
        logger.info(f"✓ Current season detected: {season.value} {year}")
        
        return True
        
    except Exception as e:
        logger.error(f"Basic functionality test failed: {e}")
        return False


@click.command()
@click.option('--check-only', is_flag=True, help='Only check setup without making changes')
def main(check_only):
    """初始化 AnimeScore 项目"""
    
    logger.remove()
    logger.add(sys.stdout, level="INFO", 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    logger.info("=== AnimeScore Project Setup ===")
    
    if not check_only:
        logger.info("Setting up directories...")
        setup_directories()
        
        logger.info("Setting up configuration...")
        setup_config()
    
    logger.info("Checking dependencies...")
    deps_ok = check_dependencies()
    
    if deps_ok:
        logger.info("Testing basic functionality...")
        func_ok = test_basic_functionality()
        
        if func_ok:
            logger.info("🎉 Setup completed successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Edit config/config.yaml to add your API keys")
            logger.info("2. Run: python scripts/run_seasonal_analysis.py")
        else:
            logger.error("❌ Setup completed with errors")
            sys.exit(1)
    else:
        logger.error("❌ Missing dependencies")
        sys.exit(1)


if __name__ == "__main__":
    main()
