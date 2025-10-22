import os
import random
import requests
import io
import textwrap
import pandas as pd
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
    concatenate_audioclips,
)
from PIL import Image, ImageDraw, ImageFont, __version__ as PIL_VERSION

# ================= CONFIGURATION =================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRND7UwlVedot36-b5MyqJ2xWj_7jvAJBy7f-t8zy7HANfZKhp5nJm4hNb3DM4mfL5gGHtEmbOJRB4b/pub?gid=0&single=true&output=csv"
MIN_DURATION = 60   # seconds
FONT_SIZE = 48
TEXT_COLOR = "white"
TEXT_BG_OPACITY = 0.0
MAX_CHARS_PER_LINE = 40

BACKGROUND_DIR = "assets/background"
MUSIC_DIR = "assets/music"
print(f"Pillow version: {PIL_VERSION}")

def list_files(dir_path):
    if not os.path.isdir(dir_path):
        raise SystemExit(f"Directory not found: {dir_path}")
    files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    if not files:
        raise SystemExit(f"No files found in {dir_path}")
    return files

# ================= PICK RANDOM ASSETS =================
background_files = list_files(BACKGROUND_DIR)
music_files = list_files(MUSIC_DIR)
bg_choice = random.choice(background_files)
music_choice = random.choice(music_files)

# ================= FETCH QUOTE FROM CSV =================
resp = requests.get(CSV_URL)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))

# Prefer Formatted; fallback
formatted = None
if "Formatted" in df.columns:
    s = df["Formatted"].dropna()
    if len(s):
        formatted = str(s.iloc[-1]).strip()
if not formatted:
    q = str(df["Quote"].dropna().iloc[-1]).strip() if "Quote" in df.columns and df["Quote"].dropna().shape[0] else ""
    a = str(df["Author"].dropna().iloc[-1]).strip() if "Author" in df.columns and df["Author"].dropna().shape[0] else ""
    if q and a:
        formatted = f"“{q}” — {a}"
    elif q:
        formatted = f"“{q}”"
    else:
        raise SystemExit("No usable text found in CSV.")
print("Using quote:", formatted)

# ================= FONT + MEASUREMENT HELPERS =================
def load_font(size):
    candidates = [
        os.environ.get("FONT_PATH", "").strip(),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def measure(draw, text, font):
    # Returns width, height
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            w, h = draw.textsize(text, font=font)  # very old fallback
            return w, h

def line_height(font):
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent + 8
    except Exception:
        img = Image.new("RGB", (10, 10))
        d = ImageDraw.Draw(img)
        return measure(d, "Ag", font)[1] + 8

# ================= TEXT IMAGE =================
def make_text_image(text, size, font_size=48, text_color="white", bg_opacity=0.0, max_chars=40):
    w, h = size
    font = load_font(font_size)
    wrapper = textwrap.TextWrapper(width=max_chars, break_long_words=True, break_on_hyphens=True)
    lines = wrapper.wrap(text=text) or [""]

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lh = line_height(font)
    text_block_h = lh * len(lines)

    if bg_opacity > 0:
        box_h = text_block_h + 40
        box_w = int(w * 0.9)
        box_x = (w - box_w) // 2
        box_y = (h - box_h) // 2
        draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h],
                       fill=(0, 0, 0, int(255 * bg_opacity)))

    y = (h - text_block_h) // 2
    for line in lines:
        lw, _ = measure(draw, line, font)
        x = (w - lw) // 2
        draw.text((x, y), line, font=font, fill=text_color)
        y += lh

    return img

# ================= BACKGROUND CLIP =================
def open_background(path):
    lower = path.lower()
    if lower.endswith((".mp4", ".mov", ".gif", ".webm", ".mkv")):
        return VideoFileClip(path).without_audio()
    # Try as image (works even if extensionless)
    try:
        Image.open(path).verify()
        return ImageClip(path).set_duration(MIN_DURATION)
    except Exception:
        # If it’s actually a video with no extension, try video open as fallback
        return VideoFileClip(path).without_audio()

clip = open_background(bg_choice)

# Ensure at least MIN_DURATION
if clip.duration < MIN_DURATION:
    loops = int(MIN_DURATION // max(0.1, clip.duration)) + 1
    clip = concatenate_videoclips([clip] * loops).subclip(0, MIN_DURATION)
else:
    clip = clip.subclip(0, MIN_DURATION)

# ================= TEXT OVERLAY =================
w, h = clip.size
text_img = make_text_image(
    formatted, size=(w, h), font_size=FONT_SIZE,
    text_color=TEXT_COLOR, bg_opacity=TEXT_BG_OPACITY,
    max_chars=MAX_CHARS_PER_LINE
)
text_img_path = "quote_overlay.png"
text_img.save(text_img_path)
txt_clip = ImageClip(text_img_path).set_duration(clip.duration).set_position(("center", "center"))

# ================= AUDIO =================
audio = AudioFileClip(music_choice)
if audio.duration < clip.duration:
    loops = int(clip.duration // max(0.1, audio.duration)) + 1
    audio = concatenate_audioclips([audio] * loops).subclip(0, clip.duration)
else:
    audio = audio.subclip(0, clip.duration)

# ================= COMPOSE =================
final = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
final.write_videofile("motivational_video.mp4", fps=24, codec="libx264", audio_codec="aac")
print("Saved motivational_video.mp4")
