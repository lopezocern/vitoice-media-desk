# coding:utf-8

import os
import shutil, random
import os.path
rootdir = r"H:\NudeFileZilla\Deep Face" # 指明被遍历的文件夹

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

def rename_file():
    for parent,dirnames,filenames in os.walk(rootdir):#三个参数：分别返回1.父目录 2.所有文件夹名字（不含路径） 3.所有文件名字
        print("===================================================", parent, "===================================================")
        file_name = parent.split('\\')
        len_1 = int(len(file_name)) - 1
        print("========dir name========", file_name[len_1])
        dir_name = file_name[len_1]

        for filename in filenames:
            name = filename.replace('download_', '')
            if dir_name.lower() in filename.lower():
                # print("====in======== ",filename)
                pass
            # else:
                # print("....not in.... ",filename)

            print("***new_name*** ", name)
            os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名

            try:
                os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
            except FileExistsError:
                number_x = random.randint(0,9)
                name = name + str(number_x)
                os.rename(os.path.join(parent, filename), os.path.join(parent, name))

rename_file()

# @pysnooper.snoop()
# def t():
#     a = world_charter_dict['ResidentEvil']
#     if 'ada' in a:
#         print('xaxax')
#
# t()