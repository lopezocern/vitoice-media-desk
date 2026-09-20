import os

# 指定父目录路径，可以修改为你需要的路径
parent_dir = r'H:\NFZ\短视频\A_2_原_图片_AI'

for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    folder_name = char
    # 拼接得到完整的文件夹路径
    folder_path = os.path.join(parent_dir, folder_name)
    # 检查文件夹是否存在，如果不存在则创建
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"文件夹 '{folder_name}' 已创建。")
    else:
        print(f"文件夹 '{folder_name}' 已存在。")