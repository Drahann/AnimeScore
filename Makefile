# AnimeScore Makefile

.PHONY: help install setup demo test clean run

# 默认目标
help:
	@echo "AnimeScore - 动漫评分统计系统"
	@echo ""
	@echo "可用命令:"
	@echo "  install    - 安装依赖包"
	@echo "  setup      - 初始化项目设置"
	@echo "  demo       - 运行演示程序"
	@echo "  test       - 运行测试"
	@echo "  run        - 运行季度分析"
	@echo "  clean      - 清理临时文件"
	@echo ""

# 安装依赖
install:
	pip install -r requirements.txt

# 项目初始化
setup:
	python scripts/setup_project.py

# 运行演示
demo:
	python scripts/demo.py

# 运行测试
test:
	python -m pytest tests/ -v

# 运行季度分析
run:
	python scripts/run_seasonal_analysis.py

# 运行当前季度分析
run-current:
	python scripts/run_seasonal_analysis.py --verbose

# 运行指定季度分析
run-season:
	@echo "请指定季度，例如: make run-season SEASON=2024-1"
	@if [ -z "$(SEASON)" ]; then \
		echo "错误: 请提供 SEASON 参数"; \
		echo "示例: make run-season SEASON=2024-1"; \
		exit 1; \
	fi
	python scripts/run_seasonal_analysis.py --season $(SEASON) --verbose

# 清理临时文件
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# 开发环境设置
dev-install: install
	pip install -e .
	pip install pytest pytest-asyncio black flake8 mypy

# 代码格式化
format:
	black src/ tests/ scripts/

# 代码检查
lint:
	flake8 src/ tests/ scripts/
	mypy src/

# 完整检查
check: format lint test

# 构建包
build:
	python setup.py sdist bdist_wheel

# 安装本地包
install-local:
	pip install -e .

# 查看项目状态
status:
	@echo "=== 项目状态 ==="
	@echo "Python 版本: $(shell python --version)"
	@echo "项目目录: $(shell pwd)"
	@echo ""
	@echo "=== 目录结构 ==="
	@ls -la
	@echo ""
	@echo "=== 配置文件 ==="
	@if [ -f "config/config.yaml" ]; then \
		echo "✓ config/config.yaml 存在"; \
	else \
		echo "✗ config/config.yaml 不存在"; \
	fi
	@echo ""
	@echo "=== 数据目录 ==="
	@ls -la data/ 2>/dev/null || echo "data/ 目录不存在"

# 快速开始
quickstart: install setup demo
	@echo ""
	@echo "🎉 快速开始完成！"
	@echo ""
	@echo "接下来的步骤:"
	@echo "1. 编辑 config/config.yaml 添加 API 密钥"
	@echo "2. 运行: make run"
