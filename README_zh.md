# 舰队Collection副官 🚢

一个智能的艦隊これくしょん（舰队Collection）自动化系统，利用AI生成和执行浏览器自动化脚本来完成日常、周常和季节性任务。

## 🎯 功能特性

### 1. AI驱动的代码生成
- 使用browser-use配合大语言模型(LLM)自动生成Selenium和Playwright自动化脚本
- 分析游戏界面并生成上下文感知的自动化代码
- 支持日常远征、周常任务和季节性活动的复杂任务序列

### 2. 智能执行与恢复
- 执行生成的自动化脚本，内置错误处理机制
- AI干预系统实时检测并解决问题
- 自适应执行，从失败中学习并提升性能

## 🚀 快速开始

### 系统要求
- Python 3.12+
- Node.js 22+
- Chrome/Chromium浏览器
- 有效的KanColle账户

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/kancolle-vice-admiral.git
cd kancolle-vice-admiral

# 使用uv安装Python依赖
uv venv
source .venv/bin/activate  # Windows系统: .venv\Scripts\activate
uv pip install -r requirements.txt

# 安装Node.js依赖
npm install
```

### 配置

1. 设置环境变量:
```bash
cp .env.example .env
# 编辑.env文件配置你的设置
```

2. 在`config.json`中配置你的KanColle凭据和偏好设置

## 📖 使用方法

### 生成自动化脚本
```bash
# 生成日常任务脚本
python generate_scripts.py --task daily

# 生成周常任务脚本
python generate_scripts.py --task weekly

# 生成特定活动脚本
python generate_scripts.py --task event --event-name "Summer Event 2024"
```

### 执行自动化
```bash
# 运行日常自动化
python run_automation.py --script daily_tasks.py

# 带AI监控运行
python run_automation.py --script weekly_quests.py --ai-monitor
```

## 🔧 架构设计

- **脚本生成器**: 使用browser-use的AI驱动代码生成
- **执行引擎**: 强大的脚本执行与错误处理
- **AI监控器**: 实时干预和问题解决
- **任务管理器**: 自动化任务的调度和协调

## 🛡️ 安全特性

- **速率限制**: 尊重游戏服务器限制，避免被检测
- **错误恢复**: 自动从常见失败情况中恢复
- **手动干预**: 需要时可轻松手动介入
- **日志记录**: 全面的日志记录用于调试和监控

## 📝 支持的任务

- 日常远征和补给
- 周常任务完成
- 装备开发和改修
- 活动地图推进
- 资源管理
- 舰队编成

## 🤝 贡献

1. Fork此仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## ⚠️ 免责声明

此工具仅供教育和个人使用。请确保遵守：
- KanColle服务条款
- 当地法律法规
- 负责任的自动化实践

使用风险自负。开发者不对任何账户处罚或损害负责。

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 🌏 语言版本

- [English README](README.md)
- [日本語版 README](README_ja.md)

---

**注意**: 本项目与DMM或官方KanColle开发团队无关联或认可。

**しまかぜ、出撃しまーす！** ⚓ 
