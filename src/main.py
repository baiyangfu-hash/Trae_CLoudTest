"""
英语学习助手 - 主程序入口
"""
import sys
import os
import re
import html
import random
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
    QStackedWidget, QFrame, QScrollArea, QGridLayout, QMessageBox,
    QSizePolicy, QProgressBar, QFileDialog
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QIcon

from dictionary import Dictionary, format_translation_html, first_meaning, short_meaning
from database import Database
import travel_vocab
from dialogs_data import get_all_dialogs, get_dialog
from fsrs_engine import FSRSEngine, FSRSState
from tts_engine import TTSEngine
from cefr_tagger import CEFRTagger, get_words_by_level, ensure_cefr_lexicon
from dictation_page import DictationPage
from us_travel_dialogs import get_all_us_dialogs, get_us_dialog
from roleplay_page import RolePlayPage
from dialog_importer import DialogImporter, ImportError as DialogImportError
from course_page import CoursePage
from grammar_practice_page import GrammarPracticePage
from level_test_page import LevelTestPage
from study_tracker import get_tracker, BADGES

EXCHANGE_LABELS = {
    'p': '过去式', 'd': '过去分词', 'i': '现在分词', '3': '第三人称单数',
    's': '复数', 'r': '比较级', 't': '最高级',
}


def format_pos(pos):
    """'v:31/n:69' -> 'n. v.'"""
    if not pos:
        return ""
    items = []
    for part in pos.split('/'):
        if ':' in part:
            name, weight = part.split(':', 1)
            try:
                items.append((int(weight), name.strip()))
            except ValueError:
                items.append((0, name.strip()))
        elif part.strip():
            items.append((0, part.strip()))
    items.sort(reverse=True)
    return " ".join(f"{name}." for _, name in items[:3])


def format_exchange(exchange):
    """'s:airports/d:tipped' -> '复数 airports；过去分词 tipped'"""
    if not exchange:
        return ""
    result = []
    for part in exchange.split('/'):
        if ':' not in part:
            continue
        kind, form = part.split(':', 1)
        if kind in EXCHANGE_LABELS and form:
            result.append(f"{EXCHANGE_LABELS[kind]} {form}")
    return "；".join(result)


def entry_to_html(entry, with_english=True):
    """把词条渲染成 HTML：单词、音标、词性、出差语境、中文释义、英文释义、变形"""
    word = html.escape(entry.get('word', ''))
    parts = [f'<span style="font-size:22px;font-weight:bold;color:#2c3e50">{word}</span>']
    pos = format_pos(entry.get('pos', ''))
    if pos:
        parts.append(f' <span style="color:#7f8c8d">{html.escape(pos)}</span>')
    phonetic = (entry.get('phonetic') or '').strip()
    if phonetic:
        parts.append(f'<br><span style="color:#7f8c8d">/{html.escape(phonetic)}/</span>')
    if entry.get('inflected_from'):
        parts.append(f'<br><span style="color:#e67e22">“{html.escape(entry["inflected_from"])}” 是 '
                     f'{word} 的变形</span>')

    gloss = travel_vocab.get_gloss(entry.get('word', ''))
    if gloss:
        topic = travel_vocab.get_topic_of(entry.get('word', '')) or ''
        parts.append(f'<br><br><span style="color:#8e44ad;font-weight:bold">出差常用：{html.escape(gloss[0])}</span>')
        if topic:
            parts.append(f' <span style="color:#95a5a6">（{html.escape(str(topic))}）</span>')
        parts.append(f'<br><span style="color:#8e44ad">💬 {html.escape(gloss[1])}</span>')

    translation = format_translation_html(entry.get('translation', '')) or '暂无释义'
    parts.append(f'<br><br><b>中文释义</b><br>{translation}')
    if with_english and entry.get('definition'):
        parts.append(f'<br><br><b>英文释义</b><br>{format_translation_html(entry["definition"])}')
    exchange = format_exchange(entry.get('exchange', ''))
    if exchange:
        parts.append(f'<br><br><span style="color:#95a5a6;font-size:12px">变形：{html.escape(exchange)}</span>')
    return ''.join(parts)


