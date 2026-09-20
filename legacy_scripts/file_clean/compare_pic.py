import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import os
from concurrent.futures import ThreadPoolExecutor

def calculate_similarity(img1_path, img2_path):
    """计算两张图像的 SSIM 相似度

    Args:
        img1_path (str): 图像1路径
        img2_path (str): 图像2路径

    Returns:
        float: SSIM 相似度
    """

    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
    return ssim(img1, img2)

def compare_and_move(image_pair, folder_path, similarity_threshold):
    """比较图像对，并移动相似图像

    Args:
        image_pair (tuple): 图像对 (img1_path, img2_path)
        folder_path (str): 文件夹路径
        similarity_threshold (float): 相似度阈值
    """

    img1_path, img2_path = image_pair
    similarity = calculate_similarity(img1_path, img2_path)

    if similarity > similarity_threshold:
        # 创建相似图像文件夹
        similar_images_folder = os.path.join(folder_path, 'similar_images')
        os.makedirs(similar_images_folder, exist_ok=True)

        # 移动图像
        new_img1_path = os.path.join(similar_images_folder, os.path.basename(img1_path))
        new_img2_path = os.path.join(similar_images_folder, os.path.basename(img2_path))
        os.rename(img1_path, new_img1_path)
        os.rename(img2_path, new_img2_path)

def process_folder(folder_path, similarity_threshold=0.9, num_workers=4):
    """处理文件夹中的图像

    Args:
        folder_path (str): 文件夹路径
        similarity_threshold (float, optional): 相似度阈值. Defaults to 0.9.
        num_workers (int, optional): 线程池大小. Defaults to 4.
    """

    image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
    image_paths = [os.path.join(folder_path, f) for f in image_files]
    image_pairs = [(image_paths[i], image_paths[j]) for i in range(len(image_paths)) for j in range(i+1, len(image_paths))]

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for _ in executor.map(compare_and_move, image_pairs, [folder_path] * len(image_pairs), [similarity_threshold] * len(image_pairs)):
            pass

if __name__ == '__main__':
    parent_folder_path = r'H:\NudeFileZilla\浏览器采集\AI Picture\Z 赵露思'
    for subfolder in os.listdir(parent_folder_path):
        folder_path = os.path.join(parent_folder_path, subfolder)
        if os.path.isdir(folder_path):
            process_folder(folder_path)