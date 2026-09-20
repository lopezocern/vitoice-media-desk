# MediaDesk 媒体工作台 — 工作空间交接说明

> 本目录（`G:\Code\vitoice_media_desk`）即新工作空间根。虚拟环境 `.venv` 保留在此、无需迁移。

## 一、如何运行（桌面客户端，阶段一）

```powershell
# 首次：已建好 .venv（Python 3.12 + PySide6 6.11），无需重建
.\.venv\Scripts\python.exe main.py
# 无头自检（验证界面/配置/命令构建，不执行真实压缩）
.\.venv\Scripts\python.exe tests\smoke_test.py   # 期望：PASS 20 / FAIL 0
```

## 二、目录结构

| 路径 | 说明 |
|------|------|
| `main.py` | 桌面客户端入口 |
| `app/` | 桌面客户端源码（config / env / ffmpeg_runner / task / state / ui） |
| `tests/` | 自检脚本（无头 offscreen） |
| `docs/media-desk-prd/` | 需求文档（`media-desk-prd.html`，含可交互原型） |
| `legacy_scripts/` | 原始脚本归档（自 `G:\Code\pythonProject` 复制，已排除 venv/缓存） |

## 三、原始脚本功能核对（已归档至 `legacy_scripts`）

| 原始脚本 | 功能 | 桌面台状态 |
|----------|------|-----------|
| `video_music/FFmpeg_fast.py` | 大文件压缩（GPU） | **压缩 · 阶段一已实现** |
| `video_music/FFmpeg_cut.py` | 按时间段切割 | **切割 · 阶段二已实现** |
| `video_music/FFmpeg_Splicing.py` | 视频拼接 | **拼接 · 阶段二已实现** |
| `video_music/mp4towebm.py` | 格式转码 | **格式转换 · 阶段二已实现** |
| `file_clean/rename_pypinyin.py` | 中文名加拼音前缀 | **文件整理 · 阶段二已实现**（含垃圾清理+干跑） |
| `video_music/video_compare_glm.py` | 视频内容对比（GLM） | 未规划 |
| `file_clean/compare_pic.py` | 图片对比 | 未规划 |
| `AI_TTS/edge-tts.py`、`chat.py` | 文字转语音 | 未规划 |
| `auto_ui/auto_press.py`、`auto_test.py` | 自动化脚本 | 未纳入桌面台 |
| `tele_tools/telegram-bot.py`、`tele_group.py` | Telegram 机器人 | 未纳入桌面台 |
| `share/`、`wp-auto/`、`算法/` | 工具脚本与算法练习 | 归档 |
| `recycle_bin_cleaner.py` | 回收站清理 | 独立工具（未纳入） |

## 四、阶段一已实现与已知限制（重要）

- **点击这里：** 桌面壳层（顶栏/可折叠侧边栏/底部任务栏）、视频压缩（多文件拖拽/参数/并发队列/实时进度）、设置、配置持久化、GPU 检测回退。
- 关键限制：这个开发环境下配的 FFmpeg 是**精简裁剪版**——只有 `libx264` 编码器、无 `libx265`、无 `lavfi` 虚拟输入。因此：
  1. 桌面台软件编码统一用 **libx264**（比预案的 libx265 更通用）；
  2. 本环境**无法本地生成测试视频**做真实压测，压缩端到端需在装有完整 FFmpeg 的机器验证；
  3. **打包发布必须随附完整版 FFmpeg**（含 libx265/h264/hevc_nvenc），阶段二多格式转码强依赖它。`ffmpeg_path` 配置已预留，可在「全局设置 → FFmpeg 路径」指定随附路径。

## 五、敏感文件警告（务请注意）

- `legacy_scripts/tele_tools/.env` 含 Telegram 机器人等凭据。
- 切勿提交到任何版本库、或随工程外发。若需共享工程，应先删除该文件。

## 六、待办

1. 【剩余真机验证】在真实用户机器上按 `docs/real-machine-verification-checklist.md` 走一遍（gui 交互、真实素材、多核性能）。
2. 音视频转文字：未纳入本轮（成本在模型体积与打包），保留位置、优先级待定。

## 七、最近进度（2026-09-01）

