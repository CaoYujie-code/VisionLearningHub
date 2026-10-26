# Vision Learning Hub · 视觉学习实验室

从像素和 NumPy 开始，学习 OpenCV、经典视觉算法、YOLO 数据处理与 Linux / 嵌入式基础。通过课程阅读、手敲代码、图像对照和多样例验收积累自己的视觉工程。

**0.3.0：保留网页版，新增可选安装的 VS Code 扩展。** 插件提供学习面板，代码使用 VS Code 原生编辑器；课程与基础实验可离线使用，官方资料链接需要联网。

## 能做什么

| 模块 | 当前能力 |
| --- | --- |
| 学习路线 | 16 章，包含原理、适用情况、易错点、自查与笔记 |
| 编程练习 | 32 道练习，每道 5 组正式验收样例；修改代码和依赖后重新判断进度 |
| 图像实验室 | 12 种 OpenCV 方法、4 类内置场景、自定义图片与参数对照 |
| 学习资料 | 24 份官方资料索引，支持搜索、阶段筛选和收藏 |
| VS Code | 侧栏路线、原生 Python 文件、终端运行、Python 断点调试、测试资源管理器 |
| 本地记录 | SQLite 笔记、历史、收藏、代码快照，ZIP 备份恢复 |
| 清除功能 | 分别清除实验缓存、验收历史、全部学习记录；保留源码；单题重置先备份代码 |

YOLO 目前提供标签、坐标与指标练习，尚未接入真实训练、模型推理及完整 mAP 评价。Linux / 嵌入式包含课程与离线日志练习，尚未连接开发板或终端。VS Code 插件不会自动安装到你的编辑器。

## 仓库结构

```text
VisionLearningHub/                 # 本仓库根目录，唯一的 .git 在这里
├─ README.md
├─ .github/workflows/check.yml
└─ VisionLearningHub/              # 应用工程，普通目录
   ├─ backend/                    # API、图像实验和文件工作区
   ├─ frontend/                   # 网页 / VS Code 共用学习界面
   ├─ learning/                   # 课程练习、判题、存储和调试入口
   ├─ extensions/vscode/          # 可选 VS Code 扩展源码
   ├─ content/                    # 官方资料索引
   ├─ docs/
   └─ tests/
```

## 方式一：网页版

需要 Python 3.12 和 Node.js 22。下面从仓库根目录执行，Windows PowerShell 示例：

```powershell
cd VisionLearningHub
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm ci
npm run check
npm run build
.\.venv\Scripts\python.exe launch.py
```

配置好后，双击工程中的 `启动学习平台.cmd`；结束时使用 `停止学习平台.cmd`。关闭浏览器不等于停止网页版服务。虚拟环境不随仓库提交，移动目录后建议重建；不要依赖另一台电脑复制来的 `.venv`。

## 方式二：VS Code 扩展

### 安装与卸载

从维护者提供的安装包取得 `vision-learning-hub-0.3.0.vsix`，或按下文自行构建。VS Code → 扩展 → 右上角 `…` → **从 VSIX 安装**，由你决定是否安装。当前版本未发布到 Visual Studio Marketplace，不能承诺在商店中搜索得到。

禁用和卸载使用 VS Code 扩展面板的标准操作，按编辑器提示重载窗口。扩展停用时结束自身的 Python 服务；异常退出时通过父进程管道关闭服务。代码和学习记录保留，卸载前可主动备份或清除。

### 首次使用

1. 在桌面 VS Code 中打开一个可信任的本地文件夹作为学习工程。
2. 为该工程创建 Python 3.12 虚拟环境并安装项目 `requirements.lock.txt`。也可以使用已有的兼容环境。
3. 打开左侧“视觉学习”，执行 **Vision: Python 环境设置与检查**，需要时选择解释器。安装依赖按钮会展示目标解释器，确认后才运行 pip。
4. 从课程选择练习，点击“打开代码文件”。写在 `.vision-learning/exercises/*.py` 中的是真实源码。
5. “终端运行”用于探索；“断点调试”需要自行安装 Microsoft Python Debugger（`ms-python.debugpy`）。建议同时安装 Python 与 Pylance 获得补全。
6. 点击“多样例验收”，或使用 VS Code 测试资源管理器。执行前保存练习文件，结果绑定保存后的代码快照。

