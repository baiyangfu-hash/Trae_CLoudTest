"""
英语学习助手 - 主程序入口
"""
import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
    QStackedWidget, QFrame, QScrollArea, QGridLayout, QMessageBox,
    QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from dictionary import Dictionary
from database import Database
from dialogs_data import get_all_dialogs, get_dialog
from fsrs_engine import FSRSEngine, FSRSState
from dictation_page import DictationPage
from us_travel_dialogs import get_all_us_dialogs, get_us_dialog
from roleplay_page import RolePlayPage

class WordCard(QFrame):
    """单词卡片组件"""
    def __init__(self, word_data, parent=None):
        super().__init__(parent)
        self.word_data = word_data
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            WordCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }
            WordCard:hover {
                border: 1px solid #4a90d9;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # 单词
        word_label = QLabel(self.word_data.get('word', ''))
        word_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(word_label)

        # 音标
        phonetic = self.word_data.get('phonetic', '')
        if phonetic:
            phonetic_label = QLabel(f"/{phonetic}/")
            phonetic_label.setStyleSheet("font-size: 13px; color: #7f8c8d;")
            layout.addWidget(phonetic_label)

        # 释义
        translation = self.word_data.get('translation', '')
        if translation:
            trans_label = QLabel(translation)
            trans_label.setStyleSheet("font-size: 13px; color: #34495e;")
            trans_label.setWordWrap(True)
            layout.addWidget(trans_label)

        # 词性
        pos = self.word_data.get('pos', '')
        if pos:
            pos_label = QLabel(pos)
            pos_label.setStyleSheet("font-size: 11px; color: #95a5a6;")
            layout.addWidget(pos_label)

        self.setMaximumWidth(280)

class DictionaryPage(QWidget):
    """词典页面"""
    def __init__(self, dictionary, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入单词查询...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4a90d9;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("查询")
        search_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # 随机单词按钮
        random_btn = QPushButton("随机单词")
        random_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        random_btn.clicked.connect(self._on_random)
        layout.addWidget(random_btn, alignment=Qt.AlignLeft)

        # 结果区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.results_container = QWidget()
        self.results_layout = QGridLayout(self.results_container)
        self.results_layout.setSpacing(8)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.results_container)
        layout.addWidget(scroll)

        # 详情区域
        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        self.detail_area.setMaximumHeight(200)
        self.detail_area.hide()
        layout.addWidget(self.detail_area)

    def _on_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return

        # 清空之前的结果
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.detail_area.hide()

        # 精确查询
        result = self.dictionary.lookup(keyword)
        if isinstance(result, dict):
            # 显示详情
            self._show_detail(result)
        elif isinstance(result, list) and result:
            # 显示模糊匹配结果
            self._show_word_list(result)
        else:
            # 尝试搜索
            results = self.dictionary.search(keyword)
            if results:
                self._show_word_list(results)
            else:
                self.detail_area.setText(f"未找到单词: {keyword}")
                self.detail_area.show()

    def _show_detail(self, word_data):
        """显示单词详情"""
        text = f"""
<b style="font-size:20px">{word_data.get('word', '')}</b>  <span style="color:#7f8c8d">{word_data.get('pos', '')}</span>

<font color="#7f8c8d">音标: /{word_data.get('phonetic', '')}/</font>

<b>释义:</b>
{word_data.get('translation', '暂无释义')}

<b>英文释义:</b>
{word_data.get('definition', '暂无')}

<font color="#95a5a6" size="2">变形: {word_data.get('exchange', '无')}</font>
        """
        self.detail_area.setHtml(text)
        self.detail_area.show()

    def _show_word_list(self, words):
        """显示单词列表"""
        for i, word_data in enumerate(words):
            card = WordCard(word_data)
            card.mousePressEvent = lambda e, w=word_data: self._show_detail(w)
            row = i // 3
            col = i % 3
            self.results_layout.addWidget(card, row, col)

    def _on_random(self):
        """随机单词"""
        words = self.dictionary.get_random_words(6)
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.detail_area.hide()
        self._show_word_list(words)

class DialogLineWidget(QFrame):
    """对话行组件"""
    def __init__(self, line_data, dict_lookup_func, parent=None):
        super().__init__(parent)
        self.line_data = line_data
        self.dict_lookup = dict_lookup_func
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            DialogLineWidget {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 10px;
                padding: 12px;
                margin: 4px 8px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 12, 16, 12)

        # 说话人
        speaker = self.line_data.get('speaker', '')
        speaker_label = QLabel(f"🧑 {speaker}:")
        speaker_label.setStyleSheet("font-weight: bold; color: #4a90d9; font-size: 13px;")
        layout.addWidget(speaker_label)

        # 英文文本（可点击查词）
        text = self.line_data.get('text', '')
        text_layout = QHBoxLayout()
        text_layout.setSpacing(4)

        words = text.split()
        for word in words:
            # 去除标点
            clean_word = word.strip('.,!?;:"').lower()
            btn = QPushButton(word)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    color: #2c3e50;
                    font-size: 15px;
                    padding: 2px 4px;
                    border: none;
                    background: transparent;
                }
                QPushButton:hover {
                    color: #4a90d9;
                    background-color: #e8f4fc;
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda checked, w=clean_word: self._on_word_click(w))
            text_layout.addWidget(btn)

        text_layout.addStretch()
        layout.addLayout(text_layout)

        # 中文翻译
        translation = self.line_data.get('translation', '')
        trans_label = QLabel(translation)
        trans_label.setStyleSheet("color: #7f8c8d; font-size: 13px; padding-left: 8px;")
        layout.addWidget(trans_label)

    def _on_word_click(self, word):
        """点击单词查词"""
        self.dict_lookup(word)

