import requests

url = "https://www.vitoice131.com/wp-json/wp/v2/posts"
# miniOrange 插件通常要求在 Header 中加入 Authorization
headers = {
    "Authorization": "Basic bG9wZXpvY2Vybjphc3BpY2UxMjM=", # 或者是 Basic 格式，根据插件提示来
    "Content-Type": "application/json"
}

data = {
    "title": "通过 miniOrange 发布的文章",
    "content": "内容测试",
    "status": "publish"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())

