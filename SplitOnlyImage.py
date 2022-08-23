# 本文件仅仅用来分割图片，也就是说用来分割 test 集
# 并没有分割对应的标注

import os
import numpy as np
import cv2
import copy
import dota_utils as util

class splitbase():
    def __init__(self,
                 srcpath,
                 dstpath,
                 gap=100,
                 subsize=1024,
                 ext='.png'):

        self.gap = gap # 重叠的像素
        self.subsize = subsize # 子图的大小
        self.slide = self.subsize - self.gap # 裁剪时滑动的位移
        self.srcpath = srcpath  # 未裁剪的图的位置
        self.dstpath = dstpath  # 裁剪后的图的保存位置
        self.ext = ext # 图片后缀


    def saveimagepatches(self, img, subimgname, left, up, ext='.png'):
        # 根据给定的左上角，裁剪对应的patch并保存

        subimg = copy.deepcopy(img[up: (up + self.subsize), left: (left + self.subsize)])
        outdir = os.path.join(self.dstpath, subimgname + ext)
        cv2.imwrite(outdir, subimg)


    def SplitSingle(self, name, rate, extent):
        # 读取，并计算出裁剪 patch 的左上角, 调用 self.saveimagepatches 去保存

        img = cv2.imread(os.path.join(self.srcpath, name + extent))
        assert np.shape(img) != ()

        if (rate != 1):
            resizeimg = cv2.resize(img, None, fx=rate, fy=rate, interpolation = cv2.INTER_CUBIC)
        else:
            resizeimg = img
        outbasename = name + '__' + str(rate) + '__'

        weight = np.shape(resizeimg)[1]
        height = np.shape(resizeimg)[0]
        
        left, up = 0, 0
        while (left < weight):
            if (left + self.subsize >= weight):
                left = max(weight - self.subsize, 0)
            up = 0
            while (up < height):
                if (up + self.subsize >= height):
                    up = max(height - self.subsize, 0)
                subimgname = outbasename + str(left) + '___' + str(up)
                self.saveimagepatches(resizeimg, subimgname, left, up)
                if (up + self.subsize >= height):
                    break
                else:
                    up = up + self.slide
            if (left + self.subsize >= weight):
                break
            else:
                left = left + self.slide


    def splitdata(self, rate): 

        # rate 指要在裁剪前缩放的比例
        
        # 获取该路径下的所有文件
        imagelist = util.GetFileFromThisRootDir(self.srcpath)
        # 获取图片的所有 ID : P2598
        imagenames = [util.custombasename(x) for x in imagelist if (util.custombasename(x) != 'Thumbs')]
        for name in imagenames:
            self.SplitSingle(name, rate, self.ext)

            
if __name__ == '__main__':
    split = splitbase(r'example/images',
                      r'example/imagesSplit')
    split.splitdata(rate=1)