class DialogPage(QWidget):
    """情景对话页面"""
    def __init__(self, dictionary, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.current_dialog = None
        self._setup_ui()
        self._load_dialog_list()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧对话列表
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #f5f6fa;")
        left_panel.setMaximumWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)

        list_title = QLabel("📚 情景对话")
        list_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        left_layout.addWidget(list_title)

        self.dialog_list = QListWidget()
        self.dialog_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 8px;
                margin: 4px 0;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e8f4fc;
            }
        """)
        self.dialog_list.itemClicked.connect(self._on_dialog_selected)
        left_layout.addWidget(self.dialog_list)

        layout.addWidget(left_panel)

        # 右侧对话内容
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        # 标题栏
        self.title_label = QLabel("选择一个对话开始学习")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        right_layout.addWidget(self.title_label)

        # 查词结果区域
        self.lookup_result = QTextEdit()
        self.lookup_result.setReadOnly(True)
        self.lookup_result.setMaximumHeight(120)
        self.lookup_result.setStyleSheet("""
            QTextEdit {
                background-color: #fff8e1;
                border: 1px solid #ffe082;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        self.lookup_result.hide()
        right_layout.addWidget(self.lookup_result)

        # 对话内容滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.dialog_container = QWidget()
        self.dialog_layout = QVBoxLayout(self.dialog_container)
        self.dialog_layout.setSpacing(8)
        self.dialog_layout.setContentsMargins(0, 0, 0, 0)
        self.dialog_layout.addStretch()
        scroll.setWidget(self.dialog_container)
        right_layout.addWidget(scroll)

        layout.addWidget(right_panel)

    def _load_dialog_list(self):
        """加载对话列表（基础 + 美国出差）"""
        self._all_dialogs = []
        
        # 基础对话
        for d in get_all_dialogs():
            self._all_dialogs.append(d)
        
        # 美国出差对话
        for d in get_all_us_dialogs():
            self._all_dialogs.append(d)
        
        for dialog in self._all_dialogs:
            item_text = f"{dialog['title']}\n{dialog['title_en']} | {dialog['difficulty']}"
            self.dialog_list.addItem(item_text)

    def _on_dialog_selected(self, item):
        """选择对话"""
        index = self.dialog_list.row(item)
        if index < len(self._all_dialogs):
            dialog_id = self._all_dialogs[index]['id']
            self._show_dialog(dialog_id)

    def _show_dialog(self, dialog_id):
        """显示对话内容"""
        # 先从基础对话找，再从美国出差对话找
        dialog = get_dialog(dialog_id) or get_us_dialog(dialog_id)
        if not dialog:
            return

        self.current_dialog = dialog
        self.title_label.setText(f"{dialog['title']} - {dialog['title_en']}")

        # 清空之前的对话行
        while self.dialog_layout.count() > 1:
            item = self.dialog_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加对话行
        for line in dialog['lines']:
            line_widget = DialogLineWidget(line, self._lookup_word)
            self.dialog_layout.insertWidget(self.dialog_layout.count() - 1, line_widget)

    def _lookup_word(self, word):
        """查词并显示"""
        result = self.dictionary.lookup(word)
        if isinstance(result, dict):
            text = f"<b>{result.get('word', word)}</b> /{result.get('phonetic', '')}/ {result.get('pos', '')}<br>{result.get('translation', '暂无释义')}"
            self.lookup_result.setHtml(text)
            self.lookup_result.show()
        else:
            self.lookup_result.hide()

class StudyPage(QWidget):
    """单词学习页面 - 间隔重复卡片"""
    def __init__(self, dictionary, database, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.database = database
        self.fsrs = FSRSEngine()
        self.current_word = None
        self.current_word_data = None
        self.showing_answer = False
        self._setup_ui()
        self._load_next_card()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)

        # 顶部信息栏
        info_layout = QHBoxLayout()
        self.progress_label = QLabel("今日新词: 0 | 待复习: 0")
        self.progress_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()

        self.streak_label = QLabel("🔥 连续学习: 0 天")
        self.streak_label.setStyleSheet("font-size: 14px; color: #e67e22;")
        info_layout.addWidget(self.streak_label)
        layout.addLayout(info_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #e0e0e0;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 4px;
            }
        """)
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(30)

        # 单词卡片区域
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 16px;
                padding: 40px;
            }
        """)
        self.card_frame.setMinimumSize(600, 350)
        self.card_frame.setMaximumSize(700, 450)
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignCenter)

        # 单词
        self.word_label = QLabel("Loading...")
        self.word_label.setStyleSheet("font-size: 42px; font-weight: bold; color: #2c3e50;")
        self.word_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.word_label)

        # 音标
        self.phonetic_label = QLabel("")
        self.phonetic_label.setStyleSheet("font-size: 20px; color: #7f8c8d;")
        self.phonetic_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.phonetic_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        line.setMaximumWidth(400)
        card_layout.addWidget(line, alignment=Qt.AlignCenter)

        # 释义区域（默认隐藏）
        self.answer_area = QWidget()
        answer_layout = QVBoxLayout(self.answer_area)
        answer_layout.setSpacing(12)
        answer_layout.setAlignment(Qt.AlignCenter)

        self.pos_label = QLabel("")
        self.pos_label.setStyleSheet("font-size: 16px; color: #95a5a6;")
        self.pos_label.setAlignment(Qt.AlignCenter)
        answer_layout.addWidget(self.pos_label)

        self.translation_label = QLabel("")
        self.translation_label.setStyleSheet("font-size: 22px; color: #34495e;")
        self.translation_label.setAlignment(Qt.AlignCenter)
        self.translation_label.setWordWrap(True)
        answer_layout.addWidget(self.translation_label)

        self.definition_label = QLabel("")
        self.definition_label.setStyleSheet("font-size: 14px; color: #7f8c8d; font-style: italic;")
        self.definition_label.setAlignment(Qt.AlignCenter)
        self.definition_label.setWordWrap(True)
        answer_layout.addWidget(self.definition_label)

        card_layout.addWidget(self.answer_area)
        self.answer_area.hide()

        layout.addWidget(self.card_frame, alignment=Qt.AlignCenter)
        layout.addSpacing(20)

        # 按钮区域
        self.btn_area = QWidget()
        btn_layout = QHBoxLayout(self.btn_area)
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignCenter)

        # 显示答案按钮
        self.show_btn = QPushButton("显示答案")
        self.show_btn.setStyleSheet("""
            QPushButton {
                padding: 14px 60px;
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        self.show_btn.clicked.connect(self._show_answer)
        btn_layout.addWidget(self.show_btn)

        # 评分按钮（默认隐藏）
        self.rating_buttons = []
        rating_configs = [
            ("again", "重来", "#e74c3c", "1天"),
            ("hard", "困难", "#e67e22", "2天"),
            ("good", "一般", "#4a90d9", "4天"),
            ("easy", "简单", "#27ae60", "7天"),
        ]

        for rating, text, color, default_interval in rating_configs:
            btn = QPushButton(f"{text}\n< {default_interval}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 10px 20px;
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    opacity: 0.8;
                }}
            """)
            btn.setProperty("rating", rating)
            btn.clicked.connect(lambda checked, r=rating: self._on_rating(r))
            btn.hide()
            btn_layout.addWidget(btn)
            self.rating_buttons.append(btn)

        layout.addWidget(self.btn_area, alignment=Qt.AlignCenter)
        layout.addStretch()

    def _load_next_card(self):
        """加载下一张卡片"""
        # 先获取到期复习的单词
        due_words = self.database.get_due_words(limit=10)

        # 如果没有到期单词，获取随机新词
        if not due_words:
            random_words = self.dictionary.get_random_words(10)
            for word_data in random_words:
                self.database.get_or_create_user_word(word_data['word'])
            due_words = self.database.get_due_words(limit=10)

        if due_words:
            self.current_word = due_words[0]['word']
            self.current_word_data = self.dictionary.lookup(self.current_word)
            if isinstance(self.current_word_data, dict):
                self._show_card()
            else:
                # 如果词典查不到，跳过
                self._load_next_card()
        else:
            self.word_label.setText("🎉 今日学习完成！")
            self.phonetic_label.setText("明天再来吧")
            self.show_btn.hide()
            for btn in self.rating_buttons:
                btn.hide()

        self._update_progress()

    def _show_card(self):
        """显示卡片正面"""
        self.showing_answer = False
        self.answer_area.hide()
        self.show_btn.show()
        for btn in self.rating_buttons:
            btn.hide()

        word = self.current_word_data.get('word', '')
        phonetic = self.current_word_data.get('phonetic', '')

        self.word_label.setText(word)
        self.phonetic_label.setText(f"/{phonetic}/" if phonetic else "")

    def _show_answer(self):
        """显示答案"""
        self.showing_answer = True
        self.show_btn.hide()

        translation = self.current_word_data.get('translation', '暂无释义')
        definition = self.current_word_data.get('definition', '')
        pos = self.current_word_data.get('pos', '')

        self.pos_label.setText(pos)
        self.translation_label.setText(translation)
        self.definition_label.setText(definition)
        self.answer_area.show()

        # 显示评分按钮并更新间隔天数
        user_word = self.database.get_or_create_user_word(self.current_word)
        fsrs_state = FSRSState.from_json(user_word.get('fsrs_state'))
        intervals = self.fsrs.get_rating_intervals(fsrs_state)

        interval_texts = {
            'again': '1天',
            'hard': f"{intervals.get('hard', 2)}天",
            'good': f"{intervals.get('good', 4)}天",
            'easy': f"{intervals.get('easy', 7)}天",
        }

        rating_texts = {
            'again': '重来',
            'hard': '困难',
            'good': '一般',
            'easy': '简单',
        }

        for btn in self.rating_buttons:
            rating = btn.property("rating")
            btn.setText(f"{rating_texts.get(rating, rating)}\n< {interval_texts.get(rating, '1天')}")
            btn.show()

    def _on_rating(self, rating):
        """处理评分"""
        if not self.current_word:
            return

        # 获取当前状态
        user_word = self.database.get_or_create_user_word(self.current_word)
        fsrs_state = FSRSState.from_json(user_word.get('fsrs_state'))

        # 执行 FSRS 算法
        new_state, due_date = self.fsrs.review(fsrs_state, rating)

        # 更新数据库
        status = 'learning' if new_state.state in [1, 3] else 'review'
        self.database.update_user_word(
            self.current_word,
            status=status,
            fsrs_state=new_state.to_json(),
            due_date=due_date.isoformat()
        )

        # 记录学习
        self.database.add_study_record(self.current_word, 'review', rating)

        # 更新统计
        is_new = user_word.get('status') == 'new'
        self.database.update_daily_stats(
            new_words=1 if is_new else 0,
            review_words=0 if is_new else 1,
            correct_count=1 if rating != 'again' else 0,
            total_count=1
        )

        # 加载下一张
        self._load_next_card()

    def _update_progress(self):
        """更新进度显示"""
        stats = self.database.get_daily_stats()
        due_count = len(self.database.get_due_words(limit=100))
        self.progress_label.setText(f"今日新词: {stats['new_words']} | 待复习: {due_count}")
        self.progress_bar.setValue(min(stats['new_words'] + stats['review_words'], 50))
        self.progress_bar.setMaximum(50)


