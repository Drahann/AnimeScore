# 缺失数据分析和人工查找指南

本指南介绍如何使用缺失数据分析工具来找出需要人工查找的动漫，并生成便于查找的清单。

## 🔧 工具概述

我们提供了两个主要工具：

1. **`analyze_missing_data.py`** - 分析结果文件，找出缺失网站数据的动漫
2. **`generate_search_list.py`** - 生成人工查找清单，按优先级排序并提供搜索链接

## 📋 使用流程

### 步骤1: 运行季度分析

首先运行季度分析获得结果文件：

```bash
python scripts/run_seasonal_analysis.py --season "2023-4" --verbose
```

这会在 `data/results/` 目录下生成JSON格式的结果文件。

### 步骤2: 分析缺失数据

使用分析工具找出缺失数据：

```bash
python scripts/analyze_missing_data.py "data/results/anime_ranking_Fall_2023_20250802_140205.json"
```

**输出文件**：
- `missing_data_Fall_2023_YYYYMMDD_HHMMSS.csv` - 详细的缺失数据表格
- `missing_data_Fall_2023_YYYYMMDD_HHMMSS.json` - 完整的分析结果

**分析报告示例**：
```
📊 缺失数据分析摘要
============================================================
总动漫数量: 95
有缺失数据的动漫: 42
缺失数据比例: 44.2%

🌐 网站覆盖率:
  anilist   :  82/95 ( 86.3%)
  bangumi   :  54/95 ( 56.8%)
  filmarks  :  95/95 (100.0%)
  mal       :  95/95 (100.0%)

❌ 缺失模式 (前10个):
  缺失 bangumi                       :  29 个动漫
  缺失 anilist,bangumi               :  12 个动漫
  缺失 anilist                       :   1 个动漫
```

**注意**: 分析只包含配置文件中启用的网站 (enabled: true)。禁用的网站 (如douban、imdb) 不会被视为缺失。

### 步骤3: 生成查找清单

使用查找清单生成器创建人工查找清单：

```bash
python scripts/generate_search_list.py missing_data_Fall_2023_20250802_142425.json
```

**输出文件** (保存在 `data/searchlist/` 目录):
- `search_list_YYYYMMDD_HHMMSS.csv` - 主要查找清单（按优先级排序）
- `search_list_YYYYMMDD_HHMMSS.json` - 详细数据（包含搜索URL）
- `search_list_YYYYMMDD_HHMMSS_by_website.csv` - 按缺失网站分组的清单

## 📊 输出文件说明

### 主要查找清单 (search_list_*.csv)

包含以下关键字段：

| 字段 | 说明 |
|------|------|
| `priority` | 查找优先级 (0-100，越高越重要) |
| `rank` | 在季度排名中的位置 |
| `title` | 动漫原标题 |
| `title_english` | 英文标题 |
| `missing_websites` | 缺失的网站列表 |
| `search_keyword_1/2/3` | 建议的搜索关键词 |
| `anilist_search_url` | AniList搜索链接 |
| `bangumi_search_url` | Bangumi搜索链接 |
| `filmarks_search_url` | Filmarks搜索链接 |
| `mal_search_url` | MyAnimeList搜索链接 |
| `composite_score` | 综合评分 |
| `total_votes` | 总投票数 |

### 优先级计算规则

优先级基于以下因素计算：

1. **排名分数** (50分): 排名越高分数越高
2. **投票数分数** (30分): 投票越多分数越高  
3. **置信度分数** (20分): 置信度越高分数越高
4. **缺失惩罚**: 缺失网站越多扣分越多

**高优先级动漫** (优先级 >= 70) 应该优先查找。

**注意**: 只有配置文件中启用的网站 (enabled: true) 才会被包含在分析中。

## 🔍 人工查找建议

### 查找策略

1. **按优先级查找**: 从高优先级动漫开始
2. **按网站分组**: 先查找只缺失1-2个网站的动漫
3. **使用多个关键词**: 尝试不同的搜索关键词
4. **检查英文标题**: 有些网站可能只有英文条目

### 搜索技巧

#### AniList搜索
- 使用日文原标题效果最好
- 英文标题也有很好的效果
- 可以尝试去掉特殊符号的简化标题
- 注意季度信息 (Season 2, Part 2等)

#### Bangumi搜索
- 中文标题和日文标题都要尝试
- 注意动漫可能有不同的中文译名
- 查看条目类型和播出时间
- 可以搜索制作公司名称

#### Filmarks搜索
- 日文标题效果最好
- 注意区分动漫和真人电影
- 查看上映/播出年份

#### MyAnimeList搜索
- 英文标题和日文标题都有效
- 可以使用罗马音标题
- 注意季度和类型信息

### 常见问题

**Q: 为什么有些热门动漫在某些网站找不到？**
A: 可能原因：
- 网站收录策略不同
- 地区限制
- 分类方式不同（如动漫vs电影）
- 标题翻译差异

**Q: 如何确认找到的是正确的条目？**
A: 检查以下信息：
- 上映/播出时间
- 集数
- 制作公司
- 类型（TV/Movie/OVA等）

## 📈 数据补全流程

找到缺失的动漫条目后：

1. **记录外部ID**: 记录在目标网站的ID或URL
2. **更新配置**: 如果需要，更新爬虫配置
3. **重新运行分析**: 验证数据是否正确获取
4. **检查数据质量**: 确认评分和投票数合理

## 🛠️ 高级用法

### 自定义输出格式

```bash
# 只生成CSV格式
python scripts/analyze_missing_data.py input.json --csv-only

# 只生成JSON格式  
python scripts/analyze_missing_data.py input.json --json-only

# 自定义输出文件名
python scripts/analyze_missing_data.py input.json -o custom_name
```

### 批量处理

可以编写脚本批量处理多个季度的结果：

```bash
for file in data/results/*.json; do
    python scripts/analyze_missing_data.py "$file"
done
```

## 📝 注意事项

1. **数据时效性**: 分析结果基于运行时的数据，网站内容可能会更新
2. **搜索准确性**: 自动生成的搜索URL仅供参考，可能需要手动调整
3. **优先级参考**: 优先级是建议性的，可根据实际需要调整查找顺序
4. **网站政策**: 注意各网站的使用条款和访问频率限制

## 🔗 相关文档

- [AnimeScore 用户指南](../README.md)
- [爬虫配置指南](scraper_configuration.md)
- [数据质量检查](data_quality_guide.md)