- **界面浅色打磨还原（按设计图确认后实施）**：
  - 配色主色 `#5B66F0`→`#4f5bd5`，配套 `#eef0fe`/`#e3e6fd` 两档浅色用于 active/悬停；卡片白底+微阴影，内容区 `#eef1f8` 撑起主次。
  - 侧边导航图标化：`app/ui/icons.py` 用 QPainter 手绘线性图标（不依赖 QtSvg，绿色版零额外插件），划分为「工作台 / 系统」两组；选中态图标随状态换品牌色。
  - 概览页重构：环境状态条（绿点 + FFmpeg/GPU/编码器徽标）+ 3×2 模块网格（每卡图标 + 彩色状态徽标）。
  - 顶部标题栏加品牌「M」图标 + MediaDesk 副标；底部状态栏分区化（运行中/完成/失败计数着色 + 环境提示）。
  - 控件精修：圆角 8→9/12px、悬停描边变主色、按压微反馈、进度条按状态着色（运行/完成/失败/等待）。
  - 验证：`smoke_test` 保持 **PASS 67 / FAIL 0**；新增 `tests/ui_build_check.py` 无头实例化主窗口遍历全部页面 PASS，并输出界面截图至 `docs/ui-design/shots/`。
  - 设计图存档：`docs/ui-design/ui-redesign-mockup.html`（用户确认的浅色微调方向）。
- **高保真交互原型（HTML/CSS/JS，独立存档）**：`docs/prototype/mediadesk/` 7 页 SPA（总览/压缩/切割/拼接/转换/整理/设置），hash 路由、任务进度模拟、拖拽导入、参数联动；`design-contract.md` 定令牌与壳层一致，未来正式功能迭代以此为对齐基准。
- **UI 交互落地收尾（对齐设计契约，2026-09-01）**：
  - 总览页模块卡可点击跳转：`overview.py` 的 `ModuleCard` 增加 `clicked` 信号与鼠标按下/抬起判定，`OverviewPage.module_activated` 经 `MainWindow._activate_module` 联动侧边栏切换（对应契约「卡片点击→导航」）。
  - 切割时间段弹窗补实时反馈：`cut.py` 的 `CutDialog` 每行新增时长列（随输入实时刷新 HH:MM:SS），底部汇总「N 段 · 总时长」，无效段标「存在无效时间段」，行改为 3 元组并同步 `_accept` 解包。
  - 验证：`smoke_test` 仍 **PASS 67/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（6 张卡点击各发出正确 kind、弹窗时长 1:30+0:45=2:15、非法/空档正确提示）PASS。
- **UI 原生控件精修 + 无边框标题栏（对齐原型，消除“两个头/下拉无字/按钮最丑”，2026-09-01）**：
  - `styles.py`：补 `QComboBox QAbstractItemView` 弹层 QSS（白底 + 灰字 + 选中 `#4f5bd5` 高亮，解决“下拉看不到文字”）；下拉/数值框箭头用 border 三角（免外链资源）；`QToolTip` 白底圆角；`QDialog QMessageBox` 背景统一；通用 `QPushButton` 基线样式（未命名按钮也精修）；`WinBtn/WinBtnClose/QSizeGrip` 样式。
  - `main_window.py`：改为无边框自绘标题栏 `_TitleBar`（空白/文字区拖动、双击最大化/还原），右上角加 最小化/最大化/关闭 按钮；`_toggle_max` 用 `availableGeometry` 避免贴住任务栏；底部状态栏加 `QSizeGrip` 角缩放。
  - 验证：`smoke_test` BEGIN **PASS 67/FAIL 0**；`ui_build_check` UI-BUILD-OK，全部 7 页可切换。
