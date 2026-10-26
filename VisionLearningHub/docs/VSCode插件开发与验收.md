# VS Code 插件开发与验收

插件源码在 `extensions/vscode/`。它复用 `frontend/` 的课程、资料、图像实验与记录页面，通过 Webview 消息桥调用扩展管理的本机 Python 服务；代码编辑使用 VS Code TextDocument。

## 数据与执行约定

- 活动工程的 `.vision-learning/exercises/` 是代码事实来源，SQLite 保存快照、笔记和历史。
- 后端同步磁盘文件，忽略学习面板提交的旧代码；运行前扩展保存打开的练习文件，包括前置依赖。
- 正式验收在独立进程运行提交时的文件快照，普通 `from exercises.T04 import solve` 导入解析到同一份快照。
- 调试入口 `python -m learning.debug_runner` 直接导入磁盘文件，可在实际练习文件中打断点。
- 终端与调试不计通关；面板或测试资源管理器的多样例验收才计通关。
- 一个学习空间同一时间由一个扩展宿主管理服务。锁记录宿主 PID；失效宿主锁可重新获取。
- 服务只监听 `127.0.0.1`，每次会话和停止控制使用随机令牌。Webview 无任意地址请求能力，桥接接口限制在平台路由。
- 停用时停止所属服务、任务与调试；宿主异常结束时，Python 的父进程管道 EOF 触发退出。

## 原生编辑器与依赖

插件不强制依赖或安装其他扩展。基本文件编辑与验收可独立使用；Python / Pylance 提供补全，Microsoft Python Debugger 提供断点调试。

用户可指定 `visionLearning.pythonPath`。默认发现工程 `.venv`，再尝试 Python 扩展选定解释器及系统 Python。检查和安装依赖均指向该解释器；安装需确认，不改全局 PATH。

目前主要验收 Windows 桌面 VS Code。远程 SSH / WSL 支持需要独立验证，不能因使用 `extensionKind: workspace` 就视为已经通过。

## 清除与恢复

缓存、历史、全部学习记录三个范围均需要输入 `CLEAR`，后台再次验证范围与确认值。运行中的任务阻止清除。递归清理只允许当前数据目录下的固定子目录，并拒绝越界链接。

清除学习记录保留 `exercises/`。单题重置独立确认，在 `.vision-backups/` 保存原文件后写入模板。

恢复 ZIP 时先备份当前记录。IDE 模式将备份代码存到 `data/restored-code/`，继续以实际编辑文件计算进度，避免静默覆盖。旧备份指纹不匹配时显示为历史成绩。

## 本地开发与打包

在应用目录执行：

```powershell
npm ci
npm run check
npm run build
npm ci --prefix extensions/vscode
npm --prefix extensions/vscode run check
npm --prefix extensions/vscode test
npm --prefix extensions/vscode run package
```

打包脚本只复制 Python 源码、资料与前端构建产物，不包含 `.venv`、`node_modules`、学习数据库或用户图片。VSIX 位于外层仓库 `releases/`，不自动安装或发布。

## 隔离测试

```powershell
.\.venv\Scripts\python.exe tests\test_platform.py
.\.venv\Scripts\python.exe tests\test_acceptance_v020.py
.\.venv\Scripts\python.exe tests\test_workspace.py
.\.venv\Scripts\python.exe tests\run_browser.py --node node
.\.venv\Scripts\python.exe tests\run_vscode_host.py --code "C:\你的路径\Code.exe"
```

浏览器脚本使用本机 Chrome，路径见 `tests/browser.mjs`。宿主脚本解压本次 VSIX，使用独立用户目录、临时学习工程及 `--extensionDevelopmentPath`，不调用全局安装命令。基本宿主测试禁用其他已安装扩展，避免第三方扩展干扰。增加 `--with-debugger` 参数会在独立配置中启用本机已安装的 Microsoft Python 扩展，用实际断点和变量读取验证调试；仍不会安装扩展。

测试数据在忽略的 `.test-data/`，结果在 `validation/`。超时失败时需检查日志，并确认只清理本次测试宿主及其服务。正式代码和学习记录不参与测试。

## 发布与版本维护

GitHub Actions 验证类型、Python 回归、扩展核心规则并生成 VSIX artifact。真实 VS Code 宿主和本机 Chrome 的检查在本机执行，不冒充云端已验证。

扩展 `publisher` 字段只是安装包标识。当前未配置 Marketplace 发布者身份，也未上架。正式上架前需要发布者账号、发布凭据与单独的发布审核；无需上架即可自主安装或卸载 VSIX。
