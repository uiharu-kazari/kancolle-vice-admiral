# KanColle Vice Admiral 🚢

An intelligent automation system for 艦隊これくしょん (Kantai Collection) that leverages AI to generate and execute browser automation scripts for daily, weekly, and seasonal tasks.

## 🎯 Features

### 1. AI-Powered Code Generation
- Uses browser-use with Large Language Models (LLM) to automatically generate Selenium and Playwright automation scripts
- Analyzes game interface and generates context-aware automation code
- Supports complex task sequences for daily expeditions, weekly quests, and seasonal events

### 2. Intelligent Execution & Recovery
- Executes generated automation scripts with built-in error handling
- AI intervention system that detects and resolves issues in real-time
- Adaptive execution that learns from failures and improves performance

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Node.js 22+
- Chrome/Chromium browser
- Valid KanColle account

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kancolle-vice-admiral.git
cd kancolle-vice-admiral

# Install Python dependencies using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

### Configuration

1. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Configure your KanColle credentials and preferences in `config.json`

## 📖 Usage

### Generate Automation Scripts
```bash
# Generate scripts for daily tasks
python generate_scripts.py --task daily

# Generate scripts for weekly quests
python generate_scripts.py --task weekly

# Generate scripts for specific events
python generate_scripts.py --task event --event-name "Summer Event 2024"
```

### Execute Automation
```bash
# Run daily automation
python run_automation.py --script daily_tasks.py

# Run with AI monitoring
python run_automation.py --script weekly_quests.py --ai-monitor
```

## 🔧 Architecture

- **Script Generator**: AI-powered code generation using browser-use
- **Execution Engine**: Robust script execution with error handling
- **AI Monitor**: Real-time intervention and problem resolution
- **Task Manager**: Scheduling and coordination of automation tasks

## 🛡️ Safety Features

- **Rate Limiting**: Respects game server limits and avoids detection
- **Error Recovery**: Automatic recovery from common failure scenarios
- **Manual Override**: Easy manual intervention when needed
- **Logging**: Comprehensive logging for debugging and monitoring

## 📝 Supported Tasks

- Daily expeditions and resupply
- Weekly quest completion
- Equipment development and improvement
- Event map progression
- Resource management
- Fleet organization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This tool is for educational and personal use only. Please ensure compliance with:
- KanColle Terms of Service
- Local laws and regulations
- Responsible automation practices

Use at your own risk. The developers are not responsible for any account penalties or damages.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌏 Language Versions

- [中文版 README](README_zh.md)
- [日本語版 README](README_ja.md)

---

**Note**: This project is not affiliated with or endorsed by DMM or the official KanColle development team.

**しまかぜ、出撃しまーす！** ⚓ 
