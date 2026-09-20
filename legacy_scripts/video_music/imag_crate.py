# 生成完整的、可直接使用的代码模板
from PIL import Image, ImageDraw, ImageFont
import math
from typing import List, Optional, Tuple


def concatenate_images_horizontal(
    image_paths: List[str],
    output_path: str,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    padding: int = 0,
    align: str = 'center'  # 'top', 'center', 'bottom'
) -> str:
    """
    水平拼接图片（横向排列）

    Args:
        image_paths: 图片路径列表
        output_path: 输出路径
        background_color: 背景色 (R, G, B)
        padding: 图片之间的间距（像素）
        align: 垂直对齐方式 ('top', 'center', 'bottom')

    Returns:
        输出文件路径
    """
    images = [Image.open(path).convert('RGB') for path in image_paths]

    total_width = sum(img.width for img in images) + padding * (len(images) - 1)
    max_height = max(img.height for img in images)

    result = Image.new('RGB', (total_width, max_height), background_color)

    x_offset = 0
    for img in images:
        if align == 'top':
            y_offset = 0
        elif align == 'bottom':
            y_offset = max_height - img.height
        else:
            y_offset = (max_height - img.height) // 2

        result.paste(img, (x_offset, y_offset))
        x_offset += img.width + padding

    result.save(output_path, quality=95)
    return output_path


def concatenate_images_vertical(
    image_paths: List[str],
    output_path: str,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    padding: int = 0,
    align: str = 'center'  # 'left', 'center', 'right'
) -> str:
    """
    垂直拼接图片（纵向排列）

    Args:
        image_paths: 图片路径列表
        output_path: 输出路径
        background_color: 背景色 (R, G, B)
        padding: 图片之间的间距（像素）
        align: 水平对齐方式 ('left', 'center', 'right')

    Returns:
        输出文件路径
    """
    images = [Image.open(path).convert('RGB') for path in image_paths]

    max_width = max(img.width for img in images)
    total_height = sum(img.height for img in images) + padding * (len(images) - 1)

    result = Image.new('RGB', (max_width, total_height), background_color)

    y_offset = 0
    for img in images:
        if align == 'left':
            x_offset = 0
        elif align == 'right':
            x_offset = max_width - img.width
        else:
            x_offset = (max_width - img.width) // 2

        result.paste(img, (x_offset, y_offset))
        y_offset += img.height + padding

    result.save(output_path, quality=95)
    return output_path


def concatenate_images_grid(
    image_paths: List[str],
    output_path: str,
    cols: int = 2,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    padding: int = 10,
    uniform_size: bool = False
) -> str:
    """
    网格拼接图片（矩阵排列）

    Args:
        image_paths: 图片路径列表
        output_path: 输出路径
        cols: 列数
        background_color: 背景色 (R, G, B)
        padding: 图片之间的间距（像素）
        uniform_size: 是否统一调整为相同尺寸

    Returns:
        输出文件路径
    """
    images = [Image.open(path).convert('RGB') for path in image_paths]
    rows = math.ceil(len(images) / cols)

    if uniform_size:
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        images = [img.resize((max_width, max_height), Image.Resampling.LANCZOS) for img in images]
        cell_width, cell_height = max_width, max_height
    else:
        cell_width = max(img.width for img in images)
        cell_height = max(img.height for img in images)

    total_width = cell_width * cols + padding * (cols - 1)
    total_height = cell_height * rows + padding * (rows - 1)

    result = Image.new('RGB', (total_width, total_height), background_color)

    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols

        x = col * (cell_width + padding)
        y = row * (cell_height + padding)

        if not uniform_size:
            x += (cell_width - img.width) // 2
            y += (cell_height - img.height) // 2

        result.paste(img, (x, y))

    result.save(output_path, quality=95)
    return output_path


# ==================== 使用示例 ====================

if __name__ == "__main__":
    img1=rf'H:\NudeFileZilla\云端-本地素材\图像_B.jpg'
    img2=rf'H:\NudeFileZilla\云端-本地素材\图像_A.jpg'
    img3=rf'H:\NudeFileZilla\云端-本地素材\图像_C.jpg'
    # 示例1：水平拼接
    concatenate_images_horizontal(
        image_paths=[ img1, img2, img3],
        output_path="output_horizontal.jpg",
        # background_color=(240, 240, 240),
        padding=0,
        align='center'
    )

    # # 示例2：垂直拼接
    # concatenate_images_vertical(
    #     image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
    #     output_path="output_vertical.jpg",
    #     padding=15,
    #     align='center'
    # )
    #
    # # 示例3：网格拼接（2列）
    # concatenate_images_grid(
    #     image_paths=["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"],
    #     output_path="output_grid.jpg",
    #     cols=2,
    #     padding=10,
    #     uniform_size=True
    # )

