# MediaDesk 第三方许可与合规声明

本绿色版随分发了第三方组件。经评估：**本项目使用 LGPL/GPL 组件为动态链接/外部进程方式，无需购买 Qt 商业许可，可免费商用分发**。发布时请保留本文件。

## 组件清单与许可证

| 组件 | 许可证 | 使用方式 | 合规前提 |
|---|---|---|---|
| PySide6 / Qt6 | LGPL-3.0（备选 GPL-2/3） | 动态链接（DLL 随包） | 不修改 Qt 源码；允许用户替换所用 Qt 动态库 |
| FFmpeg（ffmpeg/ffprobe.exe） | GPL-3.0+（essentials 含 GPL 组件） | 独立外部进程（subprocess，非链接） | 作为独立程序分发；附 GPL 许可文本；标明可替换 |
| PyInstaller bootloader | GPL-2+（附分发例外） | 打包壳 | 例外允许在任何许可下分发 bootloader |
| pypinyin | MIT | 库依赖 | 无需额外条件 |

## 需随发布的许可文本
- LGPL-3.0（PySide6/Qt）：http://www.gnu.org/licenses/lgpl-3.0.html
- GPL-3.0（FFmpeg）：http://www.gnu.org/licenses/gpl-3.0.html
- FFmpeg 项目自身许可说明：https://ffmpeg.org/legal.html

## 义务要点
1. **可替换性**：不删除/锁定随包的 Qt DLL 与 ffmpeg.exe，允许最终用户用自建版本替换。
2. **保留来源声明**：本文件随产物分发。
3. **不修改组件源码**：不静态打补丁进 Qt/FFmpeg。
4. 本项目自身代码为闭源专有，因上述动态链接/外部进程方式，GPL/LGPL 不传染到本项目代码。

## 下载源（各有对应许可文本）
- PySide6 官方包：https://pypi.org/project/PySide6/
- FFmpeg essentials(gyan.dev)：https://www.gyan.dev/ffmpeg/builds/