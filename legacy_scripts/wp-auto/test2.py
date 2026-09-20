import requests
import os

# --- 配置区 ---
API_BASE = "https://www.vitoice131.com/wp-json/wp/v2"
# 填入你 miniOrange 插件生成的 Authorization 凭据
HEADERS = {
    "Authorization": "Basic bG9wZXpvY2Vybjphc3BpY2UxMjM=",
}

# 本地图片路径列表
IMG_DIR = r"C:\Users\Administrator\Pictures"
IMG_FILES = [
    "A1.jpg",
    "A2.jpg",
    "A3.jpg"
]

# 文案内容
TEXTS = [
    "针对这一突发状况，官方紧急回应，表示已经知晓部分玩家在特定NVIDIA App设置下会遇到显示故障，并提供了一套临时的手动修复方案。",
    "官方指出，如果你遇到了画面显示异常，请尝试以下操作：",
    "打开 NVIDIA App > 进入“图形（Graphics）”选项 > 选择“全局设置（Global Settings）” > 将“DLSS覆盖 - 超分辨率模式（DLSS Override - Super Resolution Mode）”修改为“使用3D应用程序设置（Use 3D Application Setting）”，之后重启游戏即可。"
]

links = """
<p>
链接：<a href="https://pan.quark.cn/s/452cc4aa9a1d">夸克网盘</a><br>
网址：<a href="https://funletu.com/66932.html">点击跳转</a><br>
GitHub：<a href="https://github.com/jianchang512/pyvideotrans">项目地址</a>
</p>
"""

# --- 执行区 ---

def upload_image(file_path):
    """上传图片并返回 URL"""
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        media_headers = HEADERS.copy()
        media_headers.update({
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": "image/jpeg"
        })
        res = requests.post(f"{API_BASE}/media", headers=media_headers, data=f)
        return res.json().get("source_url")

print("正在上传图片...")
img_urls = []
for img in IMG_FILES:
    full_path = os.path.join(IMG_DIR, img)
    url = upload_image(full_path)
    img_urls.append(url)
    print(f"已上传: {url}")

# 组合 HTML 正文
html_content = f"""
<p>{TEXTS[0]}</p>
<img src="{img_urls[0]}" />
<p>{TEXTS[1]}</p>
<img src="{img_urls[1]}" />
<p>{TEXTS[2]}</p>
<img src="{img_urls[2]}" />
<hr>
{links}
"""

# 发布文章
post_data = {
    "title": "NVIDIA App 设置导致显示故障的修复方案",
    "content": html_content,
    "status": "publish", # 直接发布
    "categories": [1]    # 根据你的后台修改分类 ID
}

final_res = requests.post(f"{API_BASE}/posts", headers=HEADERS, json=post_data)

if final_res.status_code == 201:
    print("🎉 文章发布成功！")
    print(f"预览地址: {final_res.json().get('link')}")
else:
    print("❌ 发布失败:", final_res.text)