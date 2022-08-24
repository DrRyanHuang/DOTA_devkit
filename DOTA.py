#The code is used for visulization, inspired from cocoapi
#  Licensed under the Simplified BSD License [see bsd.txt]

import os
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon, Circle
import numpy as np
import dota_utils as util
from collections import defaultdict
import cv2


def _isArrayLike(obj):
    if type(obj) == str: # 如果是字符串则直接返回
        return False
    # 是否可迭代
    return hasattr(obj, '__iter__') and hasattr(obj, '__len__')

class DOTA:
    def __init__(self, basepath):
        self.basepath = basepath
        self.labelpath = os.path.join(basepath, 'labelTxt')
        self.imagepath = os.path.join(basepath, 'images')
        self.imgpaths = util.GetFileFromThisRootDir(self.imagepath)
        self.labpaths = util.GetFileFromThisRootDir(self.labelpath)
        self.imglist = [util.custombasename(x) for x in self.imgpaths]
        self.catToImgs = defaultdict(list) # cls: `ship` -> ["P0010", "P0030", ......]
        self.ImgToAnns = defaultdict(list) # P0010 -> 标注信息
        self.createIndex()

        # 将文件ID写入文件
        imageset_path = os.path.join(basepath, "imageset.txt")
        with open(imageset_path, "w") as f:
            f.write("\n".join(self.imglist))

    def createIndex(self):

        # 就是将 self.catToImgs 与 self.ImgToAnns 填充完毕
        for filename in self.labpaths:
            objects = util.parse_dota_poly(filename)
            imgid = util.custombasename(filename)
            self.ImgToAnns[imgid] = objects
            for obj in objects:
                cat = obj['name']
                self.catToImgs[cat].append(imgid)


    # 根据传入类别返回图片ID: P0010
    def getImgIds(self, catNms=[]):
        """
        :param catNms: category names
        :return: all the image ids contain the categories
        """
        catNms = catNms if _isArrayLike(catNms) else [catNms]
        if len(catNms) == 0:
            # 如果啥[类]都不传入，则都返回
            return self.imglist
        else:
            imgids = set()
            for i, cat in enumerate(catNms):
                if i == 0:
                    imgids = set(self.catToImgs[cat])
                else:
                    imgids &= set(self.catToImgs[cat])
        return list(imgids)


    # 加载标注
    # 注意 imgId 只能传入单个 ID
    def loadAnns(self, catNms=[], imgId = None, difficult=None):
        """
        :param catNms: category names
        :param imgId: the img to load anns
        :return: objects
        """
        catNms = catNms if _isArrayLike(catNms) else [catNms]
        objects = self.ImgToAnns[imgId]
        if len(catNms) == 0:
            return objects
        outobjects = [obj for obj in objects if (obj['name'] in catNms)]
        return outobjects



    def showAnns(self, objects, imgId, range):
        """
        :param catNms: category names
        :param objects: objects to show
        :param imgId: img to show
        :param range: display range in the img (暂时没被使用)
        :return:
        """
        img = self.loadImgs(imgId)[0]
        plt.imshow(img)
        plt.axis('off') # 把图中的轴去掉

        ax = plt.gca()
        ax.set_autoscale_on(False)
        polygons = [] # 用来存放 orented bbox
        color = []
        circles = []
        r = 5 # 圆圈半径

        for obj in objects:
            c = (np.random.random((1, 3)) * 0.6 + 0.4).tolist()[0] # 颜色
            poly = obj['poly'] # 多边形的4个点
            polygons.append(Polygon(poly))
            color.append(c)
            point = poly[0]
            circle = Circle((point[0], point[1]), r)  # obb 第0个点绘制圆圈
            circles.append(circle)

        p = PatchCollection(polygons, facecolors=color, linewidths=0, alpha=0.4) # 绘制内部半透明效果
        ax.add_collection(p)
        p = PatchCollection(polygons, facecolors='none', edgecolors=color, linewidths=2) # 绘制外部边框
        ax.add_collection(p)
        p = PatchCollection(circles, facecolors='red') # 绘制第0个点的圈圈
        ax.add_collection(p)
        plt.show()


    # 根据 imgID: P0010 => np.ndarray
    def loadImgs(self, imgids=[]):
        """
        :param imgids: integer ids specifying img
        :return: loaded img objects
        """
        # print('isarralike:', _isArrayLike(imgids))
        imgids = imgids if _isArrayLike(imgids) else [imgids]
        print('imgids:', imgids)
        imgs = []
        for imgid in imgids:
            filename = os.path.join(self.imagepath, imgid + '.png')
            assert os.path.exists(filename), 'Filename: `{}` not exists.'.format(filename)
            # print('filename:', filename)
            img = cv2.imread(filename)
            imgs.append(img)
        return imgs


if __name__ == '__main__':
    examplesplit = DOTA('example')
    imgids = examplesplit.getImgIds(catNms=['plane']) # 根据类别找对应的图片
    img = examplesplit.loadImgs(imgids) # 根据图片ID P0010 加载图片(是个列表)
    for imgid in imgids:
        anns = examplesplit.loadAnns(imgId=imgid) # 根据图片ID加载标注
        examplesplit.showAnns(anns, imgid, 2) # 根据图片ID绘制标注，无需传入图片 np.ndarray