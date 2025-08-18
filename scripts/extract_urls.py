#!/usr/bin/env python3
"""
URL提取脚本
从JSON结果文件中提取所有评分网站的URL，输出到txt文件中便于手动检查
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import click
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import Config

class URLExtractor:
    """URL提取器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def find_latest_results_file(self) -> str:
        """查找最新的结果文件（优先从 final_results 目录）"""
        # 首先检查 final_results 目录
        final_results_dir = Path(self.config.storage.final_results_dir)
        if final_results_dir.exists():
            json_files = list(final_results_dir.glob("anime_ranking_*.json"))
            if json_files:
                latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"📂 自动选择 final_results 中的最新文件: {latest_file.name}")
                return str(latest_file)
        
        # 如果 final_results 没有文件，则从普通 results 目录查找
        results_dir = Path(self.config.storage.results_dir)
        if not results_dir.exists():
            raise FileNotFoundError("结果目录不存在")
        
        json_files = list(results_dir.glob("anime_ranking_*.json"))
        if not json_files:
            raise FileNotFoundError("没有找到分析结果文件")
        
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 自动选择 results 中的最新文件: {latest_file.name}")
        return str(latest_file)
    
    def extract_urls_from_json(self, file_path: str) -> Dict[str, List[Dict]]:
        """从JSON文件中提取所有URL"""
        logger.info(f"📂 加载JSON文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 按网站分类存储URL信息
        urls_by_website = {}
        total_urls = 0
        
        for ranking in data.get('rankings', []):
            anime_title = ranking.get('title', '未知动漫')
            
            for rating in ranking.get('ratings', []):
                website = rating.get('website', '未知网站')
                url = rating.get('url', '')
                raw_score = rating.get('raw_score', 0)
                vote_count = rating.get('vote_count', 0)
                
                if url:  # 只处理有URL的评分
                    if website not in urls_by_website:
                        urls_by_website[website] = []
                    
                    urls_by_website[website].append({
                        'anime_title': anime_title,
                        'url': url,
                        'raw_score': raw_score,
                        'vote_count': vote_count
                    })
                    total_urls += 1
        
        logger.info(f"✅ 成功提取 {total_urls} 个URL，涵盖 {len(urls_by_website)} 个网站")
        
        # 显示统计信息
        for website, urls in urls_by_website.items():
            logger.info(f"   {website}: {len(urls)} 个URL")
        
        return urls_by_website
    
    def save_urls_to_txt(self, urls_by_website: Dict[str, List[Dict]], output_path: str, format_type: str = "grouped"):
        """保存URL到txt文件"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入文件头
            f.write("=" * 80 + "\n")
            f.write("动漫评分网站URL列表\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            if format_type == "grouped":
                self._write_grouped_format(f, urls_by_website)
            elif format_type == "simple":
                self._write_simple_format(f, urls_by_website)
            elif format_type == "detailed":
                self._write_detailed_format(f, urls_by_website)
            
            # 写入统计信息
            total_urls = sum(len(urls) for urls in urls_by_website.values())
            f.write("\n" + "=" * 80 + "\n")
            f.write("统计信息:\n")
            f.write(f"总URL数: {total_urls}\n")
            f.write(f"网站数: {len(urls_by_website)}\n")
            for website, urls in sorted(urls_by_website.items()):
                f.write(f"  {website}: {len(urls)} 个\n")
        
        logger.success(f"✅ URL列表已保存到: {output_file}")
    
    def _write_grouped_format(self, f, urls_by_website: Dict[str, List[Dict]]):
        """按网站分组的格式"""
        for website, urls in sorted(urls_by_website.items()):
            f.write(f"\n{'='*20} {website.upper()} ({'='*20}\n")
            f.write(f"共 {len(urls)} 个URL\n\n")
            
            for i, url_info in enumerate(urls, 1):
                f.write(f"{i:3d}. {url_info['anime_title']}\n")
                f.write(f"     评分: {url_info['raw_score']} ({url_info['vote_count']:,} 票)\n")
                f.write(f"     URL: {url_info['url']}\n\n")
    
    def _write_simple_format(self, f, urls_by_website: Dict[str, List[Dict]]):
        """简单格式（只有URL）"""
        f.write("所有URL列表:\n\n")
        
        url_count = 1
        for website, urls in sorted(urls_by_website.items()):
            for url_info in urls:
                f.write(f"{url_count:3d}. {url_info['url']}\n")
                url_count += 1
    
    def _write_detailed_format(self, f, urls_by_website: Dict[str, List[Dict]]):
        """详细格式（包含所有信息）"""
        url_count = 1
        for website, urls in sorted(urls_by_website.items()):
            for url_info in urls:
                f.write(f"{url_count:3d}. 【{website.upper()}】{url_info['anime_title']}\n")
                f.write(f"     评分: {url_info['raw_score']} | 投票: {url_info['vote_count']:,} | 网站: {website}\n")
                f.write(f"     URL: {url_info['url']}\n")
                f.write(f"     检查: [ ] 正确 [ ] 错误 [ ] 需要修正\n\n")
                url_count += 1
    
    def save_urls_by_website(self, urls_by_website: Dict[str, List[Dict]], output_dir: str):
        """为每个网站单独保存URL文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for website, urls in urls_by_website.items():
            website_file = output_path / f"urls_{website}_{timestamp}.txt"
            
            with open(website_file, 'w', encoding='utf-8') as f:
                f.write(f"{website.upper()} 网站URL列表\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"共 {len(urls)} 个URL\n")
                f.write("=" * 60 + "\n\n")
                
                for i, url_info in enumerate(urls, 1):
                    f.write(f"{i:3d}. {url_info['anime_title']}\n")
                    f.write(f"     评分: {url_info['raw_score']} ({url_info['vote_count']:,} 票)\n")
                    f.write(f"     URL: {url_info['url']}\n")
                    f.write(f"     检查: [ ] 正确 [ ] 错误\n\n")
            
            logger.info(f"✅ {website} URL列表已保存到: {website_file}")
    
    def create_url_validation_checklist(self, urls_by_website: Dict[str, List[Dict]], output_path: str):
        """创建URL验证检查清单"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("动漫评分网站URL验证检查清单\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("使用说明: 访问每个URL，检查是否指向正确的动漫页面\n")
            f.write("标记: ✓ = 正确, ✗ = 错误, ? = 需要进一步确认\n")
            f.write("=" * 50 + "\n\n")
            
            url_count = 1
            for website, urls in sorted(urls_by_website.items()):
                f.write(f"\n【{website.upper()}】网站 ({len(urls)} 个URL)\n")
                f.write("-" * 40 + "\n")
                
                for url_info in urls:
                    f.write(f"{url_count:3d}. [ ] {url_info['anime_title']}\n")
                    f.write(f"        评分: {url_info['raw_score']} | 投票: {url_info['vote_count']:,}\n")
                    f.write(f"        URL: {url_info['url']}\n")
                    f.write(f"        备注: ________________________\n\n")
                    url_count += 1
        
        logger.success(f"✅ URL验证检查清单已保存到: {output_file}")


@click.command()
@click.option('--config', '-c', default='config/config.yaml',
              help='配置文件路径')
@click.option('--input', '-i', default=None,
              help='输入的JSON文件路径 (默认: 自动选择最新文件)')
@click.option('--output', '-o', default=None,
              help='输出目录 (默认: final_results目录)')
@click.option('--format', '-f', 'format_type', 
              type=click.Choice(['grouped', 'simple', 'detailed']), 
              default='grouped',
              help='输出格式: grouped=按网站分组, simple=只有URL, detailed=详细信息')
@click.option('--separate', '-s', is_flag=True,
              help='为每个网站单独生成文件')
@click.option('--checklist', is_flag=True,
              help='生成URL验证检查清单')
@click.option('--verbose', '-v', is_flag=True,
              help='启用详细日志')
def main(config, input, output, format_type, separate, checklist, verbose):
    """URL提取程序 - 从JSON结果文件中提取所有评分网站的URL"""
    
    # 设置日志级别
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("🔗 启动URL提取程序")
    
    try:
        # 1. 加载配置
        app_config = Config.load_from_file(config)
        logger.info(f"✅ 配置加载成功: {config}")
        
        # 2. 创建URL提取器
        extractor = URLExtractor(app_config)
        
        # 3. 确定输入文件
        if input is None:
            logger.info("🔍 未指定输入文件，自动查找最新结果...")
            input_file = extractor.find_latest_results_file()
        else:
            input_file = input
            logger.info(f"📂 使用指定的输入文件: {input_file}")
        
        # 4. 提取URL
        urls_by_website = extractor.extract_urls_from_json(input_file)
        
        if not urls_by_website:
            logger.warning("⚠️ 没有找到任何URL")
            return
        
        # 5. 确定输出目录
        output_dir = output or app_config.storage.final_results_dir
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 6. 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_filename = Path(input_file).stem
        
        # 7. 保存URL列表
        if separate:
            # 为每个网站单独生成文件
            extractor.save_urls_by_website(urls_by_website, output_dir)
        else:
            # 生成统一的URL列表
            output_file = output_path / f"urls_list_{format_type}_{timestamp}.txt"
            extractor.save_urls_to_txt(urls_by_website, str(output_file), format_type)
        
        # 8. 生成检查清单
        if checklist:
            checklist_file = output_path / f"url_validation_checklist_{timestamp}.txt"
            extractor.create_url_validation_checklist(urls_by_website, str(checklist_file))
        
        logger.success("🎉 URL提取完成！")
        logger.info(f"📁 输出目录: {output_dir}")
        
        # 显示使用建议
        logger.info("\n💡 使用建议:")
        logger.info("   • 使用浏览器打开URL列表文件")
        logger.info("   • 逐个访问URL检查页面正确性")
        logger.info("   • 记录需要修正的URL")
        logger.info("   • 使用 manual_data_correction.py 修正错误数据")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
