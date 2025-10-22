import os
import json
import random
from moviepy.editor import *
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image, ImageDraw, ImageFont
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class QuoteVideoGenerator:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.width = self.config['video']['width']
        self.height = self.config['video']['height']
        self.fps = self.config['video']['fps']
        self.max_duration = self.config['video']['max_duration']
    
    def get_quotes_from_sheets(self):
        """Fetch quotes from Google Sheets"""
        try:
            # Set up credentials
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(
                'credentials.json', 
                scopes=scope
            )
            client = gspread.authorize(creds)
            
            # Open the sheet (replace with your sheet name)
            sheet = client.open(os.getenv('SHEET_NAME')).sheet1
            
            # Get all records
            records = sheet.get_all_records()
            
            return records
        except Exception as e:
            print(f"Error fetching from Google Sheets: {e}")
            return []
    
    def select_random_background(self):
        """Select a random background image"""
        bg_folder = 'assets/backgrounds'
        backgrounds = [f for f in os.listdir(bg_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]
        
        if not backgrounds:
            raise FileNotFoundError("No background images found!")
        
        return os.path.join(bg_folder, random.choice(backgrounds))
    
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
        author_text = f"- {author}"
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
        quote = quote_data.get('Quote', quote_data.get('quote', ''))
        author = quote_data.get('Author', quote_data.get('author', 'Unknown'))
        
        print(f"Generating video for: {quote[:50]}...")
        
        # Select random background
        bg_path = self.select_random_background()
        
        # Calculate video duration (estimate based on reading speed)
        # Average reading speed: ~200 words per minute
        word_count = len(quote.split())
        estimated_duration = max(10, min((word_count / 200) * 60 + 5, self.max_duration))
        
        # Load background image
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
        music_path = self.get_random_music()
        audio = AudioFileClip(music_path).subclip(0, min(estimated_duration, self.max_duration))
        audio = audio.volumex(self.config['music']['volume'])
        
        # If music is shorter than video, loop it
        if audio.duration < estimated_duration:
            audio = afx.audio_loop(audio, duration=estimated_duration)
        else:
            audio = audio.subclip(0, estimated_duration)
        
        video = video.set_audio(audio)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'output/quote_video_{timestamp}.mp4'
        
        # Write video file
        video.write_videofile(
            output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Cleanup
        if os.path.exists(text_img_path):
            os.remove(text_img_path)
        
        print(f"Video generated: {output_path}")
        return output_path
    
    def get_random_music(self):
        """Get a random music file"""
        music_folder = 'assets/music'
        music_files = [f for f in os.listdir(music_folder) if f.endswith(('.mp3', '.wav', '.m4a'))]
        
        if not music_files:
            raise FileNotFoundError("No music files found!")
        
        return os.path.join(music_folder, random.choice(music_files))

def main():
    generator = QuoteVideoGenerator()
    
    # Get quotes from Google Sheets
    quotes = generator.get_quotes_from_sheets()
    
    if not quotes:
        print("No quotes found. Using sample quote...")
        quotes = [{
            'Quote': 'The only way to do great work is to love what you do.',
            'Author': 'Steve Jobs'
        }]
    
    # Generate video for the latest quote (or random)
    latest_quote = quotes[-1]  # or use random.choice(quotes)
    generator.generate_video(latest_quote)

if __name__ == "__main__":
    main()
