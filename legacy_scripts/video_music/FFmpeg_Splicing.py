# coding:utf-8
# @time: 2024/08/02 1:20
# @Author: guoxiao
# @File: v_m
import subprocess, os, time


def sp_a(file_public_name, file_num, stat_num):
    # file_public_name = "F-925-CPart00"
    # file_num = 9
    # stat_num = 1

    video_files = []
    for i in range(file_num):
        file_name = file_public_name+str(i+stat_num)+".mp4"
        video_files.append(file_name)

    concat_list = 'concat_list.txt'
    start_time = time.time()
    file_real_name = file_public_name.replace('Part00','')
    output = f'{file_path}/{file_real_name}.mp4'  # 输入视频文件路径

    # 创建临时文件以存储视频文件列表
    with open(concat_list, 'w', encoding='utf-8') as f:
        for file in video_files:
                f.write(f"file '{file_path}/{file}'\n")

    # 拼接视频的ffmpeg命令
    ffmpeg_command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_list,
        '-c', 'copy',
        output
    ]

    # 使用subprocess调用ffmpeg进行视频拼接
    subprocess.run(ffmpeg_command, check=True)
    # 删除临时文件
    os.remove(concat_list)
    # 记录结束时间
    end_time = time.time()
    # 计算执行时间
    execution_time = end_time - start_time
    print("执行时间：", execution_time, "秒")

# file_public_name = "F-925-CPart00"
# file_num = 9
# stat_num = 1
file_path = fr"H:\NudeFileZilla\J-AV"
file_l = [
    ['ABP-840_', 2, 1]
]

for i in file_l:
    sp_a(i[0],i[1],i[2])




