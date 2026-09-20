import os
import shutil
import logging
import numpy as np
from PIL import Image
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def preprocess_image(image_path):
    """优化的 dHash 预处理"""
    try:
        with Image.open(image_path) as img:
            img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = np.array(img).astype(np.float32)
            diff = pixels[:, :-1] > pixels[:, 1:]
            return np.packbits(diff.flatten())
    except Exception as e:
        logger.error(f"预处理失败 {image_path}: {e}")
        return None


def calculate_similarity(hash1, hash2):
    """加速的汉明距离计算"""
    if hash1 is None or hash2 is None:
        return 0.0
    return 1.0 - np.count_nonzero(np.unpackbits(hash1) != np.unpackbits(hash2)) / 64


def find_similar_groups(folder_path, similarity_threshold=0.93):
    """在当前目录（不包含子目录）查找相似组"""
    # 获取当前目录（不递归子目录）的所有图片，跳过包含 'PASS' 的文件
    image_files = []
    for f in os.listdir(folder_path):
        filename = os.path.basename(f)
        if 'PASS' in filename:
            continue
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            image_files.append(os.path.join(folder_path, f))

    # 并行预处理
    image_hashes = {}
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_path = {executor.submit(preprocess_image, path): path for path in image_files}
        for future in future_to_path:
            path = future_to_path[future]
            try:
                hash_val = future.result()
                if hash_val is not None:
                    image_hashes[os.path.basename(path)] = hash_val  # 只保留文件名作为 key
            except Exception as e:
                logger.error(f"处理失败 {path}: {e}")

    # 构建相似对
    files = list(image_hashes.keys())
    similar_pairs = []

    with ThreadPoolExecutor() as executor:
        futures = []
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                f1, f2 = files[i], files[j]
                futures.append(executor.submit(
                    lambda x, y: (x, y) if calculate_similarity(image_hashes[x], image_hashes[y]) >= similarity_threshold else None,
                    f1, f2
                ))

        for future in futures:
            result = future.result()
            if result:
                similar_pairs.append(result)

    # 合并相似组
    return merge_groups(similar_pairs)


def merge_groups(pairs):
    """并查集合并分组"""
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # 初始化
    all_files = set()
    for a, b in pairs:
        all_files.update({a, b})
    for file in all_files:
        parent[file] = file

    # 合并操作
    for a, b in pairs:
        parent[find(a)] = find(b)

    # 收集分组
    groups = defaultdict(list)
    for file in all_files:
        root = find(file)
        groups[root].append(file)

    return [g for g in groups.values() if len(g) > 1]


def move_group_files(folder_path, group, group_id):
    """移动单个相似组到子目录下的 similar_images"""
    similar_folder = os.path.join(folder_path, "similar_images")
    os.makedirs(similar_folder, exist_ok=True)

    moved_files = []
    for filename in group:
        src = os.path.join(folder_path, filename)
        if not os.path.exists(src):
            continue

        # 处理文件名冲突
        base_name = f"Group{group_id:03d}_{filename}"
        dst = os.path.join(similar_folder, base_name)

        # 如果目标文件已存在，添加后缀
        counter = 1
        while os.path.exists(dst):
            name_part = os.path.splitext(base_name)[0]
            ext = os.path.splitext(base_name)[1]
            dst = os.path.join(similar_folder, f"{name_part}_{counter}{ext}")
            counter += 1

        try:
            shutil.move(src, dst)
            moved_files.append(filename)
            logger.info(f"移动成功: {filename} => {os.path.relpath(dst, folder_path)}")
        except Exception as e:
            logger.error(f"移动失败 {filename}: {e}")

    return moved_files


def process_directory(directory, group_counter):
    """处理单个目录"""
    logger.info(f"开始处理目录: {directory}")

    # 跳过已处理目录
    if "similar_images" in directory:
        return group_counter

    groups = find_similar_groups(directory)
    if not groups:
        return group_counter

    current_counter = group_counter
    for group in groups:
        moved = move_group_files(directory, group, current_counter)
        if moved:
            current_counter += 1

    # 清理空目录（保留原始结构）
    try:
        if not os.listdir(directory):
            os.rmdir(directory)
            logger.info(f"已清理空目录: {directory}")
    except Exception as e:
        logger.error(f"目录清理失败 {directory}: {e}")

    # 新增功能：如果 similar_images 目录为空，则删除该目录
    similar_images_path = os.path.join(directory, "similar_images")
    if similar_images_path:
        try:
            # 确保目录存在
            if os.path.exists(similar_images_path):
                # 检查目录是否为空
                if not os.listdir(similar_images_path):
                    os.rmdir(similar_images_path)
                    logger.info(f"已删除空的 similar_images 目录: {similar_images_path}")
        except Exception as e:
            logger.error(f"删除空的 similar_images 目录失败 {similar_images_path}: {e}")

    return current_counter


def process_structure(root_folder):
    group_counter = 1

    # 使用深度优先遍历（保证先处理子目录）
    for root, dirs, files in os.walk(root_folder, topdown=False):
        # 跳过系统隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # 特殊处理：如果当前目录包含dp子目录，优先处理dp目录
        if 'dp' in dirs:
            dp_path = os.path.join(root, 'dp')
            if os.path.exists(dp_path) and os.path.isdir(dp_path):
                logger.info(f"发现dp子目录: {dp_path}")
                new_counter = process_directory(dp_path, group_counter)
                
                # 更新全局计数器
                if new_counter > group_counter:
                    logger.info(f"在dp目录 {dp_path} 中发现 {new_counter - group_counter} 个相似组")
                    group_counter = new_counter
                    
        # 处理当前目录
        new_counter = process_directory(root, group_counter)

        # 更新全局计数器
        if new_counter > group_counter:
            logger.info(f"在目录 {root} 中发现 {new_counter - group_counter} 个相似组")
            group_counter = new_counter

    logger.info(f"全部处理完成，共发现 {group_counter - 1} 个相似组")


if __name__ == "__main__":
    # 支持两种路径格式
    # 1. AI Picture路径格式
    # target_folder = r'H:\NudeFileZilla\浏览器采集\AI Picture'
    # 2. Deep Face路径格式
    target_folder = rf"H:\NFZ\短视频"
    # target_folder = rf"H:\NudeFileZilla\Deep Face"
    process_structure(target_folder)