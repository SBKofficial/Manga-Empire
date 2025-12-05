import os
import json
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DESC = """Welcome to S Rank Manga. 🕵️‍♂️
Your hub for the best Manga, Manhwa, and Webtoon recommendations.
✅ Action, Fantasy & Isekai
✅ Underrated Hidden Gems
Subscribe to level up your reading list.
"""

def main():
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_json: return

    creds = Credentials.from_authorized_user_info(json.loads(token_json))
    youtube = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    # 1. Get Top Search Keywords
    now = datetime.datetime.now()
    try:
        resp = analytics.reports().query(
            ids="channel==MINE",
            startDate=(now - datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            endDate=now.strftime("%Y-%m-%d"),
            metrics="views",
            dimensions="insightTrafficSourceDetail",
            filters="insightTrafficSourceType==YT_SEARCH",
            sort="-views", maxResults=15
        ).execute()
        keywords = [row[0] for row in resp.get("rows", [])]
    except: keywords = []

    # 2. Update Channel Settings
    chan_resp = youtube.channels().list(mine=True, part="brandingSettings,id").execute()
    chan_id = chan_resp['items'][0]['id']
    branding = chan_resp['items'][0]['brandingSettings']
    
    core_tags = ["manhwa", "manga", "webtoon", "s rank manga", "recommendations"]
    final_tags = list(set(core_tags + keywords))[:15]
    
    branding['channel']['keywords'] = " ".join([f'"{t}"' for t in final_tags])
    branding['channel']['description'] = BASE_DESC + f"\n\n🔥 Trending Searches: {', '.join(keywords[:5])}"
    
    youtube.channels().update(part="brandingSettings", body={"id": chan_id, "brandingSettings": branding}).execute()
    print("✅ Channel SEO Optimized.")

if __name__ == "__main__":
    main()
