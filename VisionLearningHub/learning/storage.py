import hashlib
import json
import os
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from .curriculum import BY_ID, LESSONS, COURSE_VERSION
from .project_catalog import PROJECT_IDS
from .project_runner import parse_files, materialize


def data_root():
    override=os.environ.get("VLH_DATA_ROOT")
    path=Path(override) if override else Path(os.environ.get("LOCALAPPDATA",Path.home()))/"VisionLearningHub"
    path.mkdir(parents=True,exist_ok=True)
    return path


def fingerprint(key,codes):
    selected={}
    def collect(name):
        if name in selected:return
        selected[name]=codes.get(name,"")
        for dep in (() if name in PROJECT_IDS else BY_ID[name]["prerequisites"]):collect(dep)
    collect(key)
    return hashlib.sha256(json.dumps([COURSE_VERSION,selected],sort_keys=True).encode()).hexdigest()


class Store:
    def __init__(self,root=None):
        self.root=Path(root) if root else data_root()
        self.root.mkdir(parents=True,exist_ok=True)
        self.connection=sqlite3.connect(self.root/"learning.sqlite3")
        version=self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0,1):
            self.connection.close()
            raise ValueError("学习数据库由更新版本创建，请使用对应版本打开")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY,code TEXT NOT NULL,note TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,lesson TEXT,stamp REAL,
                digest TEXT,verified INTEGER,passed INTEGER,report TEXT,code TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            PRAGMA user_version=1;
        """)
        for item in LESSONS:
            self.connection.execute("INSERT OR IGNORE INTO drafts(id,code) VALUES(?,?)",(item["id"],item["starter"]))
        self.connection.commit()

    def codes(self):
        return dict(self.connection.execute("SELECT id,code FROM drafts").fetchall())

    def draft(self,key):
        return self.connection.execute("SELECT code,note FROM drafts WHERE id=?",(key,)).fetchone()

    def save(self,key,code,note):
        self.connection.execute("UPDATE drafts SET code=?,note=? WHERE id=?",(code,note,key))
        self.connection.commit()

    def record(self,key,codes,response):
        self.connection.execute("INSERT INTO attempts(lesson,stamp,digest,verified,passed,report,code) VALUES(?,?,?,?,?,?,?)",
            (key,time.time(),fingerprint(key,codes),int(response.get("verify",False)),
             int(response.get("passed",False)),json.dumps(response,ensure_ascii=False),codes[key]))
        self.connection.commit()

    def passed(self,key,codes):
        row=self.connection.execute("SELECT passed FROM attempts WHERE lesson=? AND digest=? AND verified=1 ORDER BY id DESC LIMIT 1",
                                    (key,fingerprint(key,codes))).fetchone()
        return bool(row and row[0])

    def history(self,key):
        return self.connection.execute("SELECT stamp,verified,passed,report FROM attempts WHERE lesson=? ORDER BY id DESC LIMIT 20",(key,)).fetchall()

    def setting(self,key,default=None):
        row=self.connection.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return row[0] if row else default

    def set_setting(self,key,value):
        self.connection.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(key,value));self.connection.commit()

    def backup(self,path):
        path=Path(path).resolve()
        with tempfile.TemporaryDirectory(prefix=".vision-backup-",dir=path.parent) as folder:
            target=Path(folder)/"learning.sqlite3"
            other=sqlite3.connect(target)
            try:self.connection.backup(other)
            finally:other.close()
            pending=Path(folder)/"backup.zip"
            with zipfile.ZipFile(pending,"w",zipfile.ZIP_DEFLATED) as archive:
                archive.write(target,"learning.sqlite3")
                # 备份验收图像，保留代码、参数与结果的关联。
                runs=self.root/"runs"
                if runs.exists():
                    for file in runs.rglob("*"):
                        if file.is_file():archive.write(file,file.relative_to(self.root).as_posix())
            pending.replace(path)

    def restore(self,path):
        root=self.root.resolve()
        with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix=".restore-",dir=root) as folder:
            stage=Path(folder).resolve();seen=set()
            # 完整解压并检查 CRC 后才接触当前数据库和图片。
            for info in archive.infolist():
                name=info.filename.replace("\\","/");parts=PurePosixPath(name).parts
                if (PureWindowsPath(name).drive or name.startswith("/") or ".." in parts
                        or any(":" in p or p.endswith((" ",".")) for p in parts)):
                    raise ValueError("备份包含非法路径")
                if not parts or (name!="learning.sqlite3" and parts[0]!="runs"):
                    raise ValueError("备份包含未知内容")
                normalized="/".join(parts).casefold()
                if normalized in seen:raise ValueError("备份包含重复路径")
                seen.add(normalized)
                target=(stage/Path(*parts)).resolve()
                if not target.is_relative_to(stage):raise ValueError("备份路径越界")
                if info.is_dir():target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(info))
            db=stage/"learning.sqlite3"
            if not db.is_file():raise ValueError("备份中缺少学习数据库")
            check=sqlite3.connect(db)
            try:
                if check.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("数据库校验失败")
                version=check.execute("PRAGMA user_version").fetchone()[0]
                if version!=1:raise ValueError("备份版本暂不兼容")
                drafts=check.execute("SELECT id,code,note FROM drafts").fetchall()
                attempts=check.execute("SELECT id,lesson,stamp,digest,verified,passed,report,code FROM attempts").fetchall()
                settings=check.execute("SELECT key,value FROM settings").fetchall()
            finally:check.close()
            if any(not all(isinstance(value,str) for value in row) for row in drafts):
                raise ValueError("备份中的代码或笔记格式无效")
            if any(key not in BY_ID or len(code)>100000 or len(note)>32000 for key,code,note in drafts):
                raise ValueError("备份包含未知练习或过长的代码/笔记")
            if any(row[1] not in BY_ID or not isinstance(row[7],str) for row in attempts):
                raise ValueError("备份包含无效的练习记录")
            for key,code,note in drafts:
                if key in PROJECT_IDS:parse_files(code)
            for key,value in settings:
                if not isinstance(key,str) or not isinstance(value,str):
                    raise ValueError("设置格式无效")
                if not key.startswith('hub.'):continue
                setting=json.loads(value)
                if key=='hub.bookmarks':
                    if not isinstance(setting,list) or any(not isinstance(v,str) or len(v)>8 for v in setting):
                        raise ValueError("收藏格式无效")
                elif key.startswith('hub.course.'):
                    course_id=key[11:]
                    if (len(course_id)!=3 or not course_id.startswith('S') or not course_id[1:].isdigit() or not isinstance(setting,dict)
                        or not isinstance(setting.get('note',''),str) or len(setting.get('note',''))>32000
                        or not isinstance(setting.get('checks',[]),list)
                        or any(type(i) is not int or i<0 or i>=3 for i in setting.get('checks',[]))):
                        raise ValueError("课程笔记格式无效")
                else:raise ValueError("备份包含未知平台设置")
            known={row[0] for row in drafts}
            drafts.extend((item["id"],item["starter"],"") for item in LESSONS if item["id"] not in known)

            def relocate(value):
                if isinstance(value,list):return [relocate(v) for v in value]
                if not isinstance(value,dict):return value
                result={}
                for key,v in value.items():
                    if key in ("input","output","folder","image_path") and isinstance(v,str):
                        _,marker,suffix=v.replace("\\","/").partition("/runs/")
                        if marker:
                            candidate=(root/"runs"/suffix).resolve()
                            if not candidate.is_relative_to(root/"runs"):raise ValueError("记录中的图片路径无效")
                            v=str(candidate)
                    result[key]=relocate(v)
                return result

            attempts=[(*row[:6],json.dumps(relocate(json.loads(row[6])),ensure_ascii=False),row[7]) for row in attempts]
            incoming=stage/"runs";incoming.mkdir(exist_ok=True)
            for file in incoming.rglob("*.json"):
                if file.name in ("request.json","response.json"):
                    content=relocate(json.loads(file.read_text(encoding="utf-8")))
                    file.write_text(json.dumps(content,ensure_ascii=False),encoding="utf-8")
            current=root/"runs";previous=stage/"previous-runs"
            for target in (current,incoming,previous):
                if not target.resolve().is_relative_to(root):raise ValueError("学习记录目录路径无效")
            moved_old=False;moved_new=False
            try:
                # 事务未提交前发生任何错误，都回滚代码、进度以及实验图片。
                with self.connection:
                    self.connection.execute("BEGIN IMMEDIATE")
                    for table in ("drafts","attempts","settings"):
                        self.connection.execute("DELETE FROM "+table)
                    self.connection.executemany("INSERT INTO drafts(id,code,note) VALUES(?,?,?)",drafts)
                    self.connection.executemany("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)",attempts)
                    self.connection.executemany("INSERT INTO settings(key,value) VALUES(?,?)",settings)
                    if current.exists():current.rename(previous);moved_old=True
                    incoming.rename(current);moved_new=True
            except Exception:
                if moved_new:current.rename(incoming)
                if moved_old:previous.rename(current)
                raise

    def close(self):
        self.connection.close()


EXPORT_RUNNER = '''"""运行你写的 T14：python run_detector.py 图片.png"""
import json
import sys
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
def read_image(path):
    image = cv2.imdecode(np.fromfile(str(path),np.uint8),cv2.IMREAD_COLOR)
    if image is None: raise ValueError("无法读取图片")
    return image
def student(key,image,params):
    scope={"np":np,"cv2":cv2,"read_image":read_image,"student":student,"__name__":"student"}
    exec(compile((ROOT/"student"/(key+".py")).read_text(encoding="utf-8"),key+".py","exec"),scope)
    return scope["solve"](image,params)
if __name__=="__main__":
    if len(sys.argv)<2: raise SystemExit("用法：python run_detector.py 图片路径")
    path=Path(sys.argv[1]).resolve()
    image=read_image(path)
    params={"image_path":str(path),"lower":[30,35,15],"upper":[95,255,255],"kernel":3,"min_area":150}
    from exercises.T14 import solve
    result=solve(image,params)
    out=ROOT/"output";out.mkdir(exist_ok=True)
    cv2.imencode(".png",result["mask"])[1].tofile(str(out/"mask.png"))
    def convert(value):
        if isinstance(value,np.ndarray): return value.tolist()
        if isinstance(value,np.generic): return value.item()
        raise TypeError(str(type(value)))
    (out/"pieces.json").write_text(json.dumps(result["pieces"],default=convert,ensure_ascii=False,indent=2),encoding="utf-8")
    print("结果已保存到",out)
'''


def export_project(folder,codes,notes=None):
    from backend.workspace import native_code
    folder=Path(folder);(folder/"student").mkdir(parents=True,exist_ok=True)
    (folder/"exercises").mkdir(exist_ok=True)
    (folder/"exercises"/"__init__.py").write_text("",encoding="utf-8")
    for key,code in codes.items():
        if key in PROJECT_IDS:
            materialize(key,folder/"projects"/key,parse_files(code),include_holdout=True)
            continue
        (folder/"student"/(key+".py")).write_text(code,encoding="utf-8")
        (folder/"exercises"/(key+".py")).write_text(native_code(code),encoding="utf-8")
    (folder/"run_detector.py").write_text(EXPORT_RUNNER,encoding="utf-8")
    (folder/"requirements.txt").write_text("numpy\nopencv-python-headless>=4,<5\n",encoding="utf-8")
    (folder/"README.md").write_text(
        "# 我的 OpenCV 实训项目\n\nexercises/ 为普通 Python 模块；student/ 保留原始快照。未完成关卡保留 TODO。\n"
        "综合检测器依赖 T04、T05、T06、T07、T14。\n\n"
        "独立开发运行需要 Python，并安装 requirements.txt：\n\n"
        "    python -m pip install -r requirements.txt\n"
        "    python run_detector.py 图片.png\n\n"
        "平台内运行已经自带依赖，无需执行上述安装。自己的图片可能需要调整 HSV 和面积参数。\n",
        encoding="utf-8")
    if notes:(folder/"notes.json").write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding="utf-8")
