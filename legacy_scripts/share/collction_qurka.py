import requests
from bs4 import BeautifulSoup
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定义请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 创建一个会话对象，用于复用连接
session = requests.Session()
session.headers.update(headers)

def get_page_content(url):
    """
    获取页面内容
    :param url: 页面URL
    :return: 页面内容（字符串）
    """
    try:
        response = session.get(url, timeout=15)  # 使用会话对象，增加超时时间
        response.raise_for_status()  # 检查请求是否成功
        response.encoding = response.apparent_encoding  # 设置正确的编码
        return response.text
    except requests.RequestException as e:
        print(f"获取页面 {url} 失败: {e}")
        return None

def parse_main_page(html):
    """
    解析主页面，获取所有子项目的链接
    :param html: 主页面HTML内容
    :return: 子项目链接列表
    """
    soup = BeautifulSoup(html, 'html.parser')
    project_links = []
    
    # 查找所有子项目链接
    # 根据实际网页结构，子项目链接在class为"post-item item-list"的article标签中
    items = soup.select('.post-item.item-list')  # 更新为正确的选择器
    
    for item in items:
        link = item.select_one('.entry-title a')  # 查找h2.entry-title下的a标签
        if link and 'href' in link.attrs:
            project_links.append(link['href'])  # 获取项目链接
    
    return project_links

def parse_project_page(html):
    """
    解析子项目页面，获取"夸克"链接
    :param html: 子项目页面HTML内容
    :return: 夸克链接地址，如果未找到则返回None
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 查找包含"学习地址："的文本块，然后获取其后面的链接
    text_blocks = soup.find_all(text=lambda text: text and '学习地址：' in text)
    for block in text_blocks:
        # 查找包含"学习地址："的父元素
        parent = block.parent
        
        # 在父元素中查找所有链接
        links = parent.find_all('a')
        for link in links:
            if 'href' in link.attrs:
                return link['href']
        
        # 如果在父元素中没有找到链接，尝试查找下一个兄弟元素
        next_sibling = block.next_sibling
        while next_sibling:
            if hasattr(next_sibling, 'name') and next_sibling.name == 'a' and 'href' in next_sibling.attrs:
                return next_sibling['href']
            elif hasattr(next_sibling, 'find_all'):
                links = next_sibling.find_all('a')
                for link in links:
                    if 'href' in link.attrs:
                        return link['href']
            next_sibling = next_sibling.next_sibling
    
    # 如果上述方法失败，回退到原来的方法
    links = soup.find_all('a')
    for link in links:
        if link.text and '夸克' in link.text:
            if 'href' in link.attrs:
                return link['href']
    
    return None

def save_to_file(data, file_path):
    """
    将数据保存到文件
    :param data: 要保存的数据字典
    :param file_path: 保存文件的路径
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for project_link, quark_link in data.items():
                f.write(f"项目链接: {project_link}\n")
                f.write(f"夸克链接: {quark_link}\n")
                f.write("-" * 50 + "\n")
        print(f"数据已保存到 {file_path}")
    except IOError as e:
        print(f"保存文件失败: {e}")

def process_project(project_link):
    """
    处理单个项目链接，获取夸克链接
    :param project_link: 项目链接
    :return: 元组(项目链接, 夸克链接)，如果未找到则返回None
    """
    # 确保链接是完整的
    if not project_link.startswith('http'):
        project_link = f"https://www.ahhhhfs.com{project_link}"
    
    print(f"正在爬取子项目: {project_link}")
    
    # 获取子项目页面内容
    project_content = get_page_content(project_link)
    if not project_content:
        return None
    
    # 解析子项目页面，获取夸克链接
    quark_link = parse_project_page(project_content)
    if quark_link:
        print(f"找到夸克链接: {quark_link}")
        return (project_link, quark_link)
    else:
        print(f"在子项目 {project_link} 未找到夸克链接")
        return None

def get_quark_links(start_url, max_pages=5):
    """
    获取所有页面中的夸克链接
    :param start_url: 起始URL
    :param max_pages: 最大爬取页数
    :return: 夸克链接字典，键为项目链接，值为夸克链接
    """
    quark_links = {}
    
    for page in range(1, max_pages + 1):
        # 构建页面URL
        if page == 1:
            page_url = start_url
        else:
            page_url = f"{start_url}page/{page}/"
        
        print(f"正在爬取页面: {page_url}")
        
        # 获取页面内容
        page_content = get_page_content(page_url)
        if not page_content:
            continue
        
        # 解析主页面，获取子项目链接
        project_links = parse_main_page(page_content)
        if not project_links:
            print(f"在页面 {page_url} 未找到子项目链接")
            continue
        
        print(f"在页面 {page_url} 找到 {len(project_links)} 个子项目链接")
        
        # 使用线程池并发处理子项目链接
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            futures = [executor.submit(process_project, link) for link in project_links]
            
            # 等待所有任务完成并处理结果
            for future in as_completed(futures):
                result = future.result()
                if result:
                    project_link, quark_link = result
                    quark_links[project_link] = quark_link
        
        # 页面间的延迟可以适当减少，因为并发爬取已经提高了效率
        time.sleep(random.uniform(1, 2))
    
    return quark_links

def main():
    """
    主函数
    """
    start_url = rf"https://www.ahhhhfs.com/recourse/%e6%91%84%e5%bd%b1%e5%89%aa%e8%be%91/"
    max_pages = 9 # 爬取前4页
    
    print("开始爬取夸克链接...")
    quark_links = get_quark_links(start_url, max_pages)
    
    print("\n爬取完成！")
    print(f"共找到 {len(quark_links)} 个夸克链接：")
    
    for project_link, quark_link in quark_links.items():
        print(f"项目链接: {project_link}")
        print(f"夸克链接: {quark_link}")
        print("-" * 50)
    
    # 保存数据到share目录
    save_file_path = "/share/quark_links.txt"
    save_to_file(quark_links, save_file_path)

if __name__ == "__main__":
    main()