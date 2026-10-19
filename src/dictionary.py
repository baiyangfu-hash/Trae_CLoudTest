"""
词典模块 - 离线词典查询
基于 ECDICT 数据库（常用词精简版，见 scripts/build_common_dict.py）
"""
import re
import sqlite3
import os

DICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecdict.db')
FULL_DICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecdict_full.db')

_CJK_RE = re.compile(r'[\u4e00-\u9fff]')
_EDGE_RE = re.compile(r"^[^A-Za-z]+|[^A-Za-z]+$")

_CONTRACTIONS = {
    "i'm": "be", "you're": "be", "we're": "be", "they're": "be",
    "it's": "it", "that's": "that", "there's": "there", "what's": "what", "let's": "let",
    "i'll": "i", "you'll": "you", "we'll": "we", "they'll": "they",
    "i've": "have", "you've": "have", "we've": "have", "they've": "have",
    "don't": "do", "doesn't": "do", "didn't": "do", "can't": "can", "won't": "will",
    "isn't": "be", "aren't": "be", "wasn't": "be", "weren't": "be",
    "haven't": "have", "hasn't": "have", "wouldn't": "would", "couldn't": "could",
    "shouldn't": "should", "i'd": "i", "you'd": "you",
}


def format_translation_html(text):
    """把词典释义里的换行变成 HTML 换行"""
    if not text:
        return ''
    escaped = (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    return escaped.replace('\\n', '<br>').replace('\n', '<br>')


def first_meaning(translation, max_len=24):
    """取释义的第一条，用于选择题/卡片短释义"""
    if not translation:
        return ''
    for line in translation.replace('\\n', '\n').split('\n'):
        line = line.strip()
        if line and not line.startswith('['):
            return line[:max_len * 2] if len(line) > max_len * 2 else line
    return translation.strip()[:max_len * 2]


def short_meaning(entry):
    """单词的一句话中文释义：优先用出差语境释义，否则截取词典第一条"""
    if not entry:
        return ""
    import travel_vocab
    gloss = travel_vocab.get_gloss(entry.get('word', ''))
    if gloss:
        return gloss[0]
    text = first_meaning(entry.get('translation', ''), 12)
    text = re.sub(r'^[a-zA-Z]+\.\s*', '', text)
    parts = [p.strip() for p in re.split(r'[;；,，]', text) if p.strip()]
    text = parts[0] if parts else ""
    if len(parts) > 1 and len(text) + len(parts[1]) <= 8:
        text = f"{text}，{parts[1]}"
    return text[:16] or "暂无释义"


class Dictionary:
    def __init__(self):
        self.conn = None
        self._lemma_map = None
        self._ensure_dict()
        self._connect()

    def _ensure_dict(self):
        """确保词典数据库存在，不存在时创建空表"""
        os.makedirs(os.path.dirname(DICT_PATH), exist_ok=True)
        if os.path.exists(FULL_DICT_PATH) or os.path.exists(DICT_PATH):
            return
        conn = sqlite3.connect(DICT_PATH)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stardict (
                id INTEGER PRIMARY KEY, word TEXT UNIQUE, sw TEXT, phonetic TEXT,
                definition TEXT, translation TEXT, pos TEXT, collins TEXT, oxford TEXT,
                tag TEXT, bnc TEXT, frq TEXT, exchange TEXT, detail TEXT, audio TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _connect(self):
        """连接词典数据库，优先完整版"""
        dict_path = FULL_DICT_PATH if os.path.exists(FULL_DICT_PATH) else DICT_PATH
        if os.path.exists(dict_path):
            self.conn = sqlite3.connect(dict_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    @property
    def word_count(self):
        if not self.conn:
            return 0
        try:
            return self.conn.execute('SELECT COUNT(*) FROM stardict').fetchone()[0]
        except sqlite3.Error:
            return 0

    def _load_lemma_map(self):
        """从 exchange 字段构建 变形 -> 原形 映射（went -> go, airports -> airport）"""
        if self._lemma_map is not None:
            return self._lemma_map
        mapping = {}
        if self.conn:
            try:
                cursor = self.conn.execute("SELECT word, exchange FROM stardict WHERE exchange != ''")
                for row in cursor:
                    lemma = row[0]
                    for part in (row[1] or '').split('/'):
                        if ':' not in part:
                            continue
                        kind, form = part.split(':', 1)
                        if kind in ('0', '1'):
                            continue
                        form = form.lower()
                        if form and form != lemma.lower():
                            mapping.setdefault(form, lemma)
            except sqlite3.Error:
                pass
        self._lemma_map = mapping
        return mapping

    @staticmethod
    def normalize(word):
        """去掉首尾标点，转小写"""
        if not word:
            return ''
        word = word.replace('\u2019', "'").strip()
        return _EDGE_RE.sub('', word).lower()

    def _get_exact(self, word):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM stardict WHERE word = ? COLLATE NOCASE', (word,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def lookup_one(self, word):
        """查询单个单词（含变形还原、缩写处理），只返回 dict 或 None"""
        if not self.conn:
            return None
        key = self.normalize(word)
        if not key:
            return None

        found = self._get_exact(key)
        if found:
            return found

        if key in _CONTRACTIONS:
            found = self._get_exact(_CONTRACTIONS[key])
            if found:
                return found
        if key.endswith("'s") or key.endswith("s'"):
            found = self._get_exact(key[:-2] if key.endswith("'s") else key[:-1])
            if found:
                return found

        base = key.replace("'", '')
        lemma = self._load_lemma_map().get(key) or self._load_lemma_map().get(base)
        if lemma:
            found = self._get_exact(lemma)
            if found:
                found['inflected_from'] = key
                return found

        if base != key:
            return self._get_exact(base)
        return None

    def lookup(self, word):
        """查询单词：命中返回 dict，否则尝试前缀匹配返回 list，都没有返回 None"""
        found = self.lookup_one(word)
        if found:
            return found
        if not self.conn:
            return None
        key = self.normalize(word)
        if not key:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM stardict WHERE word LIKE ? ORDER BY CAST(NULLIF(frq, '') AS INTEGER) IS NULL, "
            "CAST(NULLIF(frq, '') AS INTEGER) LIMIT 8", (key + '%',))
        rows = cursor.fetchall()
        return [dict(r) for r in rows] if rows else None

    def search(self, keyword, limit=24):
        """搜索：中文关键词搜释义（如“发票”），英文关键词先前缀后包含，按词频排序"""
        if not self.conn:
            return []
        keyword = keyword.strip()
        if not keyword:
            return []
        order = "ORDER BY CAST(NULLIF(frq, '') AS INTEGER) IS NULL, CAST(NULLIF(frq, '') AS INTEGER)"
        cursor = self.conn.cursor()
        if _CJK_RE.search(keyword):
            cursor.execute(f'SELECT * FROM stardict WHERE translation LIKE ? {order} LIMIT ?',
                           ('%' + keyword + '%', limit))
            return [dict(r) for r in cursor.fetchall()]

        key = self.normalize(keyword) or keyword.lower()
        cursor.execute(f'SELECT * FROM stardict WHERE word LIKE ? {order} LIMIT ?', (key + '%', limit))
        results = [dict(r) for r in cursor.fetchall()]
        if len(results) < limit:
            seen = {r['word'] for r in results}
            cursor.execute(f'SELECT * FROM stardict WHERE word LIKE ? {order} LIMIT ?',
                           ('%' + key + '%', limit))
            for r in cursor.fetchall():
                if r['word'] not in seen and len(results) < limit:
                    results.append(dict(r))
        return results

    def get_random_words(self, count=10, common_only=True):
        """获取随机单词（默认只取常用词）"""
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        where = ''
        if common_only:
            where = ("WHERE (CAST(NULLIF(collins, '') AS INTEGER) >= 3 OR "
                     "(CAST(NULLIF(frq, '') AS INTEGER) BETWEEN 1 AND 6000))")
        cursor.execute(f'SELECT * FROM stardict {where} ORDER BY RANDOM() LIMIT ?', (count,))
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows and common_only:
            return self.get_random_words(count, common_only=False)
        return rows

    def get_words(self, words):
        """批量按单词取词条，返回 {小写单词: dict}"""
        result = {}
        for w in words:
            entry = self.lookup_one(w)
            if entry:
                result[w.lower()] = entry
        return result

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
