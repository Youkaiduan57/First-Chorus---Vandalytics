import time
import cv2
import numpy as np
from collections import deque
from PIL import Image, ImageDraw, ImageFont
 

CROP_SIZE = 260          
SMOOTHING = 10           
LOW_THRESHOLD = -12      
HIGH_THRESHOLD = 12      
FPS_LIMIT = 60           
FONT_CANDIDATES = [
    "assets/fonts/Rajdhani-Regular.ttf",
    "assets/fonts/Rajdhani-SemiBold.ttf",
    "Rajdhani-SemiBold.ttf",
    "Rajdhani-Regular.ttf",
]
GUIDE_OFFSET = 16       
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
    try:
        import mss
    except ImportError:
        raise ImportError("mss is required to run the AI Coach UI. Install it with 'pip install mss' and try again.")
 
    with mss.mss() as sct:
        monitor = sct.monitors[1]
 
        print("Minimal AI Crosshair Coach Running (Rajdhani UI)...")
        print("Press Q to quit")
 
        while True:
            start_time = time.time()

            frame = np.array(sct.grab(monitor))
            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

            crop = center_crop(gray_full, CROP_SIZE)
            offset = detect_offset(crop) - GUIDE_OFFSET
            history.append(offset)
            smooth_offset = int(np.mean(history))
 
            
            status, color = get_status(smooth_offset)
 

            vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            h, w = vis.shape[:2]
 

            cv2.line(vis, (0, h // 2 + GUIDE_OFFSET), (w, h // 2 + GUIDE_OFFSET), (60, 60, 60), 1)

            pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)

            try:
                fill_color = tuple(int(c) for c in color)
            except Exception:
                fill_color = (255, 255, 255)
 
            draw.text((14, 10), status, font=font, fill=fill_color)
 
            vis = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
 
            cv2.imshow("AI Coach", vis)
 
            elapsed = time.time() - start_time
            delay = max(1, int((1 / FPS_LIMIT - elapsed) * 1000))
 
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break
 
    cv2.destroyAllWindows()
 
 
if __name__ == '__main__':
    main()