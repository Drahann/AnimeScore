# AnimeScore 数据补全系统指南

<div align="center">

🔄 **智能四层数据补全体系**

确保最高的数据完整性和分析准确性

[系统概述](#-系统概述) • [使用指南](#-使用指南) • [配置选项](#-配置选项) • [最佳实践](#-最佳实践)

</div>

## 🎯 系统概述

AnimeScore 采用创新的四层数据补全体系，将数据完整性从初始的 ~65% 提升到最终的 ~95%，确保重要动漫都有完整、准确的评分数据。

### 📊 数据完整性提升效果

| 阶段 | 完整性 | 说明 |
|------|--------|------|
| **第一层后** | ~65% | 基础自动收集 |
| **第二层后** | ~85% | 智能搜索补全 |
| **第三层后** | ~95% | 手动精确补全 |
| **第四层后** | 100% | 最终排名调整 |

## 🔄 四层补全体系

### 1️⃣ 第一层：自动数据收集

**功能**：并发从多个网站获取动漫数据
**特点**：
- 基于动漫ID和标题的精确匹配
- 异步并发请求，效率高
- 自动缓存，避免重复请求
- 智能去重和数据验证

**局限性**：
- 部分动漫在某些网站搜索失败
- 长标题、特殊字符、续作动漫容易失败
- 中国/韩国动漫在日本网站数据较少

### 2️⃣ 第二层：智能二次搜索补全

**功能**：自动识别缺失数据并进行智能重搜索
**核心算法**：

#### 缺失数据识别
```python
# 识别每个动漫缺失的网站数据
missing_websites = enabled_websites - existing_websites

# 只为有一定数据基础的动漫进行补全
if len(existing_websites) >= min_existing_websites:
    mark_for_completion(anime)
```

#### 多搜索策略
```python
search_terms = [
    original_title,                    # 原始标题
    english_title,                     # 英文标题  
    simplify_title(original_title),    # 简化标题（去除季数）
    remove_brackets(original_title),   # 去除括号内容
    remove_season_info(original_title) # 去除季数信息
]
```

#### 智能重试机制
```python
for term in search_terms:
    try:
        results = await scraper.search_anime(session, term)
        if results:
            rating_data = await scraper.get_anime_rating(session, results[0])
            if rating_data:
                return rating_data  # 成功找到数据
    except Exception:
        continue  # 尝试下一个搜索词
```

**成功案例**：
- `Jidou Hanbaiki ni Umarekawatta Ore wa Meikyuu wo Samayou 2nd Season`
  - ❌ 原标题搜索失败
  - ✅ 英文标题 `"Reborn as a Vending Machine, I Now Wander the Dungeon Season 2"` 成功
- `Arknights: Enshin Shomei`
  - ❌ 原标题在Bangumi搜索失败
  - ✅ 英文标题 `"Arknights: Perish in Frost"` 成功

### 3️⃣ 第三层：手动精确补全

**功能**：交互式手动补全重要动漫的缺失数据
**适用场景**：
- 自动搜索失败的重要动漫（排名靠前）
- 需要特定网站数据的动漫
- 数据质量要求极高的分析

#### 使用方法
```bash
# 快速手动补全（推荐）
python scripts/quick_manual_completion.py

# 完整手动补全流程
python scripts/manual_data_completion.py -i data/results/latest_result.json
```

#### 操作流程
1. **自动识别**：程序识别数据不完整的动漫
2. **优先级排序**：按动漫排名排序，重要的优先
3. **详细展示**：显示动漫信息和现有评分数据
4. **交互式输入**：用户选择是否补全，输入缺失数据
5. **数据验证**：验证输入格式和范围
6. **即时合并**：立即合并到分析结果并保存

#### 界面示例
```
📺 动漫: Kimetsu no Yaiba Movie: Mugen Jou-hen
🌍 英文名: Demon Slayer: Kimetsu no Yaiba Infinity Castle
🏆 当前排名: #1
⭐ 综合评分: 1.846
📊 现有评分数据:
   anilist: 8.5 (1500 票)
   mal: 8.2 (5000 票)

❌ 缺失网站: bangumi
❓ 是否要为这个动漫补全数据? (y/n/q): y

🔍 请为 bangumi 网站输入评分数据:
   评分 (0.0-10.0): 7.7
   投票数 (默认100): 364
   ✅ 已添加 bangumi 数据: 7.7
```

### 4️⃣ 第四层：手动删除和排名调整

**功能**：删除重复、错误或不相关的动漫，重新计算排名
**适用场景**：
- 删除重复的动漫条目
- 移除错误或测试数据
- 过滤特定类型（如只保留TV动画）
- 清理不相关的内容

#### 使用方法
```bash
python scripts/manual_anime_removal.py
```

#### 删除格式
```bash
单个删除: 5
多个删除: 3,7,12  
范围删除: 1-5,10,15-20
组合删除: 1,3-5,8,10-12
```

#### 操作流程
1. **查看排名**：浏览当前动漫排名列表
2. **选择删除**：指定要删除的动漫排名
3. **确认操作**：显示删除列表并要求确认
4. **自动重排**：删除后自动重新计算排名和百分位
5. **保存结果**：生成新的分析结果文件

## 📋 使用指南

### 🚀 快速开始

#### 1. 启用数据补全的完整分析
```bash
# 运行完整分析（包含智能数据补全）
python scripts/run_seasonal_analysis.py --completion --verbose

# 分析完成后，查看数据完整性
python -c "
import json
with open('data/results/anime_ranking_Summer_2025_latest.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
website_counts = {}
for anime in data['rankings']:
    count = anime['website_count']
    website_counts[count] = website_counts.get(count, 0) + 1
print('数据完整性统计:')
for count in sorted(website_counts.keys()):
    percentage = website_counts[count] / len(data['rankings']) * 100
    print(f'  {count}个网站: {website_counts[count]}部动漫 ({percentage:.1f}%)')
"
```

#### 2. 手动补全重要动漫
```bash
# 启动手动补全程序
python scripts/quick_manual_completion.py

# 按提示操作：
# - 查看数据不完整的动漫列表
# - 选择要补全的动漫
# - 输入缺失的评分数据
# - 程序自动保存更新后的结果
```

#### 3. 清理和调整排名
```bash
# 启动删除程序
python scripts/manual_anime_removal.py

# 常见操作：
# - 删除重复条目（如两个相同的动漫）
# - 移除错误数据
# - 过滤不需要的类型
```

### 🔧 配置选项

#### 数据补全配置
```yaml
# config/config.yaml
data_completion:
  # 启用智能数据补全
  enabled: true
  
  # 搜索参数
  max_retry_per_anime: 3        # 每个动漫每个网站的最大重试次数
  search_timeout: 30            # 搜索超时时间（秒）
  use_alternative_names: true   # 使用备选名称搜索
  parallel_searches: 5          # 并行搜索数量
  
  # 补全条件
  min_existing_websites: 1      # 尝试补全的最小现有网站数
  
  # 优先级网站
  priority_websites: 
    - "bangumi"
    - "mal"
    - "anilist"
```

#### 命令行选项
```bash
# 启用数据补全
python scripts/run_seasonal_analysis.py --completion

# 禁用数据补全
python scripts/run_seasonal_analysis.py --no-completion

# 使用自定义配置
python scripts/run_seasonal_analysis.py --config custom_config.yaml --completion
```

## 💡 最佳实践

### 🎯 推荐工作流程

1. **第一次分析**：
   ```bash
   python scripts/run_seasonal_analysis.py --completion --verbose
   ```

2. **检查数据完整性**：
   - 查看控制台输出的补全统计
   - 重点关注排名前20的动漫是否有完整数据

3. **手动补全重要动漫**：
   ```bash
   python scripts/quick_manual_completion.py
   ```
   - 优先补全排名前10的动漫
   - 重点关注缺失2个网站数据的动漫

4. **清理和调整**：
   ```bash
   python scripts/manual_anime_removal.py
   ```
   - 删除明显的重复条目
   - 移除不相关的内容

5. **最终验证**：
   - 检查最终的数据完整性统计
   - 确认重要动漫都有完整数据

### ⚡ 效率提升技巧

1. **批量操作**：手动补全时可以连续处理多个动漫
2. **优先级策略**：先处理排名靠前的重要动漫
3. **数据验证**：输入数据时注意评分范围和投票数的合理性
4. **备份策略**：每次操作都会生成新文件，保留历史版本

### 🚨 注意事项

1. **数据质量**：手动输入的数据要确保准确性
2. **网络稳定**：智能搜索需要稳定的网络连接
3. **API限制**：注意各网站的API调用频率限制
4. **存储空间**：每次操作都会生成新文件，注意磁盘空间

## 📊 效果评估

### 数据完整性指标
- **3网站完整率**：有3个网站数据的动漫比例
- **平均网站数**：每个动漫的平均网站数量
- **重要动漫完整率**：排名前20动漫的数据完整性

### 质量提升效果
- **评分准确性**：更多数据源提高评分可靠性
- **排名稳定性**：完整数据减少排名波动
- **置信度提升**：更高的数据完整性提升置信度

---

<div align="center">

**🎉 通过四层数据补全体系，AnimeScore 确保了最高质量的动漫评分分析！**

</div>
