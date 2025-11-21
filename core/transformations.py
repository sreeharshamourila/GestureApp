import cv2
import numpy as np

# Basic flips / color
def flip_horizontal(img):
    return cv2.flip(img, 1)

def flip_vertical(img):
    return cv2.flip(img, 0)

def grayscale(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

def to_color(img):
    return img.copy()

# Rotation 90 degrees
def rotate_left(img):
    return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

def rotate_right(img):
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

# Brightness/contrast
def adjust_brightness(img, amount):
    # amount: -100..+100
    return cv2.convertScaleAbs(img, alpha=1.0, beta=amount)

def adjust_contrast(img, factor):
    # factor: 0.1..3.0 (1.0 = same)
    return cv2.convertScaleAbs(img, alpha=factor, beta=0)

# Sketch-like effect
def sketch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inv = cv2.bitwise_not(gray)
    blur = cv2.GaussianBlur(inv, (21, 21), 0)
    sketch_img = cv2.divide(gray, 255 - blur, scale=256)
    return cv2.cvtColor(sketch_img, cv2.COLOR_GRAY2BGR)

# Sepia
def sepia(img):
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    sep = cv2.transform(img, kernel)
    return np.clip(sep, 0, 255).astype(np.uint8)

# Posterize
def posterize(img, levels=4):
    if levels < 2:
        return img.copy()
    shift = 256 // levels
    return ((img // shift) * shift).astype(np.uint8)

# Zoom keeping original canvas size
def zoom(img, scale):
    if scale == 1.0:
        return img.copy()
    h, w = img.shape[:2]
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    if scale > 1.0:
        # center crop to original size
        x = (new_w - w) // 2
        y = (new_h - h) // 2
        return resized[y:y + h, x:x + w].copy()
    else:
        # pad to original size centered
        canvas = np.zeros_like(img)
        x = (w - new_w) // 2
        y = (h - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas
