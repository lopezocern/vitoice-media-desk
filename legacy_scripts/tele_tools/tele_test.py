from telegram import Bot

BOT_TOKEN = "7102099198:AAEBZ_hNl2d2q-582lIA2h06n-nrs6y3AWg"


async def test_bot():
    bot = Bot(BOT_TOKEN)

    # 获取 Bot 信息
    me = await bot.get_me()
    print(f"Bot 名称: {me.username}")
    print(f"Bot ID: {me.id}")

    # 尝试获取更新
    updates = await bot.get_updates(limit=10)
    print(f"\n待处理更新数: {len(updates)}")

    for upd in updates:
        print(f"\n更新 ID: {upd.update_id}")
        if upd.message:
            print(f"  类型: 消息")
            print(f"  聊天: {upd.message.chat.title} ({upd.message.chat.type})")
            print(f"  内容: {upd.message.text[:30] if upd.message.text else 'N/A'}")
        elif upd.channel_post:
            print(f"  类型: 频道帖子")
            print(f"  聊天: {upd.channel_post.chat.title}")


import asyncio

asyncio.run(test_bot())