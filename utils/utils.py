import random

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import json
import pickle
import glob
import matplotlib.pyplot as plt
import sys,os

# set printoptions
torch.set_printoptions(linewidth=1320, precision=5, profile='long')
np.set_printoptions(linewidth=320, formatter={'float_kind': '{:11.5g}'.format})  # format short g, %precision=5

def load_classes(xview_names_and_labels_filepath):
    """
    Loads class labels at 'xview_names_and_labels_filepath'
    Format shall be assumed to be csv where one line is (name , label)_i
    """
    names  = []
    labels = []
    with open(xview_names_and_labels_filepath) as f:
        for i,line in enumerate(f):
            name_i,label_i = line.split(',')
            names.append(name_i)
            labels.append(int(label_i))
    # Sort w.r.t. labels
    idx    = np.argsort(labels).astype(int)
    labels = np.array(labels)[idx].tolist()
    names  = np.array(names)[idx].tolist()
    return names,labels

def convert_class_labels_to_indices(class_labels,unique_class_labels):
    """
    Function that takes a list of N class labels and the list of all M<N unique class labels and returns a list of size N, where each entry is the index of the corresponding label in the list of unique class labels. For example, given class_labels = [34,89,34,34,11] and unique_class_labels = [11,34,89], the output = [1,2,1,1,0]. 
    """
    for i in range(len(unique_class_labels)):
        label_i = unique_class_labels[i]
        idx_i   = [i for i,e in enumerate(class_labels) if e == label_i]
        for j in range(len(idx_i)):
            class_labels[idx_i[j]] = i
    return class_labels
        
def modelinfo(model):
    nparams = sum(x.numel() for x in model.parameters())
    ngradients = sum(x.numel() for x in model.parameters() if x.requires_grad)
    print('\n%4s %70s %9s %12s %20s %12s %12s' % ('', 'name', 'gradient', 'parameters', 'shape', 'mu', 'sigma'))
    for i, (name, p) in enumerate(model.named_parameters()):
        name = name.replace('module_list.', '')
        print('%4g %70s %9s %12g %20s %12g %12g' % (
            i, name, p.requires_grad, p.numel(), list(p.shape), p.mean(), p.std()))
    print('\n%g layers, %g parameters, %g gradients' % (i + 1, nparams, ngradients))

def zerocenter_class_indices(classes):
    """
    This function takes a list of N elements with M<N unique labels, and relabels them such that the labels are 0,1,...,M-1. Note that this function assumes that all class labels of interest appear at least once in classes.

    | **Inputs:**
    |    *classes:* N-list of original class indices.

    | **Outputs:**
    |    *classes_zeroed:* N-list of classes relabeled such that the labels are 0...M-1  
    | e.g., [5,9,7,12,7,9] --> [0,2,1,3,1,2]
    """
    classes                 = classes.astype(int)
    classes_unique          = np.unique(classes)
    mapping_to_zeroed       = np.zeros(max(classes_unique)+1).astype(int)
    mapping_to_zeroed[:]    = -1
    mapping_to_zeroed[classes_unique] = np.arange(len(classes_unique))
    classes_zeroed          = [mapping_to_zeroed[int(c)] for c in classes]
    return classes_zeroed

def xview_classes2indices(classes):  # remap xview classes 11-94 to 0-61
    indices = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 1, 2, -1, 3, -1, 4, 5, 6, 7, 8, -1, 9, 10, 11, 12, 13, 14,
               15, -1, -1, 16, 17, 18, 19, 20, 21, 22, -1, 23, 24, 25, -1, 26, 27, -1, 28, -1, 29, 30, 31, 32, 33, 34,
               35, 36, 37, -1, 38, 39, 40, 41, 42, 43, 44, 45, -1, -1, -1, -1, 46, 47, 48, 49, -1, 50, 51, -1, 52, -1,
               -1, -1, 53, 54, -1, 55, -1, -1, 56, -1, 57, -1, 58, 59]
    return [indices[int(c)] for c in classes]


