import os
import json
import random
import pandas as pd
from moviepy.editor import *
from moviepy.video.fx.all import fadein, fadeout
import moviepy.audio.fx.all as afx
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

class QuoteVideoGenerator:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.width = self.config['video']['width']
        self.height = self.config['video']['height']
        self.fps = self.config['video']['fps']
        self.max_duration = self.config['video']['max_duration']
        
        # Define available assets
        self.backgrounds = [f'assets/backgrounds/i{i}.jpg' for i in range(1, 6)]
        self.music_files = [f'assets/music/m{i}.mp3' for i in range(1, 6)]
    
    def verify_assets(self):
        """Verify all required assets exist"""
        missing = []
        
        for bg in self.backgrounds:
            if not os.path.exists(bg):
                missing.append(bg)
        
        for music in self.music_files:
            if not os.path.exists(music):
                missing.append(music)
        
        if missing:
            raise FileNotFoundError(f"Missing assets: {', '.join(missing)}")
        
        print(f"✓ Found {len(self.backgrounds)} background images")
        print(f"✓ Found {len(self.music_files)} music files")
    
    def get_quotes_from_csv(self, csv_url):
        """Fetch quotes from public Google Sheets CSV"""
        try:
            # Read CSV from URL
            df = pd.read_csv(csv_url)
            
            # Convert to list of dictionaries
            quotes = df.to_dict('records')
            
            print(f"✓ Fetched {len(quotes)} quotes from Google Sheets")
            print(f"✓ Columns found: {list(df.columns)}")
            
            return quotes
        except Exception as e:
            print(f"⚠ Error fetching from Google Sheets: {e}")
            return []
    
    def select_random_background(self):
        """Select a random background image (i1.jpg to i5.jpg)"""
        return random.choice(self.backgrounds)
    
    def select_random_music(self):
        """Select a random music file (m1.mp3 to m5.mp3)"""
        return random.choice(self.music_files)
    
    def create_text_image(self, quote, author):
        """Create an image with the quote text"""
        img = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Try to load custom font, fallback to default
        try:
            quote_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                                           self.config['text']['quote_font_size'])
            author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 
                                            self.config['text']['author_font_size'])
        except:
            print("⚠ Using default font (custom fonts not available)")
            quote_font = ImageFont.load_default()
            author_font = ImageFont.load_default()
        
        # Wrap text
        quote_lines = self.wrap_text(quote, quote_font, self.config['text']['max_quote_width'])
        
        # Calculate total height
        quote_height = len(quote_lines) * (self.config['text']['quote_font_size'] + 20)
        author_height = self.config['text']['author_font_size'] + 40
        total_height = quote_height + author_height
        
        # Starting Y position (centered)
        y = (self.height - total_height) // 2
        
        # Draw quote lines
        for line in quote_lines:
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            # Draw stroke (outline)
            stroke_width = self.config['text']['stroke_width']
            for adj_x in range(-stroke_width, stroke_width+1):
                for adj_y in range(-stroke_width, stroke_width+1):
                    draw.text((x+adj_x, y+adj_y), line, font=quote_font, 
                             fill=self.config['text']['stroke_color'])
            
            # Draw main text
            draw.text((x, y), line, font=quote_font, 
                     fill=self.config['text']['font_color'])
            y += self.config['text']['quote_font_size'] + 20
        
        # Draw author
        author_text = f"— {author}"
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        author_width = bbox[2] - bbox[0]
        x = (self.width - author_width) // 2
        y += 40
        
        # Author stroke
        for adj_x in range(-stroke_width, stroke_width+1):
            for adj_y in range(-stroke_width, stroke_width+1):
                draw.text((x+adj_x, y+adj_y), author_text, font=author_font,
                         fill=self.config['text']['stroke_color'])
        
        draw.text((x, y), author_text, font=author_font, 
                 fill=self.config['text']['font_color'])
        
        return img
    
    def wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            
            # Create a temporary image to measure text
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            
            if width > max_width:
                if len(current_line) == 1:
                    lines.append(current_line[0])
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def generate_video(self, quote_data):
        """Generate video for a single quote"""
        # Handle different column name formats
        quote = quote_data.get('Quote', quote_data.get('quote', ''))
        author = quote_data.get('Author', quote_data.get('author', 'Unknown'))
        
        print(f"\n{'='*60}")
        print(f"Generating video for quote:")
        print(f'"{quote[:50]}..."')
        print(f"By: {author}")
        print(f"{'='*60}\n")
        
        # Select random background and music
        bg_path = self.select_random_background()
        music_path = self.select_random_music()
        
        print(f"Using background: {os.path.basename(bg_path)}")
        print(f"Using music: {os.path.basename(music_path)}")
        
        # Calculate video duration (based on reading speed)
        # Average reading speed: ~200 words per minute
        word_count = len(quote.split())
        estimated_duration = max(10, min((word_count / 200) * 60 + 5, self.max_duration))
        
        print(f"Video duration: {estimated_duration:.1f} seconds")
        
        # Load and prepare background image
        bg_clip = ImageClip(bg_path).set_duration(estimated_duration)
        bg_clip = bg_clip.resize((self.width, self.height))
        
        # Create text overlay
        text_img = self.create_text_image(quote, author)
        text_img_path = 'temp_text.png'
        text_img.save(text_img_path)
        
        text_clip = ImageClip(text_img_path).set_duration(estimated_duration)
        text_clip = text_clip.set_position('center')
        
        # Composite video
        video = CompositeVideoClip([bg_clip, text_clip])
        video = video.fx(fadein, 1).fx(fadeout, 1)
        
        # Add music
        print("Processing audio...")
        audio = AudioFileClip(music_path)
        
        # Random start point in the music (if music is longer than video)
        if audio.duration > estimated_duration:
            max_start = audio.duration - estimated_duration
            start_time = random.uniform(0, max_start)
            audio = audio.subclip(start_time, start_time + estimated_duration)
        else:
            # Loop music if it's shorter than video
            audio = afx.audio_loop(audio, duration=estimated_duration)
        
        audio = audio.volumex(self.config['music']['volume'])
        
        # Add fade in/out to audio
        audio = audio.audio_fadein(1).audio_fadeout(1)
        
        video = video.set_audio(audio)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_author = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_author = safe_author.replace(' ', '_')[:30]
        output_path = f'output/quote_{safe_author}_{timestamp}.mp4'
        
        # Write video file
        print("Rendering video...")
        video.write_videofile(
            output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset='medium',
            threads=4
        )
        
        # Cleanup
        if os.path.exists(text_img_path):
            os.remove(text_img_path)
        
        print(f"\n✓ Video generated successfully: {output_path}")
        return output_path

