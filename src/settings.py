"""
用户设置 - 以 JSON 文件持久化
"""
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'settings.json')

DEFAULTS = {
    'hide_basic_levels': False,
    'basic_levels': ['A1', 'A2'],
}


def _load():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key, default=None):
    data = _load()
    if key in data:
        return data[key]
    if default is not None:
        return default
    return DEFAULTS.get(key)


def set(key, value):
    data = _load()
    data[key] = value
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hidden_levels():
    """当前被折叠隐藏的级别列表（未开启隐藏时为空）"""
    if not get('hide_basic_levels'):
        return []
    return list(get('basic_levels') or [])


def is_hidden(level):
    return level in hidden_levels()