def xview_indices2classes(indices):  # remap xview classes 11-94 to 0-61
    class_list = [11, 12, 13, 15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 32, 33, 34, 35, 36, 37, 38, 40, 41,
                  42, 44, 45, 47, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 62, 63, 64, 65, 66, 71, 72, 73, 74,
                  76, 77, 79, 83, 84, 86, 89, 91, 93, 94]
    return class_list[indices]


def xview_class_weights(indices):  # weights of each class in the training set, normalized to mu = 1
    weights = 1 / torch.FloatTensor(
        [74, 364, 713, 71, 2925, 209767, 6925, 1101, 3612, 12134, 5871, 3640, 860, 4062, 895, 149, 174, 17, 1624, 1846,
         125, 122, 124, 662, 1452, 697, 222, 190, 786, 200, 450, 295, 79, 205, 156, 181, 70, 64, 337, 1352, 336, 78,
         628, 841, 287, 83, 702, 1177, 313865, 195, 1081, 882, 1059, 4175, 123, 1700, 2317, 1579, 368, 85])
    weights /= weights.sum()
    return weights[indices]


def xview_class_weights_hard_mining(indices):  # weights of each class in the training set, normalized to mu = 1
    weights = 1 / torch.FloatTensor(
        [33.97268, 93.15154, 65.63010, 25.50680, 315.10718, 11155.36523, 435.13831, 90.31747, 243.61844, 949.65210,
         617.89618, 444.08023, 288.31467, 624.93048, 172.96718, 32.82379, 40.19281, 20.85552, 489.79105, 611.20111,
         59.31967, 56.11718, 34.23215, 165.60268, 555.22137, 362.42404, 57.16855, 50.70805, 169.26582, 63.82553,
         157.74074, 76.08432, 20.93476, 32.51611, 22.38825, 33.12125, 34.09357, 24.90087, 59.74687, 200.52057,
         64.62336, 46.36672, 103.29935, 110.10422, 145.03802, 17.35346, 226.90453, 89.09844, 10227.20508, 46.64930,
         90.11716, 49.69421, 116.69005, 269.13092, 37.82637, 173.11961, 490.53397, 447.31345, 17.29692, 14.43979])
    weights /= weights.sum()
    return weights[indices]


def plot_one_box(x, im, color=None, label=None, line_thickness=None):
    tl = line_thickness or round(0.003 * max(im.shape[0:2]))  # line thickness
    color = color or [random.randint(0, 255) for _ in range(3)]
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    cv2.rectangle(im, c1, c2, color, thickness=tl)
    if label:
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(im, c1, c2, color, -1)  # filled
        cv2.putText(im, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)


def weights_init_normal(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        torch.nn.init.normal_(m.weight.data, 0.0, 0.03)
    elif classname.find('BatchNorm2d') != -1:
        torch.nn.init.normal_(m.weight.data, 1.0, 0.03)
        torch.nn.init.constant_(m.bias.data, 0.0)


def xyxy2xywh(box):
    xywh = np.zeros(box.shape)
    xywh[:, 0] = (box[:, 0] + box[:, 2]) / 2
    xywh[:, 1] = (box[:, 1] + box[:, 3]) / 2
    xywh[:, 2] = box[:, 2] - box[:, 0]
    xywh[:, 3] = box[:, 3] - box[:, 1]
    return xywh


def compute_ap(recall, precision):
    """ Compute the average precision, given the recall and precision curves.
    Code originally from https://github.com/rbgirshick/py-faster-rcnn.
    # Arguments
        recall:    The recall curve (list).
        precision: The precision curve (list).
    # Returns
        The average precision as computed in py-faster-rcnn.
    """
    # correct AP calculation
    # first append sentinel values at the end
    mrec = np.concatenate(([0.], recall, [1.]))
    mpre = np.concatenate(([0.], precision, [0.]))

    # compute the precision envelope
    for i in range(mpre.size - 1, 0, -1):
        mpre[i - 1] = np.maximum(mpre[i - 1], mpre[i])

    # to calculate area under PR curve, look for points
    # where X axis (recall) changes value
    i = np.where(mrec[1:] != mrec[:-1])[0]

    # and sum (\Delta recall) * prec
    ap = np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1])
    return ap


