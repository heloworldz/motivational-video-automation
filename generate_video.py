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
from PIL import Image, ImageDraw, ImageFont

# ================= CONFIGURATION =================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRND7UwlVedot36-b5MyqJ2xWj_7jvAJBy7f-t8zy7HANfZKhp5nJm4hNb3DM4mfL5gGHtEmbOJRB4b/pub?gid=0&single=true&output=csv"
MIN_DURATION = 60   # minimum video duration in seconds
FONT_SIZE = 48
TEXT_COLOR = "white"
TEXT_BG_OPACITY = 0.0
MAX_CHARS_PER_LINE = 40

BACKGROUND_DIR = "assets/background"
MUSIC_DIR = "assets/music"
# ==================================================

def list_files(dir_path, allowed_ext=None):
    if not os.path.isdir(dir_path):
        raise SystemExit(f"Directory not found: {dir_path}")
    files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
             if os.path.isfile(os.path.join(dir_path, f))]
    if allowed_ext:
        files = [f for f in files if f.lower().endswith(tuple(allowed_ext))]
    if not files:
        raise SystemExit(f"No files found in {dir_path}")
    return files

# ================= RANDOM BACKGROUND & MUSIC =================
background_files = list_files(BACKGROUND_DIR, allowed_ext=[".mp4", ".mov", ".gif", ".jpg", ".jpeg", ".png", ".webp"])
music_files = list_files(MUSIC_DIR, allowed_ext=[".mp3", ".wav", ".m4a", ".aac", ".flac"])
bg_choice = random.choice(background_files)
music_choice = random.choice(music_files)

# ================= FETCH QUOTE FROM CSV =================
resp = requests.get(CSV_URL)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))

# Prefer Formatted; fallback to Quote/Author if needed
text = None
if "Formatted" in df.columns:
    series = df["Formatted"].dropna()
    if len(series):
        text = str(series.iloc[-1]).strip()
if not text:
    q = str(df["Quote"].dropna().iloc[-1]).strip() if "Quote" in df.columns and df["Quote"].dropna().shape[0] else ""
    a = str(df["Author"].dropna().iloc[-1]).strip() if "Author" in df.columns and df["Author"].dropna().shape[0] else ""
    if q and a:
        text = f"“{q}” — {a}"
    elif q:
        text = f"“{q}”"
    else:
        raise SystemExit("No usable text found in CSV.")
formatted = text

# ================= FONT HELPERS (Pillow 10+ safe) =================
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

def measure(draw, s, font):
    # Prefer draw.textbbox; fallback to draw.textsize; fallback to font.getbbox
    try:
        bbox = draw.textbbox((0, 0), s, font=font)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    except Exception:
        try:
            w, h = draw.textsize(s, font=font)
            return (w, h)
        except Exception:
            try:
                bbox = font.getbbox(s)
                return (bbox[2] - bbox[0], bbox[3] - bbox[1])
            except Exception:
                # last resort approximation
                return (int(0.6 * font.size * max(1, len(s))), font.size)

def line_height(font):
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent + 8
    except Exception:
        # fallback using measured glyphs
        img = Image.new("RGB", (10, 10))
        d = ImageDraw.Draw(img)
        return measure(d, "Ag", font)[1] + 8

# ================= HELPER: MAKE TEXT IMAGE =================
def make_text_image(text, size, font_size=48, text_color="white",
                    bg_opacity=0.0, max_chars=40):
    w, h = size
    font = load_font(font_size)

    # Wrap text by character count (simple + robust)
    wrapper = textwrap.TextWrapper(width=max_chars, break_long_words=True, break_on_hyphens=True)
    lines = wrapper.wrap(text=text) or [""]

    # Measure
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lh = line_height(font)
    text_block_h = lh * len(lines)

    # Optional semi-opaque box
    if bg_opacity > 0:
        box_h = text_block_h + 40
        box_w = int(w * 0.9)
        box_x = (w - box_w) // 2
        box_y = (h - box_h) // 2
        draw.rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            fill=(0, 0, 0, int(255 * bg_opacity))
        )

    # Draw centered lines
    y = (h - text_block_h) // 2
    for line in lines:
        lw, _ = measure(draw, line, font)
        x = (w - lw) // 2
        draw.text((x, y), line, font=font, fill=text_color)
        y += lh

    return img

# ================= PREPARE BACKGROUND CLIP =================
bg_lower = bg_choice.lower()
if bg_lower.endswith((".mp4", ".mov", ".gif")):
    clip = VideoFileClip(bg_choice).without_audio()
else:
    img_clip = ImageClip(bg_choice).set_duration(MIN_DURATION)
    clip = img_clip

# Ensure video is at least MIN_DURATION
if clip.duration < MIN_DURATION:
    loops = int(MIN_DURATION // max(0.1, clip.duration)) + 1
    clip = concatenate_videoclips([clip] * loops).subclip(0, MIN_DURATION)
else:
    clip = clip.subclip(0, MIN_DURATION)

# ================= ADD QUOTE TEXT =================
w, h = clip.size
text_img = make_text_image(
    formatted, size=(w, h), font_size=FONT_SIZE,
    text_color=TEXT_COLOR, bg_opacity=TEXT_BG_OPACITY,
    max_chars=MAX_CHARS_PER_LINE
)
text_img_path = "quote_overlay.png"
text_img.save(text_img_path)
txt_clip = ImageClip(text_img_path).set_duration(clip.duration).set_position(("center", "center"))

# ================= LOAD & ADJUST AUDIO =================
audio = AudioFileClip(music_choice)
if audio.duration < clip.duration:
    loops = int(clip.duration // max(0.1, audio.duration)) + 1
    audio = concatenate_audioclips([audio] * loops).subclip(0, clip.duration)
else:
    audio = audio.subclip(0, clip.duration)

# ================= COMPOSE FINAL VIDEO =================
final = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
final.write_videofile("motivational_video.mp4", fps=24, codec="libx264", audio_codec="aac")
print("Saved motivational_video.mp4")
