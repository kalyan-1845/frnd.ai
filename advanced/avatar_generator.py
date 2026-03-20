"""
Advanced Avatar frame generator for BKR 2.0 - Human Clone Edition.

Generates 12+ viseme-based animation frames for realistic lip-sync:
- 8 mouth shape frames (A, E, I, O, U, M, S, neutral)
- Expression frames (smile, neutral, concerned)
- Idle frames with natural movement
- Blink frames with eye variation

This creates a realistic animated human clone that can speak with lip-sync.
"""
from __future__ import annotations

import glob
import os
from typing import Tuple

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance

import config

try:
    import cv2
except Exception:
    cv2 = None


TARGET_SIZE = 640

_GENERATED_FRAME_NAMES = {
    "idle.png",
    "idle_shift.png",
    "idle_breath.png",
    "blink.png",
    "blink_quick.png",
    "eyes_open.png",
    "smile.png",
    "speak_1.png",
    "speak_2.png",
    "viseme_neutral.png",
    "viseme_A.png",
    "viseme_E.png",
    "viseme_I.png",
    "viseme_O.png",
    "viseme_U.png",
    "viseme_MBP.png",
    "viseme_STH.png",
}


def _is_generated_avatar_asset(path: str) -> bool:
    return os.path.basename(path).lower() in {n.lower() for n in _GENERATED_FRAME_NAMES}


def _resolve_source_photo() -> str | None:
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    preferred = [
        getattr(config, "ASSISTANT_SOURCE_PHOTO", ""),
        os.path.join(assets_dir, "bkr2.0.png"),
        os.path.join(assets_dir, "bkr2.0.jpg"),
        os.path.join(assets_dir, "bkr2.0.jpeg"),
        os.path.join(assets_dir, "user_photo.png"),
        os.path.join(assets_dir, "user_photo.jpg"),
        os.path.join(assets_dir, "user_photo.jpeg"),
        os.path.join(assets_dir, "user_photo.webp"),
        os.path.join(assets_dir, "my_photo.png"),
        os.path.join(assets_dir, "my_photo.jpg"),
        os.path.join(assets_dir, "my_photo.jpeg"),
        os.path.join(assets_dir, "my_photo.webp"),
    ]
    for path in preferred:
        if not path:
            continue
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and not _is_generated_avatar_asset(abs_path):
            return abs_path

    # Try any custom image in assets, excluding generated animation frames.
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        files = sorted(glob.glob(os.path.join(assets_dir, ext)))
        for path in files:
            abs_path = os.path.abspath(path)
            if _is_generated_avatar_asset(abs_path):
                continue
            return abs_path

    # Last fallback: use existing avatar frame as source so system still works.
    fallback = os.path.abspath(config.ASSISTANT_AVATAR_PATH)
    if os.path.exists(fallback):
        return fallback
    return None


def _prepare_square_image(source_path: str, size: int = TARGET_SIZE) -> Image.Image:
    img = Image.open(source_path).convert("RGBA")
    w, h = img.size
    scale = max(size / max(w, 1), size / max(h, 1))
    nw, nh = int(w * scale), int(h * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - nw) // 2
    y = (size - nh) // 2
    canvas.paste(resized, (x, y), resized)
    return canvas


def _detect_face_box(img: Image.Image) -> Tuple[int, int, int, int]:
    """Detect face region with enhanced precision for lip-sync."""
    if cv2 is not None:
        arr = np.array(img.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        try:
            cascade = cv2.CascadeClassifier(
                os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            )
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(int(img.width * 0.2), int(img.height * 0.2)),
            )
        except Exception:
            faces = ()

        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            return int(x), int(y), int(w), int(h)

    # Fallback for centered portraits
    return (
        int(img.width * 0.25),
        int(img.height * 0.18),
        int(img.width * 0.50),
        int(img.height * 0.58),
    )


