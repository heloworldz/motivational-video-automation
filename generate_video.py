#!/usr/bin/env python3
"""
Motivational Video Generator
Creates a 60-second video with random background, music, and quote
"""

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
from PIL import Image, ImageDraw, ImageFont

# ================= CONFIGURATION =================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRND7UwlVedot36-b5MyqJ2xWj_7jvAJBy7f-t8zy7HANfZKhp5nJm4hNb3DM4mfL5gGHtEmbOJRB4b/pub?gid=0&single=true&output=csv"
VIDEO_DURATION = 60  # seconds
FONT_SIZE = 48
TEXT_COLOR = "white"
TEXT_BG_OPACITY = 0.25  # Semi-transparent background
MAX_CHARS_PER_LINE = 40

BACKGROUND_DIR = "assets/background"
MUSIC_DIR = "assets/music"

print("="*60)
print("MOTIVATIONAL VIDEO GENERATOR")
print("="*60)

# ================= HELPER FUNCTIONS =================
def get_random_file(directory, extensions):
    """Select a random file from directory with specified extensions"""
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    valid_files = []
    for filename in os.listdir(directory):
        if any(filename.lower().endswith(ext) for ext in extensions):
            valid_files.append(os.path.join(directory, filename))
    
    if not valid_files:
        raise FileNotFoundError(f"No valid files found in {directory}")
    
    selected = random.choice(valid_files)
    return selected

def fetch_quotes_from_csv():
    """Fetch all quotes from Google Sheets CSV"""
    print("Fetching quotes from Google Sheets...")
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Failed to fetch CSV: {e}")
    
    df = pd.read_csv(io.StringIO(response.text))
    quotes = []
    
    # Try Formatted column first
    if "Formatted" in df.columns:
        formatted = df["Formatted"].dropna()
        quotes.extend([str(q).strip() for q in formatted if str(q).strip()])
    
    # Fallback to Quote and Author columns
    if not quotes and "Quote" in df.columns:
        quote_col = df["Quote"].dropna()
        author_col = df["Author"].dropna() if "Author" in df.columns else pd.Series()
        
        for i, quote_text in enumerate(quote_col):
            quote_text = str(quote_text).strip()
            if quote_text:
                if i < len(author_col):
                    author = str(author_col.iloc[i]).strip()
                    if author and author != 'nan':
                        quotes.append(f'"{quote_text}" — {author}')
                    else:
                        quotes.append(f'"{quote_text}"')
                else:
                    quotes.append(f'"{quote_text}"')
    
    if not quotes:
        raise ValueError("No quotes found in CSV")
    
    return quotes

def load_font(size):
    """Load a suitable font"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    
    # Fallback to default
    return ImageFont.load_default()

def create_text_overlay(text, dimensions):
    """Create a transparent PNG with text overlay"""
    width, height = dimensions
    font = load_font(FONT_SIZE)
    
    # Create transparent image
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Wrap text
    wrapper = textwrap.TextWrapper(width=MAX_CHARS_PER_LINE, break_long_words=False)
    lines = wrapper.wrap(text)
    
    # Calculate text dimensions
    line_height = FONT_SIZE + 15
    total_text_height = line_height * len(lines)
    
    # Draw semi-transparent background box
    if TEXT_BG_OPACITY > 0:
        padding = 40
        box_width = int(width * 0.8)
        box_height = total_text_height + (padding * 2)
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2
        
        draw.rectangle(
            [(box_x, box_y), (box_x + box_width, box_y + box_height)],
            fill=(0, 0, 0, int(255 * TEXT_BG_OPACITY))
        )
    
    # Draw text centered
    y_position = (height - total_text_height) // 2
    
    for line in lines:
        # Get text width for centering
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_position = (width - text_width) // 2
        
        draw.text((x_position, y_position), line, font=font, fill=TEXT_COLOR)
        y_position += line_height
    
    return img

# ================= MAIN PROCESS =================
def main():
    # 1. Select random assets
    print("\n1. Selecting random assets...")
    background = get_random_file(BACKGROUND_DIR, ['.jpg', '.jpeg', '.png'])
    music = get_random_file(MUSIC_DIR, ['.mp3', '.wav', '.m4a'])
    print(f"   Background: {os.path.basename(background)}")
    print(f"   Music: {os.path.basename(music)}")
    
    # 2. Select random quote
    print("\n2. Selecting random quote...")
    quotes = fetch_quotes_from_csv()
    selected_quote = random.choice(quotes)
    print(f"   Total quotes available: {len(quotes)}")
    print(f"   Selected: {selected_quote[:60]}..." if len(selected_quote) > 60 else f"   Selected: {selected_quote}")
    
    # 3. Create video base
    print("\n3. Creating video...")
    video_clip = ImageClip(background).set_duration(VIDEO_DURATION)
    width, height = video_clip.size
    print(f"   Dimensions: {width}x{height}")
    print(f"   Duration: {VIDEO_DURATION} seconds")
    
    # 4. Create and add text overlay
    print("\n4. Adding text overlay...")
    text_img = create_text_overlay(selected_quote, (width, height))
    text_img.save("temp_overlay.png")
    text_clip = ImageClip("temp_overlay.png").set_duration(VIDEO_DURATION)
    
    # Composite video with text
    video = CompositeVideoClip([video_clip, text_clip])
    
    # 5. Add and process audio
    print("\n5. Processing audio...")
    audio = AudioFileClip(music)
    
    # Loop audio if needed
    if audio.duration < VIDEO_DURATION:
        loops = int(VIDEO_DURATION / audio.duration) + 1
        print(f"   Looping audio {loops} times")
        audio = concatenate_audioclips([audio] * loops)
    
    audio = audio.subclip(0, VIDEO_DURATION)
    video = video.set_audio(audio)
    
    # 6. Export final video
    print("\n6. Rendering final video...")
    print("   This may take 1-2 minutes...")
    
    video.write_videofile(
        "motivational_video.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="faster",
        logger=None  # Suppress verbose output
    )
    
    # Cleanup
    if os.path.exists("temp_overlay.png"):
        os.remove("temp_overlay.png")
    
    print("\n" + "="*60)
    print("✅ VIDEO CREATED SUCCESSFULLY!")
    print(f"   Output: motivational_video.mp4")
    print(f"   Size: {os.path.getsize('motivational_video.mp4') / (1024*1024):.2f} MB")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
