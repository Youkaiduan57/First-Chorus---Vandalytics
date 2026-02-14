import numpy as np
import cv2
import win32gui
import win32con
import ctypes
import time
import sys
from pynput import mouse

ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

WINDOW_NAME = "Overlay Guide"

STEP1_X = 0.875
STEP1_Y = 0.955
STEP1_W = 0.05
STEP1_H = 0.035

STEP2_X = 0.66666
STEP2_Y = 0.85
STEP2_W = 0.18
STEP2_H = 0.11

STEP3_X = 0.81
STEP3_Y = 0.35
STEP3_W = 0.092
STEP3_H = 0.05

ARROW_OFFSET_X = -0.13
ARROW_OFFSET_Y = -0.14
ARROW_THICKNESS = 6
ARROW_TIP_LENGTH = 0.25

STEP4_X = 0.795
STEP4_Y = 0.42
STEP4_W = 0.1
STEP4_H = 0.05
#percent to coords
def percent_box(x_p, y_p, w_p, h_p):
    x1 = int(SCREEN_WIDTH * x_p)
    y1 = int(SCREEN_HEIGHT * y_p)
    x2 = int(x1 + SCREEN_WIDTH * w_p)
    y2 = int(y1 + SCREEN_HEIGHT * h_p)
    return (x1, y1, x2, y2)
steps = [
    {
        "box": percent_box(STEP1_X, STEP1_Y, STEP1_W, STEP1_H),
        "label": "Click Battery Icon"
    },
    {
        "box": percent_box(STEP2_X, STEP2_Y, STEP2_W, STEP2_H),
        "label": "Click The Battery"
    },
    {
        "box": percent_box(STEP3_X, STEP3_Y, STEP3_W, STEP3_H),
        "label": "Click Power Mode"
    },
    {
        "box": percent_box(STEP4_X, STEP4_Y, STEP4_W, STEP4_H),
        "label": "Select Best Performance"
    }
]
current_step = 0
running = True
#create window
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(
    WINDOW_NAME,
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)
hwnd = win32gui.FindWindow(None, WINDOW_NAME)
#transperent and clickthrough
win32gui.SetWindowLong(
    hwnd,
    win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_TOPMOST
    | win32con.WS_EX_TRANSPARENT
)
#color to transperent
win32gui.SetLayeredWindowAttributes(
    hwnd,
    0x000000,
    0,
    win32con.LWA_COLORKEY
)
#at top all times
def force_topmost():
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE |
        win32con.SWP_NOSIZE |
        win32con.SWP_NOACTIVATE |
        win32con.SWP_SHOWWINDOW
    )
#checking for clicks
def on_click(x, y, button, pressed):
    global current_step, running

    if not pressed or current_step >= len(steps):
        return
    if current_step == 1:
        current_step += 1
        return
    x1, y1, x2, y2 = steps[current_step]["box"]

    if x1 <= x <= x2 and y1 <= y <= y2:
        current_step += 1

        if current_step >= len(steps):
            running = False

listener = mouse.Listener(on_click=on_click)
listener.start()
#keeps track of last time forced topmost
last_force = 0

while running:

    if time.time() - last_force > 0.2:
        force_topmost()
        last_force = time.time()

    overlay = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

    if current_step < len(steps):

        x1, y1, x2, y2 = steps[current_step]["box"]
        label = steps[current_step]["label"]

        if current_step == 1:

            target_x = (x1 + x2) // 2
            target_y = (y1 + y2) // 2

            start_x = int(target_x + SCREEN_WIDTH * ARROW_OFFSET_X  )
            start_y = int(target_y + SCREEN_HEIGHT * ARROW_OFFSET_Y)

            cv2.arrowedLine(
                overlay,
                (start_x, start_y),
                (target_x, target_y),
                (0, 0, 255),
                ARROW_THICKNESS,
                tipLength=ARROW_TIP_LENGTH
            )

            cv2.putText(
                overlay,
                label + " (Click anywhere)",
                (start_x - 50, start_y - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                2
            )

        else:
            cv2.rectangle(
                overlay,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                3
            )

            cv2.putText(
                overlay,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )
    cv2.imshow(WINDOW_NAME, overlay)
    if cv2.waitKey(1) & 0xFF == 27:
        break
listener.stop()
cv2.destroyAllWindows()
sys.exit()