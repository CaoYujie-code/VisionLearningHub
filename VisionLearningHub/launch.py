"""Open the local platform with the bundled virtual environment. No system settings changed."""
import argparse
import ctypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

PROJECT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('VLH_DATA_ROOT', Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'VisionLearningHub'))
ROOT.mkdir(parents=True, exist_ok=True)
WORKSPACE = hashlib.sha256((str(PROJECT.resolve())+'|'+str(ROOT.resolve())).encode()).hexdigest()
STATE = ROOT / 'server.json'


def get_json(url):
    with urllib.request.urlopen(url, timeout=1) as response:
        return json.load(response)


def tell(message):
    if sys.stdout:
        print(message)
    else:
        ctypes.windll.user32.MessageBoxW(0, message, 'Vision 学习实验室', 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    if args.stop:
        if not STATE.exists():
            tell('没有找到由启动器管理的服务。'); return
        state = json.loads(STATE.read_text(encoding='utf-8'))
        try:
            health = get_json(state['url'] + '/api/health')
        except Exception:
            tell('学习平台服务已停止。'); return
        if health.get('instance') != state['instance'] or health.get('app') != 'vision-learning-hub':
            raise RuntimeError('服务标识不匹配，未停止其他程序。')
        request = urllib.request.Request(state['url'] + '/api/shutdown', data=b'{}', method='POST', headers={'X-VLH-Control':state['control']})
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
        tell('已通知学习平台停止服务。代码与笔记已保存在本机。'); return
    with (ROOT / 'launcher.lock').open('a+b') as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return
        try:
            for port in range(args.port, args.port + 10):
                url = 'http://127.0.0.1:' + str(port)
                try:
                    health = get_json(url + '/api/health')
                    if health.get('app') == 'vision-learning-hub' and health.get('workspace') == WORKSPACE:
                        if not args.no_browser:
                            webbrowser.open(url)
                        if sys.stdout: print(url)
                        return
                except Exception:
                    pass
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1', port)) == 0:
                        continue
                instance = secrets.token_hex(16); control = secrets.token_urlsafe(32)
                environment = os.environ.copy()
                environment.update(VLH_INSTANCE=instance, VLH_CONTROL=control, PYTHONUTF8='1')
                with (ROOT / 'server.log').open('ab') as log:
                    process = subprocess.Popen([sys.executable, str(PROJECT / 'app_server.py'), '--port', str(port)], cwd=PROJECT, env=environment,
                        stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                ready = False
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('服务启动失败，请查看日志：' + str(ROOT / 'server.log'))
                    try:
                        health = get_json(url + '/api/health')
                        if health.get('instance') == instance:
                            ready = True; break
                    except Exception:
                        pass
                    time.sleep(.15)
                if not ready:
                    process.terminate()
                    raise RuntimeError('启动超时，请查看日志：' + str(ROOT / 'server.log'))
                STATE.write_text(json.dumps(dict(url=url,pid=health['pid'],instance=instance,control=control)), encoding='utf-8')
                if not args.no_browser:
                    webbrowser.open(url)
                if sys.stdout: print(url)
                return
            raise RuntimeError('本机 8766–8775 端口均已占用。')
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        tell(str(error))
        sys.exit(1)
