# coding:utf-8
# @time: 2022/5/10 23:20
# @Author: guoxiao
# @File: tet
#coding=utf-8
import os
import shutil
import os.path
# rootdir = r"H:\NudeFileZilla\BJ"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla\J-AV"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla\Game"# 指明被遍历的文件夹
# rootdir = r"H:\NudeFileZilla\Eastern"
rootdir = r"H:\NudeFileZilla\Deep Face\A temp\原_去衣_AI\X"
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
    for filename in filenames:
        # print(filename)
        # nameList=filename.split('[ThZu.Cc]')
        name = (filename.replace('[ThZu.Cc]', '').replace('@蜂鳥@FENGNIAO151.VIP-','').replace('2048社区 - big2048.com@', '').replace('bbs2048.org@', '')\
            .replace('[Woxav.Com]', '').replace('@蜂鳥@FENGNIAO131.VIP-', '').replace('Netflav - ', '').replace('Watch ', '').replace('hhd800.com@', '')\
            .replace('[Thz.la]', '').replace('【thz.la】', '').replace('[LT20] ', '').replace('[', '').replace(']', '').replace('(', '').replace(')', '')\
            .replace('妄想族','').replace('JavFinder - ','').replace('HD-','').replace(' - Pornhub.com','').replace('  - More at javhd.net','')\
            .replace(' - Jable.TV _ 免費高清AV在線看 _ J片 AV看到飽','').replace(' - XVIDEOS.COM','').replace(' - JAV Free','').replace('M2022010403-','')\
            .replace(' - www.povgirlsHD.com.mp4','').replace('Video ','').replace('freedl.org@','').replace('HD_','').replace('---Jable.TV-_-免費高清AV在線看-_-J片-AV看到飽','')\
            .replace('- Ipx, Big Ass, Japanese, Squirt Porn - SpankBang','').replace('JAV_','').replace('44x.','').replace(' - SpankBang.','').replace(' TG频道@TBBAD','')\
            .replace('X 上的 ','').replace(' - MissAV','').replace('98t.tv','').replace('格式工厂混流_','').replace('_ FC2PPV-','FC2PPV-').replace('hhd800.com','')\
            .replace('_tg关注_@AVWUMAYUANPIAN','').replace('FHD','').replace('_ ','').replace('gc2048.com-','').replace('gc2048.com-','').replace('-TG发布频道@CCTAV','')
            .replace(' Porn - VXXX.com','').replace(' - Jav, Teen, Asian Porn','').replace('ssstwitter.com_','').replace('_','').replace('_','')
            .replace('AI明星换脸 AI ','').replace('Watch','').replace('TG@HentaiLsp','').replace('reb.mp4','_reb.mp4').replace('电报搜 @HaoKanDeAV ','')
            .replace('More-Telegram@HTHUB ','').replace('Watch ','').replace(', Japanese Girl','').replace(', Jav Pmv','').replace('Porn_reb ','_reb')
            .replace(', Anal Porn','').replace('TG@HanLme1','').replace('TG@HanLme1', '').replace('.mp4_reb', '').replace('Partconcat', '').replace(' 电报群@yzdyhw ', '')
            .replace('更多视频Telegram搜索@', '').replace('电报群@', '').replace('更多福利电报搜@', '').replace('绅士联盟电报搜@', '').replace('袋鼠资源电报群@DDSDSZY', '')
            .replace(' @JavCutBot', '').replace('更多精品剪辑@AVVCUT', '').replace(' @javdsp', '').replace(' @JAVDSP', '')
            .replace('@c950511', '').replace('资源 电报群 @CTHHFL', '').replace('kpop', '')
        )

        # name = (filename.replace('_', ''))
        print(name)
        # [082710-465]
        # filenew=nameList[0]+'.jpg'
        # print filenew
        try:
            os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
        except FileExistsError:
            name = (filename.replace('_', '1'))
            os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名

        # try:
        #     os.rename(os.path.join(parent, filename), os.path.join(parent, name))  # 重命名
        # except PermissionError as e :
        #     error_list.append(e)
print(error_list)