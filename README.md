# Quote Video Generator 🎬

Automatically generates motivational quote videos with background music and images.

## Features
- Fetches quotes from Google Sheets
- Random background selection
- NCS music integration
- Automated video generation via GitHub Actions
- Maximum 60-second videos

## Setup

### 1. Google Sheets API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Sheets API
4. Create Service Account credentials
5. Download the JSON credentials file

### 2. GitHub Secrets
Add these secrets to your repository (Settings → Secrets and variables → Actions):

- `GOOGLE_CREDENTIALS`: Content of your Google credentials JSON file
- `SHEET_NAME`: Name of your Google Sheet

### 3. Add Assets
- Place background images in `assets/backgrounds/`
- Place NCS music files in `assets/music/`

### 4. Run
- Manual: Go to Actions → Generate Quote Video → Run workflow
- Automatic: Runs daily at 9 AM UTC
- On Push: Triggers when scripts are modified

## Configuration
Edit `config.json` to customize:
- Video dimensions
- Font sizes
- Colors
- Music volume

## Output
Videos are saved in `output/` and available as artifacts in GitHub Actions.