解释器可通过 `visionLearning.pythonPath` 指定。扩展的终端任务、调试配置和验收服务使用同一个解释器。未指定时先发现工程 `.venv`，再尝试 Python 扩展选择的环境与系统 Python。

### 学习记录与清除范围

插件数据属于当前工程，保存在 `<打开的工程>/.vision-learning/`：

| 路径 | 用途 |
| --- | --- |
| `exercises/` | 学生代码，清除学习记录不会删除 |
| `data/learning.sqlite3` | 笔记、收藏、验收历史与代码快照 |
| `data/runs/` | 验收样例和结果图 |
| `data/restored-code/` | 恢复旧备份时暂存的代码，供手动比较 |
| `.vision-backups/` | 重置单题之前保存的原代码 |

通过“记录与设置”或 **Vision: 清除学习记录或缓存** 操作，输入 `CLEAR` 才执行：

- **实验缓存**：删除实验图片、上传图片和可重新生成的预览，保留进度。
- **验收历史**：删除历史与运行图片，通关归零，保留笔记、收藏和源码。
- **全部学习记录**：同时清除笔记、收藏、图片以及当前数据目录中的导出备份。先把需要的备份导出到其他位置。源码与单题重置备份保留。
- **重置当前练习**：另一个独立命令，经确认后把原代码备份，再恢复 TODO 模板。

旧网页版 ZIP 备份可在插件中恢复。插件恢复笔记和历史，但将备份代码另存到 `data/restored-code/`，不覆盖正在编辑的文件；代码不同的历史成绩显示为旧版本。网页与插件默认使用不同数据空间，不自动共享数据库。

## 构建 VSIX

先完成前端构建，再在应用目录执行：

```powershell
npm ci --prefix extensions/vscode
npm --prefix extensions/vscode run check
npm --prefix extensions/vscode test
npm --prefix extensions/vscode run package
```

安装包输出到仓库根目录 `releases/`。构建不会调用 VS Code 安装命令，也不会发布到扩展市场。VSIX 包含界面和 Python 业务源码，不包含 Python 解释器、虚拟环境或 GPU 依赖。

## 开发与验证

```powershell
# 在内层应用目录执行；测试使用临时数据空间
.\.venv\Scripts\python.exe tests\test_platform.py
.\.venv\Scripts\python.exe tests\test_acceptance_v020.py
.\.venv\Scripts\python.exe tests\test_workspace.py
npm run check
npm run build
npm --prefix extensions/vscode test
```

浏览器测试会修改学习记录，应只针对独立测试服务运行。VS Code 集成测试入口在 `extensions/vscode/test/host.cjs`，必须使用独立用户目录与测试工作区；参阅 [插件开发与验收](VisionLearningHub/docs/VSCode插件开发与验收.md)。

平台代码仅提供课程与运行组织，练习使用 OpenCV / NumPy 官方 API；新工程的组合题采用普通 Python 模块导入。旧网页版的辅助调用暂保留兼容。当前依赖使用 headless OpenCV，通过面板看图；需要 `cv2.imshow` 时应在独立学习环境中改用对应 GUI 包，不能同时安装多个提供 `cv2` 的包。

学生代码按当前用户权限运行，进程隔离和超时不是权限沙箱。请运行自己理解的代码。本版本未完成 Marketplace 发布、独立 EXE 或实物设备验收。

资料：[首次学习指南](VisionLearningHub/docs/第一次使用与学习指南.md) · [官方资料导航](VisionLearningHub/docs/官方学习资料导航.md) · [版本验收](VisionLearningHub/docs/验收记录-0.3.0.md)
