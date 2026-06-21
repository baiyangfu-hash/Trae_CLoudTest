# 英语学习助手 v1.6.0

一款 Windows 桌面英语学习应用，对标博树（Busuu），纯本地运行，自用。

专为美国出差场景设计，覆盖超市购物、交通出行（租车/航班/轮渡）、问路、酒店餐厅、海关入境等 27 个真实对话场景。

---

## 功能模块

| 模块 | 功能 | 状态 |
|------|------|------|
| 课程大纲 | CEFR 分级学习路线（A1→A2→B1），6 个月进阶计划 | 已完成 |
| 情景对话阅读 | 27 个场景对话（5 基础 + 22 美国出差），中英对照，点击查词 | 已完成 |
| 词典查询 | 离线查词（ECDICT 340 万词库），精确/模糊搜索，音标+释义+词性+柯林斯星级 | 已完成 |
| 单词学习 | CEFR 分级词库（A1:500 / A2:1500 / B1:3000），三种学习模式（卡片/测验/拼写） | 已完成 |
| 听写练习 | 三种模式（单词/句子/对话），TTS 朗读，逐字母判分 | 已完成 |
| 语法练习 | 113 个语法点（A1:34 / A2:37 / B1:42），4 种题型自动生成 | 已完成 |
| 角色扮演 | 模拟真实对话，支持打字/语音输入，多答案匹配 | 已完成 |
| 入级测试 | 10 题快速定级，判断当前 A1/A2/B1 水平 | 已完成 |
| 学习统计 | 每日数据统计，学习记录明细 | 已完成 |
| 学习激励 | 积分系统（9 种得分规则）、连续学习天数、14 枚徽章 | 已完成 |
| 自定义导入 | 支持导入自定义对话 JSON，扩展个人场景 | 已完成 |

## 美国出差场景覆盖

| 分类 | 场景 |
|------|------|
| 超市购物 | 找商品结账、自助结账、退换货 |
| 交通出行 | 租车取车/还车、加油站、Uber/Lyft、国内航班、轮渡 |
| 问路 | 街头问路、地铁、商场内 |
| 日常交流 | 酒店入住/服务/退房、餐厅点餐、星巴克、得来速、同事闲聊、打电话 |
| 美国特有 | 海关入境（CBP 10 问）、小费指南 |

## 技术栈

- Python 3.10+
- PySide6 (Qt6 GUI)
- SQLite（本地数据库）
- ECDICT（离线词典，340 万词条）
- FSRS-4（间隔重复算法）
- CEFR（欧洲语言共同参考框架，分级词库与语法点）
- cefrpy（CEFR 词汇等级标注）
- Vosk（离线语音识别，可选）
- TTS 多引擎（SAPI5 / pyttsx3 / gTTS / edge-tts）

## 项目结构

```
src/
├── main.py                  # 主程序 + GUI（侧边栏导航 8 大模块）
├── course_page.py           # 课程大纲 UI（概览/路线图/语法/词汇 4 标签）
├── course_manager.py        # 课程管理，每日计划生成，6 个月路线图
├── cefr_tagger.py           # CEFR 词汇等级标注引擎
├── grammar_engine.py        # 113 个语法点数据库（A1/A2/B1）
├── grammar_practice.py      # 语法练习题自动生成（填空/选择/改错/排序）
├── grammar_practice_page.py # 语法练习 UI
├── level_test.py            # 入级测试引擎（30 题题库，10 题定级）
├── level_test_page.py       # 入级测试 UI
├── study_tracker.py         # 学习激励系统（积分/连胜/徽章）
├── dictionary.py            # 离线词典查询（ECDICT）
├── database.py              # SQLite 数据库管理（9+ 张表）
├── dialogs_data.py          # 基础情景对话数据（5 个）
├── us_travel_dialogs.py     # 美国出差场景对话数据（22 个）
├── dialog_importer.py       # 自定义对话导入器（JSON 格式）
├── fsrs_engine.py           # FSRS-4 间隔重复算法
├── tts_engine.py            # TTS 文本转语音引擎（4 引擎自动降级）
├── asr_engine.py            # ASR 语音识别引擎（Vosk 离线）
├── answer_matcher.py        # 多答案匹配引擎（3 策略匹配）
├── dictation_page.py        # 听写练习页面
├── roleplay_page.py         # 角色扮演页面
└── study_page.py            # 单词学习页面（卡片/测验/拼写）
tests/
└── run_tests.py             # 全模块自动化测试（13 项，全部通过）
data/
├── ecdict.db                # 精简词典（~50MB）
├── ecdict_full.db           # 完整词典（~812MB，gitignored）
└── app.db                   # 应用数据（用户词库/学习记录/统计）
models/
└── vosk-model-small-en-us/  # Vosk 语音识别模型（~50MB，需手动下载）
build.py                     # PyInstaller 打包脚本
requirements.txt             # Python 依赖清单
```

## 依赖项说明

### 核心依赖（必须安装）