class StatsPage(QWidget):
    """学习统计页面"""
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self._setup_ui()
        self._load_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = QLabel("📊 学习统计")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        # 今日概览卡片
        overview = QFrame()
        overview.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        overview_layout = QHBoxLayout(overview)
        overview_layout.setSpacing(30)

        self.stat_labels = {}
        stat_items = [
            ("new_words", "📝 新词", "#4a90d9"),
            ("review_words", "🔄 复习", "#27ae60"),
            ("correct_rate", "✅ 正确率", "#e67e22"),
            ("study_minutes", "⏱️ 分钟", "#9b59b6"),
        ]

        for key, label, color in stat_items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setAlignment(Qt.AlignCenter)

            value_label = QLabel("0")
            value_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
            value_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(value_label)

            name_label = QLabel(label)
            name_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
            name_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(name_label)

            overview_layout.addWidget(item_widget)
            self.stat_labels[key] = value_label

        layout.addWidget(overview)

        # 学习记录
        records_title = QLabel("📋 最近学习记录")
        records_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 20px;")
        layout.addWidget(records_title)

        self.records_text = QTextEdit()
        self.records_text.setReadOnly(True)
        self.records_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        self.records_text.setMaximumHeight(200)
        layout.addWidget(self.records_text)

        # 刷新按钮
        refresh_btn = QPushButton("刷新统计")
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        refresh_btn.clicked.connect(self._load_stats)
        layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)

        layout.addStretch()

    def _load_stats(self):
        """加载统计数据"""
        stats = self.database.get_daily_stats()

        self.stat_labels['new_words'].setText(str(stats['new_words']))
        self.stat_labels['review_words'].setText(str(stats['review_words']))

        correct_rate = 0
        if stats['total_count'] > 0:
            correct_rate = round(stats['correct_count'] / stats['total_count'] * 100)
        self.stat_labels['correct_rate'].setText(f"{correct_rate}%")

        self.stat_labels['study_minutes'].setText(str(stats['study_minutes']))

        # 加载最近记录
        conn = self.database.conn
        cursor = conn.cursor()
        cursor.execute(
            'SELECT word, action, result, created_at FROM study_records ORDER BY created_at DESC LIMIT 20'
        )
        records = cursor.fetchall()

        text = "<table style='width:100%; border-collapse:collapse;'>"
        text += "<tr style='background:#f5f5f5;'><th style='padding:8px;text-align:left;'>单词</th><th style='padding:8px;text-align:left;'>操作</th><th style='padding:8px;text-align:left;'>结果</th><th style='padding:8px;text-align:left;'>时间</th></tr>"

        for row in records:
            word, action, result, created_at = row
            result_text = result or '-'
            text += f"<tr><td style='padding:6px;border-bottom:1px solid #eee;'><b>{word}</b></td><td style='padding:6px;border-bottom:1px solid #eee;'>{action}</td><td style='padding:6px;border-bottom:1px solid #eee;'>{result_text}</td><td style='padding:6px;border-bottom:1px solid #eee;color:#999;'>{created_at}</td></tr>"

        text += "</table>"
        self.records_text.setHtml(text)


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("英语学习助手")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
        """)

        # 初始化数据
        self.dictionary = Dictionary()
        self.database = Database()

        self._setup_ui()

    def _setup_ui(self):
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 侧边栏导航
        sidebar = QWidget()
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
        """)
        sidebar.setMaximumWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(4)

        # 标题
        title = QLabel("📖 英语学习\n助手")
        title.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 16px;
            text-align: center;
        """)
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)

        sidebar_layout.addSpacing(20)

        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            ("📚 情景对话", 0),
            ("🔍 词典查询", 1),
            ("📝 单词学习", 2),
            ("🎧 听写练习", 3),
            ("🎭 角色扮演", 4),
            ("📊 学习统计", 5),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    color: #bdc3c7;
                    font-size: 14px;
                    padding: 14px 20px;
                    border: none;
                    text-align: left;
                    background: transparent;
                }
                QPushButton:hover {
                    color: white;
                    background-color: #34495e;
                }
                QPushButton:checked {
                    color: white;
                    background-color: #4a90d9;
                }
            """)
            btn.clicked.connect(lambda checked, i=index: self._switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # 版本信息
        version = QLabel("v1.0.0")
        version.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 8px;")
        version.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version)

        layout.addWidget(sidebar)

        # 内容区域
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f0f2f5;")

        # 页面1: 情景对话
        self.dialog_page = DialogPage(self.dictionary)
        self.stack.addWidget(self.dialog_page)

        # 页面2: 词典查询
        self.dict_page = DictionaryPage(self.dictionary)
        self.stack.addWidget(self.dict_page)

        # 页面3: 单词学习
        self.study_page = StudyPage(self.dictionary, self.database)
        self.stack.addWidget(self.study_page)

        # 页面4: 听写练习
        self.dictation_page = DictationPage(self.dictionary, self.database)
        self.stack.addWidget(self.dictation_page)

        # 页面5: 角色扮演
        self.roleplay_page = RolePlayPage(self.dictionary, self.database)
        self.stack.addWidget(self.roleplay_page)

        # 页面6: 学习统计
        self.stats_page = StatsPage(self.database)
        self.stack.addWidget(self.stats_page)

        layout.addWidget(self.stack)

        # 默认选中第一个
        self.nav_buttons[0].setChecked(True)

    def _switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def closeEvent(self, event):
        """关闭时清理资源"""
        self.dictionary.close()
        self.database.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
