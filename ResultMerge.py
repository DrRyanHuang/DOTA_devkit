# 建议先跑通 demo.ipynb 文件之后, 在进行本文件的单步调试
# 该文件用于合并最后检测的结果, 但是不能用来合并刚分割的标注文件
# 
# 即, 将 `Task1_ship.txt` 文件中的 items:
# P1234__0.5__0___924 1 1024 27 1024 53 931 192 919 184
# P1234__0.5__0___924 1 769 101 788 96 804 108 785 114
# P1234__0.5__0___924 1 896 275 916 290 902 312 881 298
# P1234__0.5__0___924 1 19 204 42 196 39 215 19 221
# 合并为:
# P0770 1.0 856.0 696.0 1468.0 1008.0 1340.0 1298.0 716.0 988.0
# P2598 1.0 1364.0 254.0 2128.0 306.0 2028.0 1798.0 1288.0 1754.0
# 并写入 `Task1_ship.txt` 文件中
#
# 即合并结果, 并做NMS
"""
    To use the code, users should to config detpath, annopath and imagesetfile
    detpath is the path for 15 result files, for the format, you can refer to "http://captain.whu.edu.cn/DOTAweb/tasks.html"
    search for PATH_TO_BE_CONFIGURED to config the paths
    Note, the evaluation is on the large scale images
    (上边的链接已经打不开了)
"""
import os
import numpy as np
import dota_utils as util
import re
import time
import polyiou

## the thresh for nms when merge image
nms_thresh = 0.3

def py_cpu_nms_poly(dets, thresh):
    # 这是四边形的 nms

    scores = dets[:, 8]
    polys = []
    areas = []
    for i in range(len(dets)):
        tm_polygon = polyiou.VectorDouble([ dets[i][0], dets[i][1],
                                            dets[i][2], dets[i][3],
                                            dets[i][4], dets[i][5],
                                            dets[i][6], dets[i][7]])
        polys.append(tm_polygon)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        ovr = []
        i = order[0]
        keep.append(i)
        for j in range(order.size - 1):
            iou = polyiou.iou_poly(polys[i], polys[order[j + 1]])
            ovr.append(iou)
        ovr = np.array(ovr)
        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]
    return keep


def py_cpu_nms(dets, thresh):
    # 这是矩形框的 nms

    """Pure Python NMS baseline."""
    #print('dets:', dets)
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    ## index for dets
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]

    return keep


def nmsbynamedict(nameboxdict, nms, thresh):
    # 将每个 ID 对应的 bbox 做nms
    # 最后依旧返回字典, {ID : [bbox, bbox]}
    nameboxnmsdict = {x: [] for x in nameboxdict}
    for imgname in nameboxdict:
        #print('imgname:', imgname)
        #keep = py_cpu_nms(np.array(nameboxdict[imgname]), thresh)
        #print('type nameboxdict:', type(nameboxnmsdict))
        #print('type imgname:', type(imgname))
        #print('type nms:', type(nms))
        keep = nms(np.array(nameboxdict[imgname]), thresh)
        #print('keep:', keep)
        outdets = []
        #print('nameboxdict[imgname]: ', nameboxnmsdict[imgname])
        for index in keep:
            # print('index:', index)
            outdets.append(nameboxdict[imgname][index])
        nameboxnmsdict[imgname] = outdets
    return nameboxnmsdict


# 根据 rate 恢复原来多边形的大小
def poly2origpoly(poly, x, y, rate):

    origpoly = []
    for i in range(int(len(poly)/2)):
        tmp_x = float(poly[i * 2] + x) / float(rate)
        tmp_y = float(poly[i * 2 + 1] + y) / float(rate)
        origpoly.append(tmp_x)
        origpoly.append(tmp_y)
    return origpoly


def mergebase(srcpath, dstpath, nms):

    # for循环循环每一个类, 将每一个类的分割小图合并并做NMS
    # 之后将NMS后的合并结果保存到新目录
    filelist = util.GetFileFromThisRootDir(srcpath) # 获取那15个类的文件夹位置
    for fullname in filelist:
        name = util.custombasename(fullname) # eg: 'Task1_baseball-diamond' 此时还未做NMS
        #print('name:', name)
        dstname = os.path.join(dstpath, name + '.txt')
        with open(fullname, 'r') as f_in:
            nameboxdict = {} # 用来存放每个 ID 文件对应的所有 pred/GT
            lines = f_in.readlines()
            splitlines = [x.strip().split(' ') for x in lines]
            for splitline in splitlines: # 每一行就是一个 obb 框, 循环用来更新 nameboxdict 
                subname = splitline[0]
                splitname = subname.split('__')
                oriname = splitname[0]
                pattern1 = re.compile(r'__\d+___\d+')
                #print('subname:', subname)
                x_y = re.findall(pattern1, subname)
                x_y_2 = re.findall(r'\d+', x_y[0])
                x, y = int(x_y_2[0]), int(x_y_2[1])

                pattern2 = re.compile(r'__([\d+\.]+)__\d+___')

                rate = re.findall(pattern2, subname)[0]

                confidence = splitline[1]
                poly = list(map(float, splitline[2:]))
                origpoly = poly2origpoly(poly, x, y, rate) # 根据 rate 恢复原来的大小
                det = origpoly
                det.append(confidence)
                det = list(map(float, det)) # 将每个元素转化为 float
                if (oriname not in nameboxdict):
                    nameboxdict[oriname] = []
                nameboxdict[oriname].append(det)
            nameboxnmsdict = nmsbynamedict(nameboxdict, nms, nms_thresh) # 将每个ID对应的bbox做nms

            # 上一个循环NMS之后, 重新写每一个类文件有哪些文件ID, 以及对应的ID有哪些obb
            with open(dstname, 'w') as f_out:
                for imgname in nameboxnmsdict:
                    for det in nameboxnmsdict[imgname]:
                        #print('det:', det)
                        confidence = det[-1]
                        bbox = det[0:-1]
                        outline = imgname + ' ' + str(confidence) + ' ' + ' '.join(map(str, bbox))
                        #print('outline:', outline)
                        f_out.write(outline + '\n')
                        # 每一行是：
                        # 'P0770 1.0 638.0 350.0 780.0 422.0 716.0 566.0 564.0 498.0'


def mergebyrec(srcpath, dstpath): # 用来合并矩形的结果(hbb)
    """
    srcpath: result files before merge and nms
    dstpath: result files after merge and nms
    """

    mergebase(srcpath,
              dstpath,
              py_cpu_nms)


def mergebypoly(srcpath, dstpath): # 用来合并多边形的结果(obb)
    """
    srcpath: result files before merge and nms
    dstpath: result files after merge and nms
    """

    mergebase(srcpath,
              dstpath,
              py_cpu_nms_poly)


if __name__ == '__main__':
    # see demo for example
    mergebypoly(r'Task1', 
                r'Task1_merge')
    # mergebyrec()