| 包名 | 版本 | 用途 |
|------|------|------|
| PySide6 | >=6.5.0 | GUI 框架（Qt6），窗口、控件、事件 |
| requests | >=2.28.0 | HTTP 请求（gTTS/edge-tts 下载音频用） |
| cefrpy | >=0.1.0 | CEFR 词汇等级标注（P7 引入，MIT 许可证） |

### TTS 引擎（至少安装一个，推荐全部安装）

| 包名 | 版本 | 用途 | 网络要求 |
|------|------|------|----------|
| pyttsx3 | >=2.90 | 离线 TTS，跨平台 | 无需网络 |
| gTTS | >=2.3.0 | Google 在线 TTS | 需要网络 |
| edge-tts | >=6.1.0 | Edge 在线 TTS，音质好 | 需要网络 |

> Windows 用户额外福利：系统自带 SAPI5，无需安装任何 TTS 包即可朗读。
> TTS 引擎自动降级顺序：SAPI5 → pyttsx3 → gTTS → edge-tts

### 语音识别（可选）

| 包名 | 版本 | 用途 | 说明 |
|------|------|------|------|
| vosk | >=0.3.45 | 离线语音识别引擎 | 需下载模型（见下方） |
| pyaudio | >=0.2.11 | 麦克风录音 | Vosk 的录音依赖 |

### 打包工具

| 包名 | 版本 | 用途 |
|------|------|------|
| pyinstaller | >=6.0 | 打包为独立 Windows exe |

## 安装运行

### 1. 克隆仓库

```bash
git clone https://github.com/baiyangfu-hash/Trae_CLoudTest.git
cd Trae_CLoudTest/english-learning-app
```

### 2. 安装依赖

```bash
# 基础运行（必须）
pip install -r requirements.txt

# 或最小安装（仅核心功能）
pip install PySide6 requests cefrpy
```

### 3. 下载词典（首次运行）

```bash
# 完整版 ECDICT（推荐，340 万词条，812MB）
# 下载地址：https://github.com/skywind3000/ECDICT/releases
# 放置到 data/ecdict_full.db

# 精简版已包含在仓库中（data/ecdict.db，~50MB）
```

### 4. 启用语音识别（可选）

```bash
# 1. 安装依赖
pip install vosk pyaudio

# 2. 下载模型
# https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
# 解压到 models/vosk-model-small-en-us/
```

### 5. 运行程序

```bash
python src/main.py
```

### 6. 打包为 exe（独立运行，无需安装 Python）

```bash
pip install pyinstaller
python build.py
# 输出: dist/英语学习助手.exe
```

## 运行测试

```bash
python tests/run_tests.py
```

当前测试覆盖 13 个模块，全部通过：
- 词典查询、数据库操作、FSRS 算法、TTS 引擎
- 答案匹配、对话数据、美国出差对话、对话导入
- CEFR 标注、语法引擎、课程管理、语法练习、入级测试

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| P1 | 基础框架 + 词典查询 + 情景对话阅读 | 已完成 |
| P2 | 单词学习 + 间隔重复 + 学习统计 | 已完成 |
| P3 | 听写练习 + TTS + 自动判分 | 已完成 |
| P4 | 美国出差场景对话（22 个） | 已完成 |
| P5 | 角色扮演模式 + 语音识别 + 多答案匹配 | 已完成 |
| P6 | ECDICT 完整词典 + 自定义对话导入 | 已完成 |
| P7 | CEFR 分级体系 + 课程大纲 + 学习路线 | 已完成 |
| P8 | CEFR 分级词库 + 三种学习模式（卡片/测验/拼写） | 已完成 |
| P9 | 113 个语法点 + 4 种题型自动生成 | 已完成 |
| P10 | 入级测试 + 学习激励系统（积分/连胜/徽章） | 已完成 |

## 学习路线（6 个月达成 B1）

| 月份 | 阶段 | 目标 | 每日任务 |
|------|------|------|----------|
| 1-2 | A1 入门 | 掌握 500 词 + 34 个语法点 | 新学 8 词 + 复习 + 1 个对话 |
| 3-4 | A2 基础 | 掌握 1500 词 + 37 个语法点 | 新学 12 词 + 复习 + 语法练习 |
| 5-6 | B1 进阶 | 掌握 3000 词 + 42 个语法点 | 新学 15 词 + 复习 + 角色扮演 |

## 许可证

自用项目，代码开源供学习参考。ECDICT 词典数据遵循其原始许可证。

## 注意事项

1. **首次启动**：建议先完成"入级测试"，系统会根据你的水平推荐学习起点
2. **词典选择**：默认使用精简版词典，如需完整释义可下载 ECDICT 完整版放到 `data/ecdict_full.db`
3. **TTS 离线**：无网络时自动使用 pyttsx3 或 Windows SAPI5，无需担心
4. **语音识别**：Vosk 模型需手动下载（~50MB），不下载不影响其他功能
5. **数据备份**：`data/app.db` 包含所有学习记录，建议定期备份