- **深色模式适配 + 参数区表单化重排（用户真机反馈“大黑框/文字看不清”，2026-09-01）**：
  - 根因：系统深色模式下 QSS 未覆盖的原生控件（任务列表 viewport 容器、QMessageBox、QMenu 等）取系统深色 palette → 黑框；上轮加的 `QDialog QWidget{background:#fff}` 过宽把消息框子控件刷成白底，深色 palette 文字为白 → 白底白字。
  - `main.py` 新增 `_apply_light_palette()`：全局强制浅色 QPalette（Window/Base/Text/Button/ToolTip/Placeholder/Disabled 全组），任何深色系统下渲染一致。
  - `styles.py`：删除过宽 `QDialog QWidget` 规则，改为 `QDialog{background:#fff} + QDialog QLabel{color}`；新增 QMenu/QCheckBox/`QScrollArea>QWidget>QWidget{background:transparent}`（修复黑框透白）/`FormLbl`/`EmptyHint` 样式；通用 QPushButton 补 disabled 态。
  - 参数区表单化：`compression.py`/`cut.py`/`convert.py`/`concat.py` 参数区重排为 `QFormLayout` 卡片（标签列对齐、? 帮助归位到控件旁、输出目录并入卡片），`widgets.py` 新增 `form_label()` 助手；交互逻辑/信号/配置读写零改动。
  - 空态引导：4 个功能页任务列表新增 `EmptyHint`（居中“暂无文件…”），随添加/移除自动显隐。
  - 验证：AST 全通过；`smoke_test` **PASS 67/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（palette 生效、4 页空态提示初始显示、添加文件后隐藏/移除后恢复）PASS。
- **硬件加速真 bug 修复 + 弹窗样式 + 压缩页设计还原（2026-09-01）**：
  - **GPU 没生效根因**：`convert.py` 两处访问不存在的 `env.nvenc` 属性（实际是 `env.gpu_encoders`）→ 勾选 GPU 后点「开始转换」抛 `AttributeError` 被 Qt 吞掉，任务静默失败。已改用 `env.gpu_encoders` + `env.encoder`（尊重全局开关）；`_on_gpu_toggled` 的回退提示同步修复。
  - `main_window.py` 设置页 GPU 开关：从只落库改为 落库 + `state.start_env_probe()` 立即重探测，顶栏状态/总览/压缩页编码器即时联动。
  - `styles.py`：`QMessageBox` 按钮（Ghost 风格白底描边、min-width 72、hover 主色、default 高亮）与正文 13.5px；新增 `Pill` 胶囊（编码器标签）、`SegBox/SegBtn` 分段选择器、`SectionDot` 段落竖条、`DropBox/DropBig/DropSmall` 两行拖拽区 QSS；任务卡圆角 12/进度条圆角 999/内边距 11×14。
  - `widgets.py`：新增 `Segmented`（互斥分段选择器，API 对齐 QComboBox 的 currentData/setCurrentData/currentChanged）与 `section_title()`（主色竖条 + 标题）；TaskRow 内边距 11×14、间距 14、pct 44px 右对齐、进度条 7px 胶囊形 + 运行/完成态渐变（`#4f5bd5→#7a5ce0` / `#2f9e54→#36b061`）。
  - `compression.py` 按设计稿重排：页面头加副标题「多文件拖入，硬件加速，实时进度」；拖拽区改两行 `_DropBox`（大字 13.5 + 小字 12，整块可点击=添加文件，hover 主色虚线）；任务列表/压缩参数段落标题带主色竖条；速度档位由下拉改分段选择器（超快|平衡|快速）；编码器显示改胶囊；底部改「左统计 + 右 停止本轮/追加文件(ghost)/开始压缩(primary)」。
  - 验证：AST OK；`smoke_test` **PASS 67/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（EnvProbe 属性、Segmented 取值切换、转换页 GPU 勾选+_start 分支、设置页 `_on_gpu_toggled` 存在）PASS。
- **高级参数积压 + 箭头方块 + 硬编开关联动修复（2026-09-01）**：
  - **积压**：`compression.py` 页面主体改为整体 `QScrollArea`（`#PageScroll` 透明无边框），任务列表给最小高 240；高级参数展开后页面变长整体滚动，不再挤压任务列表；拖拽经 viewport 事件过滤器继续生效；底部操作条固定在滚动区外。
  - **箭头方块**：删除 QSS 里用 border 画三角的 `QComboBox::down-arrow` 与 `QSpinBox::up/down-arrow` 规则（Qt QSS 不支持该技巧，渲染成方块），改回 Qt 默认箭头绘制；drop-down/按钮区仍保持透明。
  - **硬编开关“依然有问题”根因**：`probe_env()` 之前在 `gpu_enabled=False` 时干脆不检测硬编列表（返回空），切换开关必须重跑 3 个子进程探测且无反馈。现改为探测与开关解耦（总是检测 `gpu_encoders`），`encoder`/`label` 动态读开关；设置页 `_on_gpu_toggled` 落库后直接 `env_changed.emit()` 同步广播，顶栏/总览/压缩页胶囊即时刷新、零延迟。转换页 GPU 复选框初始值改为读全局 `gpu_enabled`，与会话一致。
  - 验证：AST OK；`smoke_test` **PASS 67/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（开关切换 encoder/label 即时变化、滚动结构、GPU 同步、设置页广播）PASS。
