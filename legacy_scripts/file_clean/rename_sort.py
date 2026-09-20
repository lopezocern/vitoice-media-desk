import os
from pathlib import Path

ROOT_PATH = r"H:\NudeFileZilla\Deep Face" # 修改这里
exclude = {'A', 'A temp', 'A 电影电视剧', 'A 原_去衣_AI', 'E'}
targets = {'dp', 'V', 'P'}
images = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.heic', '.heif'}

root = Path(ROOT_PATH)

for folder in root.iterdir():
    if not folder.is_dir() or folder.name in exclude:
        continue

    for sub in folder.iterdir():
        if not sub.is_dir():
            continue

        sub_name = sub.name

        # 处理根目录图片（排除mp4）
        root_imgs = sorted([f for f in sub.iterdir() if f.is_file() and f.suffix.lower() in images])
        for i, f in enumerate(root_imgs, 1):
            new_name = f"{sub_name}_{i:03d}{f.suffix}"
            f.rename(sub / new_name)
            print(f"{f.name} -> {new_name}")

        # 处理 dp/V/P（所有文件）
        for t in targets:
            t_path = sub / t
            if not t_path.exists():
                continue
            files = sorted([f for f in t_path.iterdir() if f.is_file()])
            for i, f in enumerate(files, 1):
                new_name = f"{sub_name}_{t}_{i:03d}{f.suffix}"
                f.rename(t_path / new_name)
                print(f"{f.name} -> {new_name}")

print("完成！")