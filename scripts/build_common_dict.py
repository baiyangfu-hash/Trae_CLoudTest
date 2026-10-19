"""
从完整 ECDICT (stardict.db) 精简出常用词词典 data/ecdict.db

用法:
    python scripts/build_common_dict.py /path/to/stardict.db

完整 ECDICT 下载:
    https://github.com/skywind3000/ECDICT/releases (ecdict-sqlite-28.zip)
"""
import os
import re
import sqlite3
import sys

OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecdict.db')

SCHEMA = '''
CREATE TABLE stardict (
    id INTEGER PRIMARY KEY,
    word TEXT UNIQUE,
    sw TEXT,
    phonetic TEXT,
    definition TEXT,
    translation TEXT,
    pos TEXT,
    collins TEXT,
    oxford TEXT,
    tag TEXT,
    bnc TEXT,
    frq TEXT,
    exchange TEXT,
    detail TEXT,
    audio TEXT
)
'''

FILTER_SQL = '''
SELECT word, sw, phonetic, definition, translation, pos, collins, oxford, tag, bnc, frq, exchange
FROM stardict
WHERE translation IS NOT NULL AND translation != ''
  AND word NOT LIKE '% %'
  AND word GLOB '[A-Za-z]*'
  AND (
        collins > 0
     OR oxford = 1
     OR (tag IS NOT NULL AND tag != '')
     OR (frq > 0 AND frq <= 25000)
     OR (bnc > 0 AND bnc <= 25000)
  )
'''

WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\-\.]*$")


PHONETIC_FIX = str.maketrans({'ә': 'ə', 'є': 'ɛ', 'ε': 'ɛ', ':': 'ː', '\xa0': ' '})


def clean(value):
    if value is None:
        return ''
    return str(value)


def clean_phonetic(value):
    return clean(value).translate(PHONETIC_FIX).replace("'", 'ˈ').strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src_path = sys.argv[1]
    out_path = os.path.abspath(OUT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)

    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(out_path)
    dst.execute(SCHEMA)

    rows = []
    for r in src.execute(FILTER_SQL):
        word = r[0]
        if not WORD_RE.match(word):
            continue
        rows.append((word, clean(r[1]), clean_phonetic(r[2]), clean(r[3]), clean(r[4]), clean(r[5]),
                     clean(r[6]), clean(r[7]), clean(r[8]), clean(r[9]), clean(r[10]), clean(r[11])))

    dst.executemany(
        'INSERT OR IGNORE INTO stardict (word, sw, phonetic, definition, translation, pos, '
        'collins, oxford, tag, bnc, frq, exchange) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    dst.execute('CREATE INDEX idx_stardict_word_nocase ON stardict(word COLLATE NOCASE)')
    dst.commit()
    count = dst.execute('SELECT COUNT(*) FROM stardict').fetchone()[0]
    dst.execute('VACUUM')
    dst.close()
    src.close()
    print(f'完成: {count} 个常用词 -> {out_path} ({os.path.getsize(out_path) / 1024 / 1024:.1f} MB)')


if __name__ == '__main__':
    main()