def main():
    print("Quote Video Generator")
    print("=" * 60)
    
    generator = QuoteVideoGenerator()
    
    # Verify assets exist
    try:
        generator.verify_assets()
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure all assets are in place:")
        print("- assets/backgrounds/i1.jpg through i5.jpg")
        print("- assets/music/m1.mp3 through m5.mp3")
        return
    
    # Your Google Sheets CSV URL
    csv_url = os.getenv('SHEET_CSV_URL', 
                        'https://docs.google.com/spreadsheets/d/e/2PACX-1vRND7UwlVedot36-b5MyqJ2xWj_7jvAJBy7f-t8zy7HANfZKhp5nJm4hNb3DM4mfL5gGHtEmbOJRB4b/pub?gid=0&single=true&output=csv')
    
    # Get quotes from Google Sheets
    quotes = generator.get_quotes_from_csv(csv_url)
    
    if not quotes:
        print("\n⚠ No quotes found in Google Sheets. Using sample quote...")
        quotes = [{
            'Quote': 'The only way to do great work is to love what you do.',
            'Author': 'Steve Jobs'
        }]
    
    # Generate video for the latest quote
    latest_quote = quotes[-1]
    generator.generate_video(latest_quote)
    
    print("\n" + "=" * 60)
    print("Done!")

if __name__ == "__main__":
    main()