def bbox_iou(box1, box2, x1y1x2y2=True):
    # if len(box1.shape) == 1:
    #    box1 = box1.reshape(1, 4)

    """
    Returns the IoU of two bounding boxes
    """
    if x1y1x2y2:
        # Get the coordinates of bounding boxes
        b1_x1, b1_y1, b1_x2, b1_y2 = box1[:, 0], box1[:, 1], box1[:, 2], box1[:, 3]
        b2_x1, b2_y1, b2_x2, b2_y2 = box2[:, 0], box2[:, 1], box2[:, 2], box2[:, 3]
    else:
        # Transform from center and width to exact coordinates
        b1_x1, b1_x2 = box1[:, 0] - box1[:, 2] / 2, box1[:, 0] + box1[:, 2] / 2
        b1_y1, b1_y2 = box1[:, 1] - box1[:, 3] / 2, box1[:, 1] + box1[:, 3] / 2
        b2_x1, b2_x2 = box2[:, 0] - box2[:, 2] / 2, box2[:, 0] + box2[:, 2] / 2
        b2_y1, b2_y2 = box2[:, 1] - box2[:, 3] / 2, box2[:, 1] + box2[:, 3] / 2

    # get the corrdinates of the intersection rectangle
    inter_rect_x1 = torch.max(b1_x1, b2_x1)
    inter_rect_y1 = torch.max(b1_y1, b2_y1)
    inter_rect_x2 = torch.min(b1_x2, b2_x2)
    inter_rect_y2 = torch.min(b1_y2, b2_y2)
    # Intersection area
    inter_area = torch.clamp(inter_rect_x2 - inter_rect_x1, 0) * torch.clamp(inter_rect_y2 - inter_rect_y1, 0)
    # Union Area
    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)

    return inter_area / (b1_area + b2_area - inter_area + 1e-16)


