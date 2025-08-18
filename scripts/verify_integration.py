#!/usr/bin/env python3
"""
验证豆瓣增强爬虫集成状态
"""
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

def verify_integration():
    """验证集成状态"""
    logger.info("🔍 验证豆瓣增强爬虫集成状态")
    
    success_count = 0
    total_tests = 0
    
    # 测试1: 检查模块导入
    total_tests += 1
    try:
        from src.scrapers.douban_enhanced import DoubanEnhancedScraper
        logger.success("✅ 豆瓣增强爬虫模块导入成功")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 豆瓣增强爬虫模块导入失败: {e}")
    
    # 测试2: 检查工厂注册
    total_tests += 1
    try:
        from src.scrapers.base import ScraperFactory
        from src.models.anime import WebsiteName
        
        available_scrapers = ScraperFactory.get_available_scrapers()
        
        if WebsiteName.DOUBAN in available_scrapers:
            logger.success("✅ 豆瓣爬虫已在工厂中注册")
            success_count += 1
        else:
            logger.error("❌ 豆瓣爬虫未在工厂中注册")
    except Exception as e:
        logger.error(f"❌ 工厂注册检查失败: {e}")
    
    # 测试3: 检查爬虫实例创建
    total_tests += 1
    try:
        from src.scrapers.base import ScraperFactory
        from src.models.anime import WebsiteName
        from src.models.config import WebsiteConfig
        
        config = WebsiteConfig(
            enabled=True,
            base_url="https://movie.douban.com",
            rate_limit=5.0,
            timeout=60
        )
        
        scraper = ScraperFactory.create_scraper(WebsiteName.DOUBAN, config)
        
        if scraper and isinstance(scraper, DoubanEnhancedScraper):
            logger.success(f"✅ 豆瓣增强爬虫实例创建成功: {type(scraper).__name__}")
            success_count += 1
        else:
            logger.error(f"❌ 豆瓣爬虫实例创建失败或类型错误: {type(scraper) if scraper else None}")
    except Exception as e:
        logger.error(f"❌ 爬虫实例创建检查失败: {e}")
    
    # 测试4: 检查增强功能
    total_tests += 1
    try:
        if scraper and hasattr(scraper, '_search_with_ajax_and_direct_access'):
            logger.success("✅ 确认包含AJAX+直接访问组合策略")
            success_count += 1
        else:
            logger.error("❌ 缺少AJAX+直接访问组合策略")
    except Exception as e:
        logger.error(f"❌ 增强功能检查失败: {e}")
    
    # 测试5: 检查配置文件
    total_tests += 1
    try:
        from src.models.config import Config

        config_path = project_root / "config" / "config.yaml"
        if config_path.exists():
            config = Config.load_from_file(str(config_path))

            # 检查豆瓣是否在启用的网站列表中
            enabled_websites = config.get_enabled_websites()
            if 'douban' in enabled_websites:
                douban_config = config.get_website_config('douban')
                logger.success("✅ 豆瓣配置已启用")
                logger.info(f"   基础URL: {douban_config.base_url}")
                logger.info(f"   请求限制: {douban_config.rate_limit}秒")
                logger.info(f"   超时时间: {douban_config.timeout}秒")
                success_count += 1
            else:
                logger.warning("⚠️ 豆瓣未在启用的网站列表中")
        else:
            logger.error("❌ 配置文件不存在")
    except Exception as e:
        logger.error(f"❌ 配置文件检查失败: {e}")
    
    # 测试6: 检查分析器集成
    total_tests += 1
    try:
        from src.models.config import Config
        from src.core.analyzer import AnimeAnalyzer
        
        config = Config.load_from_file(str(config_path))
        analyzer = AnimeAnalyzer(config)
        
        scraper_status = analyzer.get_scraper_status()
        
        if 'douban' in scraper_status and scraper_status['douban']:
            logger.success("✅ 豆瓣爬虫已集成到分析器")
            
            # 检查爬虫类型
            if WebsiteName.DOUBAN in analyzer.scrapers:
                douban_scraper = analyzer.scrapers[WebsiteName.DOUBAN]
                if isinstance(douban_scraper, DoubanEnhancedScraper):
                    logger.success("✅ 分析器中使用的是豆瓣增强爬虫")
                    success_count += 1
                else:
                    logger.error(f"❌ 分析器中使用的不是豆瓣增强爬虫: {type(douban_scraper).__name__}")
            else:
                logger.error("❌ 豆瓣爬虫未在分析器中找到")
        else:
            logger.error("❌ 豆瓣爬虫未集成到分析器或未启用")
    except Exception as e:
        logger.error(f"❌ 分析器集成检查失败: {e}")
    
    # 总结
    logger.info("=" * 60)
    logger.info(f"📊 集成验证结果: {success_count}/{total_tests} 项测试通过")
    
    if success_count == total_tests:
        logger.success("🎉 豆瓣增强爬虫已完全集成到主程序！")
        logger.info("✨ 现在可以使用以下功能:")
        logger.info("   • AJAX+直接访问组合搜索策略")
        logger.info("   • 智能反反爬虫技术")
        logger.info("   • 完整的评分数据获取")
        logger.info("   • 多重备用搜索策略")
        return True
    elif success_count >= total_tests * 0.8:
        logger.warning("⚠️ 豆瓣增强爬虫基本集成成功，但有部分问题需要解决")
        return True
    else:
        logger.error("❌ 豆瓣增强爬虫集成失败，需要检查配置和代码")
        return False

def show_usage_guide():
    """显示使用指南"""
    logger.info("=" * 60)
    logger.info("📖 使用指南:")
    logger.info("")
    logger.info("1. 运行季度分析:")
    logger.info("   python scripts/run_seasonal_analysis.py --season 2024-1")
    logger.info("")
    logger.info("2. 测试豆瓣搜索:")
    logger.info("   python scripts/test_ajax_direct_combo.py")
    logger.info("")
    logger.info("3. 配置文件位置:")
    logger.info("   config/config.yaml")
    logger.info("")
    logger.info("4. 豆瓣配置项:")
    logger.info("   websites.douban.enabled: true")
    logger.info("   websites.douban.rate_limit: 5.0")
    logger.info("   websites.douban.timeout: 60")

def main():
    """主函数"""
    logger.info("🎬 豆瓣增强爬虫集成验证")
    
    success = verify_integration()
    
    if success:
        show_usage_guide()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
