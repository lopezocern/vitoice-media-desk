import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==================== 配置 ====================
# tasklist | findstr python
# taskkill /F /IM python.exe
BOT_TOKEN = "7102099198:AAEBZ_hNl2d2q-582lIA2h06n-nrs6y3AWg"
SAVE_PATH = r"I:\clawdbot\telegram"
# 可选：指定只监听特定群/频道（留空则监听所有）
TARGET_CHAT_ID = None  # 例如：-1001234567890 或 "@群组用户名"

# 确保保存目录存在
os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "photos"), exist_ok=True)
os.makedirs(os.path.join(SAVE_PATH, "texts"), exist_ok=True)


# ==================== 处理器 ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息"""
    # 获取消息对象（兼容群和频道）
    message = (
            update.message or  # 普通群消息
            update.channel_post or  # 频道消息
            update.edited_message or  # 编辑过的群消息
            update.edited_channel_post  # 编辑过的频道消息
    )

    if not message or not message.text:
        return

    # 如果指定了目标聊天，检查是否匹配
    if TARGET_CHAT_ID and str(message.chat_id) != str(TARGET_CHAT_ID):
        return

    chat_type = message.chat.type
    chat_title = message.chat.title or message.chat.username or "未知"

    print(f"📝 收到文本消息 [{chat_type}]")
    print(f"   来自: {chat_title} (ID: {message.chat_id})")
    print(f"   内容: {message.text[:50]}...")

    # 保存文本
    file_name = f"text_{message.chat_id}_{message.message_id}.txt"
    file_path = os.path.join(SAVE_PATH, "texts", file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"消息ID: {message.message_id}\n")
        f.write(f"聊天ID: {message.chat_id}\n")
        f.write(f"类型: {chat_type}\n")
        f.write(f"聊天名称: {chat_title}\n")
        f.write(f"发送者: {message.from_user.username if message.from_user else 'N/A'}\n")
        f.write(f"时间: {message.date}\n")
        f.write(f"内容:\n{message.text}\n")

    print(f"✅ 已保存: {file_path}\n")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片消息"""
    message = (
            update.message or
            update.channel_post or
            update.edited_message or
            update.edited_channel_post
    )

    if not message or not message.photo:
        return

    if TARGET_CHAT_ID and str(message.chat_id) != str(TARGET_CHAT_ID):
        return

    chat_type = message.chat.type
    chat_title = message.chat.title or message.chat.username or "未知"

    print(f"🖼️  收到图片 [{chat_type}]")
    print(f"   来自: {chat_title}")

    # 获取最大尺寸图片
    photo = message.photo[-1]
    file_obj = await context.bot.get_file(photo.file_id)

    # 生成文件名
    ext = file_obj.file_path.split('.')[-1] if '.' in file_obj.file_path else "jpg"
    file_name = f"photo_{message.chat_id}_{message.message_id}.{ext}"
    file_path = os.path.join(SAVE_PATH, "photos", file_name)

    # 下载
    await file_obj.download_to_drive(file_path)
    print(f"✅ 图片已下载: {file_path}")

    # 保存说明文字
    if message.caption:
        caption_path = os.path.join(SAVE_PATH, "texts", f"caption_{message.chat_id}_{message.message_id}.txt")
        with open(caption_path, 'w', encoding='utf-8') as f:
            f.write(message.caption)
        print(f"✅ 说明已保存")


async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """调试处理器 - 打印所有收到的更新"""
    print(f"\n🔍 收到更新类型: {update.effective_chat.type if update.effective_chat else 'N/A'}")
    print(f"   Chat ID: {update.effective_chat.id if update.effective_chat else 'N/A'}")
    print(f"   Message: {update.effective_message.text if update.effective_message else 'N/A'}")
    print(f"   Raw update: {update.to_dict() if hasattr(update, 'to_dict') else str(update)[:200]}")


def main():
    print("🚀 启动 Telegram Bot...")
    print(f"💾 保存路径: {os.path.abspath(SAVE_PATH)}")
    print(f"🎯 目标聊天: {TARGET_CHAT_ID if TARGET_CHAT_ID else '所有聊天'}")
    print("-" * 50)

    application = Application.builder().token(BOT_TOKEN).build()

    # 添加调试处理器（先添加，不阻止后续处理）
    application.add_handler(MessageHandler(filters.ALL, debug_handler), group=0)

    # 文本处理器 - 监听所有聊天类型
    application.add_handler(
        MessageHandler(
            filters.TEXT &
            (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),  # 群和频道
            handle_text
        ),
        group=1
    )

    # 图片处理器
    application.add_handler(
        MessageHandler(
            filters.PHOTO &
            (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),
            handle_photo
        ),
        group=1
    )

    print("✅ Bot 正在运行，发送消息到群里测试...")
    print("按 Ctrl+C 停止\n")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # 忽略启动前的消息
    )


if __name__ == "__main__":
    main()