def build_targets(pred_boxes, pred_conf, pred_cls, target, anchor_wh, nA, nC, nG, requestPrecision):
    """
    returns nGT, nCorrect, tx, ty, tw, th, tconf, tcls
    """
    nB = len(target)  # target.shape[0]
    nT = [len(x) for x in target]  # torch.argmin(target[:, :, 4], 1)  # targets per image
    tx = torch.zeros(nB, nA, nG, nG)  # batch size (4), number of anchors (3), number of grid points (13)
    ty = torch.zeros(nB, nA, nG, nG)
    tw = torch.zeros(nB, nA, nG, nG)
    th = torch.zeros(nB, nA, nG, nG)
    tconf = torch.ByteTensor(nB, nA, nG, nG).fill_(0)
    tcls = torch.ByteTensor(nB, nA, nG, nG, nC).fill_(0)  # nC = number of classes
    TP = torch.ByteTensor(nB, max(nT)).fill_(0)
    FP = torch.ByteTensor(nB, max(nT)).fill_(0)
    FN = torch.ByteTensor(nB, max(nT)).fill_(0)
    TC = torch.ShortTensor(nB, max(nT)).fill_(-1)  # target category

    for b in range(nB):
        nTb = nT[b]  # number of targets (measures index of first zero-height target box)
        if nTb == 0:
            continue
        t = target[b]  # target[b, :nTb]
        FN[b, :nTb] = 1

        # Convert to position relative to box
        TC[b, :nTb], gx, gy, gw, gh = t[:, 0].long(), t[:, 1] * nG, t[:, 2] * nG, t[:, 3] * nG, t[:, 4] * nG
        # Get grid box indices and prevent overflows (i.e. 13.01 on 13 anchors)
        gi = torch.clamp(gx.long(), min=0, max=nG - 1)
        gj = torch.clamp(gy.long(), min=0, max=nG - 1)

        # iou of targets-anchors (using wh only)
        box1 = t[:, 3:5] * nG
        # box2 = anchor_grid_wh[:, gj, gi]
        box2 = anchor_wh.unsqueeze(1).repeat(1, nTb, 1)
        #import pdb; pdb.set_trace()
        inter_area = torch.min(box1, box2).prod(2)
        iou_anch = inter_area / (gw * gh + box2.prod(2) - inter_area + 1e-16)

        # Select best iou_pred and anchor
        iou_anch_best, a = iou_anch.max(0)  # best anchor [0-2] for each target

        # Two targets can not claim the same anchor
        if nTb > 1:
            iou_order = np.argsort(-iou_anch_best)  # best to worst
            # u = torch.cat((gi, gj, a), 0).view(3, -1).numpy()
            # _, first_unique = np.unique(u[:, iou_order], axis=1, return_index=True)  # first unique indices
            u = gi.float() * 0.4361538773074043 + gj.float() * 0.28012496588736746 + a.float() * 0.6627147212460307
            _, first_unique = np.unique(u[iou_order], return_index=True)  # first unique indices
            # print(((np.sort(first_unique) - np.sort(first_unique2)) ** 2).sum())
            i = iou_order[first_unique]
            # best anchor must share significant commonality (iou) with target
            i = i[iou_anch_best[i] > 0.10]
            if len(i) == 0:
                continue

            a, gj, gi, t = a[i], gj[i], gi[i], t[i]
            if len(t.shape) == 1:
                t = t.view(1, 5)
        else:
            if iou_anch_best < 0.10:
                continue
            i = 0

        tc, gx, gy, gw, gh = t[:, 0].long(), t[:, 1] * nG, t[:, 2] * nG, t[:, 3] * nG, t[:, 4] * nG

        # Coordinates
        tx[b, a, gj, gi] = gx - gi.float()
        ty[b, a, gj, gi] = gy - gj.float()
        # Width and height
        tw[b, a, gj, gi] = torch.sqrt(gw / anchor_wh[a, 0]) / 2
        th[b, a, gj, gi] = torch.sqrt(gh / anchor_wh[a, 1]) / 2

        # One-hot encoding of label
        tcls[b, a, gj, gi, tc] = 1
        tconf[b, a, gj, gi] = 1

        if requestPrecision:
            # predicted classes and confidence
            tb = torch.cat((gx - gw / 2, gy - gh / 2, gx + gw / 2, gy + gh / 2)).view(4, -1).t()  # target boxes
            pcls = torch.argmax(pred_cls[b, a, gj, gi], 1).cpu()
            pconf = torch.sigmoid(pred_conf[b, a, gj, gi]).cpu()
            iou_pred = bbox_iou(tb, pred_boxes[b, a, gj, gi].cpu())

            TP[b, i] = (pconf > 0.99) & (iou_pred > 0.5) & (pcls == tc)
            FP[b, i] = (pconf > 0.99) & (TP[b, i] == 0)  # coordinates or class are wrong
            FN[b, i] = pconf <= 0.99  # confidence score is too low (set to zero)

    return tx, ty, tw, th, tconf, tcls, TP, FP, FN, TC


