# 📖 AnimeScore 用户手册

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)
![Version](https://img.shields.io/badge/Version-1.0-success.svg)

**动漫综合评分统计系统完整使用指南**

[快速开始](#-快速开始) • [基础使用](#-基础使用) • [高级功能](#-高级功能) • [故障排除](#-故障排除)

</div>

## 🎯 项目简介

AnimeScore 是一个动漫综合评分统计系统，它从6个主流评分网站（Bangumi、MAL、AniList、豆瓣、IMDB、Filmarks）收集数据，使用科学的数学模型计算出公平、准确的综合评分和排名。

### 🌟 核心特色
- **🔗 多平台整合**: 6大主流评分网站数据
- **🧮 科学算法**: Z-score标准化 + 加权平均
- **📅 季度分析**: 专注当季新番排名
- **🔄 智能补全**: 多层数据完整性保障
- **📊 多种输出**: JSON、CSV、HTML等格式
- **🎨 可视化**: 精美的HTML排名卡片

## 🚀 快速开始

### 📋 环境要求
- **Python**: 3.8 或更高版本
- **系统**: Windows / Linux / macOS
- **内存**: 建议 2GB 以上

### ⚡ 三步快速体验

#### 第一步：获取项目
```bash
# 克隆项目
git clone https://github.com/Drahann/AnimeScore.git
cd AnimeScore

# 安装依赖
pip install -r requirements.txt
```

#### 第二步：初始化
```bash
# 初始化项目
python scripts/setup_project.py
```

#### 第三步：运行分析
```bash
# 分析指定季度（以2024年夏季为例）
python scripts/run_seasonal_analysis.py --season "Summer 2024" --formats "simple_csv"
```

🎉 **完成！** 结果将保存在 `data/results/` 目录下。

## 📖 基础使用

### 🎯 主分析命令

#### 基本语法
```bash
python scripts/run_seasonal_analysis.py [选项]
```

#### 常用参数
| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--season` | `-s` | 指定分析季度 | `-s "Summer 2024"` |
| `--formats` | `-f` | 输出格式 | `-f "simple_csv"` |
| `--completion` | - | 启用数据补全 | `--completion` |
| `--verbose` | `-v` | 详细日志 | `-v` |

#### 季度格式说明
```bash
# 支持两种格式
--season "Summer 2024"    # 英文格式
--season "2024-3"         # 数字格式（3=夏季）

# 季度对应关系
Winter = 1    Spring = 2    Summer = 3    Fall = 4
```

### 📊 输出格式选择

#### 格式对比
| 格式 | 文件名后缀 | 内容 | 适用场景 |
|------|------------|------|----------|
| `simple_csv` | `_simple.csv` | 核心排名信息 | 快速查看 |
| `csv` | `.csv` | 完整详细数据 | Excel分析 |
| `json` | `.json` | 所有原始数据 | 程序处理 |
| `xlsx` | `.xlsx` | 格式化表格 | 商业报告 |

#### 格式选择示例
```bash
# 只要简化结果
--formats "simple_csv"

# 要完整数据
--formats "csv"

# 要多种格式
--formats "json,csv,simple_csv"

# 要所有格式
--formats "json,csv,xlsx,simple_csv"
```

### 🎬 使用示例

#### 🔰 新手推荐
```bash
# 最简单的使用方式
python scripts/run_seasonal_analysis.py --season "Summer 2024" --formats "simple_csv"
```

#### ⚡ 快速分析
```bash
# 禁用数据补全，快速获取结果
python scripts/run_seasonal_analysis.py --season "Summer 2024" --no-completion --formats "simple_csv"
```

#### 🔧 完整分析
```bash
# 启用所有功能
python scripts/run_seasonal_analysis.py --season "Summer 2024" --completion --formats "json,csv,simple_csv" --verbose
```

## 🔧 高级功能

### 🔑 API配置（推荐）

#### 配置步骤
```bash
# 1. 复制配置文件
cp config/config.example.yaml config/config.yaml

# 2. 编辑配置文件
notepad config/config.yaml    # Windows
nano config/config.yaml       # Linux/Mac
```

#### 配置示例
```yaml
api_keys:
  bangumi:
    access_token: "your_bangumi_token"
  mal:
    client_id: "your_mal_client_id"
    client_secret: "your_mal_client_secret"
```

### 📝 数据管理工具

#### 手动数据补全
```bash
# 启动交互式补全工具
python scripts/manual_data_completion.py

# 系统会引导您逐步补全缺失数据
```

#### 手动删除动漫
```bash
# 启动删除工具
python scripts/manual_anime_removal.py

# 支持单个、多个、范围删除
```

#### 数据分析工具
```bash
# 分析缺失数据
python scripts/analyze_missing_data.py

# 生成搜索清单
python scripts/generate_search_list.py
```

### 🎨 可视化生成

#### HTML排名卡片
```bash
# 生成精美的HTML排名卡片
python scripts/generate_improved_html_cards.py

# 结果保存在 data/html_cards/ 目录
```

#### 计算公式说明
```bash
# 生成公式说明图
python scripts/generate_formula_explanation.py

# 结果保存在 data/formula_explanation_*/ 目录
```

## 📋 完整操作流程

### 🎯 标准工作流程

#### 第一次使用
```bash
# 1. 项目准备
git clone https://github.com/Drahann/AnimeScore.git
cd AnimeScore
pip install -r requirements.txt
python scripts/setup_project.py

# 2. 配置API（可选但推荐）
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml 添加API密钥

# 3. 运行分析
python scripts/run_seasonal_analysis.py --season "Summer 2024" --completion --verbose

# 4. 数据管理（如需要）
python scripts/manual_data_completion.py
python scripts/manual_anime_removal.py

# 5. 生成可视化
python scripts/generate_improved_html_cards.py
python scripts/generate_formula_explanation.py
```

#### 日常使用
```bash
# 分析新季度
python scripts/run_seasonal_analysis.py --season "Fall 2024" --completion

# 生成卡片
python scripts/generate_improved_html_cards.py
```

### 🔄 批量分析多季度
```bash
# 分析多个季度（需要分别运行）
python scripts/run_seasonal_analysis.py --season "Spring 2024" --formats "simple_csv"
python scripts/run_seasonal_analysis.py --season "Summer 2024" --formats "simple_csv"
python scripts/run_seasonal_analysis.py --season "Fall 2024" --formats "simple_csv"
python scripts/run_seasonal_analysis.py --season "Winter 2025" --formats "simple_csv"
```

## 📊 结果查看

### 📁 输出文件位置
```
data/
├── results/                    # 分析结果
│   ├── anime_ranking_Summer_2024_*.json
│   ├── anime_ranking_Summer_2024_*.csv
│   └── anime_ranking_Summer_2024_*_simple.csv
├── html_cards/                 # HTML卡片
│   └── improved_top3_*/ranking_improved.html
└── formula_explanation_*/      # 公式说明
    └── formula_explanation.html
```

### 🔍 快速查看结果
```bash
# 查看生成的文件
ls data/results/

# 查看简化CSV内容（Windows）
type data\results\*_simple.csv

# 查看简化CSV内容（Linux/Mac）
cat data/results/*_simple.csv

# 在浏览器中打开HTML卡片
# 直接双击 data/html_cards/*/ranking_improved.html
```

### 📋 简化CSV格式示例
```csv
排名,动漫名称,综合评分,参与网站数,总投票数
1,葬送的芙莉莲,1.856,5,125000
2,进击的巨人 最终季,1.642,4,98000
3,鬼灭之刃 柱训练篇,1.234,5,85000
```

## 🎮 交互式操作指南

### 📝 手动数据补全流程

当运行 `python scripts/manual_data_completion.py` 时：

```
🔍 AnimeScore 手动数据补全工具
📊 加载分析结果...

发现需要补全的动漫: 葬送的芙莉莲 (排名: #1)
缺失网站: MAL, IMDB

=== MAL 数据补全 ===
请输入 MAL 评分 (1-10, 或按回车跳过): 9.1
请输入 MAL 投票数: 87543

=== IMDB 数据补全 ===
请输入 IMDB 评分 (1-10, 或按回车跳过): 8.9
请输入 IMDB 投票数: 12470

✅ 数据已保存并合并到结果中
📊 重新计算排名...
🎉 补全完成！新的结果已保存。
```

### 🗑️ 手动删除动漫流程

当运行 `python scripts/manual_anime_removal.py` 时：

```
🗑️ AnimeScore 手动删除工具
📊 当前排名列表:

1. 葬送的芙莉莲 (评分: 1.856)
2. 进击的巨人 最终季 (评分: 1.642)
3. 鬼灭之刃 柱训练篇 (评分: 1.234)
...

请选择删除方式:
1. 删除单个动漫
2. 删除多个动漫
3. 删除排名范围
4. 退出

请输入选择 (1-4): 1
请输入要删除的动漫排名: 5

确认删除 "某某动漫" (排名 #5)? (y/N): y
✅ 动漫已删除，排名已重新计算
📊 新的排名已生成并保存
```

## 🧮 计算公式说明

### 核心算法
```
综合评分 = Σ(Z_i × W_i) / Σ(W_i)
```

### 计算步骤
1. **Z-score标准化**: `Z = (S - μ) / σ`
   - 消除不同平台的评分尺度差异
   - S = 原始评分，μ = 网站平均分，σ = 网站标准差

2. **权重计算**: `W = ln(N) × P`
   - 基于投票数的对数权重乘以平台权重
   - N = 投票数，P = 平台权重系数

3. **加权平均**: 计算最终综合评分

### 平台权重分配
| 网站 | 权重系数 | 说明 |
|------|----------|------|
| MyAnimeList | 1.0 | 全球最大动漫数据库 |
| AniList | 0.8 | 现代化平台，用户活跃 |
| Bangumi | 0.7 | 专业评分，质量较高 |
| IMDB | 0.6 | 国际知名，覆盖面广 |
| 豆瓣 | 0.5 | 中文用户为主 |
| Filmarks | 0.4 | 日本本土平台 |

## ⚙️ 配置选项详解

### 📄 配置文件结构
```yaml
# config/config.yaml
api_keys:
  bangumi:
    access_token: "your_token"
  mal:
    client_id: "your_client_id"
    client_secret: "your_client_secret"
  anilist:
    # AniList 无需API密钥

data_completion:
  enabled: true
  max_retries: 3
  timeout: 30

output:
  formats: ["json", "csv", "simple_csv"]
  directory: "data/results"

logging:
  level: "INFO"
  file: "data/logs/animescore.log"
```

### 🔧 常用配置修改
```bash
# 修改输出格式
output:
  formats: ["simple_csv"]  # 只输出简化CSV

# 禁用数据补全
data_completion:
  enabled: false

# 启用调试日志
logging:
  level: "DEBUG"
```

## 🚨 故障排除

### ❓ 常见问题

#### 问题1: 安装依赖失败
```bash
# 解决方案：升级pip并重新安装
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 问题2: API请求失败
```bash
# 检查网络连接
ping bangumi.tv

# 检查API密钥配置
python -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"
```

#### 问题3: 数据补全效果不佳
```bash
# 使用手动补全工具
python scripts/manual_data_completion.py

# 分析缺失数据
python scripts/analyze_missing_data.py
```

#### 问题4: 生成的HTML卡片无法打开
```bash
# 检查文件路径
ls data/html_cards/

# 重新生成
python scripts/generate_improved_html_cards.py
```

### 🔍 调试命令
```bash
# 检查项目状态
python scripts/setup_project.py

# 查看详细日志
python scripts/run_seasonal_analysis.py --season "Summer 2024" --verbose

# 查看日志文件
cat data/logs/animescore.log    # Linux/Mac
type data\logs\animescore.log   # Windows

# 测试配置
python -c "
import yaml
try:
    config = yaml.safe_load(open('config/config.yaml'))
    print('✅ 配置文件格式正确')
    print(f'API密钥数量: {len(config.get(\"api_keys\", {}))}')
except Exception as e:
    print(f'❌ 配置文件错误: {e}')
"
```

### 📞 获取帮助
```bash
# 查看命令帮助
python scripts/run_seasonal_analysis.py --help

# 查看所有可用脚本
ls scripts/

# 查看项目文档
ls *.md
```

## 📚 进阶使用技巧

### 🎯 效率提升技巧

#### 1. 使用简写参数
```bash
# 完整命令
python scripts/run_seasonal_analysis.py --season "Summer 2024" --formats "simple_csv" --verbose

# 简写版本
python scripts/run_seasonal_analysis.py -s "Summer 2024" -f "simple_csv" -v
```

#### 2. 批处理脚本
创建 `batch_analysis.bat` (Windows) 或 `batch_analysis.sh` (Linux/Mac):
```bash
#!/bin/bash
# 批量分析多个季度
seasons=("Spring 2024" "Summer 2024" "Fall 2024" "Winter 2025")
for season in "${seasons[@]}"; do
    echo "分析 $season..."
    python scripts/run_seasonal_analysis.py -s "$season" -f "simple_csv"
done
echo "批量分析完成！"
```

#### 3. 结果对比
```bash
# 生成多个季度的简化CSV后，可以用Excel或其他工具对比
ls data/results/*_simple.csv
```

### 🔄 自动化工作流

#### 定期更新脚本
```bash
#!/bin/bash
# auto_update.sh - 自动更新当前季度排名
current_season="Fall 2024"  # 根据实际情况修改

echo "🔄 开始自动更新 $current_season 排名..."
python scripts/run_seasonal_analysis.py -s "$current_season" --completion -v
python scripts/generate_improved_html_cards.py
echo "✅ 更新完成！"
```

### 📊 数据分析建议

#### 1. 数据质量评估
```bash
# 分析数据完整性
python scripts/analyze_missing_data.py

# 查看各网站覆盖率
grep "网站覆盖率" data/logs/animescore.log
```

#### 2. 结果验证
```bash
# 对比不同配置的结果
python scripts/run_seasonal_analysis.py -s "Summer 2024" --completion -f "csv"
python scripts/run_seasonal_analysis.py -s "Summer 2024" --no-completion -f "csv"
# 比较两次结果的差异
```

## 🎉 总结

AnimeScore 为您提供了一套完整的动漫评分分析解决方案。通过本手册，您可以：

- ✅ **快速上手**: 三步即可开始使用
- ✅ **深度分析**: 利用多种工具进行数据管理
- ✅ **可视化展示**: 生成专业的HTML排名卡片
- ✅ **自定义配置**: 根据需求调整各种参数
- ✅ **故障排除**: 解决使用过程中的常见问题

### 🚀 下一步建议

1. **新用户**: 先运行快速体验命令，熟悉基本流程
2. **进阶用户**: 配置API密钥，启用数据补全功能
3. **专业用户**: 使用完整的数据管理工具链，生成专业报告

---

<div align="center">

**📖 更多文档**: [README.md](README.md) • [API配置指南](API_SETUP_GUIDE.md) • [数据补全指南](DATA_COMPLETION_GUIDE.md)

**🎯 如果这个项目对你有帮助，请给它一个星标！**

</div>