- **硬编“没生效”根因修复（选错 ffmpeg 二进制）+ ? 即时提示（2026-09-01）**：
  - **根因**：本机有 RTX 4070 SUPER，但 PATH 首位是 TRAE 自带的精简版 ffmpeg（`e:\TRAE SOLO CN\...\ffmpeg.exe`，不含 nvenc），应用按 `shutil.which` 只取 PATH 第一个 → `gpu_encoders` 恒为空 → 无论开关怎么切顶栏都是「硬件加速未启用·软件编码」。`D:\FFmpeg\bin\ffmpeg.exe`（完整版，含 hevc/h264/av1_nvenc）排在后面从未被使用。
  - `env.py` 重写候选解析：`_path_ffmpeg_candidates()` 按 PATH 顺序枚举全部 ffmpeg.exe（去重）；`probe_env()` 逐个验证 `-version` 后**优先选中首个带 NVENC 的完整版**，选中的目录缓存为模块级 `_resolved_dir`，`ffmpeg_exe()`/`ffprobe_exe()` 从该目录取同一套二进制（手动手册路径 > 随包 ffmpeg/bin > 探测选中 > PATH 首个，符合项目路径优先级约束）；`EnvProbe` 新增 `ffmpeg_path` 字段供设置页展示。
  - 环境标签三态：`硬件加速可用 · hevc_nvenc` / `硬件加速已开启 · 未检测到 NVENC · 软件编码 libx264` / `硬件加速已关闭 · 软件编码 libx264`（旧文案把“未检测到硬编”和“开关关闭”混为一谈）；状态栏 EnvHint 同步三态。
  - 设置页：FFmpeg 卡新增「当前使用：<实际路径>」行；GPU 卡新增检测状态行（绿：已检测到 NVENC…；黄：当前 FFmpeg 不含 NVENC 硬编，可装完整版并在上方指定路径）；均随 env_changed 即时刷新。
  - `widgets.py` `HelpLabel`：`enterEvent` 直接 `QToolTip.showText`，悬停**立即**弹出说明（16px 小目标 + 系统悬停延迟是“放上去没有说明”的原因）；修复 `QToolTip` 应从 QtWidgets 导入的 ImportError。
  - 测试修正：`smoke_test` 的“默认编码器为 libx264”改为确定性两态断言（GPU 关→libx264；GPU 开且硬编可用→nvenc，finally 还原配置）；修复本机 `config.json` 的 UTF-8 BOM（PowerShell 写入导致应用 json.loads 失败回退默认值）。
  - 验证：本机实测 `probe_env()` 选中 `D:\FFmpeg\bin\ffmpeg.exe`、检出 `hevc_nvenc/h264_nvenc`、ffprobe 同目录联动；开关切换 encoder/label 即时变化；**真实 hevc_nvenc 硬件转码端到端 PASS**（ffprobe 确认输出 hevc）；`smoke_test` **PASS 68/FAIL 0**；`ui_build_check` UI-BUILD-OK。