def non_max_suppression(prediction, conf_thres=0.5, nms_thres=0.4, mat=None, opt=None, img=None, model2=None, device='cpu'):
    prediction = prediction.cpu()

    """
    Removes detections with lower object confidence score than 'conf_thres' and performs
    Non-Maximum Suppression to further filter detections.
    Returns detections with shape:
        (x1, y1, x2, y2, object_conf, class_score, class_pred)
    """

    output = [None for _ in range(len(prediction))]
    for image_i, pred in enumerate(prediction):
        # Filter out confidence scores below threshold
        # Get score and class with highest confidence

        # cross-class NMS
        if model2 is not None:
            thresh = 0.85
            a = pred.clone()
            a = a[np.argsort(-a[:, 4])]  # sort best to worst
            radius = 30  # area to search for cross-class ious
            for i in range(len(a)):
                if i >= len(a) - 1:
                    break

                close = (np.abs(a[i, 0] - a[i + 1:, 0]) < radius) & (np.abs(a[i, 1] - a[i + 1:, 1]) < radius)
                close = close.nonzero()

                if len(close) > 0:
                    close = close + i + 1
                    iou = bbox_iou(a[i:i + 1, :4], a[close.squeeze(), :4].reshape(-1, 4), x1y1x2y2=False)
                    bad = close[iou > thresh]

                    if len(bad) > 0:
                        mask = torch.ones(len(a)).type(torch.ByteTensor)
                        mask[bad] = 0
                        a = a[mask]
            pred = a

        x, y, w, h = pred[:, 0].numpy(), pred[:, 1].numpy(), pred[:, 2].numpy(), pred[:, 3].numpy()
        a = w * h  # area
        ar = w / (h + 1e-16)  # aspect ratio
        log_w, log_h, log_a, log_ar = np.log(w), np.log(h), np.log(a), np.log(ar)

        # n = len(w)
        # shape_likelihood = np.zeros((n, 60), dtype=np.float32)
        # x = np.concatenate((log_w.reshape(-1, 1), log_h.reshape(-1, 1)), 1)
        # from scipy.stats import multivariate_normal
        # for c in range(60):
        # shape_likelihood[:, c] = multivariate_normal.pdf(x, mean=mat['class_mu'][c, :2], cov=mat['class_cov'][c, :2, :2])

        if model2 is None:
            class_prob, class_pred = torch.max(F.softmax(pred[:, 5:], 1), 1)
        else:
            # Start secondary classification of each chip
            class_prob, class_pred = secondary_class_detection(x, y, w, h, img.copy(), model2, device)
            # for i in range(len(class_prob2)):
            #     if class_prob2[i] > class_prob[i]:
            #         class_pred[i] = class_pred2[i]

        # Gather bbox priors
        srl = 6  # sigma rejection level
        if ((opt == None) & (mat != None)):
            mu    = mat['class_mu'][class_pred].T
            sigma = mat['class_sigma'][class_pred].T * srl            
        elif ((opt != None) & (mat == None)):
            mu    = np.loadtxt(opt.class_mean  , delimiter = ',')[class_pred].T
            sigma = np.loadtxt(opt.class_sigma , delimiter = ',')[class_pred].T * srl
        else:
            sys.exit('Must provide either at matlab .mat file or csv-delimted file for class stats')

        v = ((pred[:, 4] > conf_thres) & (class_prob > .3)).numpy()
        v *= (a > 20) & (w > 4) & (h > 4) & (ar < 10) & (ar > 1 / 10)
        v *= (log_w > mu[0] - sigma[0]) & (log_w < mu[0] + sigma[0])
        v *= (log_h > mu[1] - sigma[1]) & (log_h < mu[1] + sigma[1])
        v *= (log_a > mu[2] - sigma[2]) & (log_a < mu[2] + sigma[2])
        v *= (log_ar > mu[3] - sigma[3]) & (log_ar < mu[3] + sigma[3])
        v = v.nonzero()

        pred = pred[v]
        class_prob = class_prob[v]
        class_pred = class_pred[v]
        # x, y, w, h = x[v], y[v], w[v], h[v]

        # If none are remaining => process next image
        nP = pred.shape[0]
        if not nP:
            continue

        # From (center x, center y, width, height) to (x1, y1, x2, y2)
        box_corner = pred.new(nP, 4)
        xy = pred[:, 0:2]
        wh = pred[:, 2:4] / 2
        box_corner[:, 0:2] = xy - wh
        box_corner[:, 2:4] = xy + wh
        pred[:, :4] = box_corner

        # Detections ordered as (x1, y1, x2, y2, obj_conf, class_prob, class_pred)
        detections = torch.cat((pred[:, :5], class_prob.float().unsqueeze(1), class_pred.float().unsqueeze(1)), 1)
        # Iterate through all predicted classes
        unique_labels = detections[:, -1].cpu().unique()
        if prediction.is_cuda:
            unique_labels = unique_labels.cuda()

        nms_style = 'OR'  # 'AND' or 'OR' (classical)
        for c in unique_labels:
            # Get the detections with the particular class
            detections_class = detections[detections[:, -1] == c]
            # Sort the detections by maximum objectness confidence
            _, conf_sort_index = torch.sort(detections_class[:, 4], descending=True)
            detections_class = detections_class[conf_sort_index]
            # Perform non-maximum suppression
            max_detections = []

            if nms_style == 'OR':  # Classical NMS
                while detections_class.shape[0]:
                    # Get detection with highest confidence and save as max detection
                    max_detections.append(detections_class[0].unsqueeze(0))
                    # Stop if we're at the last detection
                    if len(detections_class) == 1:
                        break
                    # Get the IOUs for all boxes with lower confidence
                    ious = bbox_iou(max_detections[-1], detections_class[1:])

                    # Remove detections with IoU >= NMS threshold
                    detections_class = detections_class[1:][ious < nms_thres]

            elif nms_style == 'AND':  # 'AND'-style NMS, at least two boxes must share commonality to pass, single boxes erased
                while detections_class.shape[0]:
                    if len(detections_class) == 1:
                        break

                    ious = bbox_iou(detections_class[:1], detections_class[1:])

                    if ious.max() > 0.5:
                        max_detections.append(detections_class[0].unsqueeze(0))

                    # Remove detections with IoU >= NMS threshold
                    detections_class = detections_class[1:][ious < nms_thres]

            if len(max_detections) > 0:
                max_detections = torch.cat(max_detections).data
                # Add max detections to outputs
                output[image_i] = max_detections if output[image_i] is None else torch.cat(
                    (output[image_i], max_detections))

    return output


