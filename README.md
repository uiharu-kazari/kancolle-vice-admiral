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
- **Python 3.12+** - Download from [python.org](https://www.python.org/downloads/)
- **uv package manager** - Modern Python package manager
- **Chrome/Chromium browser** - For automation
- **Valid KanColle account** - DMM account with KanColle access
- **Google Gemini API key** - For AI automation

### Step 1: Install Dependencies

We use [UV](https://docs.astral.sh/uv/) as our package manager. If you don't have UV installed, please install it first from the [UV Installation Guide](https://docs.astral.sh/uv/getting-started/installation/).

### Step 2: Clone and Setup Project

```bash
# Clone the repository
git clone https://github.com/yourusername/kancolle-vice-admiral.git
cd kancolle-vice-admiral

# Install dependencies and setup environment
uv sync
uv run playwright install chromium
```

### Step 3: Environment Configuration

1. **Copy the environment template:**
```bash
cp .env.example .env
```

2. **Edit `.env` file with your credentials:**
```bash
# Open .env in your favorite editor
nano .env  # or code .env, vim .env, etc.
```

3. **Configure the following variables:**
```env
# DMM Account (Required)
DMM_EMAIL=your_dmm_email@example.com
DMM_PASSWORD=your_dmm_password

# Gemini AI API (Required)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# Automation Settings (Optional)
AUTO_RETRY_COUNT=3
LOG_LEVEL=INFO
```

### Step 4: Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key to your `.env` file

### Step 5: First Run

```bash
# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Validate your environment
uv run python main.py validate
```

### Step 6: Start Using

```bash
# Test login to DMM and KanColle
uv run python main.py login

# If login works, try generating a script
python main.py generate "check daily missions"

# Execute automation tasks
python main.py execute "collect daily missions"
```

## 📖 Usage

### Basic Commands

```bash
# Login to DMM and navigate to KanColle
python main.py login

# Validate your environment setup
python main.py validate

# Run daily automation tasks
python main.py daily
```

### Generate Automation Scripts
```bash
# Generate scripts for daily tasks
python main.py generate "daily expeditions"

# Generate scripts for weekly quests
python main.py generate "weekly PvP battles"

# Generate scripts for specific events
python main.py generate "Summer Event 2024 E1 farming"
```

### Execute Specific Tasks
```bash
# Execute daily missions
python main.py execute "collect daily missions"

# Execute expedition management
python main.py execute "send long expeditions"

# Execute equipment development
python main.py execute "develop equipment with resources"
```

### Advanced Options
```bash
# Enable debug logging
python main.py execute "daily tasks" --debug
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

- [中文版 README](README.zh.md)
- [日本語版 README](README.ja.md)

---

**Note**: This project is not affiliated with or endorsed by DMM or the official KanColle development team.

**しまかぜ、出撃しまーす！** ⚓ 
