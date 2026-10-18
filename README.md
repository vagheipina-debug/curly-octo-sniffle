# G3Q Helper - Mobile Quiz App

Fast PDF-based question answering app for Gujarat Gyan Guru Quiz (G3Q).

## Features
- Upload PDF study material
- Camera / Gallery capture + OCR
- Ultra-fast answers using Groq API
- Dark / Light mode
- Installable as PWA (Add to Home Screen)

## How to Run

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional but recommended) Set Groq API key:
```bash
# Windows
set GROQ_API_KEY=your_key_here

# Mac/Linux
export GROQ_API_KEY=your_key_here
```
Get free key at: https://console.groq.com

3. Start the app:
```bash
python app.py
```

4. Open on phone (same Wi-Fi):
- Find your computer IP (ipconfig / ifconfig)
- Open `http://YOUR_IP:5000` in phone browser
- Or use ngrok for public URL

## Make APK
1. Run the app + ngrok
2. Go to https://www.pwabuilder.com
3. Paste your ngrok URL → Start → Package for Android → Download APK