def secondary_class_detection(x, y, w, h, img, model, device):
    # Runs secondary classifier on bounding boxes
    print('Classifying boxes...', end='')

    # 1. create 48-pixel squares from each chip
    img = np.ascontiguousarray(img.transpose([1, 2, 0]))  # torch to cv2 (i.e. cv2 = 608 x 608 x 3)
    height = 64

    # img -= np.array([60.134, 49.697, 40.746]).reshape((1, 1, 3))  # rgb_mean
    # img /= np.array([29.990, 24.498, 22.046]).reshape((1, 1, 3))  # rgb_std

    l = np.round(np.maximum(w, h) * 1.10 + 2) / 2
    x1 = np.maximum(x - l, 1).astype(np.uint16)
    x2 = np.minimum(x + l, img.shape[1]).astype(np.uint16)
    y1 = np.maximum(y - l, 1).astype(np.uint16)
    y2 = np.minimum(y + l, img.shape[0]).astype(np.uint16)

    n = len(x)
    images = []
    for i in range(n):
        images.append(cv2.resize(img[y1[i]:y2[i], x1[i]:x2[i]], (height, height), interpolation=cv2.INTER_LINEAR))

    # # plot
    # images_numpy = images.copy()
    # import matplotlib.pyplot as plt
    # rgb_mean = [60.134, 49.697, 40.746]
    # rgb_std = [29.99, 24.498, 22.046]
    # for i in range(36):
    #     im = images_numpy[i + 300].copy()
    #     for j in range(3):
    #         im[:, :, j] *= rgb_std[j]
    #         im[:, :, j] += rgb_mean[j]
    #
    #     im /= 255
    #     plt.subplot(6, 6, i + 1).imshow(im)

    images = np.stack(images).transpose([0, 3, 1, 2])  # cv2 to pytorch
    images = np.ascontiguousarray(images)
    images = torch.from_numpy(images).to(device)

    with torch.no_grad():
        classes = []
        nB = int(n / 1000) + 1  # number of batches
        print('%g batches...' % nB, end='')
        for i in range(nB):
            print('%g ' % i, end='')
            j0 = int(i * 1000)
            j1 = int(min(j0 + 1000, n))
            im = images[j0:j1]
            classes.append(model(im).cpu())

        classes = torch.cat(classes, 0)
    return torch.max(F.softmax(classes, 1), 1)


