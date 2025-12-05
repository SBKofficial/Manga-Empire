import os
import json
import requests
import random
import asyncio
import re
import time
import cv2
from bs4 import BeautifulSoup
import edge_tts
from moviepy.editor import *
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
DB_FILE = "database.json"
VIDEO_OUTPUT = "short.mp4"
# ✅ REVERTED TO STABLE BASE URL
WEBSITE_URL = "https://sbkofficial.github.io/Manga-Empire/" 
TARGET_URL = "https://asuracomic.net/" 

# --- YOUTUBE UPLOADER (omitted for brevity, assume unchanged) ---
class YouTubeUploader:
    def __init__(self):
        token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
        if not token_json: raise Exception("❌ No Token Found in Secrets!")
        creds = Credentials.from_authorized_user_info(json.loads(token_json))
        self.youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    def upload(self, file, title, desc, tags):
        print(f"🚀 Uploading: {title}")
        body = {
            "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "24"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(file, chunksize=-1, resumable=True)
        req = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        res = None
        while res is None:
            status, res = req.next_chunk()
            if status: print(f"Uploading... {int(status.progress() * 100)}%")
        return res['id']

    def comment(self, vid_id, text):
        try:
            self.youtube.commentThreads().insert(
                part="snippet",
                body={"snippet": {"videoId": vid_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}
            ).execute()
            print("✅ Comment Posted.")
        except Exception as e:
            print(f"⚠️ Comment Error: {e}")

# --- MODULE 2: SCRAPER (FIXED) ---
def get_trending():
    print("🕷️ Scraping Asura (Base URL)...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(TARGET_URL, headers=headers)
        r.raise_for_status() # Raise error for bad status codes
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # NEW ROBUST LOGIC: Target the latest update list first
        item = soup.find('div', class_='utao-sty') # Common item style for listings
        
        if not item:
            # Fallback to the general story card list
            item = soup.find('div', class_='bs') 
        
        if not item:
            print("❌ Could not find a primary manga container.")
            return None

        # Extract data from the first found container
        link = item.find('a')['href']
        title = item.find('a')['title']
        
        # Get Details page
        r2 = requests.get(link, headers=headers)
        r2.raise_for_status()
        s2 = BeautifulSoup(r2.text, 'html.parser')
        
        # Get image, using robust selector
        img_tag = s2.find('div', class_='thumb').find('img') if s2.find('div', class_='thumb') else s2.find('div', class_='fthumb').find('img')
        img = img_tag['src'] if img_tag else "PLACEHOLDER_URL"

        desc_div = s2.find('div', class_='entry-content')
        desc = desc_div.text.strip().replace("\n", " ") if desc_div else "A legendary story you must read."
        desc = re.sub(r'\s+', ' ', desc)[:250]
        
        return {"title": title, "link": link, "image": img, "desc": desc}
    
    except requests.exceptions.RequestException as req_e:
        print(f"❌ Network Error or Invalid URL: {req_e}")
        return None
    except Exception as e: 
        print(f"❌ Scraper Logic Error: {e}")
        return None

# --- MODULE 3: VIDEO GENERATOR (omitted for brevity, assume unchanged) ---
async def make_video(data):
    print("🎬 Generating Video...")
    # Download Image
    try:
        img_data = requests.get(data['image']).content
        with open("cover.jpg", 'wb') as f: f.write(img_data)
    except:
        print("⚠️ Failed to download image. Using blank file.")
        # Create a temporary black image to avoid crash
        Image.new('RGB', (1080, 1920), color = 'black').save("cover.jpg")
    
    # Audio Script
    text = f"If you need a new S-Rank series, read {data['title']}. {data['desc']}. This is a certified hidden gem. Read it now on our website, link in the comments."
    await edge_tts.Communicate(text, "en-US-ChristopherNeural").save("voice.mp3")
    
    # Editing
    audio = AudioFileClip("voice.mp3")
    clip = ImageClip("cover.jpg").set_duration(audio.duration + 1)
    clip = clip.resize(height=1920)
    clip = clip.crop(x1=clip.w/2 - 540, y1=0, width=1080, height=1920)
    clip = clip.fl(lambda gf, t: cv2.resize(gf(t)[int(min(gf(t).shape[:2])*(0.04*t)):-int(min(gf(t).shape[:2])*(0.04*t)) or None], (gf(t).shape[1], gf(t).shape[0])))
    clip.set_audio(audio).write_videofile(VIDEO_OUTPUT, fps=24, codec='libx264', audio_codec='aac')
    print("✅ Video Ready.")


# --- MAIN ---
if __name__ == "__main__":
    data = get_trending()
    if not data: exit()
    
    # Database Logic
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f: json.dump([], f)
    
    with open(DB_FILE, 'r') as f: db = json.load(f)
    
    if any(d['title'] == data['title'] for d in db):
        print("⚠️ Already done today.")
    else:
        db.insert(0, data)
        with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
        print("✅ Database Updated.")
        
        asyncio.run(make_video(data))
        
        try:
            yt = YouTubeUploader()
            title = f"{data['title']} is S-RANK Material 🤯 #shorts"
            if len(title) > 100: title = f"Read {data['title']} Now! 😱 #shorts"
            
            desc = f"Welcome to S Rank Manga.\n\nRead here: {WEBSITE_URL}\n\n#manhwa #manga #srankmanga"
            vid_id = yt.upload(VIDEO_OUTPUT, title, desc, ["manhwa", "manga", "srankmanga"])
            
            yt.comment(vid_id, f"🔥 Read {data['title']} here: {WEBSITE_URL}")
        except Exception as e:
            print(f"❌ Upload failed: {e}")
