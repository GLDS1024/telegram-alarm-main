import os, sys
import cv2
import time
import pyautogui
import configparser
import aircv as ac
import numpy as np


def mse(image1,image2):
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    diff = np.square(gray1 - gray2)

    m = np.mean(diff)
    return round(m,2)


if __name__ == "__main__":
    
    pyautogui.PAUSE = 0.005
    
    # path = os.path.dirname(os.path.realpath(sys.executable))
    path = os.path.dirname(os.path.realpath(__file__))

    # load config file
    file = path+'/config.ini'
    con = configparser.ConfigParser()
    con.read(file, encoding='utf-8')
    sections = con.sections()
    items = con.items('app') 
    items = dict(items)
    start = int(items['start'])
    end = int(items['end'])
    print('\033[95m' + 'start:'+str(start)+' end:'+str(end)+ '\033[0m')
    
    # match target file
    pos = None
    while(True):
        im = pyautogui.screenshot()
        im.save(path+'/screenshot.png')
        try:
            imsrc = ac.imread(path+'/screenshot.png')
            if(os.path.exists(path+'/target1.png')):
                imobj = ac.imread(path+'/target1.png') 
                pos = ac.find_template(imsrc, imobj, 0.8)
            if(pos==None):
                print('\033[32m' + 'target1 매치 실패!'+ '\033[0m')
                if(os.path.exists(path+'/target2.png')):
                    imobj1 = ac.imread(path+'/target2.png')
                    pos = ac.find_template(imsrc, imobj1, 0.8)
                if(pos == None):
                    print('\033[32m' + 'target2 매치 실패!'+ '\033[0m')
                else:
                    break;
            else:
                break;
        finally:
            time.sleep(2)
            
    # main run
    print('\033[31m' + '매치 성공!'+ '\033[0m',pos['rectangle'])
    rect = pos['rectangle']
    cropped = im.crop((rect[0][0],rect[0][1],rect[3][0],rect[3][1]))
    cropped.save(path+'/a.png')
    while(True):
        img = pyautogui.screenshot()
        img.save(path+'/screenshot.png',quality=80)

        cropped = img.crop((rect[0][0],rect[0][1],rect[3][0],rect[3][1]))
        cropped.save(path+'/b.png')

        img1 = cv2.imread(path+'/a.png')
        img2 = cv2.imread(path+'/b.png')
        diff = mse(img1,img2)
        print(diff)

        if(diff>start and diff<end):
            script = path+'/sample-3s.wav'
            os.system(f'afplay \'{script}\'')
            time.sleep(int(items['alarmsleep']))
        
        if(diff>end):
            try:
                imsrc = ac.imread(path+'/screenshot.png')
                imobj = ac.imread(path+'/target1.png') 
                pos = ac.find_template(imsrc, imobj, 0.8)
                if(pos!=None):
                    print('Target1 image match',pos['rectangle'])
                    rect = pos['rectangle']
                    cropped = img.crop((rect[0][0],rect[0][1],rect[3][0],rect[3][1]))
                    cropped.save(path+'/a.png')
                else:
                    imobj1 = ac.imread(path+'/target2.png')
                    pos = ac.find_template(imsrc, imobj1, 0.8)
                    if(pos!=None):
                        print('Target2 image match',pos['rectangle'])
                        rect = pos['rectangle']
                        cropped = img.crop((rect[0][0],rect[0][1],rect[3][0],rect[3][1]))
                        cropped.save(path+'/a.png')
            finally:
                continue
            
                
        time.sleep(int(items['loopsleep']))
        
        

    