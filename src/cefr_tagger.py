"""
CEFR 词汇标注模块 - 基于 cefrpy 为单词标注 CEFR 等级
"""
import sqlite3
import os
import json
from datetime import datetime

# 尝试导入 cefrpy
try:
    from cefrpy import CEFRAnalyzer
    CEFRPY_AVAILABLE = True
except ImportError:
    CEFRPY_AVAILABLE = False

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')
ECDICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecdict_full.db')
FALLBACK_DICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecdict.db')

# CEFR 等级定义
CEFR_LEVELS = {
    'A1': {'order': 1, 'label': 'A1 入门', 'word_target': 500, 'description': '能理解和使用日常表达和基础短语'},
    'A2': {'order': 2, 'label': 'A2 基础', 'word_target': 1500, 'description': '能理解常见话题的句子和常用表达'},
    'B1': {'order': 3, 'label': 'B1 进阶', 'word_target': 3000, 'description': '能应对旅行和工作中的大部分场景'},
    'B2': {'order': 4, 'label': 'B2 中级', 'word_target': 5000, 'description': '能流利交流，理解复杂文本'},
    'C1': {'order': 5, 'label': 'C1 高级', 'word_target': 8000, 'description': '能灵活有效地使用语言'},
    'C2': {'order': 6, 'label': 'C2 精通', 'word_target': 12000, 'description': '能轻松理解几乎所有听到和读到的内容'},
}