def createChips():
    # Creates *.h5 file of all chips in xview dataset for training independent classifier

    import scipy.io
    import numpy as np
    import cv2
    import h5py
    from sys import platform

    mat = scipy.io.loadmat('utils/targets_c60.mat')
    unique_images = np.unique(mat['id'])

    height = 64
    full_height = 128
    X, Y = [], []
    for counter, i in enumerate(unique_images):
        print(counter)

        if platform == 'darwin':  # macos
            img = cv2.imread('/Users/glennjocher/Downloads/DATA/xview/train_images/%g.bmp' % i)
        else:  # gcp
            img = cv2.imread('../train_images/%g.bmp' % i)

        for j in np.nonzero(mat['id'] == i)[0]:
            c, x1, y1, x2, y2 = mat['targets'][j]
            x, y, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
            if ((c == 48) | (c == 5)) & (random.random() > 0.1):  # keep only 10% of buildings and cars
                continue

            l = np.round(np.maximum(w, h) * 1.1 + 2) / 2 * (full_height / height)  # square
            lx, ly = l, l

            x1 = np.maximum(x - lx, 1).astype(np.uint16)
            x2 = np.minimum(x + lx, img.shape[1]).astype(np.uint16)
            y1 = np.maximum(y - ly, 1).astype(np.uint16)
            y2 = np.minimum(y + ly, img.shape[0]).astype(np.uint16)

            img2 = cv2.resize(img[y1:y2, x1:x2], (full_height, full_height), interpolation=cv2.INTER_LINEAR)

            X.append(img2[np.newaxis])
            Y.append(c)

        # plot
        # import matplotlib.pyplot as plt
        # for j in range(36):
        #     plt.subplot(6, 6, j + 1).imshow(X[-36 + j][0, 32:-32, 32:-32, ::-1])

    X = np.concatenate(X)[:, :, :, ::-1]
    X = torch.from_numpy(np.ascontiguousarray(X))
    Y = torch.from_numpy(np.ascontiguousarray(np.array(Y))).long()

    with h5py.File('chips_10pad_square.h5') as hf:
        hf.create_dataset('X', data=X)
        hf.create_dataset('Y', data=Y)


def strip_optimizer_from_checkpoint(filename='checkpoints/best.pt'):
    # Strip optimizer from *.pt files for lighter files (reduced by 2/3 size)
    import torch
    a = torch.load(filename, map_location='cpu')
    a['optimizer'] = []
    torch.save(a, filename.replace('.pt', '_lite.pt'))


def plotResults(resultsfilepath):
    # Plot YOLO training results
    import numpy as np
    import matplotlib.pyplot as plt
    plt.figure(figsize=(16, 8))
    s = ['X', 'Y', 'Width', 'Height', 'Objectness', 'Classification', 'Total Loss', 'Precision', 'Recall','PrecisionVsRecall']
    for f in (resultsfilepath,):
        results = np.loadtxt(f, usecols=[2, 3, 4, 5, 6, 7, 8, 9, 10]).T
        for i in range(9):
            plt.subplot(2, 5, i + 1)
            plt.plot(results[i, :300], marker='.', label=f)
            plt.title(s[i])
        # Last plot: PrecisionVsRecall
        plt.subplot(2,5,10)
        plt.plot(results[8, :300], results[7, :300], marker='.')
        plt.plot([0,.6],[0,.6],'k--')
        plt.gca().set_aspect('equal')
        plt.title('PrecisionVsRecall')
        plt.legend()
    plt.show()

