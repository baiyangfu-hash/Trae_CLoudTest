# 英语学习助手

一款 Windows 桌面英语学习应用，对标博树（Busuu），纯本地运行，自用。

## 功能模块

| 模块 | 功能 | 状态 |
|------|------|------|
| 情景对话阅读 | 27个场景对话（5基础+22美国出差），中英对照，点击查词 | 已完成 |
| 词典查询 | 离线查词，精确/模糊搜索，音标+释义+词性 | 已完成 |
| 单词学习 | FSRS间隔重复算法，四色评分，自动安排复习 | 已完成 |
| 听写练习 | 三种模式（单词/句子/对话），TTS朗读，逐字母判分 | 已完成 |
| 角色扮演 | 模拟真实对话，支持打字/语音输入，多答案匹配 | 已完成 |
| 学习统计 | 每日数据统计，学习记录明细 | 已完成 |

## 美国出差场景覆盖

| 分类 | 场景 |
|------|------|
| 超市购物 | 找商品结账、自助结账、退换货 |
| 交通出行 | 租车取车/还车、加油站、Uber/Lyft、国内航班、轮渡 |
| 问路 | 街头问路、地铁、商场内 |
| 日常交流 | 酒店入住/服务/退房、餐厅点餐、星巴克、得来速、同事闲聊、打电话 |
| 美国特有 | 海关入境(CBP 10问)、小费指南 |

## 技术栈

- Python 3.10+
- PySide6 (Qt6 GUI)
- SQLite (本地数据库)
- ECDICT (离线词典)
- FSRS-4 (间隔重复算法)
- Vosk (语音识别，可选)

## 项目结构

```
src/
├── main.py              # 主程序 + GUI
├── dictionary.py        # 离线词典查询
├── database.py          # 数据库管理
├── dialogs_data.py      # 基础情景对话数据
├── us_travel_dialogs.py # 美国出差场景对话数据
├── fsrs_engine.py       # FSRS 间隔重复算法
├── tts_engine.py        # TTS 文本转语音引擎
├── asr_engine.py        # ASR 语音识别引擎
├── answer_matcher.py    # 多答案匹配引擎
├── dictation_page.py    # 听写练习页面
└── roleplay_page.py     # 角色扮演页面
tests/
└── run_tests.py         # 全模块自动化测试
data/
├── ecdict.db            # 词典数据库
└── app.db               # 应用数据
build.py                 # PyInstaller 打包脚本
```

## 安装运行

### 基础运行（推荐）
```bash
pip install PySide6
python src/main.py
```

### 启用语音识别（可选）
```bash
pip install vosk pyaudio
# 下载模型: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
# 解压到 models/vosk-model-small-en-us/
```

### 打包为 exe
```bash
pip install PySide6 pyinstaller
python build.py
# 输出: dist/英语学习助手.exe
```

## 运行测试
```bash
python tests/run_tests.py
```

## 开发阶段

- P1: 基础框架 + 词典查询 + 情景对话阅读
- P2: 单词学习 + 间隔重复 + 学习统计
- P3: 听写练习 + TTS + 自动判分
- P4: 美国出差场景对话（22个）
- P5: 角色扮演模式 + 语音识别 + 多答案匹配
