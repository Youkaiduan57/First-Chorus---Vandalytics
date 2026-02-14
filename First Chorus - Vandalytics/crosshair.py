import argparse
import time
import cv2
import numpy as np
import mss
import win32gui
import win32con
import ctypes

ctypes.windll.user32.SetProcessDPIAware()
user32 = ctypes.windll.user32

SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

WINDOW_NAME = "Crosshair Overlay"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--crop-size", type=int, default=250)
    parser.add_argument("--shot-threshold", type=int, default=180)
    parser.add_argument("--shot-cooldown", type=float, default=0.1)
    args = parser.parse_args()

    sct = mss.mss()
    monitor = sct.monitors[args.monitor]

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

    win32gui.SetLayeredWindowAttributes(
        hwnd,
        0x000000,
        0,
        win32con.LWA_COLORKEY
    )

    last_shot_time = 0
    crop_size = args.crop_size

    # --- smoothing state ---
    smoothed_offset = 0
    last_valid_offset = 0
    alpha = 0.25   # lower = smoother

    print("Overlay running — ESC to quit")

    while True:

        start_time = time.time()

        screenshot = sct.grab(monitor)
        frame = np.array(screenshot)

        if frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        half = crop_size // 2
        left = max(0, center_x - half)
        top = max(0, center_y - half)
        right = min(w, center_x + half)
        bottom = min(h, center_y + half)

        center_crop = frame[top:bottom, left:right]
        overlay = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

        offset = None

        if center_crop.size != 0:
            gray = cv2.cvtColor(center_crop, cv2.COLOR_BGR2GRAY)

            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)

                if cv2.contourArea(largest) > 10:  # filter noise
                    M = cv2.moments(largest)
                    if M["m00"] != 0:
                        cy = int(M["m01"] / M["m00"])
                        offset = (top + cy) - center_y

            brightness = float(np.mean(gray))
            current_time = time.time()
            if brightness > args.shot_threshold and (current_time - last_shot_time) > args.shot_cooldown:
                last_shot_time = current_time
                print("SHOT detected!")

        # --- smoothing ---
        if offset is not None:
            last_valid_offset = offset

        smoothed_offset = (alpha * last_valid_offset) + ((1 - alpha) * smoothed_offset)

        draw_y = int(center_y + smoothed_offset)

        # --- draw vertical line ---
        cv2.line(
            overlay,
            (center_x, center_y),
            (center_x, draw_y),
            (0, 0, 255),
            3
        )

        # --- draw offset top left ---
        cv2.putText(
            overlay,
            f"Offset: {int(smoothed_offset)} px",
            (40, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.imshow(WINDOW_NAME, overlay)

        if cv2.waitKey(1) & 0xFF == 27:
            break

        # small frame cap for smoothness
        elapsed = time.time() - start_time
        if elapsed < 0.005:
            time.sleep(0.005 - elapsed)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()