# Vision Learning Hub · 视觉学习实验室

**当前版本：0.3.0，支持网页版与可选 VS Code 扩展。** 独立于 `VisionLearningStudio`，使用浏览器界面、Python 练习进程和 SQLite 学习记录。建设日期：2026-10-25。

VS Code 插件安装、使用与清除说明见 [仓库首页](../README.md)。

## 打开平台

双击本文件夹中的 **`启动学习平台.cmd`**。启动器会启动本地服务并打开浏览器，默认地址为 `http://127.0.0.1:8766`；端口占用时尝试后续端口。重复启动会复用相同学习空间的服务。

用完后双击 **`停止学习平台.cmd`**。关闭浏览器标签页不会自动结束后台服务。服务只监听本机地址。

首次克隆请按下方步骤创建 `.venv`、安装依赖并构建 `dist`，之后可使用启动脚本。**本版不是独立 EXE 安装包**；`.venv` 依赖本机的 Python 安装，不能直接搬到另一台电脑后保证可用。

## 已经实现

- **16 章学习路线**：Python/NumPy、OpenCV、几何与搜索、深度学习基础、YOLO 数据与后处理、Linux、嵌入式部署和综合项目。每章包含原理、适用情况、易错点、自查与笔记。
- **32 道可运行练习**：28 道 Python/OpenCV/经典算法题，其中新增 V01–V06 六道视觉基础题；另有 3 道 YOLO 数据与后处理题和 1 道离线日志解析题。
- **代码工作台**：手敲代码、自动保存、Tab 缩进、错误行定位、提示与参考实现、输入输出对照、历史报告。
- **两种检查**：运行一个样例用于调试；通过五组样例的正式验收才计入进度。修改自己或前置关卡的代码后，进度重新判断。
- **图像实验室**：灰度直方图、全局 / 局部 / Otsu 阈值、直方图均衡、高斯 / 中值 / 双边滤波、Sobel、Canny、HSV 与形态学；可调参数、查看中间图、上传图片，并比较阴影、噪声和同色背景下的表现。
- **24 份官方资料**：搜索、按阶段筛选、收藏与阅读任务；查阅外部资料需要联网。
- **本地记录**：课程与练习笔记、代码草稿、验收记录、收藏、备份恢复和代码项目导出。

## 当前边界

YOLO 部分能执行标签检查、letterbox 坐标还原和二分类 Precision/Recall 计算；**尚未接入 YOLO 模型训练、模型推理或完整 mAP 评价**。

Linux 与嵌入式部分有课程、资料、自查及一题离线日志练习；**尚未连接 WSL/Linux 终端、SSH、摄像头或开发板**。离线合成图验收不能代替实物项目测试。

练习在独立 Python 进程中运行，支持停止与 25 秒超时。它不是权限沙箱，具有当前用户的本机文件权限，只运行自己理解的练习代码。

## 建议从哪里开始

打开“学习路线” → **S00 从数组开始** → **P01 循环与筛选** → **P02 切片与统计**。

每次按“读约定 → 自己实现 → 运行一个样例 → 查看中间结果 → 多样例验收 → 写下理解”的顺序练习。不要把抄完参考代码等同于掌握。

详细操作见 [第一次使用与学习指南](docs/第一次使用与学习指南.md)。早期 [平台建设方案](docs/平台建设方案.md) 中的后续设想不代表当前全部实现。原 `content/sample_exercise.json` 是保留的设计样例，不参与实际判题。

## 数据与备份

默认数据目录为 `%LOCALAPPDATA%\VisionLearningHub`，通常是 `C:\Users\asus\AppData\Local\VisionLearningHub`。

- `learning.sqlite3`：草稿、笔记、历史与收藏。
- `runs/`：验收时的输入、代码请求和结果图片。
- `lab/`、`uploads/`、`previews/`：探索素材与预览。
- `exports/`：导出文件及恢复前的自动备份。
- `server.log`：启动与接口日志。

在“记录与设置”中下载 ZIP 备份。备份包含数据库和 `runs/`，不包括实验室临时图片与上传素材。恢复前会先备份当前状态；无效备份不会替换现有数据。ZIP 导入上限为 128 MB，解压总量上限为 512 MB。

## 开发与重建环境

技术栈：React + TypeScript + esbuild；FastAPI；SQLite；NumPy / OpenCV。静态资源全部本地提供，不依赖 CDN。

开发入口：`frontend/` 界面、`backend/courses.py` 章节、`learning/` 练习与验收、`content/resource_catalog.json` 资料。

在新电脑重新部署时，需要合适的 Python 3.12 和 Node.js；先创建环境、安装依赖并构建：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm ci
npm run check
npm run build
.\.venv\Scripts\python.exe launch.py
```

依赖锁定：`requirements.lock.txt` 与 `package-lock.json`。本次验证环境为 Windows、Python 3.12、OpenCV 4.13.0、NumPy 2.3.5，浏览器为本机 Chrome。

自动检查：

```powershell
.\.venv\Scripts\python.exe tests\test_platform.py
.\.venv\Scripts\python.exe tests\test_acceptance_v020.py
.\.venv\Scripts\python.exe tests\test_workspace.py
npm run check
npm run build
```

浏览器测试 `npm run test:browser` 需要先用 `VLH_DATA_ROOT` 指定独立测试目录、启动测试服务，并把 `VLH_TEST_URL` 指向该地址。它会修改测试学习记录，不能对正式学习空间执行。详情见 [验收记录](docs/验收记录.md)。
