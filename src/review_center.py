"""
复习中心 - 跨级别混合复习、错题本、A1/A2 抽测
A1/A2 内容可以在课程页折叠隐藏，但这里始终可以复习，不会被放弃。
"""
import json
import os
import random
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QLineEdit, QCheckBox, QSizePolicy
)

import settings
import travel_vocab
from dictionary import short_meaning
from fsrs_engine import FSRSEngine, FSRSState
from level_test import LEVEL_TEST_QUESTIONS
from review_bank import get_scene_questions
from study_tracker import get_tracker

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')

BASIC_GROUPS = ('A1', 'A2')


class ReviewEngine:
    def __init__(self, database, dictionary, rng=None):
        self.database = database
        self.dictionary = dictionary
        self.rng = rng or random.Random()
        self.fsrs = FSRSEngine()
        self._level_map = None
        self._ensure_tables()

    def _ensure_tables(self):
        self.database.cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.database.cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_misses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL UNIQUE,
                level TEXT,
                qtype TEXT,
                payload TEXT NOT NULL,
                miss_count INTEGER NOT NULL DEFAULT 1,
                streak INTEGER NOT NULL DEFAULT 0,
                last_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.database.conn.commit()

    def _levels(self):
        if self._level_map is None:
            self._level_map = {}
            try:
                conn = sqlite3.connect(DB_PATH)
                try:
                    for word, level in conn.execute('SELECT word, cefr_level FROM vocab_cefr WHERE cefr_level IS NOT NULL'):
                        self._level_map[word] = level
                finally:
                    conn.close()
            except sqlite3.Error:
                pass
        return self._level_map

    def level_of(self, word):
        return self._levels().get(word) or self._levels().get(word.lower())

    def group_of(self, word):
        level = self.level_of(word)
        if level in BASIC_GROUPS:
            return level
        return 'other'

    def _matches(self, word, groups):
        return not groups or self.group_of(word) in groups

    def due_words(self, groups=None, limit=30):
        now = datetime.now().isoformat()
        rows = self.database.cursor.execute(
            "SELECT word, due_date FROM user_words WHERE status != 'new' AND due_date IS NOT NULL AND due_date <= ? ORDER BY due_date",
            (now,)
        ).fetchall()
        words = [r['word'] for r in rows if self._matches(r['word'], groups)]
        return words[:limit]

    def due_counts(self):
        counts = {'A1': 0, 'A2': 0, 'other': 0}
        for w in self.due_words(limit=100000):
            counts[self.group_of(w)] += 1
        counts['total'] = counts['A1'] + counts['A2'] + counts['other']
        return counts

    def learned_counts(self):
        counts = {'A1': 0, 'A2': 0, 'other': 0}
        rows = self.database.cursor.execute("SELECT word FROM user_words WHERE status != 'new'").fetchall()
        for r in rows:
            counts[self.group_of(r['word'])] += 1
        counts['total'] = sum(counts.values())
        return counts

    def mistake_words(self, limit=30):
        rows = self.database.cursor.execute(
            "SELECT s.word FROM study_records s JOIN ("
            "SELECT word, MAX(id) AS mid FROM study_records WHERE action = 'review' GROUP BY word"
            ") m ON s.id = m.mid WHERE s.result = 'again' ORDER BY s.id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [r['word'] for r in rows]

    def rate(self, word, rating, answered=True):
        user_word = self.database.get_or_create_user_word(word)
        state = FSRSState.from_json(user_word.get('fsrs_state'))
        new_state, due_date = self.fsrs.review(state, rating)
        status = 'learning' if new_state.state in [1, 3] else 'review'
        self.database.update_user_word(word, status=status, fsrs_state=new_state.to_json(), due_date=due_date.isoformat())
        self.database.add_study_record(word, 'review', rating)
        is_new = user_word.get('status') == 'new'
        self.database.update_daily_stats(
            new_words=1 if is_new else 0, review_words=0 if is_new else 1,
            correct_count=1 if rating != 'again' else 0, total_count=1
        )
        tracker = get_tracker()
        badges = tracker.record('new_word' if is_new else 'review_word')
        if answered and rating != 'again':
            badges += tracker.record('correct_answer')
        return badges

    def is_known_word(self, word):
        row = self.database.cursor.execute(
            "SELECT status FROM user_words WHERE word = ?", (word,)
        ).fetchone()
        return bool(row) and row['status'] != 'new'

    def _word_questions(self, groups, count):
        levels = [g for g in groups if g in BASIC_GROUPS] or list(BASIC_GROUPS)
        states = self.database.get_user_word_states()
        learned = [w for w, st in states.items()
                   if st['status'] != 'new' and self.level_of(w) in levels]
        self.rng.shuffle(learned)
        pool = list(learned)
        learned_set = set(learned)
        try:
            from cefr_tagger import get_words_by_level
            extra = []
            for lv in levels:
                extra += [r['word'] for r in get_words_by_level(lv, 600)]
            self.rng.shuffle(extra)
            pool += [w for w in extra if w not in learned_set]
        except Exception:
            pass

        entries = []
        for w in pool:
            if len(entries) >= count + 40:
                break
            entry = self.dictionary.lookup_one(w)
            if not entry:
                continue
            meaning = short_meaning(entry)
            if not meaning or meaning == '暂无释义' or not w.isalpha():
                continue
            entries.append((w, meaning))
        if len(entries) < 4:
            return []

        questions = []
        used = set()
        for word, meaning in entries:
            if len(questions) >= count:
                break
            if word in used:
                continue
            others = [m for w, m in entries if w != word and m != meaning]
            others = list(dict.fromkeys(others))
            if len(others) < 3:
                continue
            options = self.rng.sample(others, 3) + [meaning]
            self.rng.shuffle(options)
            level = self.level_of(word) or 'A2'
            questions.append({
                'type': 'vocab', 'level': level, 'word': word,
                'question': f"「{word}」是什么意思？",
                'options': options, 'answer': meaning, 'explain': f"{word} = {meaning}",
            })
            used.add(word)
        return questions

    def _bank_questions(self, groups):
        levels = [g for g in groups if g in BASIC_GROUPS] or list(BASIC_GROUPS)
        bank = []
        for lv in levels:
            for q in LEVEL_TEST_QUESTIONS.get(lv, []):
                item = deepcopy(q)
                item['level'] = lv
                item.setdefault('explain', '')
                bank.append(item)
        for q in get_scene_questions(levels):
            bank.append(deepcopy(q))
        return bank

    def build_spot_check(self, groups=BASIC_GROUPS, n=10):
        groups = tuple(groups) or BASIC_GROUPS
        word_target = max(1, int(n * 0.4))
        questions = self._word_questions(groups, word_target)
        bank = self._bank_questions(groups)
        self.rng.shuffle(bank)
        seen = {q['question'] for q in questions}
        redo = self.missed_questions(groups, limit=max(1, int(n * 0.3)))
        for q in redo:
            if q['question'] not in seen:
                seen.add(q['question'])
                questions.append(q)
        for q in bank:
            if len(questions) >= n:
                break
            if q['question'] in seen:
                continue
            seen.add(q['question'])
            questions.append(q)
        for q in questions:
            opts = list(q['options'])
            self.rng.shuffle(opts)
            q['options'] = opts
        self.rng.shuffle(questions)
        return questions[:n]

    def record_check(self, label, results, log=True):
        score = sum(1 for r in results if r['correct'])
        if not log:
            for r in results:
                self._track_miss(r)
            self.database.conn.commit()
            return score
        detail = {}
        types = {}
        for r in results:
            lv = r.get('level') or '其他'
            right, total = detail.get(lv, [0, 0])
            detail[lv] = [right + (1 if r['correct'] else 0), total + 1]
            tp = r.get('type') or 'other'
            right, total = types.get(tp, [0, 0])
            types[tp] = [right + (1 if r['correct'] else 0), total + 1]
            self._track_miss(r)
        detail['_types'] = types
        self.database.cursor.execute(
            'INSERT INTO review_checks (label, score, total, detail) VALUES (?, ?, ?, ?)',
            (label, score, len(results), json.dumps(detail, ensure_ascii=False))
        )
        self.database.conn.commit()
        return score

    def _track_miss(self, result):
        q = result.get('question')
        if not q or q.get('type') == 'vocab' or not q.get('question'):
            return
        cur = self.database.cursor
        row = cur.execute(
            'SELECT id, miss_count, streak FROM review_misses WHERE question = ?', (q['question'],)
        ).fetchone()
        if result['correct']:
            if row:
                if row['streak'] + 1 >= 2:
                    cur.execute('DELETE FROM review_misses WHERE id = ?', (row['id'],))
                else:
                    cur.execute('UPDATE review_misses SET streak = streak + 1 WHERE id = ?', (row['id'],))
            return
        payload = json.dumps(q, ensure_ascii=False)
        if row:
            cur.execute(
                'UPDATE review_misses SET miss_count = miss_count + 1, streak = 0, payload = ?, '
                'last_at = CURRENT_TIMESTAMP WHERE id = ?', (payload, row['id'])
            )
        else:
            cur.execute(
                'INSERT INTO review_misses (question, level, qtype, payload) VALUES (?, ?, ?, ?)',
                (q['question'], q.get('level'), q.get('type'), payload)
            )

    def miss_count(self):
        row = self.database.cursor.execute('SELECT COUNT(*) AS c FROM review_misses').fetchone()
        return row['c'] if row else 0

    def missed_questions(self, groups=None, limit=10):
        rows = self.database.cursor.execute(
            'SELECT payload, level FROM review_misses ORDER BY miss_count DESC, last_at DESC'
        ).fetchall()
        out = []
        for r in rows:
            if groups and r['level'] not in groups:
                continue
            try:
                q = json.loads(r['payload'])
            except ValueError:
                continue
            q['options'] = list(q.get('options', []))
            self.rng.shuffle(q['options'])
            out.append(q)
            if len(out) >= limit:
                break
        return out

    def type_accuracy(self, limit=5):
        acc = {}
        for row in self.check_history(limit):
            try:
                detail = json.loads(row['detail'] or '{}')
            except ValueError:
                continue
            for tp, (right, total) in (detail.get('_types') or {}).items():
                a = acc.setdefault(tp, [0, 0])
                a[0] += right
                a[1] += total
        return {tp: (r / t if t else 0.0, t) for tp, (r, t) in acc.items()}

    def weak_report(self):
        cur = self.database.cursor
        top_words = [
            (r['word'], r['c']) for r in cur.execute(
                "SELECT word, COUNT(*) AS c FROM study_records "
                "WHERE action = 'review' AND result = 'again' GROUP BY word ORDER BY c DESC, word LIMIT 8"
            ).fetchall()
        ]
        top_questions = []
        for r in cur.execute(
            'SELECT payload, miss_count FROM review_misses ORDER BY miss_count DESC, last_at DESC LIMIT 5'
        ).fetchall():
            try:
                q = json.loads(r['payload'])
            except ValueError:
                continue
            top_questions.append((q.get('question', ''), q.get('answer', ''), r['miss_count']))
        return {
            'levels': self.level_accuracy(5),
            'types': self.type_accuracy(5),
            'top_words': top_words,
            'top_questions': top_questions,
            'mistakes': len(self.mistake_words(1000)),
            'misses': self.miss_count(),
        }

    def check_history(self, limit=5):
        rows = self.database.cursor.execute(
            'SELECT label, score, total, detail, created_at FROM review_checks ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def level_accuracy(self, limit=5):
        acc = {}
        for row in self.check_history(limit):
            try:
                detail = json.loads(row['detail'] or '{}')
            except ValueError:
                continue
            for lv, val in detail.items():
                if lv.startswith('_'):
                    continue
                right, total = val
                a = acc.setdefault(lv, [0, 0])
                a[0] += right
                a[1] += total
        return {lv: (r / t if t else 0.0, t) for lv, (r, t) in acc.items()}

    def days_since_check(self):
        hist = self.check_history(1)
        if not hist:
            return None
        try:
            last = datetime.fromisoformat(hist[0]['created_at'])
        except (ValueError, TypeError):
            return None
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0, (now_utc - last).days)

    def suggestion(self):
        counts = self.due_counts()
        if counts['total'] > 0:
            return f"今天有 {counts['total']} 个词到期，先做「今日复习」。"
        since = self.days_since_check()
        if since is None:
            return "还没做过 A1/A2 抽测，建议先测一次，了解哪些基础内容需要回头巩固。"
        if since >= 7:
            return f"距离上次 A1/A2 抽测已 {since} 天，建议再测一次，防止基础遗忘。"
        if self.mistake_words(1):
            return "错题本里还有没掌握的词，建议重练一遍。"
        if self.miss_count():
            return f"有 {self.miss_count()} 道抽测答错的题还没巩固，建议重做一遍。"
        return "今天的复习任务都完成了，可以去学新内容。"


CARD_STYLE = "QFrame { background: white; border-radius: 12px; }"
BTN_PRIMARY = """
    QPushButton { background: #4a90d9; color: white; border: none; border-radius: 8px; padding: 12px 20px; font-size: 15px; }
    QPushButton:hover { background: #3a7bc8; }
    QPushButton:disabled { background: #b8c4d0; }
"""
BTN_PLAIN = """
    QPushButton { background: #ecf0f1; color: #2c3e50; border: none; border-radius: 8px; padding: 12px 20px; font-size: 15px; }
    QPushButton:hover { background: #dfe6e9; }
"""
OPT_STYLE = """
    QPushButton { background: white; color: #2c3e50; border: 2px solid #dfe6e9; border-radius: 8px; padding: 12px; font-size: 15px; text-align: left; }
    QPushButton:hover { border-color: #4a90d9; }
"""


class ReviewPage(QWidget):
    """复习中心页面"""
    def __init__(self, dictionary, database, tts=None, parent=None):
        super().__init__(parent)
        self.dictionary = dictionary
        self.database = database
        self.tts = tts
        self.engine = ReviewEngine(database, dictionary)
        self.session_words = []
        self.session_index = 0
        self.session_right = 0
        self.session_wrong = []
        self.session_label = ''
        self.session_waiting_next = False
        self.questions = []
        self.q_index = 0
        self.q_results = []
        self.q_label = ''
        self.q_answered = False
        self.new_badges = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.stack.addWidget(self._build_dashboard())
        self.stack.addWidget(self._build_recall())
        self.stack.addWidget(self._build_quiz())
        self.stack.addWidget(self._build_result())

    def _label(self, text='', size=14, color='#2c3e50', bold=False, wrap=True):
        lab = QLabel(text)
        lab.setWordWrap(wrap)
        lab.setStyleSheet(f"font-size: {size}px; color: {color}; {'font-weight: bold;' if bold else ''} background: transparent;")
        return lab

    def _build_dashboard(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.addWidget(self._label("🔁 复习中心", 24, bold=True))
        lay.addWidget(self._label("A1/A2 可以折叠隐藏，但不会被放弃：这里把所有级别的到期单词、错题和基础抽测放在一起，一键开始。", 13, '#7f8c8d'))

        self.suggest_label = self._label("", 15, '#e67e22', True)
        lay.addWidget(self.suggest_label)

        cards = QHBoxLayout()
        self.due_label = self._label("", 14)
        self.mistake_label = self._label("", 14)
        self.check_label = self._label("", 14)
        for lab in (self.due_label, self.mistake_label, self.check_label):
            frame = QFrame()
            frame.setStyleSheet(CARD_STYLE)
            fl = QVBoxLayout(frame)
            fl.addWidget(lab)
            cards.addWidget(frame)
        lay.addLayout(cards)

        btns = QHBoxLayout()
        self.btn_due = QPushButton("▶ 今日复习（拼写回忆）")
        self.btn_due.setStyleSheet(BTN_PRIMARY)
        self.btn_due.clicked.connect(self.start_due_review)
        self.btn_basic_due = QPushButton("只复习 A1/A2 到期词")
        self.btn_basic_due.setStyleSheet(BTN_PLAIN)
        self.btn_basic_due.clicked.connect(lambda: self.start_due_review(BASIC_GROUPS))
        self.btn_mistakes = QPushButton("📕 错题重练")
        self.btn_mistakes.setStyleSheet(BTN_PLAIN)
        self.btn_mistakes.clicked.connect(self.start_mistake_review)
        self.btn_redo = QPushButton("🔁 重做答错的题")
        self.btn_redo.setStyleSheet(BTN_PLAIN)
        self.btn_redo.clicked.connect(self.start_missed_questions)
        for b in (self.btn_due, self.btn_basic_due, self.btn_mistakes, self.btn_redo):
            btns.addWidget(b)
        lay.addLayout(btns)

        checks = QHBoxLayout()
        self.btn_check_basic = QPushButton("📝 A1/A2 抽测（10 题）")
        self.btn_check_basic.setStyleSheet(BTN_PRIMARY)
        self.btn_check_basic.clicked.connect(lambda: self.start_spot_check(BASIC_GROUPS, 10, "A1/A2 抽测"))
        self.btn_check_a1 = QPushButton("只测 A1")
        self.btn_check_a1.setStyleSheet(BTN_PLAIN)
        self.btn_check_a1.clicked.connect(lambda: self.start_spot_check(('A1',), 10, "A1 抽测"))
        self.btn_check_a2 = QPushButton("只测 A2")
        self.btn_check_a2.setStyleSheet(BTN_PLAIN)
        self.btn_check_a2.clicked.connect(lambda: self.start_spot_check(('A2',), 10, "A2 抽测"))
        self.btn_check_long = QPushButton("全面抽测（20 题）")
        self.btn_check_long.setStyleSheet(BTN_PLAIN)
        self.btn_check_long.clicked.connect(lambda: self.start_spot_check(BASIC_GROUPS, 20, "A1/A2 全面抽测"))
        for b in (self.btn_check_basic, self.btn_check_a1, self.btn_check_a2, self.btn_check_long):
            checks.addWidget(b)
        lay.addLayout(checks)

        self.hide_box = QCheckBox("在课程大纲、单词学习页隐藏 A1/A2 内容（可随时在此恢复）")
        self.hide_box.setStyleSheet("font-size: 14px; color: #2c3e50;")
        self.hide_box.setChecked(bool(settings.get('hide_basic_levels')))
        self.hide_box.toggled.connect(self._on_hide_toggled)
        lay.addWidget(self.hide_box)

        self.history_label = self._label("", 13, '#7f8c8d')
        lay.addWidget(self.history_label)
        lay.addStretch()
        return page

    def _build_recall(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)
        top = QHBoxLayout()
        self.recall_progress = self._label("", 14, '#7f8c8d')
        top.addWidget(self.recall_progress)
        quit_btn = QPushButton("结束")
        quit_btn.setStyleSheet(BTN_PLAIN)
        quit_btn.clicked.connect(self._finish_recall)
        top.addWidget(quit_btn)
        lay.addLayout(top)

        frame = QFrame()
        frame.setStyleSheet(CARD_STYLE)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(30, 30, 30, 30)
        self.recall_tag = self._label("", 13, '#7f8c8d')
        self.recall_tag.setAlignment(Qt.AlignCenter)
        self.recall_meaning = self._label("", 28, '#2c3e50', True)
        self.recall_meaning.setAlignment(Qt.AlignCenter)
        self.recall_hint = self._label("", 16, '#7f8c8d')
        self.recall_hint.setAlignment(Qt.AlignCenter)
        self.recall_input = QLineEdit()
        self.recall_input.setPlaceholderText("拼写这个单词，回车提交")
        self.recall_input.setStyleSheet("font-size: 20px; padding: 10px; border: 2px solid #dfe6e9; border-radius: 8px;")
        self.recall_input.returnPressed.connect(self._on_recall_enter)
        self.recall_feedback = self._label("", 18, '#2c3e50')
        self.recall_feedback.setAlignment(Qt.AlignCenter)
        for w in (self.recall_tag, self.recall_meaning, self.recall_hint, self.recall_input, self.recall_feedback):
            fl.addWidget(w)
        lay.addWidget(frame)

        row = QHBoxLayout()
        self.recall_submit = QPushButton("提交")
        self.recall_submit.setStyleSheet(BTN_PRIMARY)
        self.recall_submit.clicked.connect(self._on_recall_submit)
        self.recall_reveal = QPushButton("想不起来，看答案")
        self.recall_reveal.setStyleSheet(BTN_PLAIN)
        self.recall_reveal.clicked.connect(self._on_recall_reveal)
        self.recall_speak = QPushButton("🔊")
        self.recall_speak.setStyleSheet(BTN_PLAIN)
        self.recall_speak.clicked.connect(self._on_recall_speak)
        self.recall_next = QPushButton("下一个 ▶")
        self.recall_next.setStyleSheet(BTN_PRIMARY)
        self.recall_next.clicked.connect(self._recall_next)
        for b in (self.recall_submit, self.recall_reveal, self.recall_speak, self.recall_next):
            row.addWidget(b)
        lay.addLayout(row)
        lay.addStretch()
        return page

    def _build_quiz(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)
        top = QHBoxLayout()
        self.quiz_progress = self._label("", 14, '#7f8c8d')
        top.addWidget(self.quiz_progress)
        quit_btn = QPushButton("结束")
        quit_btn.setStyleSheet(BTN_PLAIN)
        quit_btn.clicked.connect(self._finish_quiz)
        top.addWidget(quit_btn)
        lay.addLayout(top)

        frame = QFrame()
        frame.setStyleSheet(CARD_STYLE)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(24, 24, 24, 24)
        self.quiz_tag = self._label("", 13, '#7f8c8d')
        self.quiz_question = self._label("", 18, '#2c3e50', True)
        fl.addWidget(self.quiz_tag)
        fl.addWidget(self.quiz_question)
        lay.addWidget(frame)

        self.quiz_buttons = []
        for _ in range(4):
            b = QPushButton()
            b.setStyleSheet(OPT_STYLE)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda checked=False, btn=b: self._on_quiz_answer(btn))
            lay.addWidget(b)
            self.quiz_buttons.append(b)

        self.quiz_feedback = self._label("", 15, '#2c3e50')
        lay.addWidget(self.quiz_feedback)
        self.quiz_next = QPushButton("下一题 ▶")
        self.quiz_next.setStyleSheet(BTN_PRIMARY)
        self.quiz_next.clicked.connect(self._quiz_next)
        lay.addWidget(self.quiz_next)
        lay.addStretch()
        return page

    def _build_result(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        self.result_title = self._label("", 22, bold=True)
        self.result_body = self._label("", 15)
        back = QPushButton("返回复习中心")
        back.setStyleSheet(BTN_PRIMARY)
        back.clicked.connect(self.show_dashboard)
        lay.addWidget(self.result_title)
        lay.addWidget(self.result_body)
        lay.addWidget(back)
        lay.addStretch()
        return page

    def _on_hide_toggled(self, checked):
        settings.set('hide_basic_levels', bool(checked))
        window = self.window()
        for name in ('course_page', 'study_page'):
            page = getattr(window, name, None)
            if page is not None and hasattr(page, 'apply_level_visibility'):
                page.apply_level_visibility()

    def refresh(self):
        self.hide_box.blockSignals(True)
        self.hide_box.setChecked(bool(settings.get('hide_basic_levels')))
        self.hide_box.blockSignals(False)
        due = self.engine.due_counts()
        learned = self.engine.learned_counts()
        mistakes = self.engine.mistake_words(100)
        self.due_label.setText(
            f"<b>今日到期</b><br><span style='font-size:26px;color:#4a90d9'>{due['total']}</span> 个词"
            f"<br>A1 {due['A1']} · A2 {due['A2']} · 其他 {due['other']}"
            f"<br><span style='color:#7f8c8d'>已学 A1 {learned['A1']} · A2 {learned['A2']}</span>")
        self.mistake_label.setText(
            f"<b>错题本</b><br><span style='font-size:26px;color:#e74c3c'>{len(mistakes)}</span> 个词"
            f"<br><span style='color:#7f8c8d'>最近一次答错且还没答对过</span>")
        hist = self.engine.check_history(5)
        if hist:
            last = hist[0]
            since = self.engine.days_since_check()
            self.check_label.setText(
                f"<b>上次基础抽测</b><br><span style='font-size:26px;color:#27ae60'>{last['score']}/{last['total']}</span>"
                f"<br>{since if since is not None else '?'} 天前 · {last['label']}")
        else:
            self.check_label.setText("<b>上次基础抽测</b><br><span style='font-size:20px'>尚未测试</span><br>建议先测一次")
        self.suggest_label.setText("💡 " + self.engine.suggestion())
        acc = self.engine.level_accuracy(5)
        if acc:
            parts = [f"{lv} 正确率 {int(rate * 100)}%（{n}题）" for lv, (rate, n) in sorted(acc.items())]
            lines = ["最近抽测：" + " ｜ ".join(parts)]
            for row in hist[:3]:
                lines.append(f"· {row['created_at'][:16]}  {row['label']}  {row['score']}/{row['total']}")
            self.history_label.setText("<br>".join(lines))
        else:
            self.history_label.setText("")
        self.btn_due.setEnabled(due['total'] > 0)
        self.btn_basic_due.setEnabled((due['A1'] + due['A2']) > 0)
        self.btn_mistakes.setEnabled(len(mistakes) > 0)
        misses = self.engine.miss_count()
        self.btn_redo.setText(f"🔁 重做答错的题（{misses}）" if misses else "🔁 重做答错的题")
        self.btn_redo.setEnabled(misses > 0)

    def show_dashboard(self):
        self.refresh()
        self.stack.setCurrentIndex(0)

    def start_due_review(self, groups=None):
        if isinstance(groups, bool):
            groups = None
        words = self.engine.due_words(groups=groups, limit=30)
        label = '今日复习' if not groups else 'A1/A2 到期复习'
        self._start_recall(words, label)

    def start_mistake_review(self):
        self._start_recall(self.engine.mistake_words(30), '错题重练')

    def _start_recall(self, words, label):
        words = list(words)
        if not words:
            self.show_dashboard()
            return
        random.shuffle(words)
        self.session_words = words
        self.session_index = 0
        self.session_right = 0
        self.session_wrong = []
        self.session_label = label
        self.new_badges = []
        self.stack.setCurrentIndex(1)
        self._show_recall_word()

    def _current_entry(self):
        return self.dictionary.lookup_one(self.session_words[self.session_index])

    def _show_recall_word(self):
        word = self.session_words[self.session_index]
        entry = self.dictionary.lookup_one(word) or {}
        self.session_waiting_next = False
        meaning = short_meaning(entry) if entry else word
        level = self.engine.level_of(word) or ''
        topic = travel_vocab.get_topic_of(word) if hasattr(travel_vocab, 'get_topic_of') else ''
        tags = [t for t in (level, topic) if t]
        self.recall_progress.setText(f"{self.session_label}  {self.session_index + 1}/{len(self.session_words)}")
        self.recall_tag.setText(" · ".join(tags))
        self.recall_meaning.setText(meaning)
        self.recall_hint.setText(f"{word[0]}{' _' * (len(word) - 1)}  （{len(word)} 个字母）")
        self.recall_input.clear()
        self.recall_input.setEnabled(True)
        self.recall_feedback.setText("")
        self.recall_submit.setVisible(True)
        self.recall_reveal.setVisible(True)
        self.recall_speak.setVisible(False)
        self.recall_next.setVisible(False)
        self.recall_input.setFocus()

    def _on_recall_enter(self):
        if self.session_waiting_next:
            self._recall_next()
        else:
            self._on_recall_submit()

    def _on_recall_submit(self):
        if self.session_waiting_next:
            return
        typed = self.recall_input.text().strip().lower()
        if not typed:
            return
        word = self.session_words[self.session_index]
        self._grade_recall(typed == word.lower())

    def _on_recall_reveal(self):
        if self.session_waiting_next:
            return
        self._grade_recall(False)

    def _grade_recall(self, correct):
        word = self.session_words[self.session_index]
        self.session_waiting_next = True
        entry = self.dictionary.lookup_one(word) or {}
        phonetic = (entry.get('phonetic') or '').strip()
        rating = 'good' if correct else 'again'
        try:
            self.new_badges += self.engine.rate(word, rating, answered=True)
        except Exception:
            pass
        if correct:
            self.session_right += 1
            self.recall_feedback.setText(f"✅ {word}  {('/' + phonetic + '/') if phonetic else ''}")
        else:
            self.session_wrong.append(word)
            self.recall_feedback.setText(f"❌ 正确答案：<b>{word}</b>  {('/' + phonetic + '/') if phonetic else ''}")
        self.recall_input.setEnabled(False)
        self.recall_submit.setVisible(False)
        self.recall_reveal.setVisible(False)
        self.recall_speak.setVisible(True)
        self.recall_next.setVisible(True)
        self.recall_next.setFocus()
        self._on_recall_speak()

    def _on_recall_speak(self):
        if self.tts is not None and self.session_words:
            try:
                self.tts.speak(self.session_words[self.session_index])
            except Exception:
                pass

    def _recall_next(self):
        if not self.session_waiting_next:
            return
        self.session_index += 1
        if self.session_index >= len(self.session_words):
            self._finish_recall()
        else:
            self._show_recall_word()

    def _finish_recall(self):
        done = self.session_index + (1 if self.session_waiting_next else 0)
        done = min(done, len(self.session_words))
        lines = [f"完成 {done} 个词，答对 {self.session_right} 个。"]
        if self.session_wrong:
            lines.append("需要加强：" + "、".join(self.session_wrong) + "（已进入错题本，之后会更快再出现）")
        if self.new_badges:
            lines.append("🎉 获得徽章：" + "、".join(f"{b.get('icon', '')}{b.get('name', '')}" for b in self.new_badges))
        self.result_title.setText(f"✅ {self.session_label}结束")
        self.result_body.setText("<br>".join(lines))
        self.session_waiting_next = False
        self.stack.setCurrentIndex(3)

    def start_spot_check(self, groups, n, label):
        questions = self.engine.build_spot_check(groups, n)
        if not questions:
            self.result_title.setText("题库不足")
            self.result_body.setText("暂时无法生成抽测题。")
            self.stack.setCurrentIndex(3)
            return
        self.questions = questions
        self.q_index = 0
        self.q_results = []
        self.q_label = label
        self.new_badges = []
        self.stack.setCurrentIndex(2)
        self._show_question()

    def start_missed_questions(self):
        questions = self.engine.missed_questions(limit=10)
        if not questions:
            self.show_dashboard()
            return
        self.questions = questions
        self.q_index = 0
        self.q_results = []
        self.q_label = '错题重做'
        self.new_badges = []
        self.stack.setCurrentIndex(2)
        self._show_question()

    def _show_question(self):
        q = self.questions[self.q_index]
        self.q_answered = False
        names = {'vocab': '词汇', 'grammar': '语法', 'reading': '阅读', 'scene': '美国生活场景'}
        self.quiz_progress.setText(f"{self.q_label}  {self.q_index + 1}/{len(self.questions)}")
        self.quiz_tag.setText(f"{q.get('level', '')} · {names.get(q.get('type'), '')}")
        self.quiz_question.setText(q['question'])
        for btn, opt in zip(self.quiz_buttons, q['options']):
            btn.setText(opt)
            btn.setStyleSheet(OPT_STYLE)
            btn.setEnabled(True)
            btn.setVisible(True)
        for btn in self.quiz_buttons[len(q['options']):]:
            btn.setVisible(False)
        self.quiz_feedback.setText("")
        self.quiz_next.setVisible(False)

    def _on_quiz_answer(self, btn):
        if self.q_answered:
            return
        self.q_answered = True
        q = self.questions[self.q_index]
        correct = btn.text() == q['answer']
        self.q_results.append({'level': q.get('level'), 'correct': correct, 'word': q.get('word'),
                               'type': q.get('type'), 'question': q})
        for b in self.quiz_buttons:
            b.setEnabled(False)
            if b.text() == q['answer']:
                b.setStyleSheet(OPT_STYLE + "QPushButton { background: #d5f5e3; border-color: #27ae60; }")
            elif b is btn:
                b.setStyleSheet(OPT_STYLE + "QPushButton { background: #fadbd8; border-color: #e74c3c; }")
        explain = q.get('explain') or ''
        self.quiz_feedback.setText(("✅ 正确。" if correct else f"❌ 正确答案：{q['answer']}。") + (f" {explain}" if explain else ""))
        word = q.get('word')
        try:
            if word and self.engine.is_known_word(word):
                self.new_badges += self.engine.rate(word, 'good' if correct else 'again', answered=True)
            elif correct:
                self.new_badges += get_tracker().record('correct_answer')
        except Exception:
            pass
        self.quiz_next.setText("查看结果 ▶" if self.q_index + 1 >= len(self.questions) else "下一题 ▶")
        self.quiz_next.setVisible(True)

    def _quiz_next(self):
        if not self.q_answered:
            return
        self.q_index += 1
        if self.q_index >= len(self.questions):
            self._finish_quiz()
        else:
            self._show_question()

    def _finish_quiz(self):
        if not self.q_results:
            self.show_dashboard()
            return
        score = self.engine.record_check(self.q_label, self.q_results, log=self.q_label != '错题重做')
        total = len(self.q_results)
        pct = int(score * 100 / total)
        if pct >= 85:
            advice = "基础很稳，A1/A2 可以继续折叠隐藏，一周后再抽测一次。"
        elif pct >= 60:
            advice = "基础基本稳定，薄弱处已进入错题本，建议用「错题重练」补一下。"
        else:
            advice = "基础有些生疏，建议先取消隐藏 A1/A2，系统复习一遍对应课程。"
        if self.q_label == '错题重做':
            advice = f"连续答对 2 次的题会从错题题库移除，目前还剩 {self.engine.miss_count()} 道待巩固。"
        by_level = {}
        for r in self.q_results:
            lv = r.get('level') or '其他'
            a = by_level.setdefault(lv, [0, 0])
            a[0] += 1 if r['correct'] else 0
            a[1] += 1
        detail = "，".join(f"{lv}: {a[0]}/{a[1]}" for lv, a in sorted(by_level.items()))
        lines = [f"得分 {score}/{total}（{pct}%）", f"分级：{detail}", advice]
        if self.new_badges:
            lines.append("🎉 获得徽章：" + "、".join(f"{b.get('icon', '')}{b.get('name', '')}" for b in self.new_badges))
        self.result_title.setText(f"📝 {self.q_label}完成")
        self.result_body.setText("<br>".join(lines))
        self.stack.setCurrentIndex(3)
