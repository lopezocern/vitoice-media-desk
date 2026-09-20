# 回收站清理工具

## 功能说明

这个工具用于清理 `H:\NudeFileZilla\.bf\.recycle2` 目录下的所有文件和文件夹，将其移动到系统回收站，而不是永久删除。

## 文件说明

- `recycle_bin_cleaner.py` - 主要的清理脚本
- `install_requirements.py` - 安装必要的依赖包
- `run_recycle_cleaner.bat` - Windows批处理文件，一键运行

## 使用方法

### 方法1：直接运行批处理文件（推荐）
双击 `run_recycle_cleaner.bat` 即可自动完成依赖安装和清理操作。

### 方法2：手动运行
1. 先安装依赖：
   ```
   python install_requirements.py
   ```

2. 运行清理脚本：
   ```
   python recycle_bin_cleaner.py
   ```

### 方法3：命令行参数运行
```
python recycle_bin_cleaner.py
```

## 功能特性

- ✅ 安全删除到回收站（可恢复）
- ✅ 显示删除的文件列表和总大小
- ✅ 删除前确认提示
- ✅ 详细日志记录
- ✅ 自动依赖检查
- ✅ 中文界面支持

## 注意事项

1. **重要**：文件会被移动到系统回收站，如果需要可以手动从回收站恢复
2. 运行前请确保目标目录 `H:\NudeFileZilla\.bf\.recycle2` 存在
3. 脚本会自动创建日志文件 `recycle_cleaner.log`
4. 需要Python 3.6+ 环境

## 故障排除

### 如果提示找不到send2trash库
运行以下命令安装：
```
pip install send2trash
```

### 如果目录不存在
请确认路径 `H:\NudeFileZilla\.bf\.recycle2` 是否正确存在

### 权限问题
如果遇到权限错误，请尝试以管理员身份运行