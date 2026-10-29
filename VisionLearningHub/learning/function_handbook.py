"""Offline function teaching, separate from answers and grading state."""
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1]/'content/function_handbook.json').read_text(encoding='utf-8'))
CARDS = {card['id']: card for card in CATALOG['cards']}


def guide(key):
    entry = CATALOG['lessons'].get(key)
    return dict(entry, cards=[CARDS[k] for k in entry['cards']]) if entry else None


def markdown(key):
    item = guide(key)
    if not item:
        raise ValueError('此题没有基础函数示例')
    lines = ['# '+key+' 函数与场景', '', item['decision'], '',
             '先预测 → 在独立文件手敲 → 运行断言 → 只改一个参数 → 记录现象 → 回到基础题验收。', '',
             '示例只依赖 Python、OpenCV、NumPy，自带小输入，不读取个人文件，不会修改练习源码或通关状态。', '',
             '在 VS Code / PyCharm 中选择已安装这些库的解释器，打开一个 .py 文件运行；也可在本目录终端执行下列命令。', '',
             '缺依赖时在自己的虚拟环境运行：python -m pip install numpy opencv-python-headless', '',
             '不要同时安装多个提供 cv2 的 OpenCV 包；已有可用环境无需重复安装。', '',
             '讲解范围：当前课程核心函数与关键参数，不是库的全部重载。官方链接可能对应更新版本；示例测试版本见仓库验收记录。', '']
    for card in item['cards']:
        lines += ['## '+card['name'], '', '`'+card['signature']+'`', '',
                  '| 参数 | 含义 | 选择与限制 |', '| --- | --- | --- |']
        lines += ['| '+p['name']+' | '+p['meaning']+' | '+p['choice']+' |' for p in card['parameters']]
        for label,field in [('返回值','returns'),('适用场景','use'),('不适用/限制','avoid'),('常见错误','pitfall')]:
            lines += ['', '**'+label+'：** '+card[field]]
        lines += ['', '运行：`python '+card['id']+'.py`', '', '```python', card['example'].rstrip(), '```', '',
                  '**预期：** '+card['expect'], '', '**动手改一处：** '+card['experiment'], '',
                  '[官方函数资料]('+card['docs']+')', '']
        quiz=card['quiz']
        lines += ['### 场景与参数自测', '', quiz['question'], '']
        lines += ['- **'+chr(65+i)+'.** '+option['text'] for i,option in enumerate(quiz['options'])]
        lines += ['', '<details><summary>作答后查看解释</summary>', '', '正确选项：'+chr(65+quiz['answer']), '']
        lines += ['- **'+chr(65+i)+'.** '+option['explanation'] for i,option in enumerate(quiz['options'])]
        lines += ['', '</details>', '']
    lines += ['## 学完自问', '', item['question'], '', '在平台“笔记”记录输入、预测、实测和适用边界；阅读和示例通过不计基础题通关。', '']
    return '\n'.join(lines)


def write_examples(folder, key):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    item = guide(key)
    if not item:
        raise ValueError('此题没有基础函数示例')
    for card in item['cards']:
        (folder/(card['id']+'.py')).write_text(card['example'], encoding='utf-8')
    (folder/'README.md').write_text(markdown(key), encoding='utf-8')
