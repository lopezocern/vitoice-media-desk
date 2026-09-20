#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回收站清理脚本
用于删除 H:\\NudeFileZilla\\.bf\\.recycle2 目录下的内容到系统回收站
"""

import os
import sys
import subprocess
from pathlib import Path
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recycle_cleaner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 目标回收站目录
RECYCLE_DIR = r"H:\NudeFileZilla\.bf\.recycle2"
# RECYCLE_DIR = r"G:\A648-PC\.bf\.recycle2"

def check_and_install_send2trash():
    """检查和安装send2trash库"""
    try:
        import send2trash
        return send2trash
    except ImportError:
        print("❌ 错误: 需要安装 send2trash 库")
        print("📦 正在尝试自动安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "send2trash"])
            import send2trash
            print("✅ send2trash 安装成功!")
            return send2trash
        except Exception as e:
            print(f"❌ 自动安装失败: {e}")
            print("请手动运行: pip install send2trash")
            return None


def check_directory_exists(directory):
    """检查目录是否存在"""
    if not os.path.exists(directory):
        logging.error(f"目录不存在: {directory}")
        return False
    if not os.path.isdir(directory):
        logging.error(f"路径不是目录: {directory}")
        return False
    return True


def get_directory_size(path):
    """获取目录总大小"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception as e:
        logging.warning(f"计算目录大小时出错: {e}")
    return total_size


def format_file_size(size_bytes):
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def delete_to_recycle_bin(file_path, send2trash_module):
    """将文件或目录删除到回收站"""
    try:
        send2trash_module.send2trash(file_path)
        logging.info(f"已删除到回收站: {file_path}")
        return True
    except Exception as e:
        logging.error(f"删除失败: {file_path} - {str(e)}")
        return False


def clean_recycle_directory(send2trash_module):
    """清理回收站目录"""
    if not check_directory_exists(RECYCLE_DIR):
        return False

    logging.info(f"开始清理回收站目录: {RECYCLE_DIR}")

    # 获取目录内容
    try:
        items = os.listdir(RECYCLE_DIR)
        if not items:
            logging.info("回收站目录为空，无需清理")
            return True

        # 计算总大小
        total_size = get_directory_size(RECYCLE_DIR)
        logging.info(f"发现 {len(items)} 个项目，总大小: {format_file_size(total_size)}")

        # 确认删除
        print(f"\n即将删除以下项目到回收站:")
        print(f"目录: {RECYCLE_DIR}")
        print(f"项目数量: {len(items)}")
        print(f"总大小: {format_file_size(total_size)}")

        confirm = input("是否继续? (y/N): ").strip().lower()
        if confirm != 'y':
            logging.info("用户取消操作")
            return False

        # 删除所有项目
        deleted_count = 0
        failed_count = 0

        for item in items:
            item_path = os.path.join(RECYCLE_DIR, item)
            if delete_to_recycle_bin(item_path, send2trash_module):
                deleted_count += 1
            else:
                failed_count += 1

        logging.info(f"清理完成 - 成功: {deleted_count}, 失败: {failed_count}")

        if failed_count > 0:
            logging.warning(f"有 {failed_count} 个项目删除失败，请查看日志了解详情")

        return failed_count == 0

    except Exception as e:
        logging.error(f"清理过程中发生错误: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("回收站清理工具")
    print("=" * 50)
    print(f"目标目录: {RECYCLE_DIR}")
    print("=" * 50)

    # 检查和安装send2trash
    send2trash_module = check_and_install_send2trash()
    if send2trash_module is None:
        input("\n按回车键退出...")
        sys.exit(1)

    # 执行清理
    try:
        success = clean_recycle_directory(send2trash_module)

        if success:
            print("\n✅ 清理完成!")
        else:
            print("\n❌ 清理过程中出现错误!")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        logging.error(f"未预期的错误: {e}")

    # 保持窗口打开
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()