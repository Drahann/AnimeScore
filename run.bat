@echo off
REM AnimeScore Windows 批处理脚本

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="setup" goto setup
if "%1"=="demo" goto demo
if "%1"=="test" goto test
if "%1"=="run" goto run
if "%1"=="clean" goto clean
goto help

:help
echo AnimeScore - 动漫评分统计系统
echo.
echo 可用命令:
echo   run.bat install    - 安装依赖包
echo   run.bat setup      - 初始化项目设置
echo   run.bat demo       - 运行演示程序
echo   run.bat test       - 运行测试
echo   run.bat run        - 运行季度分析
echo   run.bat clean      - 清理临时文件
echo.
goto end

:install
echo 安装依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    goto end
)
echo 依赖安装完成！
goto end

:setup
echo 初始化项目设置...
python scripts/setup_project.py
if %errorlevel% neq 0 (
    echo 错误: 项目设置失败
    goto end
)
echo 项目设置完成！
goto end

:demo
echo 运行演示程序...
python scripts/demo.py
if %errorlevel% neq 0 (
    echo 错误: 演示程序运行失败
    goto end
)
goto end

:test
echo 运行测试...
python -m pytest tests/ -v
if %errorlevel% neq 0 (
    echo 错误: 测试失败
    goto end
)
goto end

:run
echo 运行季度分析...
python scripts/run_seasonal_analysis.py --verbose
if %errorlevel% neq 0 (
    echo 错误: 分析运行失败
    goto end
)
goto end

:clean
echo 清理临时文件...
for /r %%i in (*.pyc) do del "%%i" 2>nul
for /d /r %%i in (__pycache__) do rmdir /s /q "%%i" 2>nul
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
echo 清理完成！
goto end

:end
