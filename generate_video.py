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
MIN_DURATION = 60  # minimum video duration in seconds
FONT_SIZE = 48
TEXT_COLOR = "white"
TEXT_BG_OPACITY = 0.0
MAX_CHARS_PER_LINE = 40

# ================= RANDOM BACKGROUND & MUSIC =================
background = os.listdir("assets/background")
musics = os.listdir("assets/music")
bg_choice = os.path.join("assets/background", random.choice(background))
music_choice = os.path.join("assets/music", random.choice(musics))

# ================= FETCH QUOTE FROM CSV =================
resp = requests.get(CSV_URL)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))
df = df.dropna(subset=["Formatted"])
last = df.iloc[-1]
formatted = str(last.get("Formatted", f"{last['Quote']} — {last['Author']}"))

# ================= HELPER FUNCTION =================
def make_text_image(text, size, font_size=48, text_color="white", bg_opacity=0.0, max_chars=40):
    w, h = size
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    wrapper = textwrap.TextWrapper(width=max_chars)
    lines = wrapper.wrap(text=text)

    # Use getbbox instead of getsize (Pillow >= 10)
    line_h = (font.getbbox("A")[3] - font.getbbox("A")[1]) + 8
    text_block_h = line_h * len(lines)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_opacity > 0:
        box_h = text_block_h + 40
        box_w = int(w * 0.9)
        box_x = (w - box_w) // 2
        box_y = (h - box_h) // 2
        draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(0, 0, 0, int(255 * bg_opacity)))

    y_text = (h - text_block_h) // 2
    for line in lines:
        bbox_line = font.getbbox(line)
        line_w = bbox_line[2] - bbox_line[0]
        x_text = (w - line_w) // 2
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += line_h

    return img

# ================= PREPARE BACKGROUND CLIP =================
if bg_choice.lower().endswith((".mp4", ".mov", ".gif")):
    clip = VideoFileClip(bg_choice)
else:
    img_clip = ImageClip(bg_choice).set_duration(MIN_DURATION)
    clip = img_clip

# Ensure video is at least MIN_DURATION
if clip.duration < MIN_DURATION:
    loops = int(MIN_DURATION // clip.duration) + 1
    clip = concatenate_videoclips([clip] * loops).subclip(0, MIN_DURATION)
else:
    clip = clip.subclip(0, MIN_DURATION)

# ================= ADD QUOTE TEXT =================
w, h = clip.size
text_img = make_text_image(formatted, size=(w, h), font_size=FONT_SIZE,
                           text_color=TEXT_COLOR, bg_opacity=TEXT_BG_OPACITY,
                           max_chars=MAX_CHARS_PER_LINE)
text_img_path = "quote_overlay.png"
text_img.save(text_img_path)
txt_clip = ImageClip(text_img_path).set_duration(clip.duration).set_position(("center", "center"))

# ================= LOAD & ADJUST AUDIO =================
audio = AudioFileClip(music_choice)
if audio.duration < clip.duration:
    loops = int(clip.duration // audio.duration) + 1
    audio = concatenate_audioclips([audio] * loops).subclip(0, clip.duration)
else:
    audio = audio.subclip(0, clip.duration)

# ================= COMPOSE FINAL VIDEO =================
final = CompositeVideoClip([clip, txt_clip])
final = final.set_audio(audio)
final.write_videofile("motivational_video.mp4", fps=24, codec="libx264", audio_codec="aac")

print("Saved motivational_video.mp4")