- **恢复随包 FFmpeg · 即装即用回归（2026-09-01）**：
  - 用户指出“应使用包本体，不该去找安装的”。核查发现开发机 `ffmpeg/` 目录曾被清理（`Test-Path` 为 False），导致探测回落到 PATH 并选中 TRAE 精简版——上一条“选错二进制”问题的环境面根源。
  - 从 `release/MediaDesk_绿色版_v0.1.zip` 解出随包 `ffmpeg/bin/{ffmpeg,ffprobe,LICENSE}`（gyan essentials 9.0.1，实测含 hevc/h264/av1_nvenc）恢复到项目根。
  - 路径优先级不变且验证生效：手动配置 > 随包 `ffmpeg/bin`（现生效）> PATH 内 NVENC 优先完整版 > PATH 首个；随包存在时**不再扫描 PATH**，绿色版与开发态行为一致。
  - `.gitignore` 补 `ffmpeg/`、`release/`（196MB 二进制不入库，由 `scripts/fetch_ffmpeg.py` 按需生成）。
  - 验证：实测 `probe_env()` 选中 `G:\Code\vitoice_media_desk\ffmpeg\bin\ffmpeg.exe` 且检出 NVENC；`smoke_test` **PASS 68/FAIL 0**；`ui_build_check` UI-BUILD-OK。
- **切割/拼接/转换三页统一设计语言 + 分段控件缺陷修复（2026-09-01）**：
  - **公共组件下沉 `widgets.py`**：`DropBox`（两行拖拽区，整块可点击）、`page_head()`（标题+副标题）由压缩页本地实现提升为共享组件，删除 `compression.py` 中的 `_DropBox` 重复定义与 `styles.py` 中无人使用的 `QLabel#DropZone` 死样式。
  - **三页批量套用**（cut/concat/convert 与压缩页同构）：页面头（标题+灰色副标题）、两行拖拽区（点击=添加文件）、段落竖条标题、任务列表最小高 240、**整页 `#PageScroll` 滚动**（参数全展开不积压，拖拽改走 viewport 事件过滤器）、底部操作条（左统计+右「停止/追加(Ghost)/开始(Primary)」）。
  - **速度/画质下拉 → `Segmented` 分段选择器**：cut/concat 的重编码速度（超快|平衡|快速，默认快速）、convert 的画质（高画质|平衡|低体积，默认平衡），与压缩页档位一致。
  - **修复 `Segmented.setCurrentData` 不发射信号**（此前程序化切换不触发 CRF 联动，行为校验抓出）。
  - **修复两页初始态缺陷**：cut 页标签写「精确重编码（默认）」但实际默认选中流复制 → 改为默认 reencode（与标签一致）；cut/concat 均补 `_on_mode_changed()` 初始调用（此前 copy 模式下 speed/crf 仍可编辑）；concat/convert 补 `_on_od_changed()` 初始调用（默认同源目录时目录框应禁用）。
  - `main.py` 删除 Qt6 下已弃用的 `AA_EnableHighDpiScaling`（Qt6 默认启用，仅产生 DeprecationWarning）。
  - 验证：AST OK；`smoke_test` **PASS 68/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（三页滚动结构/拖拽区/空态/目录行初始禁用、cut 与 concat 的 Segmented 取值+CRF 联动+模式切换禁用链、convert 画质分段+仅提取音频禁用链）PASS。
- **压缩页硬件加速快捷开关 + 编码器选择框（2026-09-01）**：
  - 「压缩参数」卡新增「硬件加速」行：`QCheckBox`（开启硬件加速）+ `QComboBox`（自动（推荐）/ 已检出的 NVENC 编码器），与「编码器」胶囊行相邻，一屏完成 GPU 开关与选型。
  - **开关 = 全局 `gpu_enabled`**：与设置页同一机制（落库 + `env_changed` 广播），压缩页/设置页/转换页三处勾选态互相同步（`blockSignals` 防环），顶栏/总览即时联动。
  - **选择框**：`_effective_encoder()` 综合开关+选择计算实际编码器（auto=hevc 优先序 / 指定 nvenc / 关=libx264）；选择持久化到新配置键 `gpu_encoder`，环境变化后失效选择自动重置回 auto；无硬编或开关关闭时选择框禁用、胶囊显示 libx264。
  - `_start` 改用 `_effective_encoder()`（原来只读 `env.encoder`，无法响应页面选择）。
  - 验证：AST OK；`smoke_test` **PASS 68/FAIL 0**；`ui_build_check` UI-BUILD-OK；offscreen 行为校验（初始读全局、开关落库+三页同步、选 h264_nvenc 持久化+胶囊联动、关闭回退 libx264 且保留选择、失效选择重置、无硬编环境选择框禁用）PASS。
