# Motivational Video Generator

Automatically generates 60-second motivational videos with random combinations of backgrounds, music, and quotes.

## Features
-  Creates 60-second videos automatically
-  Random background selection from 5 images
-  Random music selection from 5 tracks
-  Random quote from Google Sheets
-  Fully automated via GitHub Actions

## How to Use

1. **Run via GitHub Actions:**
   - Go to Actions tab
   - Select "Generate Motivational Video"
   - Click "Run workflow"
   - Download video from Artifacts

2. **Assets Structure:**
assets/
├── background/
│ ├── i1.jpg to i5.jpg
└── music/
└── m1.mp3 to m5.mp3
## Configuration
- Video Duration: 60 seconds
- Output: 1920x1080 (depends on background image)
- Format: MP4 (H.264/AAC)

## Workflow
Each run produces a unique video by randomly combining:
- 1 of 5 background images
- 1 of 5 music tracks
- 1 random quote from CSV
