"""Explicit learner plans, independent of grades and walkthrough self checks."""
import json
from .walkthrough import CATALOG

SETTING = 'hub.study_plan'
LABELS = {'next': '下一步学', 'stuck': '暂时卡住', 'review': '待复习'}


def validate_plan(data):
    if not isinstance(data, dict) or any(key not in CATALOG for key in data):
        raise ValueError('学习安排包含未知基础题')
    for row in data.values():
        if (not isinstance(row, dict) or set(row) != {'status', 'note'}
                or not isinstance(row['status'], str) or row['status'] not in LABELS
                or not isinstance(row['note'], str) or len(row['note']) > 1000):
            raise ValueError('学习安排格式无效：请选择安排，备注最多 1000 字')


def read_plan(store):
    data = json.loads(store.setting(SETTING, '{}'))
    validate_plan(data)
    return data


def save_plan(store, key, row):
    if key not in CATALOG:
        raise ValueError('只能安排平台已有的基础题')
    if row == {'status': 'none', 'note': ''}:
        data = read_plan(store)
        data.pop(key, None)
    else:
        validate_plan({key: row})
        data = read_plan(store)
        data[key] = dict(row)
    store.set_setting(SETTING, json.dumps(data, ensure_ascii=False))
    return data.get(key, {'status': 'none', 'note': ''})
