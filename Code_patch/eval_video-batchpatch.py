# -*- coding: utf-8 -*-
"""
Created on Thu Nov  9 12:54:02 2017

@author: jiezhen_sx
"""

from datetime import datetime
import numpy as np
import tensorflow as tf
import tensorflow.contrib.slim as slim
from tensorflow.python.ops import control_flow_ops
import os, sys, cv2
import random
import time
from PIL import Image, ImageDraw, ImageFont
from net import tiny_darknet
from sliding_window_batch import output_batchpatch
import subprocess
import shutil
#from decode_tools import decode_from_tfrecords_eval
##use ffmpeg to decode 6min video to jpgs
##detect every img that diff_mean_gray > 5 

#os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
thre_percent = 0.2

def eval_video(w, h, im):
    with tf.Graph().as_default():
        with tf.variable_scope("model") as scope:
            thre = 0.875
            HP = 0
#            x = tf.placeholder(tf.float32, [None, h, w, 3])
            patch_tf, all_windows = output_batchpatch(im)
            logits_eval = tiny_darknet(patch_tf,False)
            logits_eval = tf.reduce_mean(logits_eval,[1,2])
#            loss_eval =  tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels_eval, logits=logits_eval)
            logits_eval = tf.nn.sigmoid(logits_eval)
             
            saver = tf.train.Saver(tf.all_variables())
            init = tf.initialize_all_variables()
            sess = tf.Session(config=tf.ConfigProto(log_device_placement=False))
            sess = tf.Session()
            sess.run(init)
            sess.run(tf.local_variables_initializer())
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess=sess, coord=coord)

            ckpt = tf.train.get_checkpoint_state(r"/root/linjian/darknet_0/models/try-linjian/JZ_data/new_0_wd4e5-0.15")
#####            ckpt = tf.train.get_checkpoint_state(r"/root/linjian/darknet_0/models/lj")
            saver.restore(sess, ckpt.all_model_checkpoint_paths[-2])
             
            l = sess.run([logits_eval])
            print l, l.get_shape().as_list()
#7-4            p = l[0][0]
            for i in range(all_windows):
                p = l[0][i]
                if p[1]<= thre:
#                    print("----------------------")
#                    print p
                    HP += 1
                    print("-------"+str(HP))
#6-25                shutil.copy(obj_from, os.path.join(pick_out, time_jpg+'.jpg'))
#                else:
#                    HP = 0
            coord.request_stop()
            coord.join(threads)
            return HP, p[0], p[1], all_windows

if __name__ == '__main__':
    videoFilePath = r"/root/linjian/darknet_patch/video/"
    temp_jpgPath = r"/root/temp_img/"
    jpg_OutPath = r"/root/temp_img/%5d.jpg"
    HP_OutPath = videoFilePath+"diffmpeg_test2"
    start_time = 0
    end_time = 6*60
    shell_command_0 = r"ffmpeg -i "+videoFilePath
#    shell_command_0 = shell_command_0+r"116475395_0.mkv -s 320x180 -sws_flags bilinear "
    shell_command_0 = shell_command_0+r"test2.mkv "
    videoFile = cv2.VideoCapture(videoFilePath+'test2.mkv')
    totalFrameNumber = videoFile.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)
    rate = videoFile.get(cv2.cv.CV_CAP_PROP_FPS)
    video_time = int(totalFrameNumber/rate)
    videoFile.release()
    iter = 0   #How many 6min in a video
    i = 1 #prevent i yichu(line132), not use it ,just use it to identify the first frame of a video
#    num = 0
    final_HP_num = 0
    HP_patch_num = 0
    msec = 0
    mean_gray = 0.0
    all_windows = 0
    diff_1s_list = []
    if end_time>video_time:   #in case video is shorter than 6min
        end_time = video_time
    while end_time <= video_time:
        shell_command = shell_command_0+r"-ss "+str(start_time)+r" -to "
        shell_command = shell_command+str(end_time)+' '+jpg_OutPath
        subprocess.call(shell_command, shell=True)   #creat 6min imgs
        print("=============== "+str(iter)+" =============== ")
