# AnimeScore - 动漫评分统计系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)
![Version](https://img.shields.io/badge/Version-1.0-success.svg)

一个综合多个动漫评分网站数据的统计分析系统，通过科学的数学模型计算公平、准确的综合评分。

[快速开始](#-快速开始) • [使用指南](#-使用指南) • [计算公式](#-计算公式) • [输出格式](#-输出格式)

</div>

## 🎯 项目特色

### 🌟 核心功能
- **🔗 多平台整合**: 支持 Bangumi、MAL、豆瓣、AniList、IMDB、Filmarks 等6大主流评分网站
- **🧮 科学算法**: 使用 Z-score 标准化、对数权重、加权平均等成熟数学模型
- **📅 季度分析**: 专注于当季新番的评分分析和排名，自动识别季度动漫
- **🔄 智能数据补全**: 多层数据补全体系，确保数据完整性和准确性
- **⚡ 异步高效**: 基于 aiohttp 的异步并发数据获取，性能优秀
- **📊 多种输出**: 支持 JSON、CSV、简化CSV、HTML卡片等多种格式
- **🎨 可视化展示**: 生成精美的HTML排名卡片，支持截图保存

### 🏗️ 技术亮点
- **模块化设计**: 清晰的架构，易于维护和扩展
- **智能数据补全**: 自动搜索 + 手动补全的数据完整性保障
- **交互式管理**: 支持手动数据补全和动漫删除的用户友好界面
- **配置驱动**: 灵活的配置系统，支持多种参数调整
- **详细日志**: 完善的日志记录和错误处理
- **跨平台**: 支持 Windows、Linux、macOS

## 🚀 快速开始

### 📋 环境要求
- **Python**: 3.8 或更高版本
- **系统**: Windows / Linux / macOS
- **内存**: 建议 2GB 以上

### ⚡ 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/Drahann/AnimeScore.git
cd AnimeScore

```

#### 2. 安装依赖
```bash
pip install -r requirements.txt
```

#### 3. 初始化项目
```bash
python scripts/setup_project.py
```

#### 4. 配置API密钥（可选但推荐）
```bash
# 编辑配置文件，将占位符替换为真实API密钥
notepad config/config.yaml    # Windows
nano config/config.yaml       # Linux/Mac

# 需要替换的占位符：
# your_bangumi_access_token_here -> 您的Bangumi访问令牌
# your_mal_client_id_here -> 您的MAL客户端ID
# your_mal_client_secret_here -> 您的MAL客户端密钥
```

> **⚠️ 安全提示**: 请勿将包含真实API密钥的配置文件上传到公共仓库！

## 📖 使用指南

### 🎯 基本使用
```bash
# 分析指定季度动漫
python scripts/run_seasonal_analysis.py --season "Summer 2024"

# 启用数据补全（推荐）
python scripts/run_seasonal_analysis.py --season "Summer 2024" --completion

# 只输出简化CSV格式
python scripts/run_seasonal_analysis.py --season "Summer 2024" --formats "simple_csv"
```

### 🎨 生成可视化卡片
```bash
# 生成HTML排名卡片
python scripts/generate_improved_html_cards.py

# 生成计算公式说明图
python scripts/generate_formula_explanation.py
```

### 🔧 数据管理
```bash
# 手动数据补全
python scripts/manual_data_completion.py

# 手动删除动漫
python scripts/manual_anime_removal.py

# 分析缺失数据
python scripts/analyze_missing_data.py
```

## 🧮 计算公式

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

### 算法特点
- ✅ 使用Z-score标准化消除平台评分差异
- ✅ 采用对数权重避免大样本过度影响
- ✅ 考虑平台权重反映不同网站的可靠性
- ✅ 最低需要2个网站的评分数据才能计算

## 📊 输出格式

### 📄 简化CSV格式 (推荐)
```csv
排名,动漫名称,综合评分,参与网站数,总投票数
1,进击的巨人 最终季,1.234,5,125000
2,鬼灭之刃,1.156,4,98000
```

### 📋 完整CSV格式
包含所有详细信息：动漫信息、各网站评分、权重、排名等

### 📦 JSON格式
完整的结构化数据，包含所有计算细节和元数据

### 🎨 HTML卡片格式
精美的可视化排名卡片，支持：
- 动漫海报和横幅图片
- 各网站评分和图标
- 投票数和排名信息
- 现代化设计，适合截图分享
## 📁 项目结构

```
AnimeScore/
├── 📁 src/                     # 核心源代码
│   ├── 🔧 scrapers/           # 各网站数据抓取器
│   ├── 📊 analyzer.py         # 综合评分计算引擎
│   ├── 🔄 data_completion.py  # 数据补全系统
│   └── 📋 utils.py           # 工具函数
├── 📁 scripts/                # 可执行脚本
│   ├── 🚀 run_seasonal_analysis.py      # 主分析脚本
│   ├── 🎨 generate_improved_html_cards.py # HTML卡片生成器
│   ├── 📊 generate_formula_explanation.py # 公式说明生成器
│   ├── 🔧 manual_data_completion.py     # 手动数据补全
│   └── 🗑️ manual_anime_removal.py       # 手动删除动漫
├── 📁 config/                 # 配置文件
│   ├── ⚙️ config.yaml        # 主配置文件
│   └── 📋 config.example.yaml # 配置模板
├── 📁 data/                   # 数据目录
│   ├── 📊 results/           # 分析结果
│   ├── 🎨 html_cards/        # HTML卡片输出
│   └── 📋 searchlist/        # 搜索清单
├── 📁 WebsiteLogo/           # 网站图标资源
└── 📄 README.md              # 项目文档
```

## 🔧 核心脚本说明

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `run_seasonal_analysis.py` | 主分析脚本 | 分析指定季度动漫排名 |
| `generate_improved_html_cards.py` | HTML卡片生成 | 生成可视化排名卡片 |
| `generate_formula_explanation.py` | 公式说明生成 | 生成计算公式说明图 |
| `manual_data_completion.py` | 手动数据补全 | 补全缺失的动漫数据 |
| `manual_anime_removal.py` | 手动删除动漫 | 从排名中删除指定动漫 |
| `analyze_missing_data.py` | 缺失数据分析 | 分析数据完整性 |
## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 🐛 报告问题
- 使用 [Issues](https://github.com/Drahann/AnimeScore/issues) 报告 bug
- 提供详细的错误信息和复现步骤

### 💡 功能建议
- 在 Issues 中提出新功能建议
- 描述功能的用途和预期效果

### 🔧 代码贡献
1. Fork 项目
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

### 📡 API 文档
- [Bangumi API](https://bangumi.github.io/api/) - 班固米官方API文档
- [MyAnimeList API](https://myanimelist.net/apiconfig/references/api/v2) - MAL API v2文档
- [AniList API](https://anilist.gitbook.io/anilist-apiv2-docs/) - AniList GraphQL文档

### 🌐 相关网站
- [Bangumi](https://bgm.tv/) - 专业的动漫评分网站
- [MyAnimeList](https://myanimelist.net/) - 全球最大的动漫数据库
- [AniList](https://anilist.co/) - 现代化的动漫追踪平台

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**


</div>
