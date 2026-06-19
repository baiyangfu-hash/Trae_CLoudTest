# 英语学习助手

一款 Windows 桌面英语学习应用，对标博树（Busuu），纯本地运行。

## 功能模块

- **情景对话阅读**：多场景英语对话，中英对照，点击查词
- **单词学习**：内置词库，间隔重复记忆
- **词典查询**：离线查词，150万词条
- **学习统计**：每日学习量、掌握率趋势

## 技术栈

- Python 3.10+
- PySide6 (Qt6 GUI)
- SQLite (本地数据库)
- ECDICT (离线词典)
- FSRS (间隔重复算法)

## 安装运行

```bash
pip install -r requirements.txt
python src/main.py
```

## 项目结构

```
├── src/
│   ├── main.py           # 主程序 + GUI
│   ├── dictionary.py     # 离线词典查询
│   ├── database.py       # 数据库管理
│   ├── dialogs_data.py   # 情景对话数据
│   └── fsrs_engine.py    # 间隔重复算法
├── data/
│   ├── ecdict.db         # 词典数据库
│   └── app.db            # 应用数据
├── resources/
│   └── dialogs/          # 对话资源
├── requirements.txt
└── README.md
```

## 开发阶段

- P1: 基础框架 + 词典查询 + 情景对话阅读 ✅
- P2: 单词学习 + 间隔重复 + 学习统计 ✅
- P3: 听写练习 + 判分 + 错词复习 (待开发)
