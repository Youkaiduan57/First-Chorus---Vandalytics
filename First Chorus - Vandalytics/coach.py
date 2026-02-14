import time
import argparse
import csv
import os
import statistics
from collections import deque
 
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
 
# Minimal, consolidated AI coach
FONT_CANDIDATES = [
    "assets/fonts/Rajdhani-Regular.ttf",
    "assets/fonts/Rajdhani-SemiBold.ttf",
    "Rajdhani-SemiBold.ttf",
    "Rajdhani-Regular.ttf",
]
 
CSV_FILE = "round_stats.csv"
 
 
def load_font(size=24):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()
 
 
font = load_font(24)
 
 
def center_crop(frame, size):
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    half = size // 2
    return frame[max(0, cy - half):min(h, cy + half), max(0, cx - half):min(w, cx + half)]
 
 
def detect_offset(gray):
    # return vertical offset (px) from center based on largest contour centroid
    edges = cv2.Canny(gray, 60, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest)
    if M.get("m00", 0) == 0:
        return None
    cy = int(M.get("m01", 0) / M.get("m00", 1))
    return cy - (gray.shape[0] // 2)
 
 
def draw_overlay(name, lines):
    w, h = 360, 140
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    overlay[:] = (35, 35, 35)
 
    # title
    title = "Vandalytics"
    (txt_w, txt_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    tx = max(8, (w - txt_w) // 2)
    ty = 24
    cv2.putText(overlay, title, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0,255), 2, cv2.LINE_AA)
    cv2.line(overlay, (8, ty + 6), (w - 8, ty + 6), (60, 60, 60), 1)
 
    # tats lines below title
    y0, dy = ty + 22, 22
    for i, line in enumerate(lines):
        y = y0 + i * dy
        cv2.putText(overlay, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1, cv2.LINE_AA)
 
    cv2.imshow(name, overlay)
    cv2.waitKey(1)
 
 
def write_csv(round_num, avg_offset, max_offset, std_dev, shots, tip, file_path=CSV_FILE):
    exists = os.path.isfile(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp", "Round", "AvgOffset", "MaxOffset", "StdDev", "Shots", "Tip"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), round_num, round(avg_offset, 1), max_offset, round(std_dev, 1), shots, tip])
 
 
def main():
    parser = argparse.ArgumentParser(description="Compact AI Coach")
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--crop-ratio", type=float, default=0.2)
    parser.add_argument("--shot-threshold", type=int, default=180)
    parser.add_argument("--shot-cooldown", type=float, default=0.12)
    parser.add_argument("--round-ui-threshold", type=int, default=140)
    parser.add_argument("--smooth-frames", type=int, default=7)
    parser.add_argument("--show-overlay", type=int, default=1)
    args = parser.parse_args()
 
    try:
        import mss
    except Exception:
        raise SystemExit("mss is required; install with: pip install mss")
 
    sct = mss.mss()
    monitor = sct.monitors[args.monitor] if 0 <= args.monitor < len(sct.monitors) else sct.monitors[1]
 
    # screen size (used for UI crop position)
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
        SCREEN_W = ctypes.windll.user32.GetSystemMetrics(0)
        SCREEN_H = ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        SCREEN_W, SCREEN_H = 1920, 1080
 
    crop_size = int(min(SCREEN_W, SCREEN_H) * args.crop_ratio)
    window_name = "AI Coach Overlay"
    if args.show_overlay:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(window_name, 10, 10)
        cv2.resizeWindow(window_name, 360, 140)
 
    vertical_buf = deque(maxlen=args.smooth_frames)
    last_shot_time = 0
    shot_offsets = []
    round_num = 0
    last_ui_brightness = None
    tip = "No data yet"
 
    ROUND_END_W = int(SCREEN_W * 0.2)
    ROUND_END_H = int(SCREEN_H * 0.05)
 
    try:
        while True:
            s = sct.grab(monitor)
            frame = np.array(s)
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
 
            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2
            half = crop_size // 2
            crop = frame[max(0, cy - half):min(h, cy + half), max(0, cx - half):min(w, cx + half)]
            if crop.size == 0:
                time.sleep(0.05)
                continue
 
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
 
            offset = detect_offset(gray)
            if offset is not None:
                vertical_buf.append(offset)
                smooth = sum(vertical_buf) / len(vertical_buf)
            else:
                smooth = None
 
            # shot detection (brightness spike)
            brightness = float(np.mean(gray))
            now = time.time()
            if brightness > args.shot_threshold and (now - last_shot_time) > args.shot_cooldown:
                last_shot_time = now
                shot_offsets.append(smooth)
                print(f"SHOT @ offset={smooth if smooth is not None else 'N/A'}")
 
            # round-end detection via small UI region brightness change
            rx = cx - ROUND_END_W // 2
            ry = int(SCREEN_H * 0.05)
            if 0 <= ry < h:
                ui = frame[ry:ry + ROUND_END_H, max(0, rx):min(w, rx + ROUND_END_W)]
                if ui.size > 0:
                    ui_gray = cv2.cvtColor(ui, cv2.COLOR_BGR2GRAY)
                    ui_b = float(np.mean(ui_gray))
                else:
                    ui_b = 0.0
            else:
                ui_b = 0.0
 
            if last_ui_brightness is not None and abs(ui_b - last_ui_brightness) > args.round_ui_threshold:
                # round ended
                round_num += 1
                valid = [s for s in shot_offsets if s is not None]
                if valid:
                    avg = sum(valid) / len(valid)
                    mx = max(abs(x) for x in valid)
                    sd = statistics.stdev(valid) if len(valid) > 1 else 0.0
                    if avg > 5:
                        tip = "Raise your crosshair slightly next round"
                    elif avg < -5:
                        tip = "Lower your crosshair slightly next round"
                    else:
                        tip = "Crosshair height is on point!"
                    write_csv(round_num, avg, mx, sd, len(valid), tip)
                    print(f"=== ROUND {round_num} === Avg={avg:.1f}px, Shots={len(valid)} Tip={tip}")
                shot_offsets = []
                vertical_buf.clear()
 
            last_ui_brightness = ui_b
 
            # overlay
            if args.show_overlay:
                avg_disp = f"{(sum(vertical_buf) / len(vertical_buf)):.1f}px" if vertical_buf else "N/A"
                stats = [f"Round: {round_num}", f"Avg Offset: {avg_disp}", f"Shots: {len(shot_offsets)}", f"Tip: {tip}"]
                draw_overlay(window_name, stats)
 
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
 
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
 
 
if __name__ == '__main__':
    main()
 
 