#        print("------ "+shell_command+" ------")

        img_list = os.listdir(temp_jpgPath)
        img_list.sort(key=lambda jpg:int(jpg.split('.')[0]))   #according the number to identify next frame
        for jpg in img_list:
            fps_jpg = int(jpg.split('.')[0])
            msec = 40*fps_jpg+360000*iter   #1/25=0.04s=40ms
#            msec = 40*fps_jpg+msec   #1/25=0.04s=40msREEOR:in 6min's iter msec still add itself is wrong
            ms = msec%1000
            s = msec//1000
            min = s//60
            h_ = min//60
            min_ = min%60
            s_ = s%60
            time_h = str(h_).zfill(2)
            time_min = str(min_).zfill(2)
            time_s = str(s_).zfill(2)
            time_ms = str(ms).zfill(3)
            time_str = time_h+'_'+time_min+'_'+time_s+'_'+time_ms

            find_obj = os.path.join(temp_jpgPath, jpg)
            image = cv2.imread(find_obj)

            if iter==0 and i==1:
                last_BGR = image
                i = 0
            else:
                frameDelta_BGR = cv2.absdiff(last_BGR, image)
                frameDelta_gray = cv2.cvtColor(frameDelta_BGR, cv2.COLOR_BGR2GRAY)
                mean_gray = np.mean(frameDelta_gray)
                last_BGR = image

            if mean_gray>8.0:
#                image_tf = np.expand_dims(image, 0)
                diff_1s_list.append([mean_gray, image, jpg, time_str])
            if fps_jpg%25 == 0 and (len(diff_1s_list)>0):   #every 1s ==every 25 jpgs
                try:
                    diff_1s_list.sort(key=lambda list_1s:list_1s[0], reverse=True)   #mean_gray large2small sort
                except ValueError:
                    error_log = open(r"/root/linjian/darknet_0/video/error_log.txt","a")
                    error_log.write(str(len(diff_1s_list))+"\n")
                    for ii in range(len(diff_1s_list)):
                        error_log.write(str(diff_1s_list[ii][0])+"\n")
                    error_log.close()
                else:
                    if len(diff_1s_list)<=3:
                        top = len(diff_1s_list)
                    else:
                        top = 3
                    for top3 in range(top):   #every top3 init img
                        obj_Path = os.path.join(temp_jpgPath, diff_1s_list[top3][2])
                        ##############output_patch##############
                        #patch_tf, all_windows = output_batchpatch(diff_1s_list[top3][1])
                        HP_patch_num, HP, YT, all_windows=  eval_video(256, 180, diff_1s_list[top3][1])
#                        if HP_patch == 1:
#                            HP_patch_num += 1
                        if float(HP_patch_num/all_windows)>thre_percent:
                            final_HP_num += 1
                            shutil.copy(obj_Path, os.path.join(HP_OutPath, diff_1s_list[top3][3]+'.jpg'))
                            print("--------------HP_patch number in one frame : "+str(HP_patch_num))
                            print("--------------all_windows number in one frame : "+str(all_windows))
                            print("-------------- "+diff_1s_list[top3][2]+" --------------")
                            print('--------------How many times HP showed :'+str(final_HP_num))
                            HP_patch_num = 0
                            all_windows = 0
                        ########################################
            if fps_jpg%25 == 0:   #every 1s clear list
                diff_1s_list[:]=[]
            del image
###            i += 1
        subprocess.call(r"rm -rf /root/temp_img/*.jpg", shell=True)
        start_time = end_time
        if start_time == video_time:
            break
        if end_time < video_time:
            end_time +=360
        if end_time > video_time:
                end_time = video_time
        iter += 1

#    videoFile.release()

#eval()


