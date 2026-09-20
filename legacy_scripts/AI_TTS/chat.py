# coding:utf-8
# @time: 2023/2/24 22:42
# @Author: guoxiao
# @File: chat

import time

# 设置请求的端点和订阅密钥
endpoint = '<YOUR_ENDPOINT>'
subscription_key = '<YOUR_SUBSCRIPTION_KEY>'

# 设置需要转换为语音的文本
text = '<YOUR_TEXT_TO_CONVERT>'

# 构建请求的URL
url = endpoint + '/tts/edge/v1.0/synthesize'

# 设置请求头
headers = {
    'Content-Type': 'application/ssml+xml',
    'Authorization': 'Bearer ' + subscription_key
}

# 构建SSML请求体
ssml = """
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="en-US-AriaNeural">
        {0}
    </voice>
</speak>
""".format(text)

# 发送POST请求
response = requests.post(url, headers=headers, data=ssml)

# 检查请求是否成功
if response.status_code == 200:
    # 获取生成的语音的二进制数据
    audio_data = response.content

    # 保存语音到文件
    filename = 'output.wav'
    with open(filename, 'wb') as file:
        file.write(audio_data)

    print('语音已生成并保存到文件：{0}'.format(filename))
else:
    print('生成语音时发生错误：{0}'.format(response.text))
