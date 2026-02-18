import os
import time
import threading
import configparser
import cv2
import numpy as np
import pyautogui
import aircv as ac
from PIL import Image


def mse(image1, image2):
    try:
        if image1 is None or image2 is None:
            return 0.0
        if image1.size == 0 or image2.size == 0:
            return 0.0
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        if gray1.shape != gray2.shape:
            # shapes differ, compute on overlapping region
            h = min(gray1.shape[0], gray2.shape[0])
            w = min(gray1.shape[1], gray2.shape[1])
            gray1 = gray1[:h, :w]
            gray2 = gray2[:h, :w]
        diff = np.square(gray1.astype('float32') - gray2.astype('float32'))
        m = np.mean(diff)
        return round(float(m), 2)
    except Exception:
        return 0.0


def run_monitor(path, stop_event: threading.Event = None, status_callback=None, instance_id: str = ""):
    if stop_event is None:
        stop_event = threading.Event()

    file = os.path.join(path, 'config.ini')
    con = configparser.ConfigParser()

    def status(msg):
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    try:
        pyautogui.PAUSE = 0.005
    except Exception:
        pass

    # load templates (once)
    tpl1 = None
    tpl2 = None
    tpl1_path = os.path.join(path, 'target1.png')
    tpl2_path = os.path.join(path, 'target2.png')
    if os.path.exists(tpl1_path):
        tpl1 = cv2.imread(tpl1_path)
        if tpl1 is None:
            status(f'Failed to read {tpl1_path}')
    if os.path.exists(tpl2_path):
        tpl2 = cv2.imread(tpl2_path)
        if tpl2 is None:
            status(f'Failed to read {tpl2_path}')

    # initial target match (in-memory)
    pos = None
    status('Searching for target...')
    while not stop_event.is_set():
        im_pil = pyautogui.screenshot()
        # convert to cv2 BGR
        try:
            im_arr = np.array(im_pil)
            if im_arr.size == 0:
                status('Empty screenshot array')
                time.sleep(1)
                continue
            im_np = cv2.cvtColor(im_arr, cv2.COLOR_RGB2BGR)
        except Exception as e:
            status(f'Error converting screenshot to array: {e}')
            time.sleep(1)
            continue
        try:
            if tpl1 is not None:
                try:
                    if im_np.shape[0] >= tpl1.shape[0] and im_np.shape[1] >= tpl1.shape[1]:
                        res = cv2.matchTemplate(im_np, tpl1, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        if max_val >= 0.8:
                            h, w = tpl1.shape[:2]
                            x, y = max_loc
                            rect = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                            pos = {'rectangle': rect}
                except Exception as e:
                    status(f'Error matching tpl1: {e}')
            if pos is None and tpl2 is not None:
                try:
                    if im_np.shape[0] >= tpl2.shape[0] and im_np.shape[1] >= tpl2.shape[1]:
                        res = cv2.matchTemplate(im_np, tpl2, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        if max_val >= 0.8:
                            h, w = tpl2.shape[:2]
                            x, y = max_loc
                            rect = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                            pos = {'rectangle': rect}
                except Exception as e:
                    status(f'Error matching tpl2: {e}')

            if pos is None:
                status('target match failed')
            else:
                break
        except Exception as e:
            status(f'Error during initial match: {e}')
        finally:
            time.sleep(2)

    if stop_event.is_set():
        status('Stopped before match')
        return

    status('매치 성공')

    # allow_alarm controls whether alarms can be played; only true after a successful match
    allow_alarm = True

    rect = pos['rectangle']
    # baseline image in memory (cv2 BGR)
    # rect may be list of corner points; compute min/max to get left,top,right,bottom
    xs = [p[0] for p in rect]
    ys = [p[1] for p in rect]
    x0 = int(min(xs))
    x3 = int(max(xs))
    y0 = int(min(ys))
    y3 = int(max(ys))
    # use last im_pil from loop
    try:
        # ensure coordinates are within image
        img_w, img_h = im_pil.size
        x0c = max(0, min(img_w, x0))
        x3c = max(0, min(img_w, x3))
        y0c = max(0, min(img_h, y0))
        y3c = max(0, min(img_h, y3))
        if x3c <= x0c or y3c <= y0c:
            status('Empty baseline crop (zero size); aborting')
            return
        cropped_pil = im_pil.crop((x0c, y0c, x3c, y3c))
        if cropped_pil is None:
            status('Empty baseline crop (None); aborting')
            return
        w0, h0 = cropped_pil.size
        if w0 == 0 or h0 == 0:
            status('Empty baseline crop (zero size); aborting')
            return
        a_arr = np.array(cropped_pil)
        if a_arr.size == 0:
            status('Empty baseline array; aborting')
            return
        a_img = cv2.cvtColor(a_arr, cv2.COLOR_RGB2BGR)
    except Exception as e:
        status(f'Error creating baseline image: {e}')
        return

    # main loop
    while not stop_event.is_set():
        try:
            con.read(file, encoding='utf-8')
            items = dict(con.items('app'))
            # support both English and Korean keys
            start = int(items.get('start', items.get('매치시작점', '10')))
            end = int(items.get('end', items.get('매치마감점', '100')))
            loopsleep = int(items.get('loopsleep', items.get('수면', '2')))
            alarmsleep = int(items.get('alarmsleep', items.get('알람 수면', '3')))

            img_pil = pyautogui.screenshot()
            try:
                img_arr = np.array(img_pil)
                if img_arr.size == 0:
                    status('Empty screenshot array in main loop')
                    time.sleep(1)
                    continue
                img_np = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
            except Exception as e:
                status(f'Error converting screenshot to array in main loop: {e}')
                time.sleep(1)
                continue

            # crop in memory with clamped coordinates
            h_img, w_img = img_np.shape[:2]
            x0c = max(0, min(w_img, x0))
            x3c = max(0, min(w_img, x3))
            y0c = max(0, min(h_img, y0))
            y3c = max(0, min(h_img, y3))
            if x3c <= x0c or y3c <= y0c:
                status('Invalid crop region in main loop; skipping frame')
                time.sleep(1)
                continue
            cropped_np = img_np[y0c:y3c, x0c:x3c]
            if cropped_np is None or cropped_np.size == 0:
                status('Empty cropped region in main loop; skipping frame')
                time.sleep(1)
                continue
            b_img = cropped_np

            diff = mse(a_img, b_img)
            status(f'매치율: {diff}')

            if diff > start and diff < end and allow_alarm:
                script = os.path.join(path, 'sample-3s.wav')
                try:
                    os.system(f'afplay "{script}"')
                except Exception:
                    pass
                # sleep but remain responsive to stop_event
                for _ in range(max(1, alarmsleep)):
                    if stop_event.is_set():
                        break
                    time.sleep(1)

            if diff > end:
                # perform template match on current screenshot (in-memory)
                try:
                    matched = False
                    if tpl1 is not None:
                        try:
                            res = cv2.matchTemplate(img_np, tpl1, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.8:
                                status('Target1 image match')
                                h, w = tpl1.shape[:2]
                                x, y = max_loc
                                x0n, y0n = x, y
                                x3n, y3n = x + w, y + h
                                # clamp
                                h_img, w_img = img_np.shape[:2]
                                x0c = max(0, min(w_img, x0n))
                                x3c = max(0, min(w_img, x3n))
                                y0c = max(0, min(h_img, y0n))
                                y3c = max(0, min(h_img, y3n))
                                if x3c > x0c and y3c > y0c:
                                    a_candidate = img_np[y0c:y3c, x0c:x3c]
                                    if a_candidate is not None and a_candidate.size > 0:
                                        a_img = a_candidate
                                        x0, y0, x3, y3 = x0c, y0c, x3c, y3c
                                        matched = True
                        except Exception as e:
                            status(f'Error matching tpl1 in re-match: {e}')
                    if not matched and tpl2 is not None:
                        try:
                            res = cv2.matchTemplate(img_np, tpl2, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.8:
                                status('Target2 image match')
                                h, w = tpl2.shape[:2]
                                x, y = max_loc
                                x0n, y0n = x, y
                                x3n, y3n = x + w, y + h
                                h_img, w_img = img_np.shape[:2]
                                x0c = max(0, min(w_img, x0n))
                                x3c = max(0, min(w_img, x3n))
                                y0c = max(0, min(h_img, y0n))
                                y3c = max(0, min(h_img, y3n))
                                if x3c > x0c and y3c > y0c:
                                    a_candidate = img_np[y0c:y3c, x0c:x3c]
                                    if a_candidate is not None and a_candidate.size > 0:
                                        a_img = a_candidate
                                        x0, y0, x3, y3 = x0c, y0c, x3c, y3c
                                        matched = True
                        except Exception as e:
                            status(f'Error matching tpl2 in re-match: {e}')
                    if not matched:
                        status('none image match')
                        # if re-match failed, prevent alarms until a successful rematch
                        allow_alarm = False
                except Exception as e:
                    status(f'Error during re-match: {e}')
                else:
                    # if matched successfully, allow alarms
                    allow_alarm = True

            for _ in range(max(1, loopsleep)):
                if stop_event.is_set():
                    break
                time.sleep(1)

        except Exception as e:
            status(f'Error in main loop: {e}')
            time.sleep(2)

    status('Monitor stopped')
