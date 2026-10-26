"""File-backed exercises for the optional VS Code client. No visual algorithms here."""
import os
from pathlib import Path
import re

from learning.curriculum import LESSONS, BY_ID
from learning.project_catalog import PROJECT_IDS
from learning.project_runner import materialize, load_sources, serialize, parse_files, write_sources


def native_code(code):
    """Migrate old teaching helpers to visible standard imports / OpenCV calls."""
    code = code.replace('read_image(params["image_path"])',
                        'cv2.imdecode(np.fromfile(params["image_path"], np.uint8), cv2.IMREAD_COLOR)')
    dependencies = sorted(set(re.findall(r'student\([\"\']([A-Z]\d{2})[\"\']\s*,', code)))
    for key in dependencies:
        code = re.sub(r'student\([\"\']' + key + r'[\"\']\s*,\s*', key.lower() + '(', code)
    if dependencies:
        code = '\n'.join(f'from exercises.{key} import solve as {key.lower()}' for key in dependencies) + '\n' + code
    return code


class Workspace:
    def __init__(self, folder):
        self.root = Path(folder).resolve()
        self.exercises = self.root / 'exercises'

    def file(self, key):
        if key not in BY_ID:
            raise ValueError('未知练习')
        path = self.root / 'projects' / key / 'main.py' if key in PROJECT_IDS else self.exercises / (key + '.py')
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            raise ValueError('练习文件不能链接到学习工程外部')
        return path

    def initialize(self, store):
        self.exercises.mkdir(parents=True, exist_ok=True)
        if not self.exercises.resolve().is_relative_to(self.root):
            raise ValueError('练习目录超出学习工程')
        (self.exercises / '__init__.py').touch(exist_ok=True)
        for lesson in LESSONS:
            if lesson['id'] in PROJECT_IDS:
                project=self.root/'projects'/lesson['id']
                if not project.resolve().is_relative_to(self.root):raise ValueError('项目目录超出学习空间')
                code,_=store.draft(lesson['id'])
                materialize(lesson['id'],project,parse_files(code))
                continue
            file = self.file(lesson['id'])
            if not file.exists():
                code, _ = store.draft(lesson['id'])
                with file.open('x', encoding='utf-8') as stream:
                    stream.write(native_code(code))
        self.sync(store)

    def sync(self, store):
        for lesson in LESSONS:
            key = lesson['id']; file = self.file(key)
            if key in PROJECT_IDS:
                code=serialize(load_sources(file.parent))
            elif file.exists():
                if file.stat().st_size > 400000:
                    raise ValueError(f'{key} 代码文件过大')
                code = file.read_text(encoding='utf-8-sig')
            else:
                code = f"raise FileNotFoundError('请恢复 exercises/{key}.py，或重置本练习')\n"
            old, note = store.draft(key)
            if old != code:
                store.save(key, code, note)

    def replace(self, key, code):
        if key in PROJECT_IDS:
            write_sources(self.file(key).parent,parse_files(code),overwrite=True)
            return
        file = self.file(key)
        temporary = file.with_suffix('.py.tmp')
        temporary.write_text(code, encoding='utf-8')
        os.replace(temporary, file)


def lesson_outline(item):
    result = {k:v for k,v in item.items() if k not in ('reference', 'starter')}
    if item['id'] == 'T01':
        result['knowledge'] = '图像是 NumPy 数组，shape 为高、宽、通道。image[y,x] 先行后列。使用 np.fromfile 和 cv2.imdecode 读取中文路径图片，返回 None 时应报告读图失败。正常彩色图片为 uint8，通道顺序是 BGR。'
        result['hints'] = ['image = cv2.imdecode(np.fromfile(params["image_path"], np.uint8), cv2.IMREAD_COLOR)。', '检查 image is None，再读取 shape 和 image[0,0].tolist()。']
    if item['id'] in ('T10', 'T14', 'A05'):
        result['knowledge'] = result['knowledge'].replace('student(id,image,params) 只运行你保存的实现；', '使用 from exercises.T04 import solve as t04 等普通模块导入组合自己的函数；')
        result['contract'] = result['contract'].replace("调用 student('T09', image, child_params)", '从 exercises.T09 导入 solve，并用 image 和 child_params 调用')
        result['hints'] = [h.replace("student('A04', image, {'box_a':..., 'box_b':...}) 调用你自己的上一关。", 'from exercises.A04 import solve as iou；用 iou(image, 参数字典) 调用自己的上一关。') for h in result['hints']]
        result['hints'] += ['组合题使用普通 Python 导入；依赖文件也在 exercises/，可一起打断点。']
    return result
