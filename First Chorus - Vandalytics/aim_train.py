import numpy as np
import cv2
import win32gui
import win32con
import ctypes
import time
import random
import sys
from pynput import mouse

ctypes.windll.user32.SetProcessDPIAware()
user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

WINDOW_NAME = "Aim Trainer Overlay"
NUM_CIRCLES = 10
CIRCLE_RADIUS = 25
CIRCLE_COLOR = (0, 0, 255)  
CIRCLE_THICKNESS = 3

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
hwnd = win32gui.FindWindow(None, WINDOW_NAME)

win32gui.SetWindowLong(
    hwnd,
    win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_TOPMOST
    | win32con.WS_EX_TRANSPARENT
)
win32gui.SetLayeredWindowAttributes(hwnd, 0x000000, 0, win32con.LWA_COLORKEY)

def force_topmost():
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
    )

def random_circle():
    x = random.randint(CIRCLE_RADIUS, SCREEN_WIDTH - CIRCLE_RADIUS)
    y = random.randint(CIRCLE_RADIUS, SCREEN_HEIGHT - CIRCLE_RADIUS)
    return (x, y)

circles = [random_circle() for _ in range(NUM_CIRCLES)]
reaction_times = []
current = 0
start_time = None
running = True

# Mouse click handler
def on_click(x, y, button, pressed):
    global current, start_time, running
    if not pressed or current >= NUM_CIRCLES:
        return
    cx, cy = circles[current]
    # Check if click inside circle
    if (x - cx) ** 2 + (y - cy) ** 2 <= CIRCLE_RADIUS ** 2:
        reaction_times.append(time.time() - start_time)
        current += 1
        if current < NUM_CIRCLES:
            start_time = time.time()
        else:
            running = False

listener = mouse.Listener(on_click=on_click)
listener.start()
start_time = time.time()

last_force = 0
while running:
    if time.time() - last_force > 0.2:
        force_topmost()
        last_force = time.time()

    overlay = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

    if current < NUM_CIRCLES:
        cx, cy = circles[current]
        cv2.circle(overlay, (cx, cy), CIRCLE_RADIUS, CIRCLE_COLOR, CIRCLE_THICKNESS)
        cv2.putText(
            overlay,
            f"Click the circle ({current + 1}/{NUM_CIRCLES})",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )

    cv2.imshow(WINDOW_NAME, overlay)
    if cv2.waitKey(1) & 0xFF == 27:
        running = False

listener.stop()
cv2.destroyAllWindows()

print("Reaction times (seconds):")
for i, t in enumerate(reaction_times, 1):
    print(f"Circle {i}: {t:.3f}s")
if reaction_times:
    print(f"Average reaction time: {sum(reaction_times)/len(reaction_times):.3f}s")

sys.exit()