import os
import sys
import asyncio
import re
import signal
import atexit
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.request import HTTPXRequest

from dotenv import load_dotenv
load_dotenv()  # 这行放在最前面，在 load_config() 之前+

# ==================== 配置（从环境变量读取） ====================

def load_config():
    """从环境变量加载配置"""
    # 必需配置
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("请设置环境变量 TELEGRAM_BOT_TOKEN")

    return {
        "BOT_TOKEN": token,
        "BASE_PATH": os.getenv("SAVE_PATH", r"I:\clawdbot\telegram"),
        "TARGET_CHAT_ID": os.getenv("TARGET_CHAT_ID"),  # 可选
        "PROXY_URL": os.getenv("PROXY_URL"),  # 可选，例如: http://127.0.0.1:7890
        # 超时设置
        "CONNECT_TIMEOUT": int(os.getenv("CONNECT_TIMEOUT", "30")),
        "READ_TIMEOUT": int(os.getenv("READ_TIMEOUT", "30")),
        "WRITE_TIMEOUT": int(os.getenv("WRITE_TIMEOUT", "30")),
        "POOL_TIMEOUT": int(os.getenv("POOL_TIMEOUT", "30")),
    }


CONFIG = load_config()

# 确保基础路径存在
os.makedirs(CONFIG["BASE_PATH"], exist_ok=True)


# ==================== 日志系统 ====================

def setup_logging():
    """设置日志系统"""
    log_dir = os.path.join(CONFIG["BASE_PATH"], "log")
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.log")

    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# ==================== 工具函数 ====================

def get_today_folder():
    """获取或创建今天的日期文件夹"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_path = os.path.join(CONFIG["BASE_PATH"], today)
    os.makedirs(today_path, exist_ok=True)
    return today_path


def get_preview_text(text, length=100):
    """获取文本前N个字符作为文件夹名"""
    if not text:
        return "无标题"

    clean_text = re.sub(r'\s+', ' ', text).strip()
    preview = clean_text[:length]
    invalid_chars = r'[<>:"/\\|?*]'
    preview = re.sub(invalid_chars, '_', preview)

    if not preview or preview.isspace():
        return "无标题"

    return preview


def get_unique_folder_name(base_path, folder_name):
    """如果文件夹名已存在，添加序号"""
    full_path = os.path.join(base_path, folder_name)
    if not os.path.exists(full_path):
        return folder_name

    counter = 1
    while True:
        new_name = f"{folder_name}_{counter}"
        full_path = os.path.join(base_path, new_name)
        if not os.path.exists(full_path):
            return new_name
        counter += 1


# ==================== 核心保存逻辑 ====================

async def save_message_to_folder(message, photo_file=None):
    """保存消息到结构化文件夹"""
    today_folder = get_today_folder()

    preview_text = ""
    if message.text:
        preview_text = message.text
    elif message.caption:
        preview_text = message.caption
    else:
        preview_text = "图片消息"

    folder_preview = get_preview_text(preview_text, 15)
    message_folder_name = get_unique_folder_name(today_folder, folder_preview)
    message_folder = os.path.join(today_folder, message_folder_name)
    os.makedirs(message_folder, exist_ok=True)

    time_str = datetime.now().strftime("%H%M%S")
    base_filename = f"{time_str}_{message.message_id}"

    photo_relative_path = None
    if photo_file:
        ext = "jpg"
        if hasattr(photo_file, 'file_path') and photo_file.file_path:
            ext = photo_file.file_path.split('.')[-1] if '.' in photo_file.file_path else "jpg"

        photo_filename = f"{base_filename}.{ext}"
        photo_path = os.path.join(message_folder, photo_filename)

        await photo_file.download_to_drive(photo_path)
        photo_relative_path = photo_filename

    md_filename = f"{base_filename}.md"
    md_path = os.path.join(message_folder, md_filename)

    content = build_markdown_content(message, photo_relative_path)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'folder': message_folder,
        'markdown': md_path,
        'photo': photo_path if photo_file else None
    }


def build_markdown_content(message, photo_relative_path=None):
    """构建 Markdown 内容"""
    lines = [
        "# 📨 Telegram 消息归档",
        "",
        f"**归档时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**消息ID:** `{message.message_id}`",
        f"**原始时间:** {message.date.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**来源:** {message.chat.title or message.chat.username or '私聊'}",
    ]

    if message.from_user:
        sender = message.from_user.username or message.from_user.full_name
        lines.append(f"**发送者:** @{sender} (ID: {message.from_user.id})")

    lines.extend(["", "---", ""])

    if photo_relative_path:
        lines.extend([
            "## 🖼️ 图片",
            "",
            f"![消息图片]({photo_relative_path})",
            "",
            f"**文件:** `{photo_relative_path}`",
            "",
            "---",
            "",
        ])

    if message.text:
        lines.extend(["## 📝 文本内容", "", message.text, ""])
    elif message.caption:
        lines.extend(["## 📝 图片说明", "", message.caption, ""])

    lines.extend([
        "---",
        "",
        "### ℹ️ 技术信息",
        f"- **Chat ID:** `{message.chat_id}`",
        f"- **Chat Type:** `{message.chat.type}`",
        f"- **Message Type:** `{'Photo' if photo_relative_path else 'Text'}`",
        "",
        f"*由 ClawdBot 自动归档*",
    ])

    return '\n'.join(lines)


# ==================== 错误处理器 ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """全局错误处理器"""
    error = context.error

    if isinstance(error, Conflict):
        logger.error(f"冲突错误: {error}")
        logger.error("另一个 Bot 实例正在运行，请先关闭其他实例！")
        os._exit(1)

    elif isinstance(error, (NetworkError, TimedOut)):
        logger.warning(f"网络错误: {error}，将在下次轮询时自动重试...")

    else:
        logger.error(f"发生错误: {error}")
        if update:
            logger.error(f"更新内容: {update}")


# ==================== 消息处理器 ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理纯文本消息"""
    message = update.message or update.channel_post or update.edited_message or update.edited_channel_post

    if not message or not message.text:
        return

    target_id = CONFIG["TARGET_CHAT_ID"]
    if target_id and str(message.chat_id) != str(target_id):
        return

    try:
        preview = message.text[:30].replace('\n', ' ')
        logger.info(f"收到文本: {preview}...")

        result = await save_message_to_folder(message, photo_file=None)

        folder_name = os.path.basename(result['folder'])
        date_folder = os.path.basename(os.path.dirname(result['folder']))

        logger.info(f"已保存到: ./{date_folder}/{folder_name}/")
        logger.info(f"  文件: {os.path.basename(result['markdown'])}")

    except Exception as e:
        logger.error(f"保存文本失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片消息"""
    message = update.message or update.channel_post or update.edited_message or update.edited_channel_post

    if not message or not message.photo:
        return

    target_id = CONFIG["TARGET_CHAT_ID"]
    if target_id and str(message.chat_id) != str(target_id):
        return

    try:
        caption_preview = message.caption[:20].replace('\n', ' ') if message.caption else "无说明"
        logger.info(f"收到图片: {caption_preview}...")

        photo = message.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)

        result = await save_message_to_folder(message, photo_file=file_obj)

        folder_name = os.path.basename(result['folder'])
        date_folder = os.path.basename(os.path.dirname(result['folder']))

        logger.info(f"已保存到: ./{date_folder}/{folder_name}/")
        logger.info(f"  Markdown: {os.path.basename(result['markdown'])}")
        logger.info(f"  图片: {os.path.basename(result['photo'])}")

    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ==================== 启动检查 ====================

