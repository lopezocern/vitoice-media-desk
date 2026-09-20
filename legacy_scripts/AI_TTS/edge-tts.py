# coding:utf-8
# @time: 2023/7/8 13:40
# @Author: guoxiao
# @File: edge-tts

import edge_tts
import asyncio
with open("speech_txt.txt", "r", encoding='utf-8') as f:  #打开文本
    data = f.read()   #读取文本

TEXT = data
print(TEXT)
# Name: zh-CN-XiaoxiaoNeural Gender: Female
# Name: zh-CN-XiaoyiNeural Gender: Female
# Name: zh-CN-YunjianNeural Gender: Male
# Name: zh-CN-YunxiNeural Gender: Male
# Name: zh-CN-YunxiaNeural Gender: Male
# Name: zh-CN-YunyangNeural Gender: Male
# Name: zh-CN-liaoning-XiaobeiNeural Gender: Female
# Name: zh-CN-shaanxi-XiaoniNeural Gender: Female

# --rate 和 --volume 选项来调整语速和音量，-50% 代表降低语速/音量。
voice = 'zh-CN-YunyangNeural'
output = '232.mp3'
rate = '+5%'
volume = '+10%'

async def my_function():
    tts = edge_tts.Communicate(text = TEXT,voice = voice,rate = rate,volume=volume)
    await tts.save(output)

if __name__ == '__main__':
    # my_function_s()
    asyncio.run(my_function())