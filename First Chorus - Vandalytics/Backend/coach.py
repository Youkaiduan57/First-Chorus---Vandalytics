import time
import cv2
import numpy as np
from collections import deque
from PIL import Image, ImageDraw, ImageFont
import argparse
import csv
import os
 
# ========= MINIMAL SETTINGS =========
CROP_SIZE = 260          # Size of center crop (crosshair zone)
SMOOTHING = 10           # Offset smoothing frames
LOW_THRESHOLD = -12      # Too low aim threshold
HIGH_THRESHOLD = 12      # Too high aim threshold
FPS_LIMIT = 60           # Frame cap for stability
FONT_CANDIDATES = [
    "assets/fonts/Rajdhani-Regular.ttf",
    "assets/fonts/Rajdhani-SemiBold.ttf",
    "Rajdhani-SemiBold.ttf",
    "Rajdhani-Regular.ttf",
]
GUIDE_OFFSET = 16       # pixels to move the horizontal guide line down (positive = down)
# ====================================
 
history = deque(maxlen=SMOOTHING)
 
 
def load_font(size=34):
    """Try candidate font paths and fall back to Pillow default."""
    for p in FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(p, size)
            print(f"Loaded font from: {p}")
            return f
        except Exception:
            continue
    print("Rajdhani not found; using default Pillow font.")
    return ImageFont.load_default()
 
 
# Global font used by the UI
font = load_font(34)
 
 
def center_crop(frame, size):
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    half = size // 2
    y0 = max(0, cy - half)
    y1 = min(h, cy + half)
    x0 = max(0, cx - half)
    x1 = min(w, cx + half)
    return frame[y0:y1, x0:x1]
 
 
def detect_offset(gray):
    # Simple vertical centroid offset detection from strongest contour
    edges = cv2.Canny(gray, 60, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 
    if not contours:
        return 0
 
    largest = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest)
    if M.get("m00", 0) == 0:
        return 0
    cy = int(M.get("m01", 0) / M.get("m00", 1))
    center_y = gray.shape[0] // 2
    return cy - center_y
 
 
def get_status(offset):
    if offset < LOW_THRESHOLD:
        return "AIM LOW", (255, 95, 95)
    elif offset > HIGH_THRESHOLD:
        return "AIM HIGH", (95, 140, 255)
    else:
        return "AIM PERFECT", (120, 255, 170)
 
def main():
    parser = argparse.ArgumentParser(description="Minimal AI Crosshair Coach")
    parser.add_argument("--log", help="Path to CSV file to append per-frame metrics")
    parser.add_argument("--max-frames", type=int, default=0, help="If >0, run only this many frames then exit (useful for tests)")
    args = parser.parse_args()
 
    try:
        import mss
    except ImportError:
        raise ImportError("mss is required to run the AI Coach UI. Install it with 'pip install mss' and try again.")
 
    log_file = None
    csv_writer = None
    if args.log:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        log_file = open(args.log, "a", newline="", encoding="utf-8")
        csv_writer = csv.writer(log_file)
        # Write header if file was empty
        if os.path.getsize(args.log) == 0:
            csv_writer.writerow(["timestamp", "offset", "smooth_offset", "status"])
 
    with mss.mss() as sct:
        monitor = sct.monitors[1]
 
        print("Minimal AI Crosshair Coach Running (Rajdhani UI)...")
        print("Press Q to quit")
 
        frame_counter = 0
        while True:
            start_time = time.time()
 
            # Capture screen
            frame = np.array(sct.grab(monitor))
            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
 
            # Center crop (crosshair zone)
            crop = center_crop(gray_full, CROP_SIZE)
 
            # Detect vertical offset (align measurement with visible guide)
            # Subtract GUIDE_OFFSET so the decision reference matches the drawn line
            offset = detect_offset(crop) - GUIDE_OFFSET
            history.append(offset)
            smooth_offset = int(np.mean(history))
 
            # Get coaching status
            status, color = get_status(smooth_offset)
 
            # Log per-frame metrics if requested
            if csv_writer:
                try:
                    csv_writer.writerow([time.time(), int(offset), int(smooth_offset), status])
                    log_file.flush()
                except Exception:
                    pass
 
            # Convert to BGR for display
            vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            h, w = vis.shape[:2]
 
            # Minimal center guide line (head level reference)
            cv2.line(vis, (0, h // 2 + GUIDE_OFFSET), (w, h // 2 + GUIDE_OFFSET), (60, 60, 60), 1)
 
            # ===== CLEAN RAJDHANI TEXT (NO UGLY OPENCV FONT) =====
            # Convert BGR (OpenCV) -> RGB (Pillow) so colors render correctly
            pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
 
            # Ensure color is an RGB tuple (get_status returns RGB-style tuples)
            try:
                fill_color = tuple(int(c) for c in color)
            except Exception:
                fill_color = (255, 255, 255)
 
            # Minimal top-left text
            draw.text((14, 10), status, font=font, fill=fill_color)
 
            # Convert back to OpenCV BGR image for display
            vis = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            # =====================================================
 
            cv2.imshow("AI Coach", vis)
 
            # FPS limiter (stable for games)
            elapsed = time.time() - start_time
            delay = max(1, int((1 / FPS_LIMIT - elapsed) * 1000))
 
            frame_counter += 1
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break
            if args.max_frames > 0 and frame_counter >= args.max_frames:
                break
    cv2.destroyAllWindows()
    if log_file:
        log_file.close()
 
 
if __name__ == '__main__':
    main()
   