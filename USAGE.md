# AnimeScore 使用指南

<div align="center">

📖 **详细的使用说明和配置指南**

[快速开始](#快速开始) • [配置选项](#配置选项) • [高级用法](#高级用法) • [故障排除](#故障排除)

</div>

## 🚀 快速开始

### 📋 环境要求

| 项目 | 要求 | 推荐 |
|------|------|------|
| **Python** | 3.8+ | 3.9+ |
| **内存** | 1GB+ | 2GB+ |
| **存储** | 100MB+ | 500MB+ |
| **网络** | 稳定连接 | 高速连接 |

### ⚡ 安装方法

#### 🐧 方法一：Linux/macOS (推荐)
```bash
# 克隆项目
git clone https://github.com/your-username/AnimeScore.git
cd AnimeScore

# 一键安装
make install && make setup && make demo
```

#### 🪟 方法二：Windows
```cmd
# 克隆项目
git clone https://github.com/your-username/AnimeScore.git
cd AnimeScore

# 使用批处理脚本
run.bat install
run.bat setup
run.bat demo
```

#### 🔧 方法三：手动安装
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化项目
python scripts/setup_project.py

# 3. 运行演示
python scripts/demo.py
```

### 🎯 验证安装

运行以下命令验证安装是否成功：

```bash
# 检查Python版本
python --version

# 检查依赖包
pip list | grep -E "(pandas|aiohttp|pydantic|loguru)"

# 运行测试
python -m pytest tests/test_scoring.py -v
```

## 🔑 API 密钥配置

### 📝 配置步骤

1. **复制配置模板**:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. **编辑配置文件**:
   ```yaml
   api_keys:
     bangumi:
       access_token: "your_bangumi_access_token_here"
     mal:
       client_id: "your_mal_client_id_here"
       client_secret: "your_mal_client_secret_here"
     anilist:
       client_id: "optional_for_rate_limiting"
   ```

### 🔗 获取 API 密钥

#### 🎯 Bangumi API (推荐优先配置)
- **难度**: ⭐⭐☆☆☆ (简单)
- **数据质量**: ⭐⭐⭐⭐⭐ (优秀)
- **获取方法**:
  1. 访问 [Bangumi 开发者页面](https://bgm.tv/dev/app)
  2. 注册账号并创建应用
  3. 获取 Access Token

#### 🌍 MyAnimeList API (可选)
- **难度**: ⭐⭐⭐☆☆ (中等)
- **数据质量**: ⭐⭐⭐⭐⭐ (优秀)
- **获取方法**:
  1. 访问 [MAL API 页面](https://myanimelist.net/apiconfig)
  2. 创建应用获取 Client ID 和 Client Secret

#### 🚀 AniList API (无需密钥)
- **难度**: ⭐☆☆☆☆ (无需配置)
- **数据质量**: ⭐⭐⭐⭐☆ (良好)
- **说明**: 使用公开的 GraphQL API，无需密钥

#### 🕷️ 其他网站 (无需密钥)
- **豆瓣、IMDB、Filmarks**: 使用网页爬虫，无需密钥
- **注意**: 爬虫方式可能受到反爬虫限制

### 🎯 最小配置建议

**新手推荐**：只配置 Bangumi
```yaml
api_keys:
  bangumi:
    access_token: "your_bangumi_token"

websites:
  bangumi:
    enabled: true
  # 其他网站先禁用
  mal:
    enabled: false
  anilist:
    enabled: false
  douban:
    enabled: false
  imdb:
    enabled: false
  filmarks:
    enabled: false
```

**进阶配置**：Bangumi + MAL + AniList
```yaml
api_keys:
  bangumi:
    access_token: "your_bangumi_token"
  mal:
    client_id: "your_mal_client_id"
    client_secret: "your_mal_client_secret"

websites:
  bangumi:
    enabled: true
  mal:
    enabled: true
  anilist:
    enabled: true  # 无需密钥
  douban:
    enabled: true  # 可选
  imdb:
    enabled: false
  filmarks:
    enabled: false
```

## 📊 使用方法

### 🎬 基础使用

#### 🎯 演示模式 (无需API密钥)
```bash
# 运行演示程序
python scripts/demo.py

# 查看演示结果
ls data/results/demo_ranking_*.json
```

#### 📅 分析当前季度
```bash
# 使用默认配置（启用数据补全）
python scripts/run_seasonal_analysis.py --completion

# 详细输出模式
python scripts/run_seasonal_analysis.py --verbose --completion

# 禁用数据补全（仅第一轮收集）
python scripts/run_seasonal_analysis.py --no-completion
```

#### 🗓️ 分析指定季度
```bash
# 使用季度编号格式 (YYYY-Q)
python scripts/run_seasonal_analysis.py --season "2024-1"  # 2024年春季
python scripts/run_seasonal_analysis.py --season "2024-2"  # 2024年夏季
python scripts/run_seasonal_analysis.py --season "2024-3"  # 2024年秋季
python scripts/run_seasonal_analysis.py --season "2024-4"  # 2024年冬季

# 使用季度名称格式
python scripts/run_seasonal_analysis.py --season "Winter 2024"
python scripts/run_seasonal_analysis.py --season "Spring 2024"
```

### 🔧 高级选项

#### 📁 自定义输出
```bash
# 指定输出目录
python scripts/run_seasonal_analysis.py --output "my_results"

# 指定输出格式
python scripts/run_seasonal_analysis.py --formats "json,csv,xlsx"

# 只输出JSON格式
python scripts/run_seasonal_analysis.py --formats "json"
```

#### ⚙️ 自定义配置
```bash
# 使用自定义配置文件
python scripts/run_seasonal_analysis.py --config "my_config.yaml"

# 组合使用多个选项
python scripts/run_seasonal_analysis.py \
  --season "2024-2" \
  --verbose \
  --output "summer_2024" \
  --formats "json,xlsx"
```

### 🔧 数据管理工具

AnimeScore 提供了强大的数据管理工具，帮助您完善和管理分析结果：

#### 🔄 手动数据补全
```bash
# 快速手动补全（推荐）
python scripts/quick_manual_completion.py

# 完整手动补全流程
python scripts/manual_data_completion.py -i data/results/latest_result.json
```

**使用场景**：
- 自动搜索失败的重要动漫
- 需要添加特定网站的评分数据
- 提高数据完整性到95%以上

**操作流程**：
1. 程序自动识别数据不完整的动漫
2. 按重要性（排名）排序显示
3. 用户选择要补全的动漫
4. 交互式输入缺失的评分数据
5. 自动合并数据并重新保存

#### 🗑️ 手动删除动漫
```bash
# 启动删除程序
python scripts/manual_anime_removal.py
```

**使用场景**：
- 删除重复的动漫条目
- 移除错误或不相关的数据
- 过滤特定类型的动漫（如只保留TV动画）
- 清理测试数据

**操作流程**：
1. 查看当前排名列表
2. 选择要删除的动漫（支持单个、多个、范围删除）
3. 确认删除操作
4. 自动重新计算排名和百分位
5. 保存更新后的结果

**删除格式示例**：
```
单个删除: 5
多个删除: 3,7,12
范围删除: 1-5,10,15-20
组合删除: 1,3-5,8,10-12
```

#### 📊 数据完整性检查
```bash
# 检查数据完整性
python -c "
import json
with open('data/results/latest_result.json', 'r', encoding='utf-8') as f:
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

### 🎮 Makefile 快捷命令

#### 🐧 Linux/macOS 用户
```bash
# 运行演示
make demo

# 运行当前季度分析
make run

# 运行详细分析
make run-current

# 运行指定季度分析
make run-season SEASON=2024-2

# 运行测试
make test

# 代码检查
make check
```

### 输出结果

分析完成后，结果会保存在 `data/results/` 目录中，包含：

- **JSON 格式**: 完整的分析数据，包含所有详细信息
- **CSV 格式**: 适合在 Excel 中查看的表格数据
- **XLSX 格式**: Excel 文件，包含格式化的表格

### 结果解读

#### 综合评分 (Composite Score)
- 使用 Z-score 标准化消除平台差异
- 应用贝叶斯平均减少小样本偏差
- 基于投票数的对数权重进行加权平均

#### 置信度 (Confidence)
- 0-1 之间的值，表示评分的可信度
- 基于参与网站数量和总投票数计算
- 值越高表示评分越可靠

#### 排名和百分位数
- 排名：在所有分析动漫中的位置
- 百分位数：超过多少百分比的其他动漫

## 配置选项

### 数学模型参数

```yaml
model:
  # 贝叶斯平均参数
  bayesian:
    min_credible_votes: 5000  # 最小可信投票数
  
  # 权重参数
  weights:
    min_votes_threshold: 50   # 最小投票数阈值
    use_natural_log: true     # 使用自然对数
  
  # 平台权重
  platform_weights:
    bangumi: 1.0
    mal: 1.0
    douban: 1.0
    anilist: 1.0
    imdb: 0.8      # IMDB 对动漫可能不太相关
    filmarks: 0.9
```

### 季度检测参数

```yaml
seasonal:
  season_buffer_days: 30    # 季度缓冲天数
  min_episodes: 1           # 最小集数要求
```

### 数据补全配置

```yaml
data_completion:
  # 启用数据补全功能
  enabled: true

  # 搜索重试参数
  max_retry_per_anime: 3        # 每个动漫每个网站的最大重试次数
  search_timeout: 30            # 搜索超时时间（秒）

  # 搜索策略
  use_alternative_names: true   # 使用备选名称搜索
  parallel_searches: 5          # 并行搜索数量

  # 补全条件
  min_existing_websites: 1      # 尝试补全的最小现有网站数

  # 优先级网站（优先补全这些网站的数据）
  priority_websites:
    - "bangumi"
    - "mal"
    - "anilist"
```

**配置说明**：
- `enabled`: 是否启用智能数据补全
- `max_retry_per_anime`: 防止无限重试，控制搜索次数
- `use_alternative_names`: 启用多搜索词策略（原标题、英文标题、简化标题等）
- `min_existing_websites`: 只为已有一定数据的动漫进行补全，避免浪费资源
- `priority_websites`: 优先补全重要网站的数据

### 网站配置

```yaml
websites:
  bangumi:
    enabled: true
    rate_limit: 1.0         # 请求间隔（秒）
    timeout: 30             # 请求超时（秒）
```

## 开发和测试

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_scoring.py -v
```

### 代码检查
```bash
# 格式化代码
black src/ tests/ scripts/

# 代码检查
flake8 src/ tests/ scripts/
```

## 故障排除

### 常见问题

**1. 导入错误**
```
ModuleNotFoundError: No module named 'src'
```
解决方法：确保在项目根目录运行脚本

**2. API 限制**
```
HTTP 429: Too Many Requests
```
解决方法：增加 `rate_limit` 配置值

**3. 配置文件错误**
```
FileNotFoundError: config/config.yaml not found
```
解决方法：运行 `python scripts/setup_project.py`

**4. 依赖包缺失**
```
ImportError: No module named 'pandas'
```
解决方法：运行 `pip install -r requirements.txt`

### 调试模式

启用详细日志：
```bash
python scripts/run_seasonal_analysis.py --verbose
```

检查日志文件：
```
data/logs/animescore.log
```

## 扩展功能

### 添加新的评分网站

1. 在 `src/scrapers/` 目录创建新的爬虫文件
2. 继承 `BaseWebsiteScraper` 或其子类
3. 实现必要的方法
4. 在 `__init__.py` 中注册爬虫

### 自定义评分算法

1. 修改 `src/core/scoring.py` 中的 `ScoringEngine` 类
2. 调整数学模型参数
3. 添加新的评分指标

### 数据导出格式

在 `scripts/run_seasonal_analysis.py` 中的 `save_results` 函数添加新的导出格式。

## 许可证

MIT License - 详见 LICENSE 文件
