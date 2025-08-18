#!/usr/bin/env python3
"""
测试豆瓣增强爬虫集成到主程序
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import Config
from src.core.analyzer import AnimeAnalyzer
from src.models.anime import WebsiteName

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

async def test_douban_integration():
    """测试豆瓣爬虫集成"""
    logger.info("🚀 测试豆瓣增强爬虫集成")
    
    try:
        # 加载配置
        config_path = project_root / "config" / "config.yaml"
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return False
        
        config = Config.load_from_file(str(config_path))
        logger.success("✅ 配置加载成功")
        
        # 创建分析器
        analyzer = AnimeAnalyzer(config)
        logger.success("✅ 分析器创建成功")
        
        # 检查豆瓣爬虫是否正确注册
        scraper_status = analyzer.get_scraper_status()
        logger.info(f"📊 爬虫状态: {scraper_status}")
        
        if WebsiteName.DOUBAN in analyzer.scrapers:
            douban_scraper = analyzer.scrapers[WebsiteName.DOUBAN]
            logger.success(f"✅ 豆瓣爬虫已注册: {type(douban_scraper).__name__}")
            
            # 检查是否是增强版
            if hasattr(douban_scraper, '_search_with_ajax_and_direct_access'):
                logger.success("✅ 确认为豆瓣增强爬虫 (包含AJAX+直接访问组合策略)")
            else:
                logger.warning("⚠️ 可能不是增强版豆瓣爬虫")
            
            # 测试搜索功能
            logger.info("🔍 测试搜索功能...")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    results = await douban_scraper.search_anime(session, "你的名字")
                    
                    if results:
                        logger.success(f"✅ 搜索成功！找到 {len(results)} 个结果")
                        
                        # 显示第一个结果
                        first_result = results[0]
                        douban_id = first_result.external_ids.get(WebsiteName.DOUBAN, "未知")
                        logger.info(f"   首个结果: {first_result.title} (ID: {douban_id})")
                        
                        # 检查是否有评分数据
                        if hasattr(first_result, '_rating_data'):
                            rating = first_result._rating_data
                            logger.success(f"   ⭐ 评分: {rating.raw_score}, 投票: {rating.vote_count:,}")
                        
                        # 测试评分获取
                        if douban_id != "未知":
                            logger.info("📊 测试评分获取...")
                            rating_data = await douban_scraper.get_anime_rating(session, douban_id)
                            
                            if rating_data:
                                logger.success(f"✅ 评分获取成功: {rating_data.raw_score}, 投票: {rating_data.vote_count:,}")
                            else:
                                logger.warning("⚠️ 评分获取失败")
                    else:
                        logger.warning("❌ 搜索未找到结果")
                        
                except Exception as e:
                    logger.error(f"❌ 搜索测试失败: {e}")
        else:
            logger.error("❌ 豆瓣爬虫未注册")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 集成测试失败: {e}")
        return False

async def test_factory_registration():
    """测试工厂注册"""
    logger.info("🏭 测试爬虫工厂注册")
    
    try:
        from src.scrapers.base import ScraperFactory
        from src.models.anime import WebsiteName
        from src.models.config import WebsiteConfig
        
        # 检查可用爬虫
        available_scrapers = ScraperFactory.get_available_scrapers()
        logger.info(f"📋 可用爬虫: {[ws.value for ws in available_scrapers]}")
        
        if WebsiteName.DOUBAN in available_scrapers:
            logger.success("✅ 豆瓣爬虫已在工厂中注册")
            
            # 尝试创建豆瓣爬虫实例
            config = WebsiteConfig(
                enabled=True,
                base_url="https://movie.douban.com",
                rate_limit=3.0,
                timeout=30
            )
            
            scraper = ScraperFactory.create_scraper(WebsiteName.DOUBAN, config)
            
            if scraper:
                logger.success(f"✅ 豆瓣爬虫实例创建成功: {type(scraper).__name__}")
                
                # 检查是否是增强版
                if hasattr(scraper, '_search_with_ajax_and_direct_access'):
                    logger.success("✅ 确认为豆瓣增强爬虫")
                    return True
                else:
                    logger.warning("⚠️ 不是增强版豆瓣爬虫")
                    return False
            else:
                logger.error("❌ 豆瓣爬虫实例创建失败")
                return False
        else:
            logger.error("❌ 豆瓣爬虫未在工厂中注册")
            return False
            
    except Exception as e:
        logger.error(f"❌ 工厂注册测试失败: {e}")
        return False

async def test_config_compatibility():
    """测试配置兼容性"""
    logger.info("⚙️ 测试配置兼容性")
    
    try:
        # 检查配置文件
        config_path = project_root / "config" / "config.yaml"
        
        if config_path.exists():
            config = Config.load_from_file(str(config_path))
            
            # 检查豆瓣配置
            if hasattr(config.websites, 'douban'):
                douban_config = config.websites.douban
                logger.success("✅ 豆瓣配置存在")
                logger.info(f"   启用状态: {douban_config.enabled}")
                logger.info(f"   基础URL: {douban_config.base_url}")
                logger.info(f"   请求限制: {douban_config.rate_limit}秒")
                logger.info(f"   超时时间: {douban_config.timeout}秒")
                
                return True
            else:
                logger.warning("⚠️ 豆瓣配置不存在")
                return False
        else:
            logger.error("❌ 配置文件不存在")
            return False
            
    except Exception as e:
        logger.error(f"❌ 配置兼容性测试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("🎬 豆瓣增强爬虫集成测试开始")
    
    # 测试结果
    results = {}
    
    # 1. 测试工厂注册
    logger.info("=" * 50)
    results['factory'] = await test_factory_registration()
    
    # 2. 测试配置兼容性
    logger.info("=" * 50)
    results['config'] = await test_config_compatibility()
    
    # 3. 测试豆瓣集成
    logger.info("=" * 50)
    results['integration'] = await test_douban_integration()
    
    # 总结结果
    logger.info("=" * 50)
    logger.info("📊 测试结果总结:")
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.success("🎉 所有测试通过！豆瓣增强爬虫已成功集成到主程序")
    else:
        logger.error("❌ 部分测试失败，请检查配置和代码")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
