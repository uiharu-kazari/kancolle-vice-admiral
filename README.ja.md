# 艦隊これくしょん副官 🚢

> **⚠️ Project Withhold Status**
>
> Development of this project is currently on hold because browser-use does not support HTML canvas interaction as required. We may resume work if we find an efficient way to interact with images.

艦隊これくしょんの日常・週間・季節のタスクを自動化するAI駆動のブラウザ自動化スクリプト生成・実行システムです。

## 🎯 機能

### 1. AI駆動のコード生成
- browser-useと大規模言語モデル(LLM)を使用してSeleniumやPlaywrightの自動化スクリプトを自動生成
- ゲーム画面を解析してコンテキストに応じた自動化コードを生成
- 日常の遠征、週間任務、季節イベントの複雑なタスクシーケンスに対応

### 2. インテリジェントな実行と復旧
- エラーハンドリング機能を内蔵した自動化スクリプトの実行
- リアルタイムで問題を検出・解決するAI介入システム
- 失敗から学習してパフォーマンスを向上させる適応実行

## 🚀 はじめに

### 前提条件
- Python 3.12+
- Node.js 22+
- Chrome/Chromiumブラウザ
- 有効な艦これアカウント

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/kancolle-vice-admiral.git
cd kancolle-vice-admiral

# uvを使用してPython依存関係をインストール
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Node.js依存関係をインストール
npm install
```

### 設定

1. 環境変数を設定:
```bash
cp .env.example .env
# .envファイルを編集して設定を調整
```

2. `config.json`で艦これの認証情報と設定を構成

## 📖 使用方法

### 自動化スクリプトの生成
```bash
# 日常タスク用スクリプト生成
python generate_scripts.py --task daily

# 週間任務用スクリプト生成
python generate_scripts.py --task weekly

# 特定イベント用スクリプト生成
python generate_scripts.py --task event --event-name "Summer Event 2024"
```

### 自動化の実行
```bash
# 日常自動化を実行
python run_automation.py --script daily_tasks.py

# AI監視付きで実行
python run_automation.py --script weekly_quests.py --ai-monitor
```

## 🔧 アーキテクチャ

- **スクリプトジェネレーター**: browser-useを使用したAI駆動のコード生成
- **実行エンジン**: エラーハンドリング機能を持つ堅牢なスクリプト実行
- **AIモニター**: リアルタイム介入と問題解決
- **タスクマネージャー**: 自動化タスクのスケジューリングと調整

## 🛡️ 安全機能

- **レート制限**: ゲームサーバーの制限を尊重し、検出を回避
- **エラー復旧**: 一般的な失敗シナリオからの自動復旧
- **手動オーバーライド**: 必要時の簡単な手動介入
- **ログ記録**: デバッグと監視のための包括的なログ記録

## 📝 対応タスク

- 日常の遠征と補給
- 週間任務の完了
- 装備開発と改修
- イベント海域の攻略
- 資源管理
- 艦隊編成

## 🤝 貢献

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを開く

## ⚠️ 免責事項

このツールは教育目的および個人使用のみを目的としています。以下に必ず従ってください：
- 艦これ利用規約
- 現地の法律および規制
- 責任ある自動化の実践

使用は自己責任でお願いします。開発者はいかなるアカウントペナルティや損害についても責任を負いません。

## 📄 ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## 🌏 言語版

- [English README](README.md)
- [中文版 README](README_zh.md)

---

**注意**: このプロジェクトはDMMや公式艦これ開発チームとは一切関係なく、承認も受けていません。

**しまかぜ、出撃しまーす！** ⚓ 