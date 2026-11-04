"""Read existing learning records without executing demonstrations or awarding grades."""
import json
import re
from pathlib import Path
from . import walkthrough as w
from .curriculum import BY_ID


def snapshot(root, store, passed):
    saved = json.loads(store.setting(w.SETTING, '{}'))
    rows = []
    for key, item in w.CATALOG.items():
        old = saved.get(key)
        changed = bool(old and old.get('revision') != w.revision(key))
        state = w.state(store, key)
        steps = item['steps']
        notes = [{'step': i, 'title': step['title'], 'text': state['notes'][step['id']]}
                 for i, step in enumerate(steps) if state['notes'].get(step['id'], '').strip()]
        result = dict(status='none', saved=0, missing=len(steps), different=0, unknown=0)
        file = Path(root)/'runs'/'walkthrough'/key/'latest.json'
        if file.is_file():
            try:
                own = json.loads(file.read_text(encoding='utf-8'))
                if not isinstance(own, dict) or not isinstance(own.get('results'), dict):
                    raise ValueError('Invalid stored results')
                result['saved'] = sum(s['id'] in own['results'] for s in steps)
                result['missing'] = len(steps) - result['saved']
                if own.get('revision') != w.revision(key):
                    result['status'] = 'stale'
                elif own.get('parameter') != state['parameter']:
                    result['status'] = 'parameter'
                else:
                    for step in steps:
                        if step['id'] not in own['results']:
                            continue
                        frame = own['results'][step['id']]
                        diff = frame.get('difference') if isinstance(frame, dict) else None
                        if (not isinstance(diff, dict) or diff.get('available') is not True
                                or type(diff.get('different')) is not int or diff['different'] < 0):
                            result['unknown'] += 1
                        elif diff['different'] > 0:
                            result['different'] += 1
                    result['status'] = 'check' if result['missing'] or result['different'] or result['unknown'] else 'same'
            except (OSError, ValueError, TypeError):
                result.update(status='unreadable', saved=0, missing=len(steps), different=0, unknown=0)
        started = bool(old) or result['status'] != 'none'
        verified = bool(passed.get(key))
        attention = changed or result['status'] in ('check', 'stale', 'parameter', 'unreadable')
        rows.append(dict(id=key, title=BY_ID[key]['title'], total=len(steps), step=state['step'],
                         step_title=steps[state['step']]['title'], parameter=state['parameter'],
                         done=len(set(state['done'])), notes=notes, started=started, changed=changed,
                         verified=verified, attention=attention, result=result))
    return dict(rows=rows, counts=dict(total=len(rows), started=sum(r['started'] for r in rows),
                verified=sum(r['verified'] for r in rows), notes=sum(len(r['notes']) for r in rows),
                attention=sum(r['attention'] for r in rows)))


def notebook(data):
    lines = ['# 我的视觉学习笔记', '',
             '以下是导出时的基础题记录。自查、图解导入和正式代码验收分别统计；数值一致不证明独立完成或其他输入正确。', '']
    for row in data['rows']:
        if not row['started'] and not row['verified']:
            continue
        lines += [f"## {row['id']} · {row['title']}", '',
                  f"当前代码：{'已验收' if row['verified'] else '待验收'}；图解自查 {row['done']}/{row['total']} 步；保存位置第 {row['step'] + 1} 步，参数 {row['parameter']}。", '']
        if row['changed']:
            lines += ['课程已更新，此处仅展示当前版本记录；旧版自查不计入当前进度。', '']
        for note in row['notes']:
            # Preserve arbitrary learner text as a fenced block, including Markdown fences.
            fence = '`' * max(3, max((len(part) for part in re.findall(r'`+', note['text'])), default=0) + 1)
            lines += [f"### 第 {note['step'] + 1} 步 · {note['title']}", '', fence + 'text', note['text'], fence, '']
        if not row['notes']:
            lines += ['尚未记录本题的逐步观察笔记。', '']
    if not any(r['started'] or r['verified'] for r in data['rows']):
        lines += ['还没有图解学习记录。先打开一道题，记录你的观察。', '']
    return '\n'.join(lines)