def save_obj(obj, name):
    with open( name , 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name, 'rb') as f:
        return pickle.load(f)

def pruneTargetFile(nums,mat):
    # Strip away all data from target matrix except those images whose numbers are specified by nums
    allid = mat['image_numbers']
    iddel = np.setdiff1d(allid,nums);
    for i in range(len(iddel)):
        idx            = np.ravel(np.where(mat['id'] == float(iddel[i]))[0])
        mat['id']      = np.delete(mat['id'],idx,axis=0)
        mat['targets'] = np.delete(mat['targets'],idx,axis=0)
        mat['wh']      = np.delete(mat['wh'],idx,axis=0)
        idx            = np.where(mat['image_numbers'] == iddel[i])[0][0]
        mat['image_numbers'] = np.delete(mat['image_numbers'],idx,axis=0) 
        mat['image_weights'] = np.delete(mat['image_weights'],idx,axis=0)
    return mat;

def plot_rgb_image(img,rgb_mean,rgb_std,obj=[]):
    for j in range(3):
        img[:, :, j] *= rgb_std[j]
        img[:, :, j] += rgb_mean[j]
    img /= 255
    if (obj != []):
        nobj = np.shape(obj)[0]
        for i in range(nobj):
            obji = obj[i];
            x0,y0,dx,dy = obji
            xlb = x0 - dx/2.
            xlt = xlb
            xrb = x0 + dx/2.
            xrt = xrb
            ylb = y0 - dy/2.
            yrb = ylb
            ylt = y0 + dy/2.
            yrt = ylt
            plt.plot([xlb,xrb,xrt,xlt,xlb],[ylb,yrb,yrt,ylt,ylb],'g',lw=2);
    plt.imshow(img)
    plt.show()

def readBmpDataset(path):
    """
    Function to read a .bmp dataset. If the provided directory does not contain .bmp files, a conversion is attempted.

    | **Inputs:**
    |   *path:* Absolute path to the dataset directory
    """
    # Read all image files from path directory, converting tif --> bmp if necessary
    filesbmp  = sorted(glob.glob('%s/*.bmp' % path))
    nbmp      = len(filesbmp)
    # If .tif data exists, convert it; if not, exit
    if (nbmp == 0):
        print('No .bmp data detected, checking for .tif...')
        filestif = sorted(glob.glob('%s/*.tif' % path))
        ntif     = len(filestif)
        if (ntif > 0):
            print('Converting .tif --> .bmp (.tif originals retained)...')
            convert_tif2bmp(path)
            filesbmp  = sorted(glob.glob('%s/*.bmp' % path))
            return filesbmp
        else:
            sys.exit('Neither .bmp nor .tif data found, exiting.')
    else:
        return filesbmp;

def convert_tif2bmp(p):
    """
    Function to convert .tif --> .bmp

    | **Inputs:**
    |   *p:* Absolute path to the dataset directory
    """
    import glob
    import cv2
    files = sorted(glob.glob('%s/*.tif' % p))
    for i, f in enumerate(files):
        img = cv2.imread(f)
        cv2.imwrite(f.replace('.tif', '.bmp'), img)
        #os.system('rm -rf ' + f)

def assert_single_gpu_support():
    """
    Function to check that only a single GPU is being used.
    Currently, all software must be run with a single GPU only, so this routine does a simple assert check on the environment variable that ensures this.
    """
    numGPU  = torch.cuda.device_count()
    try:
        assert( numGPU <= 1 )
    except AssertionError as e:
        e.args += ('Multiple GPUs detected. Currently, multiple GPU support is not available for this software. Please re-run this software in single-GPU mode, e.g. by setting the CUDA_VISIBLE_DEVICES environment variable (see documentation for details.',)
        raise