def initialize_system():
    """系统初始化检查"""
    logger.info("=" * 50)
    logger.info("正在初始化 ClawdBot 归档系统...")
    logger.info(f"基础路径: {CONFIG['BASE_PATH']}")

    if not os.path.exists(CONFIG["BASE_PATH"]):
        logger.warning(f"基础路径不存在，正在创建: {CONFIG['BASE_PATH']}")
        os.makedirs(CONFIG["BASE_PATH"], exist_ok=True)

    today_folder = get_today_folder()
    logger.info(f"今日文件夹: {os.path.basename(today_folder)}")

    log_dir = os.path.join(CONFIG["BASE_PATH"], "log")
    logger.info(f"日志目录: {log_dir}")

    if CONFIG["PROXY_URL"]:
        logger.info(f"代理设置: {CONFIG['PROXY_URL']}")
    else:
        logger.info("代理设置: 无")

    logger.info(
        f"超时设置: 连接{CONFIG['CONNECT_TIMEOUT']}s, 读取{CONFIG['READ_TIMEOUT']}s, 写入{CONFIG['WRITE_TIMEOUT']}s")

    date_folders = [f for f in os.listdir(CONFIG["BASE_PATH"])
                    if os.path.isdir(os.path.join(CONFIG["BASE_PATH"], f)) and f != "log"]
    logger.info(f"发现 {len(date_folders)} 个日期文件夹")

    logger.info("系统就绪")
    logger.info("-" * 50)


def cleanup():
    """清理函数"""
    logger.info("正在关闭 Bot...")
    logger.info("再见！")
    logging.shutdown()


def main():
    atexit.register(cleanup)

    def signal_handler(sig, frame):
        logger.info("收到中断信号，正在关闭...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    initialize_system()

    logger.info("启动 Bot...")
    logger.info("等待消息...")
    logger.info("-" * 50)

    try:
        # 准备 HTTPXRequest 参数
        request_kwargs = {
            "connection_pool_size": 8,
            "connect_timeout": CONFIG["CONNECT_TIMEOUT"],
            "read_timeout": CONFIG["READ_TIMEOUT"],
            "write_timeout": CONFIG["WRITE_TIMEOUT"],
            "pool_timeout": CONFIG["POOL_TIMEOUT"],
        }

        # 新版本使用 proxy 而不是 proxy_url
        if CONFIG["PROXY_URL"]:
            request_kwargs["proxy"] = CONFIG["PROXY_URL"]

        request = HTTPXRequest(**request_kwargs)

        application = (
            Application.builder()
            .token(CONFIG["BOT_TOKEN"])
            .request(request)
            .build()
        )

        application.add_error_handler(error_handler)

        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND &
                (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),
                handle_text
            )
        )

        application.add_handler(
            MessageHandler(
                filters.PHOTO &
                (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),
                handle_photo
            )
        )

        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=30,
            bootstrap_retries=-1,
        )

    except Conflict as e:
        logger.error(f"致命错误: {e}")
        logger.error("请确保没有其他实例在运行，然后重试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()