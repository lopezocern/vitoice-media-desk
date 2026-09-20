# coding:utf-8
# @time: 2022/5/10 23:20
# @Author: guoxiao
# @File: tet
#coding=utf-8
import os
import shutil
import os.path
rootdir = r"H:\NudeFileZilla\output"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla\PPro\J-AV\未命名文件夹"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla\Game"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla"
# rootdir = r"H:\NudeFileZilla\Deep Face"
# rootdir = r'D:\NudeFileZilla\浏览器采集\AI Picture'
# i = 0



def remove_file(old_path, new_path):
    print(old_path)
    print(new_path)
    filelist = os.listdir(old_path) #列出该目录下的所有文件,listdir返回的文件列表是不包含路径的。
    print(filelist)
    for file in filelist:
        src = os.path.join(old_path, file)
        dst = os.path.join(new_path, file)
        print('src:', src)
        print('dst:', dst)
        shutil.move(src, dst)
error_list = []
for parent,dirnames,filenames in os.walk(rootdir):#三个参数：分别返回1.父目录 2.所有文件夹名字（不含路径） 3.所有文件名字
    xnum=1
    for filename in filenames:
        # print(filename)
        name = '接客'+str(xnum)+'~1.webm'
        print(name)
        xnum=xnum+1
        # 接客<<xop>>~1.webm
        # filenew=nameList[0]+'.jpg'
        # print filenew
        try:
            # print(name)
            os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
        except FileExistsError:
            name = (filename.replace('_', '1'))
            os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
        # try:
        #     os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
        # except PermissionError as e :
        #     error_list.append(e)
print(error_list)