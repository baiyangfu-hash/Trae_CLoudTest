"""
英语学习助手 - 主程序入口
"""
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
    QStackedWidget, QFrame, QScrollArea, QGridLayout, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from dictionary import Dictionary
from database import Database
from dialogs_data import get_all_dialogs, get_dialog

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
        """加载对话列表"""
        dialogs = get_all_dialogs()
        for dialog in dialogs:
            item_text = f"{dialog['title']}\n{dialog['title_en']} | {dialog['difficulty']}"
            item = self.dialog_list.addItem(item_text)

    def _on_dialog_selected(self, item):
        """选择对话"""
        index = self.dialog_list.row(item)
        dialogs = get_all_dialogs()
        if index < len(dialogs):
            dialog_id = dialogs[index]['id']
            self._show_dialog(dialog_id)

    def _show_dialog(self, dialog_id):
        """显示对话内容"""
        dialog = get_dialog(dialog_id)
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
            ("📊 学习统计", 3),
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

        # 页面3: 单词学习 (占位)
        self.study_page = QWidget()
        study_layout = QVBoxLayout(self.study_page)
        study_label = QLabel("单词学习功能开发中...")
        study_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        study_label.setAlignment(Qt.AlignCenter)
        study_layout.addWidget(study_label)
        self.stack.addWidget(self.study_page)

        # 页面4: 学习统计 (占位)
        self.stats_page = QWidget()
        stats_layout = QVBoxLayout(self.stats_page)
        stats_label = QLabel("学习统计功能开发中...")
        stats_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        stats_label.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(stats_label)
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