class CEFRTagger:
    """CEFR 词汇标注器"""

    def __init__(self):
        self._analyzer = None
        if CEFRPY_AVAILABLE:
            try:
                self._analyzer = CEFRAnalyzer()
            except Exception:
                self._analyzer = None

    @property
    def available(self):
        return self._analyzer is not None

    def get_level(self, word: str) -> str | None:
        """获取单词的 CEFR 等级"""
        if not self._analyzer:
            return None
        try:
            return _to_level(self._analyzer.get_average_word_level_CEFR(word))
        except Exception:
            return None

    def get_level_with_pos(self, word: str, pos: str = None) -> str | None:
        """获取单词在特定词性下的 CEFR 等级"""
        if not self._analyzer:
            return None
        try:
            if pos:
                # 转换 POS 为 cefrpy 的 POSTag
                from cefrpy import POSTag
                pos_map = {
                    'n': POSTag.NN, 'v': POSTag.VB, 'adj': POSTag.JJ,
                    'adv': POSTag.RB, 'prep': POSTag.IN, 'conj': POSTag.CC,
                    'pron': POSTag.PRP, 'num': POSTag.CD, 'art': POSTag.DT,
                }
                tag = pos_map.get(pos.lower()[:3])
                if tag:
                    return self._analyzer.get_word_pos_level_CEFR(word, tag)
            return self._analyzer.get_average_word_level_CEFR(word)
        except Exception:
            return None

    def is_known(self, word: str) -> bool:
        """检查单词是否在 cefrpy 数据库中"""
        if not self._analyzer:
            return False
        try:
            return self._analyzer.is_word_in_database(word)
        except Exception:
            return False

    def get_all_vocab_by_level(self, level: str) -> list:
        """获取指定 CEFR 等级的所有单词（从已标注的数据库）"""
        if not os.path.exists(DB_PATH):
            return []
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT word, cefr_level, pos_tag, frequency_score FROM vocab_cefr WHERE cefr_level = ? ORDER BY frequency_score DESC',
                (level,)
            )
            return [dict(r) for r in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()


STOPWORDS = set('''the and for but not you are was were has had have his her him she they them their its our
your this that these those with from into onto over under about than then there here what when where which who whom
whose why how can could will would shall should may might must been being does did done doing any some such own
same too very just also only both each few more most other another every either neither nor yet once ever never
again because while until upon within without per via'''.split())


def _to_level(value):
    if value is None:
        return None
    text = str(value)
    return text if text in CEFR_LEVELS else None


def build_cefr_lexicon(limit: int = 0, progress_callback=None):
    """
    从常用词词典构建 CEFR 词汇表（重建 vocab_cefr）
    frequency_score 越大越常用：Collins 星级 + 词频排名
    """
    if not CEFRPY_AVAILABLE:
        return False, "cefrpy 未安装（pip install cefrpy）"

    dict_path = ECDICT_PATH if os.path.exists(ECDICT_PATH) else FALLBACK_DICT_PATH
    if not os.path.exists(dict_path):
        return False, "词典数据库不存在"

    try:
        analyzer = CEFRAnalyzer()
    except Exception as e:
        return False, f"cefrpy 初始化失败: {e}"

    dict_conn = sqlite3.connect(dict_path)
    dict_conn.row_factory = sqlite3.Row
    rows = dict_conn.execute(
        "SELECT word, pos, tag, collins, bnc, frq FROM stardict "
        "WHERE word IS NOT NULL AND word != ''"
    ).fetchall()
    dict_conn.close()

    def _int(v):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    batch = []
    for i, row in enumerate(rows):
        word = row['word']
        if not word.isalpha() or not word.islower() or not 3 <= len(word) <= 20 or word in STOPWORDS:
            continue
        try:
            level = _to_level(analyzer.get_average_word_level_CEFR(word))
        except Exception:
            level = None
        if not level:
            continue
        frq = _int(row['frq'])
        bnc = _int(row['bnc'])
        rank = min(x for x in (frq, bnc, 30000) if x > 0)
        score = _int(row['collins']) * 10 + (30000 - rank) / 600
        batch.append((word, level, row['pos'] or '', round(score, 2), row['tag'] or ''))
        if limit and len(batch) >= limit:
            break
        if progress_callback and i % 2000 == 0:
            progress_callback(i, len(rows))

    app_conn = sqlite3.connect(DB_PATH)
    app_cursor = app_conn.cursor()
    app_cursor.execute('''
        CREATE TABLE IF NOT EXISTS vocab_cefr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            cefr_level TEXT,
            pos_tag TEXT,
            frequency_score REAL DEFAULT 0,
            topic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    app_cursor.execute('DELETE FROM vocab_cefr')
    app_cursor.execute('DROP INDEX IF EXISTS idx_vocab_cefr_word')
    app_cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_vocab_cefr_word ON vocab_cefr(word)')
    app_cursor.execute('CREATE INDEX IF NOT EXISTS idx_vocab_cefr_level ON vocab_cefr(cefr_level)')
    app_cursor.executemany(
        'INSERT OR IGNORE INTO vocab_cefr (word, cefr_level, pos_tag, frequency_score, topic) VALUES (?, ?, ?, ?, ?)',
        batch
    )
    app_conn.commit()
    app_conn.close()
    return True, f"已标注 {len(batch)} 个单词的 CEFR 等级"


def ensure_cefr_lexicon():
    """vocab_cefr 为空时自动构建，返回是否可用"""
    if sum(get_vocab_count_by_level().values()) > 0:
        return True
    ok, _ = build_cefr_lexicon()
    return ok


def get_vocab_count_by_level():
    """获取各 CEFR 等级的词汇数量"""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT cefr_level, COUNT(*) as cnt FROM vocab_cefr WHERE cefr_level IS NOT NULL GROUP BY cefr_level ORDER BY cefr_level'
        )
        return {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def get_words_by_level(level: str, limit: int = 100):
    """获取指定等级的单词列表"""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT word, cefr_level, pos_tag, frequency_score, topic FROM vocab_cefr WHERE cefr_level = ? ORDER BY frequency_score DESC LIMIT ?',
            (level, limit)
        )
        return [dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def get_user_level_progress(db_path=None):
    """获取用户等级进度"""
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM user_level_progress ORDER BY updated_at DESC LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()