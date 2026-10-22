"""
把桌面版的情景对话导出给手机网页版（web/）使用

用法: python scripts/export_web_data.py
输出: web/data/dialogs.js
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))

import dialogs_data  # noqa: E402
import us_travel_dialogs  # noqa: E402

OUT_PATH = os.path.join(ROOT, 'web', 'data', 'dialogs.js')


def main():
    dialogs = {}
    for source in (dialogs_data.DIALOGS, us_travel_dialogs.DIALOGS):
        for key, d in source.items():
            dialogs[key] = {
                'title': d['title'],
                'title_en': d['title_en'],
                'lines': [
                    {'speaker': l['speaker'], 'text': l['text'], 'translation': l['translation']}
                    for l in d['lines']
                ],
            }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write('// 由 scripts/export_web_data.py 自动生成，请勿手改\n')
        f.write('window.DIALOGS = ')
        json.dump(dialogs, f, ensure_ascii=False, indent=1)
        f.write(';\n')
    print(f'导出 {len(dialogs)} 个对话 -> {os.path.relpath(OUT_PATH, ROOT)}')


if __name__ == '__main__':
    main()