def _detect_eyes(img: Image.Image, face_box: Tuple[int, int, int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Detect eye positions for blink animations."""
    x, y, w, h = face_box
    
    if cv2 is not None:
        arr = np.array(img.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        try:
            eye_cascade = cv2.CascadeClassifier(
                os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")
            )
            eyes = eye_cascade.detectMultiScale(
                gray[y:y+h, x:x+w],
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(int(w * 0.15), int(h * 0.1))
            )
            
            if len(eyes) >= 2:
                eyes = sorted(eyes, key=lambda e: e[0])
                left_eye = (x + eyes[0][0] + eyes[0][2]//2, y + eyes[0][1] + eyes[0][3]//2)
                right_eye = (x + eyes[1][0] + eyes[1][2]//2, y + eyes[1][1] + eyes[1][3]//2)
                return left_eye, right_eye
        except Exception:
            pass
    
    # Fallback eye positions
    left_eye = (x + int(0.35 * w), y + int(0.38 * h))
    right_eye = (x + int(0.65 * w), y + int(0.38 * h))
    return left_eye, right_eye


def _sample_skin_color(img: Image.Image, face_box: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    x, y, w, h = face_box
    sx = max(0, min(img.width - 1, int(x + 0.2 * w)))
    sy = max(0, min(img.height - 1, int(y + 0.56 * h)))
    r, g, b, _ = img.getpixel((sx, sy))
    return int(r), int(g), int(b), 235


def _draw_viseme_mouth(img: Image.Image, face_box: Tuple[int, int, int, int], 
                       viseme: str, skin: Tuple[int, int, int, int]) -> Image.Image:
    """Draw realistic mouth shapes for lip-sync (8 visemes)."""
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    
    x, y, w, h = face_box
    mx = x + int(0.50 * w)  # Center of mouth horizontally
    my = y + int(0.72 * h)  # Center of mouth vertically
    
    # Get lip color (slightly darker than skin)
    lip_color = (
        max(0, skin[0] - 20),
        max(0, skin[1] - 15),
        max(0, skin[2] - 10),
        245
    )
    
    # Inner mouth color (darker)
    mouth_inside = (30, 15, 15, 240)
    teeth_color = (255, 255, 255, 230)
    tongue_color = (180, 60, 60, 220)
    
    # Base mouth dimensions
    mouth_w = int(0.28 * w)
    mouth_h = int(0.12 * h)
    
    if viseme == "neutral":
        # Closed mouth - thin line
        draw.ellipse(
            (mx - mouth_w//2, my - mouth_h//4, mx + mouth_w//2, my + mouth_h//4),
            fill=lip_color
        )
        
    elif viseme == "A":
        # Open mouth - like "father" - wide open
        outer = (mx - mouth_w//2, my - mouth_h, mx + mouth_w//2, my + mouth_h//2)
        draw.ellipse(outer, fill=mouth_inside)
        inner = (mx - mouth_w//3, my - mouth_h//2, mx + mouth_w//3, my + mouth_h//4)
        draw.ellipse(inner, fill=tongue_color)
        # Teeth
        draw.rectangle((mx - mouth_w//3, my - mouth_h//3, mx + mouth_w//3, my), fill=teeth_color)
        
    elif viseme == "E":
        # Wide smile - like "see"
        outer = (mx - mouth_w//2, my - mouth_h//2, mx + mouth_w//2, my + mouth_h//3)
        draw.ellipse(outer, fill=mouth_inside)
        draw.ellipse(outer, outline=lip_color, width=3)
        # Teeth showing
        draw.rectangle((mx - mouth_w//3, my - mouth_h//4, mx + mouth_w//3, my), fill=teeth_color)
        # Smile lines
        draw.arc((mx - mouth_w//2, my - mouth_h//2, mx + mouth_w//2, my + mouth_h), 
                 start=0, end=180, fill=lip_color, width=2)
        
    elif viseme == "I":
        # Slight smile - like "bit"
        outer = (mx - mouth_w//3, my - mouth_h//3, mx + mouth_w//3, my + mouth_h//4)
        draw.ellipse(outer, fill=mouth_inside)
        draw.ellipse(outer, outline=lip_color, width=2)
        draw.line((mx - mouth_w//4, my, mx + mouth_w//4, my), fill=lip_color, width=2)
        
    elif viseme == "O":
        # Rounded lips - like "go"
        outer = (mx - mouth_w//3, my - mouth_h//1.5, mx + mouth_w//3, my + mouth_h//2)
        draw.ellipse(outer, fill=mouth_inside)
        draw.ellipse(outer, outline=lip_color, width=3)
        inner = (mx - mouth_w//5, my - mouth_h//3, mx + mouth_w//5, my + mouth_h//4)
        draw.ellipse(inner, fill=mouth_inside)
        
    elif viseme == "U":
        # Pursed lips - like "food"
        outer = (mx - mouth_w//4, my - mouth_h//2, mx + mouth_w//4, my + mouth_h//3)
        draw.ellipse(outer, fill=lip_color)
        draw.ellipse(outer, outline=lip_color, width=2)
        # Small opening
        draw.ellipse((mx - 3, my - 2, mx + 3, my + 2), fill=mouth_inside)
        
    elif viseme == "MBP":
        # Closed lips - M, B, P sounds
        outer = (mx - mouth_w//3, my - mouth_h//4, mx + mouth_w//3, my + mouth_h//4)
        draw.ellipse(outer, fill=lip_color)
        draw.ellipse(outer, outline=lip_color, width=2)
        # Top lip line
        draw.line((mx - mouth_w//3, my - 2, mx + mouth_w//3, my - 2), fill=lip_color, width=3)
        
    elif viseme == "STH":
        # Teeth showing - S, TH sounds
        outer = (mx - mouth_w//3, my - mouth_h//2, mx + mouth_w//3, my + mouth_h//3)
        draw.ellipse(outer, fill=mouth_inside)
        # Top teeth
        draw.rectangle((mx - mouth_w//3, my - mouth_h//4, mx + mouth_w//3, my), fill=teeth_color)
        # Bottom teeth slightly
        draw.rectangle((mx - mouth_w//4, my, mx + mouth_w//4, my + mouth_h//6), fill=teeth_color)
        
    elif viseme == "smile":
        # Big smile expression
        outer = (mx - mouth_w//2, my - mouth_h//3, mx + mouth_w//2, my + mouth_h//2)
        draw.ellipse(outer, fill=mouth_inside)
        draw.arc((mx - mouth_w//2, my - mouth_h//2, mx + mouth_w//2, my + mouth_h), 
                 start=0, end=180, fill=lip_color, width=4)
        draw.rectangle((mx - mouth_w//3, my - mouth_h//4, mx + mouth_w//3, my), fill=teeth_color)
        
    return img


def _draw_blink(img: Image.Image, face_box: Tuple[int, int, int, int], 
                eyes: Tuple[Tuple[int, int], Tuple[int, int]], 
                style: str = "normal") -> Image.Image:
    """Draw realistic eye blink - closed eyes."""
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    
    x, y, w, h = face_box
    left_eye, right_eye = eyes
    
    # Eye dimensions
    eye_w = int(0.12 * w)
    eye_h = int(0.06 * h) if style == "normal" else int(0.03 * h)
    
    # Skin color for eyelid
    skin = _sample_skin_color(img, face_box)
    
    if style == "normal":
        # Normal blink - curved line
        # Left eye
        draw.arc((left_eye[0] - eye_w//2, left_eye[1] - eye_h, 
                  left_eye[0] + eye_w//2, left_eye[1] + eye_h),
                 start=0, end=180, fill=skin, width=4)
        # Right eye
        draw.arc((right_eye[0] - eye_w//2, right_eye[1] - eye_h, 
                  right_eye[0] + eye_w//2, right_eye[1] + eye_h),
                 start=0, end=180, fill=skin, width=4)
    else:
        # Quick blink - shorter
        draw.line((left_eye[0] - eye_w//3, left_eye[1], 
                   left_eye[0] + eye_w//3, left_eye[1]), fill=skin, width=3)
        draw.line((right_eye[0] - eye_w//3, right_eye[1], 
                   right_eye[0] + eye_w//3, right_eye[1]), fill=skin, width=3)
    
    return img


def _draw_open_eyes(img: Image.Image, face_box: Tuple[int, int, int, int],
                   eyes: Tuple[Tuple[int, int], Tuple[int, int]]) -> Image.Image:
    """Draw open eyes with iris and pupil."""
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    
    x, y, w, h = face_box
    left_eye, right_eye = eyes
    
    eye_w = int(0.10 * w)
    eye_h = int(0.06 * h)
    
    # Eye white
    eye_white = (255, 255, 255, 255)
    iris_color = (100, 80, 60, 255)  # Brownish
    pupil_color = (10, 10, 10, 255)
    
    # Left eye
    draw.ellipse((left_eye[0] - eye_w//2, left_eye[1] - eye_h, 
                  left_eye[0] + eye_w//2, left_eye[1] + eye_h),
                 fill=eye_white, outline=(200, 200, 200, 255), width=2)
    draw.ellipse((left_eye[0] - eye_w//4, left_eye[1] - eye_h//2, 
                  left_eye[0] + eye_w//4, left_eye[1] + eye_h//2),
                 fill=iris_color)
    draw.ellipse((left_eye[0] - eye_w//6, left_eye[1] - eye_h//3, 
                  left_eye[0] + eye_w//6, left_eye[1] + eye_h//3),
                 fill=pupil_color)
    # Highlight
    draw.ellipse((left_eye[0] - eye_w//5, left_eye[1] - eye_h//3, 
                  left_eye[0] - eye_w//8, left_eye[1] - eye_h//5),
                 fill=(255, 255, 255, 200))
    
    # Right eye
    draw.ellipse((right_eye[0] - eye_w//2, right_eye[1] - eye_h, 
                  right_eye[0] + eye_w//2, right_eye[1] + eye_h),
                 fill=eye_white, outline=(200, 200, 200, 255), width=2)
    draw.ellipse((right_eye[0] - eye_w//4, right_eye[1] - eye_h//2, 
                  right_eye[0] + eye_w//4, right_eye[1] + eye_h//2),
                 fill=iris_color)
    draw.ellipse((right_eye[0] - eye_w//6, right_eye[1] - eye_h//3, 
                  right_eye[0] + eye_w//6, right_eye[1] + eye_h//3),
                 fill=pupil_color)
    # Highlight
    draw.ellipse((right_eye[0] - eye_w//5, right_eye[1] - eye_h//3, 
                  right_eye[0] - eye_w//8, right_eye[1] - eye_h//5),
                 fill=(255, 255, 255, 200))
    
    return img


def _build_idle_shift(base: Image.Image) -> Image.Image:
    """Enhanced idle frame with slight movement."""
    shifted = ImageChops.offset(base, 2, 0)
    mixed = Image.blend(base, shifted, 0.15)
    mixed = mixed.rotate(0.5, resample=Image.BICUBIC, expand=False)
    return ImageEnhance.Sharpness(mixed).enhance(1.05)


def _build_breathing_idle(base: Image.Image) -> Image.Image:
    """Idle frame with subtle breathing animation."""
    # Slight vertical shift
    shifted = ImageChops.offset(base, 0, -2)
    mixed = Image.blend(base, shifted, 0.1)
    return mixed


def _save(img: Image.Image, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert("RGB").save(path, format="PNG", optimize=True)


def _needs_regeneration(source_path: str, outputs: list[str]) -> bool:
    if not outputs:
        return True
    if any(not os.path.exists(p) for p in outputs):
        return True
    try:
        source_mtime = os.path.getmtime(source_path)
        try:
            generator_mtime = os.path.getmtime(__file__)
        except Exception:
            generator_mtime = 0
        try:
            config_mtime = os.path.getmtime(getattr(config, "__file__", ""))
        except Exception:
            config_mtime = 0
        trigger_mtime = max(source_mtime, generator_mtime, config_mtime)
        return any(os.path.getmtime(p) < trigger_mtime for p in outputs)
    except:
        return True


def generate_avatar_frames(source_path: str):
    """Generate all avatar frames for realistic lip-sync animation."""
    print(f"[Avatar] Generating enhanced frames from: {source_path}")
    
    base = _prepare_square_image(source_path, TARGET_SIZE)
    face_box = _detect_face_box(base)
    eyes = _detect_eyes(base, face_box)
    skin = _sample_skin_color(base, face_box)
    
    # ============= IDLE FRAMES =============
    print("[Avatar] Generating idle frames...")
    _save(base, config.ASSISTANT_AVATAR_PATH)
    
    idle_shift = _build_idle_shift(base)
    _save(idle_shift, getattr(config, "ASSISTANT_IDLE_SHIFT", config.ASSISTANT_AVATAR_PATH))
    
    breathing_idle = _build_breathing_idle(base)
    _save(breathing_idle, os.path.join(os.path.dirname(config.ASSISTANT_AVATAR_PATH), "idle_breath.png"))
    
    # ============= BLINK FRAMES =============
    print("[Avatar] Generating blink frames...")
    blink_normal = _draw_blink(base, face_box, eyes, "normal")
    _save(blink_normal, getattr(config, "ASSISTANT_BLINK", config.ASSISTANT_AVATAR_PATH))
    
    blink_quick = _draw_blink(base, face_box, eyes, "quick")
    _save(blink_quick, os.path.join(os.path.dirname(config.ASSISTANT_AVATAR_PATH), "blink_quick.png"))
    
    # ============= VISEME FRAMES (8 mouth shapes for lip-sync) =============
    print("[Avatar] Generating viseme frames for lip-sync...")
    
    visemes = ["neutral", "A", "E", "I", "O", "U", "MBP", "STH"]
    viseme_names = ["viseme_neutral", "viseme_A", "viseme_E", "viseme_I", 
                    "viseme_O", "viseme_U", "viseme_MBP", "viseme_STH"]
    
    assets_dir = os.path.dirname(config.ASSISTANT_AVATAR_PATH)
    
    for viseme, name in zip(visemes, viseme_names):
        frame = _draw_viseme_mouth(base, face_box, viseme, skin)
        path = os.path.join(assets_dir, f"{name}.png")
        _save(frame, path)
        print(f"  - {name}.png")
    
    # ============= SPEAKING FRAMES (for simple animation fallback) =============
    print("[Avatar] Generating speaking frames...")
    speak_1 = _draw_viseme_mouth(base, face_box, "E", skin)  # Wide mouth
    _save(speak_1, config.ASSISTANT_SPEAK_1)
    
    speak_2 = _draw_viseme_mouth(base, face_box, "A", skin)  # Open mouth
    _save(speak_2, config.ASSISTANT_SPEAK_2)
    
    # ============= EXPRESSION FRAMES =============
    print("[Avatar] Generating expression frames...")
    smile_frame = _draw_viseme_mouth(base, face_box, "smile", skin)
    _save(smile_frame, os.path.join(assets_dir, "smile.png"))
    
    # ============= OPEN EYES FRAMES (for when waking from blink) =============
    print("[Avatar] Generating eye frames...")
    open_eyes = _draw_open_eyes(base, face_box, eyes)
    _save(open_eyes, os.path.join(assets_dir, "eyes_open.png"))
    
    print("[Avatar] Frame generation complete!")
    print("[Avatar] Generated frames:")
    print("  - idle.png, idle_shift.png, idle_breath.png")
    print("  - blink.png, blink_quick.png, eyes_open.png")
    print("  - smile.png")
    print("  - viseme_neutral.png through viseme_STH.png (8 lip-sync frames)")
    print("  - speak_1.png, speak_2.png")


def ensure_avatar_frames(force: bool = False) -> tuple[bool, str]:
    """Ensure all avatar frames exist, regenerate if needed."""
    source_path = _resolve_source_photo()
    if not source_path:
        return False, "No source photo found for avatar generation."

    assets_dir = os.path.dirname(config.ASSISTANT_AVATAR_PATH)
    
    # Check all required frames
    required_frames = [
        config.ASSISTANT_AVATAR_PATH,
        getattr(config, "ASSISTANT_IDLE_SHIFT", config.ASSISTANT_AVATAR_PATH),
        getattr(config, "ASSISTANT_BLINK", config.ASSISTANT_AVATAR_PATH),
        config.ASSISTANT_SPEAK_1,
        config.ASSISTANT_SPEAK_2,
        os.path.join(assets_dir, "viseme_neutral.png"),
        os.path.join(assets_dir, "viseme_A.png"),
        os.path.join(assets_dir, "viseme_E.png"),
        os.path.join(assets_dir, "viseme_I.png"),
        os.path.join(assets_dir, "viseme_O.png"),
        os.path.join(assets_dir, "viseme_U.png"),
        os.path.join(assets_dir, "viseme_MBP.png"),
        os.path.join(assets_dir, "viseme_STH.png"),
    ]
    
    if not force and not _needs_regeneration(source_path, required_frames):
        return True, f"Avatar frames already current ({os.path.basename(source_path)})."

    try:
        print(f"[Avatar] Source selected: {source_path}")
        using_generated_source = _is_generated_avatar_asset(source_path)
        if using_generated_source:
            print(
                "[Avatar] Warning: source is an existing generated frame. "
                "Add assets/bkr2.0.png (or user_photo.png) for a true personalized avatar."
            )
        generate_avatar_frames(source_path)
        if using_generated_source:
            return True, (
                "Avatar frames regenerated from existing frame. "
                "For better 3D realism, add assets/bkr2.0.png and regenerate."
            )
        return True, f"Enhanced avatar frames generated from {os.path.basename(source_path)}."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Avatar generation failed: {e}"
