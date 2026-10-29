"""Versioned understanding checks: separate from executable-code grades."""
import json
import math
import re
import time
from .function_handbook import CARDS

SETTING = 'hub.function-review'


def snapshot(store):
    try:
        raw=json.loads(store.setting(SETTING, '{}'))
    except (ValueError, TypeError):
        raw={}
    raw=raw if isinstance(raw,dict) else {}
    records={}
    for key,value in raw.items():
        if key not in CARDS or not isinstance(value,dict):continue
        quiz=CARDS[key]['quiz']
        choice=value.get('choice')
        if type(choice) is not int or not 0<=choice<len(quiz['options']):continue
        attempts=value.get('attempts');wrong=value.get('wrong_attempts')
        if type(attempts) is not int or type(wrong) is not int or not 0<=wrong<=attempts or attempts<1:continue
        stale=value.get('revision')!=quiz['revision']
        records[key]={**value,'stale':stale,'correct':not stale and choice==quiz['answer']}
    return dict(records=records,total=len(CARDS),answered=sum(not v['stale'] for v in records.values()),
                correct=sum(v['correct'] for v in records.values()),review=sum(not v['correct'] for v in records.values()))


def answer(store, key, choice, revision):
    if key not in CARDS:raise ValueError('未知函数自测')
    quiz=CARDS[key]['quiz']
    if type(choice) is not int or not 0<=choice<len(quiz['options']):raise ValueError('选项编号无效')
    if revision!=quiz['revision']:raise RuntimeError('自测内容已更新，请刷新页面后重新作答')
    records=snapshot(store)['records']
    old=records.get(key,{})
    same=old.get('revision')==revision
    records[key]=dict(choice=choice,revision=revision,attempts=(old.get('attempts',0) if same else 0)+1,
                      wrong_attempts=(old.get('wrong_attempts',0) if same else 0)+int(choice!=quiz['answer']),stamp=time.time())
    # Only normalized learning data is written. Correctness is always derived from the current question.
    saved={k:{field:v[field] for field in ('choice','revision','attempts','wrong_attempts','stamp') if field in v} for k,v in records.items()}
    store.set_setting(SETTING,json.dumps(saved,ensure_ascii=False))
    return snapshot(store)


def validate_backup(value):
    if not isinstance(value,dict) or len(value)>len(CARDS):raise ValueError('函数自测记录格式无效')
    required={'choice','revision','attempts','wrong_attempts','stamp'}
    for key,row in value.items():
        if key not in CARDS or not isinstance(row,dict) or set(row)!=required:raise ValueError('函数自测项目无效')
        if type(row['choice']) is not int or not 0<=row['choice']<3:raise ValueError('函数自测选项无效')
        if not isinstance(row['revision'],str) or not re.fullmatch('[a-f0-9]{16}',row['revision']):raise ValueError('函数自测版本无效')
        if type(row['attempts']) is not int or type(row['wrong_attempts']) is not int or not 0<=row['wrong_attempts']<=row['attempts'] or row['attempts']<1:raise ValueError('函数自测次数无效')
        if type(row['stamp']) not in (int,float) or not math.isfinite(row['stamp']) or row['stamp']<0:raise ValueError('函数自测时间无效')
