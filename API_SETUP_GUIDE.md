# API 配置详细指南

## 什么是API？

API（应用程序编程接口）是网站提供给开发者获取数据的标准化方式。想象一下：
- 你想要获取某部动漫的评分数据
- 不用手动打开网页复制粘贴
- 而是通过API直接获取结构化的数据

## 为什么需要API密钥？

API密钥就像是你的"通行证"：
- 🔐 **身份验证**：证明你是合法用户
- 🚦 **访问控制**：防止滥用和过度请求
- 📊 **使用统计**：网站可以统计API使用情况

## 支持的网站和获取方法

### 1. Bangumi（班固米）

**特点**：
- ✅ 提供官方API
- ✅ 数据质量高
- ✅ 包含标准差等统计数据

**获取步骤**：

1. **注册账号**
   - 访问：https://bgm.tv/
   - 注册一个账号并登录

2. **创建应用**
   - 访问：https://bgm.tv/dev/app
   - 点击"创建新应用"
   - 填写应用信息：
     ```
     应用名称: AnimeScore分析工具
     应用描述: 用于动漫评分数据分析
     回调地址: http://localhost:8080/callback
     ```

3. **获取Access Token**
   - 创建应用后会得到 `App ID` 和 `App Secret`
   - 按照OAuth流程获取Access Token
   - 或者使用个人Access Token（推荐新手）

4. **配置到项目**
   ```yaml
   api_keys:
     bangumi:
       access_token: "your_access_token_here"
   ```

### 2. MyAnimeList (MAL)

**特点**：
- ✅ 全球最大的动漫数据库
- ✅ 官方API支持
- ⚠️ 需要OAuth认证

**获取步骤**：

1. **注册MAL账号**
   - 访问：https://myanimelist.net/
   - 注册并登录

2. **创建API应用**
   - 访问：https://myanimelist.net/apiconfig
   - 点击"Create ID"
   - 填写信息：
     ```
     App Name: AnimeScore
     App Type: web
     Description: Anime rating analysis tool
     Homepage URL: http://localhost
     Redirect URL: http://localhost:8080/callback
     ```

3. **获取密钥**
   - 创建后会得到：
     - Client ID
     - Client Secret

4. **配置到项目**
   ```yaml
   api_keys:
     mal:
       client_id: "your_client_id_here"
       client_secret: "your_client_secret_here"
   ```

### 3. AniList

**特点**：
- ✅ 现代化的GraphQL API
- ✅ 无需密钥即可使用基础功能
- ✅ 数据更新及时

**配置**：
```yaml
api_keys:
  anilist:
    # 基础使用无需密钥，高级功能可选
    client_id: "optional_for_rate_limiting"
```

### 4. 其他网站（爬虫方式）

**豆瓣、IMDB、Filmarks**：
- ❌ 没有公开API
- 🕷️ 使用网页爬虫获取数据
- ⚠️ 需要注意请求频率，避免被封IP

## 配置文件示例

创建 `config/config.yaml` 文件：

```yaml
# API密钥配置
api_keys:
  # Bangumi API
  bangumi:
    access_token: "your_bangumi_token_here"
  
  # MyAnimeList API  
  mal:
    client_id: "your_mal_client_id"
    client_secret: "your_mal_client_secret"
  
  # AniList API（可选）
  anilist:
    client_id: "optional"

# 网站配置
websites:
  bangumi:
    enabled: true
    rate_limit: 1.0    # 每秒最多1个请求
    timeout: 30
  
  mal:
    enabled: true
    rate_limit: 1.0
    timeout: 30
  
  douban:
    enabled: true
    rate_limit: 2.0    # 爬虫需要更保守的频率
    timeout: 30
  
  anilist:
    enabled: true
    rate_limit: 1.0
    timeout: 30
  
  imdb:
    enabled: false     # 可以先禁用，后续开启
    rate_limit: 3.0
    timeout: 30
  
  filmarks:
    enabled: false
    rate_limit: 2.0
    timeout: 30
```

## 简化版配置（推荐新手）

如果你觉得配置所有API太复杂，可以先从最简单的开始：

```yaml
# 最简配置 - 只使用Bangumi
api_keys:
  bangumi:
    access_token: "your_bangumi_token"

websites:
  bangumi:
    enabled: true
    rate_limit: 1.0
    timeout: 30
  
  # 其他网站先禁用
  mal:
    enabled: false
  douban:
    enabled: false
  anilist:
    enabled: false
  imdb:
    enabled: false
  filmarks:
    enabled: false
```

## 测试API配置

配置完成后，运行测试：

```bash
# 检查配置
python scripts/setup_project.py --check-only

# 运行演示（使用模拟数据）
python scripts/demo.py

# 测试真实API（需要配置密钥）
python scripts/run_seasonal_analysis.py --verbose
```

## 常见问题

### Q: 我不想配置API，能直接使用吗？
A: 可以！运行演示程序使用模拟数据：
```bash
python scripts/demo.py
```

### Q: 只配置一个网站的API可以吗？
A: 完全可以！系统会自动使用可用的数据源。

### Q: API请求失败怎么办？
A: 检查以下几点：
- API密钥是否正确
- 网络连接是否正常
- 是否超过了请求频率限制
- 查看日志文件：`data/logs/animescore.log`

### Q: 如何获得更准确的结果？
A: 配置更多的数据源：
- 至少2-3个网站的数据
- Bangumi + MAL 是比较好的组合
- 可以逐步添加其他网站

## 无API密钥的使用方式

如果你暂时不想配置API，也可以：

1. **使用演示模式**：
   ```bash
   python scripts/demo.py
   ```

2. **手动数据输入**：
   - 修改演示脚本中的数据
   - 添加你感兴趣的动漫评分

3. **后续扩展**：
   - 先熟悉系统功能
   - 再逐步配置真实的API

## 下一步

1. **选择一个网站开始**：推荐从Bangumi开始
2. **获取API密钥**：按照上面的步骤
3. **配置并测试**：确保能正常获取数据
4. **逐步添加更多数据源**：提高分析准确性

需要我帮你配置具体某个网站的API吗？或者有其他关于API使用的问题？
