"""全局样式表（QSS）：浅色打磨主题。

主色 #4f5bd5，配套两档浅色 brand-soft/soft-2 用于 active / 悬停；
卡片白底 + 阴影、内容区浅灰底撑起主次层次；控件精修圆角/悬停/聚焦反馈。
"""
from __future__ import annotations

import sys
from pathlib import Path


def _asset(name: str) -> str:
    """定位随包资源：开发期取 app/assets，PyInstaller 冻结态取 exe 同级资源。"""
    base = (Path(sys._MEIPASS) / "assets"
            if getattr(sys, "_MEIPASS", None)
            else Path(__file__).resolve().parent.parent / "assets")
    return (base / name).as_posix()


# 复选框勾选态：蓝底 + 白色对勾（图标随包，绝对路径引用）
_CHECK = f"QCheckBox::indicator:checked{{background:#4f5bd5;border-color:#4f5bd5;image:url({_asset('check-white.png')});}}"

QSS = """
*{font-family:"Microsoft YaHei UI","Segoe UI",sans-serif;outline:none;}
QMainWindow,QWidget#Root{background:#eef1f8;color:#1c2333;}

/* ---- 顶部标题栏 ---- */
QWidget#TitleBar{background:#ffffff;border-bottom:1px solid #e4e9f2;}
/* ---- 底部全局任务栏（独立于标题栏，避免同 objectName 冲突）---- */
QWidget#StatusBar{background:#ffffff;border-top:1px solid #e4e9f2;}
QLabel#EnvHint{color:#9aa3bd;font-size:11.5px;}
QWidget#SidebarEnv{dot-color:#2f9e54;}
QLabel#AppTitle{font-size:15px;font-weight:700;color:#1c2333;letter-spacing:.2px;}
QLabel#EnvCaps{font-size:11.5px;color:#4f5bd5;background:#eef0fe;border-radius:999px;padding:4px 12px;font-weight:600;}

/* ---- 侧边栏 ---- */
QWidget#Sidebar{background:#ffffff;border-right:1px solid #e4e9f2;}
QWidget#SidebarBrand{border-bottom:1px solid #eef1f8;}
QLabel#BrandName{font-size:14px;font-weight:800;color:#1c2333;line-height:1.1;}
QLabel#BrandSub{font-size:10.5px;color:#9aa3bd;font-weight:600;}
QLabel#NavGroup{color:#9aa3bd;font-size:10.5px;font-weight:700;letter-spacing:.06em;padding:14px 12px 5px 14px;}
QPushButton#NavItem{background:transparent;border:none;border-radius:9px;text-align:left;padding:8px 10px;margin:1px 8px;font-size:13px;color:#3a4256;}
QPushButton#NavItem:hover{background:#f2f4fb;color:#1f2740;}
QPushButton#NavItem:checked{background:#eef0fe;color:#4f5bd5;font-weight:600;}
QPushButton#NavCollapse{background:transparent;border:none;color:#5a6480;font-size:15px;padding:3px 7px;border-radius:7px;}
QPushButton#NavCollapse:hover{background:#eef1f8;color:#4f5bd5;}
QLabel#NavBadge{background:#3939c4;color:#fff;border-radius:999px;padding:2px 8px;font-size:10.5px;font-weight:700;}

/* ---- 页面 ---- */
QLabel#PageTitle{font-size:21px;font-weight:700;color:#1c2333;}
QLabel#PageSub{font-size:12.5px;color:#64748b;}
QLabel#SectionTitle{font-size:13px;font-weight:700;color:#3a4256;}
QFrame#OverviewCard,QFrame#SettingCard{background:#ffffff;border:1px solid #e4e9f2;border-radius:12px;}
QScrollArea#TaskList{background:#ffffff;border:1px solid #e4e9f2;border-radius:12px;}
QFrame#ModuleCard{background:#ffffff;border:1px solid #e4e9f2;border-radius:12px;}
QFrame#ModuleCard:hover{border:1px solid #4f5bd5;background:#fbfcff;}
QFrame#ModuleCard:pressed{background:#eef0fe;}
QLabel#ValueAccent{color:#4f5bd5;font-weight:600;}
QLabel#Summary{color:#64748b;font-size:12.5px;}
QLabel#EnvStrip{background:#ffffff;border:1px solid #e4e9f2;border-radius:12px;}

/* ---- 任务行 ---- */
QWidget#TaskRow{background:#ffffff;border:1px solid #e4e9f2;border-radius:12px;}
QLabel#TaskName{font-size:12.5px;color:#1f2740;font-weight:600;}
QLabel#TaskMeta{font-size:11.5px;color:#9aa3bd;}
QLabel#TaskPct{font-size:12px;color:#4f5bd5;}
QProgressBar#TaskBar{background:#edf0f7;border:none;border-radius:999px;min-height:7px;max-height:7px;}
QProgressBar#TaskBar::chunk{background:#4f5bd5;border-radius:999px;}
QToolButton#TaskRemove{background:transparent;border:none;color:#a7aec0;font-size:15px;font-weight:700;border-radius:6px;padding:2px 6px;}
QToolButton#TaskRemove:hover{color:#d1495b;background:#fdeeef;}
QToolButton#ReorderBtn{background:transparent;border:none;color:#a7aec0;font-size:12px;font-weight:700;border-radius:6px;padding:2px 8px;}
QToolButton#ReorderBtn:hover{color:#4f5bd5;background:#eef0fe;}
QToolButton#ReorderBtn:disabled{color:#dfe3ee;}

/* ---- 控件 ---- */
QPushButton#Primary{background:#4f5bd5;color:#fff;border:none;border-radius:9px;padding:8px 16px;font-weight:600;}
QPushButton#Primary:hover{background:#3f49c2;}
QPushButton#Primary:pressed{background:#3943b3;}
QPushButton#Primary:disabled{background:#b9bfdf;color:#eef1f8;}
QPushButton#Ghost{background:#ffffff;color:#3a4256;border:1px solid #d3dae8;border-radius:9px;padding:7px 14px;}
QPushButton#Ghost:hover{border-color:#4f5bd5;color:#4f5bd5;background:#f6f7fe;}
QComboBox,QSpinBox,QLineEdit{background:#ffffff;border:1px solid #d3dae8;border-radius:9px;padding:6px 11px;font-size:13px;color:#1c2333;}
QComboBox:hover,QSpinBox:hover,QLineEdit:hover{border-color:#aeb7d8;}
QComboBox:focus,QSpinBox:focus,QLineEdit:focus{border-color:#4f5bd5;}
QCheckBox#AdvToggle{font-size:12.5px;color:#3a4256;font-weight:600;}
QPushButton#Expander{background:transparent;border:none;color:#4f5bd5;font-size:12.5px;font-weight:600;
  text-align:left;padding:4px 2px;border-radius:6px;}
QPushButton#Expander:hover{background:#eef0fe;}
QToolButton#HelpLabel{background:#eef1f8;border:none;border-radius:8px;color:#8b93ab;font-size:10px;font-weight:700;}
QToolButton#HelpLabel:hover{background:#e3e6fd;color:#4f5bd5;}
QScrollBar:vertical{background:transparent;width:9px;margin:2px;}
QScrollBar::handle:vertical{background:#c6cddf;border-radius:4px;min-height:30px;}
QScrollBar::handle:vertical:hover{background:#aab3cc;}
QScrollBar::add-line,QScrollBar::sub-line{height:0;}
QMessageBox QLabel{font-size:13px;}

/* ---- 下拉框弹层 ---- */
QComboBox QAbstractItemView{background:#ffffff;border:1px solid #d3dae8;border-radius:9px;
  outline:none;selection-background-color:#eef0fe;selection-color:#4f5bd5;}
QComboBox QAbstractItemView::item{padding:8px 12px;color:#1c2333;border-radius:6px;font-size:13px;min-height:20px;}
QComboBox QAbstractItemView::item:hover{background:#eef0fe;color:#4f5bd5;}
QComboBox QAbstractItemView::item:selected{background:#4f5bd5;color:#ffffff;font-weight:600;}
QComboBox::drop-down{border:none;background:transparent;width:22px;}

/* ---- SpinBox 上下按钮（箭头走 Qt 默认绘制，QSS border 三角不支持） ---- */
QSpinBox::up-button,QDoubleSpinBox::up-button{background:transparent;border:none;width:16px;subcontrol-origin:margin;subcontrol-position:top right;}
QSpinBox::down-button,QDoubleSpinBox::down-button{background:transparent;border:none;width:16px;subcontrol-origin:margin;subcontrol-position:bottom right;}

/* ---- 按钮基线（未命名的按钮也走这套） ---- */
QPushButton{border:1px solid transparent;font-size:13px;padding:7px 14px;border-radius:9px;color:#1c2333;background:#ffffff;}
QPushButton:hover{background:#f6f7fe;}
QPushButton:disabled{color:#9aa3bd;background:#eef1f8;}

/* ---- Tooltip / 菜单 / 复选框文字 ---- */
QToolTip{border:1px solid #d3dae8;background:#ffffff;color:#1c2333;border-radius:9px;padding:6px 8px;font-size:12px;}
QMenu{background:#ffffff;border:1px solid #e4e9f2;border-radius:9px;padding:6px 4px;}
QMenu::item{padding:6px 26px;border-radius:6px;font-size:13px;color:#1c2333;}
QMenu::item:selected{background:#4f5bd5;color:#ffffff;font-weight:600;}
QMenu::separator{height:1px;background:#e4e9f2;margin:4px 8px;}
QCheckBox{font-size:13px;color:#1c2333;spacing:7px;}
QCheckBox:disabled{color:#9aa3bd;}
QCheckBox::indicator{width:18px;height:18px;border:1px solid #c3cadb;border-radius:6px;background:#ffffff;}
QCheckBox::indicator:hover{border-color:#4f5bd5;}
QCheckBox::indicator:disabled{background:#eef1f8;border-color:#d3dae8;}

/* ---- 复选框勾选态（蓝底白勾，随包资源）---- */
{check}

/* ---- 对话框（QMessageBox / CutDialog 等）---- */
QDialog{background:#ffffff;}
QDialog QLabel{color:#1c2333;}
QMessageBox{background:#ffffff;}
QMessageBox QLabel{font-size:13.5px;color:#1c2333;}
QMessageBox QPushButton{
  background:#ffffff;color:#3a4256;border:1px solid #d3dae8;
  border-radius:9px;padding:7px 20px;min-width:72px;
  font-size:13px;font-weight:600;}
QMessageBox QPushButton:hover{border-color:#4f5bd5;color:#4f5bd5;background:#f6f7fe;}
QMessageBox QPushButton:pressed{background:#eef0fe;}
QMessageBox QPushButton:default{border-color:#4f5bd5;color:#4f5bd5;}

/* ---- 胶囊（编码器 / GPU 标签）---- */
QLabel#Pill{font-size:11.5px;border-radius:999px;padding:3px 10px;font-weight:600;
  background:#eef0fe;color:#4f5bd5;}
QLabel#Pill[soft="true"]{background:#f2f4fb;color:#64748b;}

/* ---- 分段选择器（速度档位等）---- */
QFrame#SegBox{background:#eef1f8;border-radius:9px;padding:3px;}
QPushButton#SegBtn{background:transparent;border:none;border-radius:7px;
  padding:4px 14px;font-size:12px;color:#64748b;font-weight:500;}
QPushButton#SegBtn:hover{color:#1c2333;}
QPushButton#SegBtn:checked{background:#ffffff;color:#4f5bd5;font-weight:600;}

/* ---- 段落标题（主色竖条 + 文字）---- */
QFrame#SectionDot{background:#4f5bd5;border-radius:2px;max-width:5px;min-width:5px;}

/* ---- 拖拽区（两行文字）---- */
QFrame#DropBox{background:#f8faff;border:1.5px dashed #c6cff5;border-radius:12px;}
QFrame#DropBox:hover{border-color:#4f5bd5;background:#e3e6fd;}
QFrame#DropBox[drophover="true"]{border-color:#4f5bd5;background:#e3e6fd;}
QLabel#DropBig{font-size:13.5px;font-weight:600;color:#3a4256;background:transparent;}
QLabel#DropSmall{font-size:12px;color:#9aa3bd;background:transparent;}

/* ---- 页面副标题 ---- */
QLabel#PageSub{font-size:12.5px;color:#64748b;}

/* ---- 无边框窗口：标题栏控制按钮 / 缩放把手 ---- */
QPushButton#WinBtn,QPushButton#WinBtnClose{background:transparent;border:none;border-radius:7px;
  color:#3a4256;font-size:14px;font-weight:600;}
QPushButton#WinBtn:hover,QPushButton#WinBtnClose:hover{background:#eef1f8;color:#1f2740;}
QPushButton#WinBtnClose:hover{background:#d1495b;color:#fff;}
QSizeGrip{width:16px;height:16px;background:transparent;border:none;}

/* ---- 任务列表：内部容器透明，透出滚动区白底（修复深色模式黑框） ---- */
QScrollArea>QWidget>QWidget{background:transparent;}
QScrollArea{background:#ffffff;border:1px solid #e4e9f2;border-radius:9px;}
/* 页面级滚动容器（整页滚动用，不带卡片边框） */
QScrollArea#PageScroll{background:transparent;border:none;}

/* ---- 表单标签 / 空态提示 ---- */
QLabel#FormLbl{font-size:12.5px;color:#3a4256;}
QLabel#EmptyHint{color:#9aa3bd;font-size:12.5px;}
"""

# 将「{check}」占位符替换为随包资源引用的复选框勾选态规则
# （用 replace 而非 format，避免 QSS 内 CSS 花括号被当作占位符误解析）
QSS = QSS.replace("{check}", _CHECK)