class WordCard(QFrame):
    """单词卡片组件"""
    def __init__(self, word_data, parent=None):
        super().__init__(parent)
        self.word_data = word_data
        self.setFrameStyle(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
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

        word = self.word_data.get('word', '')
        word_label = QLabel(word)
        word_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(word_label)

        phonetic = (self.word_data.get('phonetic') or '').strip()
        pos = format_pos(self.word_data.get('pos', ''))
        sub = "  ".join(x for x in (f"/{phonetic}/" if phonetic else "", pos) if x)
        if sub:
            sub_label = QLabel(sub)
            sub_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            layout.addWidget(sub_label)

        meaning = StudyPage._short_meaning(self.word_data)
        meaning_label = QLabel(meaning)
        meaning_label.setStyleSheet("font-size: 13px; color: #34495e;")
        meaning_label.setWordWrap(True)
        layout.addWidget(meaning_label)

        self.setMaximumWidth(280)

    def mousePressEvent(self, event):
        parent = self.parent()
        while parent is not None and not isinstance(parent, DictionaryPage):
            parent = parent.parent()
        if parent is not None:
            parent._show_detail(self.word_data)
        super().mousePressEvent(event)


class DictionaryPage(QWidget):
    """词典页面"""
    def __init__(self, dictionary, tts=None, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.tts = tts
        self.current_word = ''
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入英文或中文查询，例如 airport / 发票 / receipt")
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

        action_layout = QHBoxLayout()
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
        action_layout.addWidget(random_btn)
        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        action_layout.addWidget(self.hint_label)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.results_container = QWidget()
        self.results_layout = QGridLayout(self.results_container)
        self.results_layout.setSpacing(8)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.results_container)
        layout.addWidget(scroll, 1)

        detail_frame = QFrame()
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(6)

        self.speak_btn = QPushButton("🔊 听发音")
        self.speak_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px;
                background-color: #8e44ad;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.speak_btn.clicked.connect(self._on_speak)
        detail_layout.addWidget(self.speak_btn, alignment=Qt.AlignLeft)

        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        self.detail_area.setMinimumHeight(220)
        self.detail_area.setMaximumHeight(340)
        detail_layout.addWidget(self.detail_area)

        self.detail_frame = detail_frame
        self.detail_frame.hide()
        layout.addWidget(detail_frame)

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_message(self, text):
        self.speak_btn.hide()
        self.current_word = ''
        self.detail_area.setHtml(f'<span style="color:#7f8c8d">{html.escape(text)}</span>')
        self.detail_frame.show()

    def _on_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return

        self._clear_results()
        self.detail_frame.hide()
        self.hint_label.setText("")

        if re.search(r'[\u4e00-\u9fff]', keyword):
            results = self.dictionary.search(keyword)
            if results:
                self.hint_label.setText(f"“{keyword}” 相关单词 {len(results)} 个，点击卡片看详情")
                self._show_word_list(results)
            else:
                self._show_message(f"没有找到包含“{keyword}”的单词，换个说法试试。")
            return

        entry = self.dictionary.lookup_one(keyword)
        if entry:
            self._show_detail(entry)
            related = [w for w in self.dictionary.search(entry['word'], limit=7)
                       if w.get('word') != entry['word']][:6]
            if related:
                self.hint_label.setText("相关单词（点击卡片查看）：")
                self._show_word_list(related)
            return

        results = self.dictionary.search(keyword)
        if results:
            self.hint_label.setText(f"没有找到 “{keyword}”，你是不是想找：")
            self._show_word_list(results)
        else:
            self._show_message(f"没有找到单词：{keyword}。请检查拼写，或直接输入中文，例如“发票”。")

    def _show_detail(self, word_data):
        """显示单词详情"""
        self.current_word = word_data.get('word', '')
        self.detail_area.setHtml(entry_to_html(word_data))
        self.speak_btn.show()
        self.detail_frame.show()
        if self.tts and getattr(self.tts, 'available', False) and self.current_word:
            self.tts.speak(self.current_word)

    def _on_speak(self):
        if not self.current_word:
            return
        if self.tts and getattr(self.tts, 'available', False):
            self.tts.speak(self.current_word)
        else:
            self.hint_label.setText("当前设备没有可用的语音引擎")

    def _show_word_list(self, words):
        """显示单词列表"""
        for i, word_data in enumerate(words):
            card = WordCard(word_data)
            self.results_layout.addWidget(card, i // 3, i % 3)

    def _on_random(self):
        """随机单词（优先出差实用词）"""
        self._clear_results()
        self.detail_frame.hide()
        pool = random.sample(travel_vocab.get_all_words(), 6)
        entries = [e for e in (self.dictionary.lookup_one(w) for w in pool) if e]
        self.hint_label.setText("随机出差实用词，点击卡片看详情")
        self._show_word_list(entries or self.dictionary.get_random_words(6))


class DialogLineWidget(QFrame):
    """对话行组件"""
    def __init__(self, line_data, dict_lookup_func, speak_func=None, parent=None):
        super().__init__(parent)
        self.line_data = line_data
        self.dict_lookup = dict_lookup_func
        self.speak_func = speak_func
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            DialogLineWidget {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 10px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 12, 16, 12)

        header = QHBoxLayout()
        speaker = self.line_data.get('speaker', '')
        speaker_label = QLabel(f"🧑 {speaker}:")
        speaker_label.setStyleSheet("font-weight: bold; color: #4a90d9; font-size: 13px;")
        header.addWidget(speaker_label)
        header.addStretch()
        speak_btn = QPushButton("🔊")
        speak_btn.setFixedSize(32, 28)
        speak_btn.setCursor(Qt.PointingHandCursor)
        speak_btn.setToolTip("朗读这一句")
        speak_btn.setStyleSheet("QPushButton { border: none; background: #f0f7ff; border-radius: 6px; }"
                                "QPushButton:hover { background: #d6e9fb; }")
        speak_btn.clicked.connect(self._on_speak)
        header.addWidget(speak_btn)
        layout.addLayout(header)

        text = self.line_data.get('text', '')
        pieces = []
        for token in text.split():
            clean = token.strip('.,!?;:"()').lower()
            safe = html.escape(token)
            if clean:
                pieces.append(f'<a href="{html.escape(clean, quote=True)}" '
                              f'style="color:#2c3e50;text-decoration:none">{safe}</a>')
            else:
                pieces.append(safe)
        self.text_label = QLabel(" ".join(pieces))
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.text_label.setStyleSheet("font-size: 16px; line-height: 1.5;")
        self.text_label.linkActivated.connect(self._on_word_click)
        layout.addWidget(self.text_label)

        translation = self.line_data.get('translation', '')
        trans_label = QLabel(translation)
        trans_label.setWordWrap(True)
        trans_label.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(trans_label)

    def _on_word_click(self, word):
        """点击单词查词"""
        self.dict_lookup(word)

    def _on_speak(self):
        if self.speak_func:
            self.speak_func(self.line_data.get('text', ''))


class DialogPage(QWidget):
    """情景对话页面"""
    def __init__(self, dictionary, tts=None, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.tts = tts
        self.current_dialog = None
        self._importer = DialogImporter()
        self._custom_dialogs = {}
        self._custom_counter = 0
        self._read_dialogs = set()
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

        # 导入对话按钮
        import_btn = QPushButton("导入对话")
        import_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 16px;
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        import_btn.clicked.connect(self._on_import_dialog)
        left_layout.addWidget(import_btn)

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
        self.lookup_result.setMaximumHeight(150)
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
        # 先从基础对话找，再从美国出差对话找，最后从自定义对话找
        dialog = get_dialog(dialog_id) or get_us_dialog(dialog_id) or self._custom_dialogs.get(dialog_id)
        if not dialog:
            return

        self.current_dialog = dialog
        self.title_label.setText(f"{dialog['title']} - {dialog['title_en']}")
        if dialog_id not in self._read_dialogs:
            self._read_dialogs.add(dialog_id)
            get_tracker().record('dialog_read')

        # 清空之前的对话行
        while self.dialog_layout.count() > 1:
            item = self.dialog_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加对话行
        for line in dialog['lines']:
            line_widget = DialogLineWidget(line, self._lookup_word, self._speak_text)
            self.dialog_layout.insertWidget(self.dialog_layout.count() - 1, line_widget)

    def _speak_text(self, text):
        if self.tts and getattr(self.tts, 'available', False) and text:
            self.tts.speak(text)
        else:
            self.lookup_result.setHtml('<span style="color:#e67e22">当前设备没有可用的语音引擎</span>')
            self.lookup_result.show()

    def _lookup_word(self, word):
        """点击单词查词并显示"""
        entry = self.dictionary.lookup_one(word)
        if entry:
            self.lookup_result.setHtml(entry_to_html(entry, with_english=False))
            if self.tts and getattr(self.tts, 'available', False):
                self.tts.speak(entry.get('word', word))
        else:
            self.lookup_result.setHtml(
                f'<span style="color:#7f8c8d">词典里没有找到 “{html.escape(word)}”</span>')
        self.lookup_result.show()

    def _on_import_dialog(self):
        """导入对话文件"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择对话文件",
            "",
            "对话文件 (*.json *.txt);;JSON 文件 (*.json);;文本文件 (*.txt);;所有文件 (*)"
        )
        if not filepath:
            return

        try:
            dialog = self._importer.import_file(filepath)

            # 生成唯一 ID
            self._custom_counter += 1
            dialog_id = f"custom_{self._custom_counter}"
            self._custom_dialogs[dialog_id] = dialog

            # 添加到列表
            dialog_info = {
                'id': dialog_id,
                'title': dialog['title'],
                'title_en': dialog['title_en'],
                'category': dialog['category'],
                'difficulty': dialog['difficulty'],
                'line_count': len(dialog['lines']),
            }
            self._all_dialogs.append(dialog_info)
            item_text = f"{dialog_info['title']}\n{dialog_info['title_en']} | {dialog_info['difficulty']}"
            self.dialog_list.addItem(item_text)

            # 自动选中新导入的对话
            self.dialog_list.setCurrentRow(len(self._all_dialogs) - 1)
            self._show_dialog(dialog_id)

            QMessageBox.information(self, "导入成功",
                                    f"成功导入对话: {dialog['title']}\n共 {len(dialog['lines'])} 行")
        except DialogImportError as e:
            QMessageBox.warning(self, "导入失败", f"导入对话失败:\n{str(e)}")

class StudyPage(QWidget):
    """单词学习页面 - CEFR分级 + 三种学习模式 + 间隔重复"""
    def __init__(self, dictionary, database, tts=None, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.database = database
        self.tts = tts
        self.fsrs = FSRSEngine()
        self.cefr_tagger = CEFRTagger()
        self.current_word = None
        self.current_word_data = None
        self.showing_answer = False
        self.current_cefr = "出差"
        self.current_mode = "card"
        self._cand_cache = {}
        self._advance_pending = False
        self._advance_timer = None
        self.study_tracker = get_tracker()
        self._setup_ui()
        self._load_next_card()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # 顶部信息栏
        info_layout = QHBoxLayout()
        self.progress_label = QLabel("今日新词: 0 | 待复习: 0")
        self.progress_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet("font-size: 13px; color: #8e44ad; font-weight: bold;")
        self.toast_label.hide()
        info_layout.addWidget(self.toast_label)
        info_layout.addStretch()
        self.streak_label = QLabel("🔥 连续学习: 0 天")
        self.streak_label.setStyleSheet("font-size: 14px; color: #e67e22;")
        info_layout.addWidget(self.streak_label)
        layout.addLayout(info_layout)

        # CEFR 等级筛选
        self._setup_cefr_tabs(layout)

        # 学习模式切换
        self._setup_mode_tabs(layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; border-radius: 4px; background-color: #e0e0e0; height: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #4a90d9; border-radius: 4px; }
        """)
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 学习内容区域（三种模式共用一个容器，切换显示）
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack, 1)

        # 卡片模式
        self.card_widget = QWidget()
        self._setup_card_mode_ui()
        self.content_stack.addWidget(self.card_widget)

        # 选择题模式
        self.quiz_widget = QWidget()
        self._setup_quiz_mode_ui()
        self.content_stack.addWidget(self.quiz_widget)

        # 拼写模式
        self.spell_widget = QWidget()
        self._setup_spell_mode_ui()
        self.content_stack.addWidget(self.spell_widget)

    def _setup_cefr_tabs(self, parent_layout):
        """CEFR 等级筛选标签"""
        cefr_layout = QHBoxLayout()
        cefr_layout.setSpacing(4)
        self.cefr_buttons = []
        levels = [("🧳 出差实用", "出差"), ("A1 入门", "A1"), ("A2 基础", "A2"), ("B1 进阶", "B1")]
        colors = {"出差": "#c0392b", "A1": "#3498db", "A2": "#27ae60", "B1": "#e67e22"}
        for label, level in levels:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(level == "出差")
            btn.setCursor(Qt.PointingHandCursor)
            c = colors.get(level, "#4a90d9")
            btn.setStyleSheet(f"""
                QPushButton {{ padding: 6px 16px; border: 2px solid {c}; border-radius: 16px;
                    background: transparent; color: {c}; font-size: 13px; font-weight: bold; }}
                QPushButton:checked {{ background: {c}; color: white; }}
                QPushButton:hover {{ background: {c}22; }}
            """)
            btn.clicked.connect(lambda checked, lv=level: self._on_cefr_tab(lv))
            cefr_layout.addWidget(btn)
            self.cefr_buttons.append((btn, level))
        cefr_layout.addStretch()
        parent_layout.addLayout(cefr_layout)

    def _setup_mode_tabs(self, parent_layout):
        """学习模式切换"""
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(4)
        self.mode_buttons = []
        modes = [("🃏 卡片模式", "card"), ("✅ 选择题", "quiz"), ("⌨️ 拼写模式", "spell")]
        for label, mode in modes:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(mode == "card")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { padding: 6px 14px; border: 1px solid #d0d0d0; border-radius: 6px;
                    background: transparent; color: #555; font-size: 12px; }
                QPushButton:checked { background: #2c3e50; color: white; border-color: #2c3e50; }
                QPushButton:hover { background: #f0f0f0; }
            """)
            btn.clicked.connect(lambda checked, m=mode: self._on_mode_tab(m))
            mode_layout.addWidget(btn)
            self.mode_buttons.append((btn, mode))
        mode_layout.addStretch()
        parent_layout.addLayout(mode_layout)

    def _setup_card_mode_ui(self):
        """卡片模式 UI"""
        layout = QVBoxLayout(self.card_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("QFrame { background: white; border: 2px solid #e0e0e0; border-radius: 16px; padding: 40px; }")
        self.card_frame.setMinimumSize(550, 320)
        self.card_frame.setMaximumSize(650, 420)
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        # 单词行（含 CEFR 标签 + 发音按钮）
        word_row = QHBoxLayout()
        word_row.setAlignment(Qt.AlignCenter)
        self.word_label = QLabel("Loading...")
        self.word_label.setStyleSheet("font-size: 38px; font-weight: bold; color: #2c3e50;")
        word_row.addWidget(self.word_label)

        self.cefr_badge = QLabel("")
        self.cefr_badge.setStyleSheet("font-size: 11px; padding: 2px 8px; border-radius: 10px; color: white;")
        self.cefr_badge.hide()
        word_row.addWidget(self.cefr_badge)

        self.speak_btn = QPushButton("🔊")
        self.speak_btn.setFixedSize(36, 36)
        self.speak_btn.setCursor(Qt.PointingHandCursor)
        self.speak_btn.setStyleSheet("QPushButton { border: none; background: #e8f4fc; border-radius: 18px; font-size: 16px; } QPushButton:hover { background: #d0e8f7; }")
        self.speak_btn.clicked.connect(self._on_speak)
        word_row.addWidget(self.speak_btn)
        card_layout.addLayout(word_row)

        # 音标
        self.phonetic_label = QLabel("")
        self.phonetic_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        self.phonetic_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.phonetic_label)

        # 词频
        self.collins_label = QLabel("")
        self.collins_label.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        self.collins_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.collins_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        line.setMaximumWidth(380)
        card_layout.addWidget(line, alignment=Qt.AlignCenter)

        # 答案区域
        self.answer_area = QWidget()
        ans_layout = QVBoxLayout(self.answer_area)
        ans_layout.setSpacing(8)
        ans_layout.setAlignment(Qt.AlignCenter)

        self.pos_label = QLabel("")
        self.pos_label.setStyleSheet("font-size: 14px; color: #95a5a6;")
        self.pos_label.setAlignment(Qt.AlignCenter)
        ans_layout.addWidget(self.pos_label)

        self.translation_label = QLabel("")
        self.translation_label.setStyleSheet("font-size: 20px; color: #34495e;")
        self.translation_label.setAlignment(Qt.AlignCenter)
        self.translation_label.setWordWrap(True)
        ans_layout.addWidget(self.translation_label)

        self.definition_label = QLabel("")
        self.definition_label.setStyleSheet("font-size: 13px; color: #7f8c8d; font-style: italic;")
        self.definition_label.setAlignment(Qt.AlignCenter)
        self.definition_label.setWordWrap(True)
        ans_layout.addWidget(self.definition_label)

        self.example_label = QLabel("")
        self.example_label.setStyleSheet("font-size: 13px; color: #8e44ad; padding: 6px 12px; background: #f5eef8; border-radius: 6px;")
        self.example_label.setAlignment(Qt.AlignCenter)
        self.example_label.setWordWrap(True)
        self.example_label.hide()
        ans_layout.addWidget(self.example_label)

        card_layout.addWidget(self.answer_area)
        self.answer_area.hide()
        layout.addWidget(self.card_frame, alignment=Qt.AlignCenter)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(10)

        self.show_btn = QPushButton("显示答案")
        self.show_btn.setStyleSheet("QPushButton { padding: 12px 50px; background: #4a90d9; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; } QPushButton:hover { background: #357abd; }")
        self.show_btn.clicked.connect(self._show_answer)
        btn_layout.addWidget(self.show_btn)

        self.rating_buttons = []
        for rating, text, color in [("again", "重来", "#e74c3c"), ("hard", "困难", "#e67e22"), ("good", "一般", "#4a90d9"), ("easy", "简单", "#27ae60")]:
            btn = QPushButton(text)
            btn.setStyleSheet(f"QPushButton {{ padding: 10px 18px; background: {color}; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }} QPushButton:hover {{ opacity: 0.8; }}")
            btn.setProperty("rating", rating)
            btn.clicked.connect(lambda checked, r=rating: self._on_rating(r))
            btn.hide()
            btn_layout.addWidget(btn)
            self.rating_buttons.append(btn)

        layout.addLayout(btn_layout)

    def _setup_quiz_mode_ui(self):
        """选择题模式 UI"""
        layout = QVBoxLayout(self.quiz_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        self.quiz_frame = QFrame()
        self.quiz_frame.setStyleSheet("QFrame { background: white; border: 2px solid #e0e0e0; border-radius: 16px; padding: 40px; }")
        self.quiz_frame.setMinimumSize(500, 380)
        self.quiz_frame.setMaximumSize(600, 450)
        qf_layout = QVBoxLayout(self.quiz_frame)
        qf_layout.setSpacing(16)
        qf_layout.setAlignment(Qt.AlignCenter)

        self.quiz_word_label = QLabel("")
        self.quiz_word_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #2c3e50;")
        self.quiz_word_label.setAlignment(Qt.AlignCenter)
        qf_layout.addWidget(self.quiz_word_label)

        self.quiz_phonetic_label = QLabel("")
        self.quiz_phonetic_label.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        self.quiz_phonetic_label.setAlignment(Qt.AlignCenter)
        qf_layout.addWidget(self.quiz_phonetic_label)

        qf_layout.addWidget(self._make_separator())

        self.quiz_prompt = QLabel("选择正确的中文释义：")
        self.quiz_prompt.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        self.quiz_prompt.setAlignment(Qt.AlignCenter)
        qf_layout.addWidget(self.quiz_prompt)

        self.quiz_options_layout = QVBoxLayout()
        self.quiz_options_layout.setSpacing(10)
        qf_layout.addLayout(self.quiz_options_layout)

        self.quiz_feedback = QLabel("")
        self.quiz_feedback.setAlignment(Qt.AlignCenter)
        self.quiz_feedback.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.quiz_feedback.hide()
        qf_layout.addWidget(self.quiz_feedback)

        layout.addWidget(self.quiz_frame, alignment=Qt.AlignCenter)

    def _setup_spell_mode_ui(self):
        """拼写模式 UI"""
        layout = QVBoxLayout(self.spell_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        self.spell_frame = QFrame()
        self.spell_frame.setStyleSheet("QFrame { background: white; border: 2px solid #e0e0e0; border-radius: 16px; padding: 40px; }")
        self.spell_frame.setMinimumSize(500, 350)
        self.spell_frame.setMaximumSize(600, 420)
        sf_layout = QVBoxLayout(self.spell_frame)
        sf_layout.setSpacing(16)
        sf_layout.setAlignment(Qt.AlignCenter)

        self.spell_hint = QLabel("")
        self.spell_hint.setStyleSheet("font-size: 20px; color: #34495e;")
        self.spell_hint.setAlignment(Qt.AlignCenter)
        self.spell_hint.setWordWrap(True)
        sf_layout.addWidget(self.spell_hint)

        self.spell_speak_btn = QPushButton("🔊 再听一次")
        self.spell_speak_btn.setStyleSheet("QPushButton { padding: 8px 20px; background: #e8f4fc; color: #4a90d9; border: none; border-radius: 8px; font-size: 14px; } QPushButton:hover { background: #d0e8f7; }")
        self.spell_speak_btn.clicked.connect(self._on_speak)
        sf_layout.addWidget(self.spell_speak_btn, alignment=Qt.AlignCenter)

        sf_layout.addWidget(self._make_separator())

        self.spell_input = QLineEdit()
        self.spell_input.setPlaceholderText("输入英文单词...")
        self.spell_input.setAlignment(Qt.AlignCenter)
        self.spell_input.setStyleSheet("QLineEdit { padding: 12px; font-size: 24px; border: 2px solid #e0e0e0; border-radius: 8px; text-align: center; } QLineEdit:focus { border-color: #4a90d9; }")
        self.spell_input.returnPressed.connect(self._on_spell_submit)
        sf_layout.addWidget(self.spell_input)

        self.spell_result = QLabel("")
        self.spell_result.setAlignment(Qt.AlignCenter)
        self.spell_result.setStyleSheet("font-size: 18px;")
        self.spell_result.hide()
        sf_layout.addWidget(self.spell_result)

        self.spell_submit_btn = QPushButton("提交")
        self.spell_submit_btn.setStyleSheet("QPushButton { padding: 10px 40px; background: #4a90d9; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #357abd; }")
        self.spell_submit_btn.clicked.connect(self._on_spell_submit)
        sf_layout.addWidget(self.spell_submit_btn, alignment=Qt.AlignCenter)

        layout.addWidget(self.spell_frame, alignment=Qt.AlignCenter)

    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        line.setMaximumWidth(350)
        return line

    # --- CEFR / Mode 切换 ---
    def _on_cefr_tab(self, level):
        self.current_cefr = level
        for btn, lv in self.cefr_buttons:
            btn.setChecked(lv == level)
        self._load_next_card()

    def _on_mode_tab(self, mode):
        self.current_mode = mode
        for btn, m in self.mode_buttons:
            btn.setChecked(m == mode)
        mode_idx = {"card": 0, "quiz": 1, "spell": 2}[mode]
        self.content_stack.setCurrentIndex(mode_idx)
        self._load_next_card()

    # --- 加载单词 ---
    def _load_next_card(self):
        self._advance_pending = False
        if self._advance_timer is not None:
            self._advance_timer.stop()
        word_data = self._get_next_word()
        if not word_data:
            self._show_complete()
            return
        self.current_word = word_data.get('word', '')
        self.current_word_data = word_data
        self.showing_answer = False

        if self.current_mode == "card":
            self._show_card_mode()
        elif self.current_mode == "quiz":
            self._show_quiz_mode()
        elif self.current_mode == "spell":
            self._show_spell_mode()

        self._update_progress()

    def _candidates(self):
        """当前标签下的候选单词（按优先级排序）"""
        level = self.current_cefr
        if level not in self._cand_cache:
            if level == "出差":
                words = travel_vocab.get_all_words()
            else:
                ensure_cefr_lexicon()
                words = [r['word'] for r in get_words_by_level(level, 1500)]
            self._cand_cache[level] = words
        return self._cand_cache[level]

    def _get_next_word(self):
        """优先到期复习，其次按顺序学新词"""
        states = self.database.get_user_word_states()
        now = datetime.now().isoformat()
        words = self._candidates()

        due = []
        for w in words:
            st = states.get(w)
            if st and st['status'] != 'new' and st['due_date'] and st['due_date'] <= now:
                due.append((st['due_date'], w))
        due.sort()
        ordered = [w for _, w in due]
        ordered += [w for w in words if w not in states or states[w]['status'] == 'new']

        for w in ordered:
            entry = self.dictionary.lookup_one(w)
            if entry:
                return entry
        return None

    def _show_complete(self):
        self.current_word = None
        self.current_word_data = None
        msg = "🎉 这一组学完了！"
        tip = "换个标签继续，或稍后回来复习"
        if self.current_mode == "card":
            self.word_label.setText(msg)
            self.phonetic_label.setText(tip)
            self.cefr_badge.hide()
            self.collins_label.hide()
            self.answer_area.hide()
            self.show_btn.hide()
            for b in self.rating_buttons:
                b.hide()
        elif self.current_mode == "quiz":
            self.quiz_word_label.setText(msg)
            self.quiz_phonetic_label.setText(tip)
            self.quiz_feedback.hide()
            self._clear_quiz_options()
        elif self.current_mode == "spell":
            self.spell_hint.setText(msg + "\n" + tip)
            self.spell_input.hide()
            self.spell_submit_btn.hide()
            self.spell_result.hide()
        self._update_progress()

    # --- 公共辅助 ---
    @staticmethod
    def _format_pos(pos):
        """'v:31/n:69' -> 'n. v.'"""
        if not pos:
            return ""
        items = []
        for part in pos.split('/'):
            if ':' in part:
                p, w = part.split(':', 1)
                try:
                    items.append((int(w), p.strip()))
                except ValueError:
                    items.append((0, p.strip()))
            elif part.strip():
                items.append((0, part.strip()))
        items.sort(reverse=True)
        return " ".join(f"{p}." for _, p in items[:3])

    @staticmethod
    def _short_meaning(entry):
        return short_meaning(entry)

    def _speak_current(self):
        if self.tts and self.tts.available and self.current_word:
            self.tts.speak(self.current_word)

    def _schedule_next(self, ms):
        """延迟进入下一题；重复调用只保留最后一次，切换标签时会被取消"""
        if self._advance_timer is None:
            self._advance_timer = QTimer(self)
            self._advance_timer.setSingleShot(True)
            self._advance_timer.timeout.connect(self._load_next_card)
        self._advance_timer.start(ms)

    def _clear_quiz_options(self):
        while self.quiz_options_layout.count():
            item = self.quiz_options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_toast(self, text, ms=4000):
        self.toast_label.setText(text)
        self.toast_label.show()
        QTimer.singleShot(ms, self.toast_label.hide)

    # --- 卡片模式 ---
    def _show_card_mode(self):
        self.content_stack.setCurrentIndex(0)
        self.answer_area.hide()
        self.show_btn.show()
        for b in self.rating_buttons:
            b.hide()

        d = self.current_word_data
        self.word_label.setText(d.get('word', ''))
        self.phonetic_label.setText(f"/{d.get('phonetic', '')}/" if d.get('phonetic') else "")

        level = self.cefr_tagger.get_level(d.get('word', '')) if self.cefr_tagger.available else None
        if level:
            colors = {"A1": "#3498db", "A2": "#27ae60", "B1": "#e67e22", "B2": "#e74c3c", "C1": "#9b59b6", "C2": "#2c3e50"}
            c = colors.get(str(level), "#7f8c8d")
            self.cefr_badge.setText(str(level))
            self.cefr_badge.setStyleSheet(f"font-size: 11px; padding: 2px 8px; border-radius: 10px; background: {c}; color: white;")
            self.cefr_badge.show()
        else:
            self.cefr_badge.hide()

        topic = travel_vocab.get_topic_of(d.get('word', ''))
        if topic:
            self.collins_label.setText(f"场景：{topic}")
            self.collins_label.show()
        else:
            self.collins_label.hide()

        self._speak_current()

    def _show_answer(self):
        if not self.current_word_data:
            return
        self.showing_answer = True
        self.show_btn.hide()
        d = self.current_word_data
        word = d.get('word', '')
        gloss = travel_vocab.get_gloss(word)

        self.pos_label.setText(self._format_pos(d.get('pos', '')))
        self.translation_label.setText(self._short_meaning(d))
        full = d.get('translation', '')
        lines = [l for l in full.replace('\\n', '\n').split('\n') if l.strip()][:3]
        self.definition_label.setTextFormat(Qt.RichText)
        self.definition_label.setText(format_translation_html("\n".join(lines)) if gloss else "")
        self.answer_area.show()

        if gloss:
            self.example_label.setText(f"💬 {gloss[1]}")
            self.example_label.show()
        else:
            self.example_label.hide()

        user_word = self.database.get_or_create_user_word(self.current_word)
        fsrs_state = FSRSState.from_json(user_word.get('fsrs_state'))
        intervals = self.fsrs.get_rating_intervals(fsrs_state)
        texts = {'again': '不会', 'hard': '模糊', 'good': '记得', 'easy': '太简单'}
        for btn in self.rating_buttons:
            r = btn.property("rating")
            btn.setText(f"{texts[r]}\n{self._interval_text(intervals.get(r, 1))}后复习")
            btn.show()

    @staticmethod
    def _interval_text(days):
        try:
            days = float(days)
        except (TypeError, ValueError):
            return "1天"
        if days < 1:
            return "今天"
        return f"{int(round(days))}天"

    def _on_speak(self):
        self._speak_current()

    # --- 选择题模式 ---
    def _show_quiz_mode(self):
        self.content_stack.setCurrentIndex(1)
        d = self.current_word_data
        self.quiz_word_label.setText(d.get('word', ''))
        self.quiz_phonetic_label.setText(f"/{d.get('phonetic', '')}/" if d.get('phonetic') else "")
        self.quiz_feedback.hide()
        self._clear_quiz_options()

        correct = self._short_meaning(d)
        options = self._generate_quiz_options(correct)
        random.shuffle(options)

        for opt in options:
            btn = QPushButton(opt)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { padding: 12px 20px; border: 2px solid #e0e0e0; border-radius: 8px;
                    background: white; color: #2c3e50; font-size: 14px; text-align: left; }
                QPushButton:hover { border-color: #4a90d9; background: #f8fbfe; }
            """)
            btn.clicked.connect(lambda checked, o=opt, c=(opt == correct): self._on_quiz_answer(o, c))
            self.quiz_options_layout.addWidget(btn)

        self._speak_current()

    def _generate_quiz_options(self, correct):
        """1 个正确释义 + 3 个干扰项（优先同场景，其次随机常用词）"""
        options = [correct]
        word = self.current_word
        pool = []
        topic = travel_vocab.get_topic_of(word)
        if topic:
            for name, words in travel_vocab.get_topics():
                if name == topic:
                    pool = [w for w in words if w != word]
        random.shuffle(pool)
        entries = []
        for w in pool:
            if len(entries) >= 12:
                break
            e = self.dictionary.lookup_one(w)
            if e:
                entries.append(e)
        if len(entries) < 8:
            entries += [e for e in self.dictionary.get_random_words(12) if e.get('word') != word]
        for e in entries:
            text = self._short_meaning(e)
            if text and text != "暂无释义" and text not in options:
                options.append(text)
            if len(options) >= 4:
                break
        for f in ["一个东西", "做某事", "某种状态", "一个地方"]:
            if len(options) >= 4:
                break
            if f not in options:
                options.append(f)
        return options[:4]

    def _on_quiz_answer(self, selected, is_correct):
        if self._advance_pending:
            return
        self._advance_pending = True
        correct = self._short_meaning(self.current_word_data)
        for i in range(self.quiz_options_layout.count()):
            w = self.quiz_options_layout.itemAt(i).widget()
            if not w:
                continue
            w.setEnabled(False)
            if w.text() == selected or w.text() == correct:
                color = "#27ae60" if w.text() == correct else "#e74c3c"
                w.setStyleSheet(f"QPushButton {{ padding: 12px 20px; border: 2px solid {color}; border-radius: 8px; background: {color}22; color: {color}; font-size: 14px; text-align: left; }}")

        self.quiz_feedback.show()
        if is_correct:
            self.quiz_feedback.setText("✅ 正确！")
            self.quiz_feedback.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
            self._record_and_advance("good", answered=True)
            self._schedule_next(1200)
        else:
            self.quiz_feedback.setText(f"❌ 正确答案: {correct}")
            self.quiz_feedback.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
            self._record_and_advance("again", answered=True)
            self._schedule_next(2500)

    # --- 拼写模式 ---
    def _show_spell_mode(self):
        self.content_stack.setCurrentIndex(2)
        d = self.current_word_data
        word = d.get('word', '')
        lines = [f"<span style='font-size:22px;color:#2c3e50'>{html.escape(self._short_meaning(d))}</span>"]
        gloss = travel_vocab.get_gloss(word)
        if gloss:
            blank = re.sub(re.escape(word), "____", gloss[1], flags=re.IGNORECASE)
            lines.append(f"<span style='font-size:14px;color:#8e44ad'>{html.escape(blank)}</span>")
        lines.append(f"<span style='font-size:13px;color:#95a5a6'>首字母 {html.escape(word[:1])}，共 {len(word)} 个字母</span>")
        self.spell_hint.setTextFormat(Qt.RichText)
        self.spell_hint.setText("<br>".join(lines))
        self.spell_input.setText("")
        self.spell_input.setEnabled(True)
        self.spell_input.show()
        self.spell_submit_btn.show()
        self.spell_result.hide()
        self.spell_input.setFocus()
        self._speak_current()

    def _on_spell_submit(self):
        if self._advance_pending or not self.current_word:
            return
        user_input = self.spell_input.text().strip().lower()
        correct = self.current_word.lower()
        if not user_input:
            return
        self._advance_pending = True
        self.spell_input.setEnabled(False)

        self.spell_result.setTextFormat(Qt.RichText)
        self.spell_result.show()
        if user_input == correct:
            self.spell_result.setText("✅ 完全正确！")
            self.spell_result.setStyleSheet("font-size: 18px; color: #27ae60; font-weight: bold;")
            self._record_and_advance("good", answered=True)
            self._schedule_next(1200)
        else:
            self.spell_result.setText(self._build_spell_comparison(user_input, correct))
            self.spell_result.setStyleSheet("font-size: 20px; font-weight: bold; letter-spacing: 2px;")
            self._record_and_advance("again", answered=True)
            self._schedule_next(3000)

    def _build_spell_comparison(self, user_input, correct):
        """逐字母对比：绿=对，红下划线=错，红删除线=多余，红_=漏掉"""
        parts = []
        for i in range(max(len(user_input), len(correct))):
            u = user_input[i] if i < len(user_input) else None
            c = correct[i] if i < len(correct) else None
            if u is not None and c is not None:
                if u == c:
                    parts.append(f'<span style="color:#27ae60">{html.escape(u)}</span>')
                else:
                    parts.append(f'<span style="color:#e74c3c;text-decoration:underline">{html.escape(u)}</span>')
            elif u is not None:
                parts.append(f'<span style="color:#e74c3c;text-decoration:line-through">{html.escape(u)}</span>')
            else:
                parts.append('<span style="color:#e74c3c">_</span>')
        return ("你的答案: " + "".join(parts) +
                f"<br><span style='color:#2c3e50;font-size:16px'>正确: {html.escape(correct)}</span>")

    # --- 通用方法 ---
    def _on_rating(self, rating):
        if not self.current_word or self._advance_pending:
            return
        self._advance_pending = True
        self._record_and_advance(rating)
        self._load_next_card()

    def _record_and_advance(self, rating, answered=False):
        """统一记录学习、更新 FSRS，并给积分/徽章"""
        if not self.current_word:
            return
        user_word = self.database.get_or_create_user_word(self.current_word)
        fsrs_state = FSRSState.from_json(user_word.get('fsrs_state'))
        new_state, due_date = self.fsrs.review(fsrs_state, rating)
        status = 'learning' if new_state.state in [1, 3] else 'review'
        self.database.update_user_word(self.current_word, status=status, fsrs_state=new_state.to_json(), due_date=due_date.isoformat())
        self.database.add_study_record(self.current_word, 'review', rating)
        is_new = user_word.get('status') == 'new'
        self.database.update_daily_stats(new_words=1 if is_new else 0, review_words=0 if is_new else 1, correct_count=1 if rating != 'again' else 0, total_count=1)

        new_badges = self.study_tracker.record('new_word' if is_new else 'review_word')
        if answered and rating != 'again':
            new_badges += self.study_tracker.record('correct_answer')
        if new_badges:
            names = "、".join(f"{b.get('icon', '')}{b.get('name', '')}" for b in new_badges)
            self._show_toast(f"🎉 获得新徽章：{names}")

    def _update_progress(self):
        stats = self.database.get_daily_stats()
        due_count = len(self.database.get_due_words(limit=100))
        self.progress_label.setText(f"今日新词: {stats['new_words']} | 待复习: {due_count}")
        self.progress_bar.setMaximum(50)
        self.progress_bar.setValue(min(stats['new_words'] + stats['review_words'], 50))
        try:
            self.streak_label.setText(f"🔥 连续学习: {self.study_tracker.get_streak_days()} 天")
        except Exception:
            pass


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

        self.tts = TTSEngine()
        self.study_tracker = get_tracker()

        self.level_test_page = LevelTestPage()
        self.course_page = CoursePage()
        self.dialog_page = DialogPage(self.dictionary, self.tts)
        self.dict_page = DictionaryPage(self.dictionary, self.tts)
        self.study_page = StudyPage(self.dictionary, self.database, self.tts)
        self.dictation_page = DictationPage(self.dictionary, self.database, tts=self.tts)
        self.roleplay_page = RolePlayPage(self.dictionary, self.database, tts=self.tts)
        self.grammar_practice_page = GrammarPracticePage()
        self.stats_page = StatsPage(self.database)

        pages = [
            ("🎯 入级测试", self.level_test_page),
            ("📋 课程大纲", self.course_page),
            ("🎭 角色扮演", self.roleplay_page),
            ("📚 情景对话", self.dialog_page),
            ("📝 单词学习", self.study_page),
            ("🎧 听写练习", self.dictation_page),
            ("📖 语法练习", self.grammar_practice_page),
            ("🔍 词典查询", self.dict_page),
            ("📊 学习统计", self.stats_page),
        ]
        nav_items = [(text, i) for i, (text, _) in enumerate(pages)]

        self.nav_buttons = []
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

        # 激励信息栏
        self.motivation_frame = QFrame()
        self.motivation_frame.setStyleSheet("QFrame { background: #f0f7ff; border-radius: 8px; margin: 8px; padding: 10px; }")
        mot_layout = QVBoxLayout(self.motivation_frame)
        mot_layout.setSpacing(4)
        mot_layout.setContentsMargins(10, 8, 10, 8)

        self.points_label = QLabel("⭐ 今日积分: 0")
        self.points_label.setStyleSheet("font-size: 12px; color: #2c3e50; font-weight: bold;")
        mot_layout.addWidget(self.points_label)

        self.streak_label = QLabel("🔥 连续学习: 0 天")
        self.streak_label.setStyleSheet("font-size: 12px; color: #e67e22;")
        mot_layout.addWidget(self.streak_label)

        self.badge_count_label = QLabel(f"🏅 徽章: 0/{len(BADGES)}")
        self.badge_count_label.setStyleSheet("font-size: 12px; color: #9b59b6;")
        mot_layout.addWidget(self.badge_count_label)

        sidebar_layout.addWidget(self.motivation_frame)

        # 版本信息
        version = QLabel("v1.6.0")
        version.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 8px;")
        version.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version)

        layout.addWidget(sidebar)

        # 内容区域
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f0f2f5;")

        for _, page in pages:
            self.stack.addWidget(page)

        layout.addWidget(self.stack)

        default_index = 2
        self.stack.setCurrentIndex(default_index)
        self.nav_buttons[default_index].setChecked(True)

        self._motivation_timer = QTimer(self)
        self._motivation_timer.timeout.connect(self._refresh_motivation)
        self._motivation_timer.start(5000)
        self._refresh_motivation()

    def _switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self._refresh_motivation()

    def _refresh_motivation(self):
        """刷新激励信息"""
        try:
            today_pts = self.study_tracker.get_today_points()
            streak = self.study_tracker.get_streak_days()
            badges = self.study_tracker.get_earned_badges()
            self.points_label.setText(f"⭐ 今日积分: {today_pts}")
            self.streak_label.setText(f"🔥 连续学习: {streak} 天")
            self.badge_count_label.setText(f"🏅 徽章: {len(badges)}/{len(BADGES)}")
        except Exception:
            pass

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