- **品牌 logo 落地 + Windows 图标全链路（2026-09-11）**：
  - 用户提供 app 图标（暖黄渐变底 + 青绿立体折纸 "V"），落地到 `app/assets/logo.png`（原始 1254px）。
  - **UI 处同步**：顶部标题栏原"蓝色 M 方块"换成 logo（`logo_256.png`）；侧边栏顶部新增品牌区（logo + MediaDesk/媒体工作台，新增 `SidebarBrand/BrandName/BrandSub` 样式）；主窗口 `setWindowIcon`（任务栏/Alt-Tab 图标）。资源路径 `_logo_path()` 兼容 PyInstaller 冻结态（`_MEIPASS/assets`）。
  - **Windows 图标全链路**：生成多分辨率 ICO（16/24/32/48/64/128/256，`app/assets/logo.ico`，87KB，Qt 手写 ICO 容器内嵌 PNG）；`portable_build.py` 加 `--add-data app/assets;assets`（内嵌 logo）与 `--icon logo.ico`（exe/文件/任务栏图标），打包后 logo.ico 复制到产物根；`create_shortcut.ps1/.bat` 桌面快捷方式默认引用产物旁 `logo.ico`；备用 `MediaDesk.spec` 同步加 datas+icon。
  - 验证：脚本 AST OK；logo.png/logo_256.png/logo.ico 齐备；ICO 头校验 7 帧合法。
- **绿色便携版构建完成**（目标：安装即用、免装环境）：
  - 依赖瘦身：仅 PySide6-Essentials（QtCore/QtGui/QtWidgets），PyInstaller 排除全部重型附加模块（WebEngine/Qml/Pdf/Multimedia 等），应用本体从全量 636MB 降至 **95MB**。
  - 随包完整版 FFmpeg（essentials 9.0.1，含 libx264/libx265/libvpx/HEVC-NVENC）：`ffmpeg/bin`。绿色版总包约 **291MB**。
  - FFmpeg 定位顺序：手动配置 → 随包 `ffmpeg/bin` → 系统 PATH（`app/env.py` 新增 `_bundle_bit`，冻结态取 exe 同级）。
  - 脚本：`scripts/portable_build.py`（构建流水线）、`scripts/fetch_ffmpeg.py`（GitHub 官方镜像快源拉 FFmpeg）、`scripts/create_shortcut.ps1/.bat`（双击建桌面快捷方式）。
  - 合规：以 LGPL-3.0 动态链接 PySide6、FFmpeg 为外部进程分发；`docs/compliance/LICENSE_NOTICE.md` 已随包并附 LICENSE，**无需购买 Qt 商业许可**（已文档化理由）。
  - 新增 `.gitignore`（排除 .venv*、dist、build、含凭据的 tele_tools/.env）。
- **真实端到端验证（本机首次）**：用随包完整 FFmpeg 生成 6s 测试视频 → 压缩到 640×360(CRF28) → 转 VP8 WebM，全部成功；编码器齐全。
- `smoke_test` 增至 **PASS 67 / FAIL 0**（含随包路径探测断言）。
- 产物：`dist\MediaDesk\`（可运行），`release\MediaDesk_绿色版_v0.1.zip`（可分发包）。
- **文件整理模块重构·需求收敛 + 实现对齐（2026-09-11）**：
  - 基于 16 张批量重命名器截图重新梳理需求，与用户拍板 3 项决策（页面式 / 不做缩略图 / 媒体库变量暂不支持但保留入口），固化进 `docs/filerename/文件整理模块重构-需求设计（精简）.md` 与 `-需求与设计.md`。
  - 组合模板变量区补齐「标签名」「来源网站」占位按钮（点击 QMessageBox 提示"暂无数据源"），重排为截图三行三列布局。
  - 修复 `rename_page.py` 残留无效导入 `transform`（引擎为私有 `_transform`）导致的 UI 构建失败；`smoke_test` 过时断言 `preview_btn` 改为检查 `op_combo`/`reset_btn`（新 UI 为实时预览，无独立预览按钮）。
  - 验证：引擎验收单测 **10/10 PASS**（A1–A6 + 变量/序列/忽略大小写/未知变量/plans）；offscreen UI 构建 OK（占位按钮就位、5 操作下拉、5 配置页）；`smoke_test` **PASS 68/FAIL 0**。