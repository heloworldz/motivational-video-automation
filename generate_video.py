import os
import random
import requests
import io
import textwrap
import pandas as pd
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_audioclips,
)
from PIL import Image, ImageDraw, ImageFont, __version__ as PIL_VERSION

# ================= CONFIGURATION =================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRND7UwlVedot36-b5MyqJ2xWj_7jvAJBy7f-t8zy7HANfZKhp5nJm4hNb3DM4mfL5gGHtEmbOJRB4b/pub?gid=0&single=true&output=csv"
VIDEO_DURATION = 60  # seconds
FONT_SIZE = 48
TEXT_COLOR = "white"
TEXT_BG_OPACITY = 0.2  # Semi-transparent black background for text
MAX_CHARS_PER_LINE = 40

BACKGROUND_DIR = "assets/background"
MUSIC_DIR = "assets/music"

print(f"Pillow version: {PIL_VERSION}")
print("="*50)

# ================= SELECT RANDOM ASSETS =================
def get_random_file(directory, extensions):
    """Get a random file from directory with given extensions"""
    if not os.path.isdir(directory):
        raise SystemExit(f"Directory not found: {directory}")
    
    files = []
    for f in os.listdir(directory):
        if any(f.lower().endswith(ext) for ext in extensions):
            files.append(os.path.join(directory, f))
    
    if not files:
        raise SystemExit(f"No valid files found in {directory}")
    
    chosen = random.choice(files)
    print(f"Selected from {directory}: {os.path.basename(chosen)}")
    return chosen

# Select random background and music
background_file = get_random_file(BACKGROUND_DIR, ['.jpg', '.jpeg', '.png'])
music_file = get_random_file(MUSIC_DIR, ['.mp3', '.wav', '.m4a'])

# ================= FETCH RANDOM QUOTE FROM CSV =================
print("\nFetching quotes from Google Sheets...")
resp = requests.get(CSV_URL)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))

# Collect all available quotes
all_quotes = []

# Try Formatted column first
if "Formatted" in df.columns:
    formatted = df["Formatted"].dropna()
    all_quotes.extend([str(q).strip() for q in formatted if str(q).strip()])

# If no formatted quotes, build from Quote and Author
if not all_quotes and "Quote" in df.columns:
    quotes = df["Quote"].dropna()
    authors = df["Author"].dropna() if "Author" in df.columns else pd.Series()
    
    for i, q in enumerate(quotes):
        q = str(q).strip()
        if q:
            if i < len(authors):
                a = str(authors.iloc[i]).strip()
                if a and a != 'nan':
                    all_quotes.append(f""{q}" — {a}")
                else:
                    all_quotes.append(f""{q}"")
            else:
                all_quotes.append(f""{q}"")

if not all_quotes:
    raise SystemExit("No quotes found in CSV")

# Select random quote
selected_quote = random.choice(all_quotes)
print(f"Selected quote: {selected_quote[:80]}..." if len(selected_quote) > 80 else f"Selected quote: {selected_quote}")

# ================= FONT HELPERS =================
def load_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    
    print("Warning: Using default font")
    return ImageFont.load_default()

def measure_text(draw, text, font):
    """Measure text dimensions"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)

def get_line_height(font):
    """Get line height for font"""
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent + 10
    except Exception:
        return FONT_SIZE + 10

# ================= CREATE TEXT OVERLAY =================
def create_text_overlay(text, img_size):
    """Create transparent image with text overlay"""
    width, height = img_size
    font = load_font(FONT_SIZE)
    
    # Wrap text
    wrapper = textwrap.TextWrapper(width=MAX_CHARS_PER_LINE, break_long_words=False)
    lines = wrapper.wrap(text)
    
    # Create transparent image
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Calculate text block dimensions
    line_height = get_line_height(font)
    text_height = line_height * len(lines)
    
    # Add semi-transparent background box if opacity > 0
    if TEXT_BG_OPACITY > 0:
        padding = 30
        box_height = text_height + (padding * 2)
        box_width = int(width * 0.85)
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2
        
        draw.rectangle(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            fill=(0, 0, 0, int(255 * TEXT_BG_OPACITY))
        )
    
    # Draw each line of text
    y_position = (height - text_height) // 2
    
    for line in lines:
        text_width, text_h = measure_text(draw, line, font)
        x_position = (width - text_width) // 2
        draw.text((x_position, y_position), line, font=font, fill=TEXT_COLOR)
        y_position += line_height
    
    return overlay

# ================= CREATE VIDEO =================
print("\nCreating video...")

# Load background image
print(f"Loading background: {background_file}")
background = ImageClip(background_file).set_duration(VIDEO_DURATION)

# Get video dimensions
video_width, video_height = background.size
print(f"Video dimensions: {video_width}x{video_height}")

# Create text overlay
print("Creating text overlay...")
text_overlay_img = create_text_overlay(selected_quote, (video_width, video_height))
text_overlay_path = "temp_text_overlay.png"
text_overlay_img.save(text_overlay_path)

# Create text clip
text_clip = ImageClip(text_overlay_path).set_duration(VIDEO_DURATION).set_position("center")

# Composite video
video = CompositeVideoClip([background, text_clip])

# ================= ADD MUSIC =================
print(f"Loading music: {music_file}")
audio = AudioFileClip(music_file)

# Loop audio if shorter than video
if audio.duration < VIDEO_DURATION:
    loops_needed = int(VIDEO_DURATION / audio.duration) + 1
    print(f"Looping audio {loops_needed} times")
    audio = concatenate_audioclips([audio] * loops_needed)

# Trim audio to exact video duration
audio = audio.subclip(0, VIDEO_DURATION)
video = video.set_audio(audio)

# ================= EXPORT VIDEO =================
print("\nExporting video (this may take a minute)...")
output_path = "motivational_video.mp4"

video.write_videofile(
    output_path,
    fps=24,
    codec="libx264",
    audio_codec="aac",
    threads=4,
    preset="medium",
    temp_audiofile="temp-audio.m4a",
    remove_temp=True
)

# Cleanup temporary file
if os.path.exists(text_overlay_path):
    os.remove(text_overlay_path)

print(f"\n✅ Success! Created {output_path}")
print(f"   Duration: {VIDEO_DURATION} seconds")
print(f"   Background: {os.path.basename(background_file)}")
print(f"   Music: {os.path.basename(music_file)}")
print(f"   Quote: {selected_quote[:50]}...")
