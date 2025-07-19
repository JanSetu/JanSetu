import os
import json
from googleapiclient.discovery import build
from extract_transcript import YouTubeTranscript  # <-- change to your module filename
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv('GOOGLE_API_KEY')  # 🔑 Put your API key here
playlist_id = "PLVOgwA_DiGzoo6KwL0eeDyUBBbTRGMgFy"  # 🔑 Put your playlist ID here - 4th session of 18th loksabha

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=api_key)

all_videos_data = []
video_ids = []

# --- Step 1: Get FIRST 50 video IDs from the playlist ---
pl_request = youtube.playlistItems().list(
    part="snippet",
    playlistId=playlist_id,
    maxResults=50   # ✅ Only first 50 videos
)
pl_response = pl_request.execute()

for item in pl_response["items"]:
    vid = item["snippet"]["resourceId"]["videoId"]
    video_ids.append(vid)

print(f"✅ Found {len(video_ids)} videos in the playlist")

# --- Step 2: Process each video ID ---
for vid in video_ids:
    print(f"🎥 Processing video: {vid}")

    # Fetch video metadata
    video_request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=vid
    )
    video_response = video_request.execute()
    if not video_response['items']:
        print(f"❌ Skipped {vid} (not found)")
        continue

    v_info = video_response['items'][0]

    title = v_info['snippet'].get('title')
    description = v_info['snippet'].get('description')
    channel = v_info['snippet'].get('channelTitle')
    views = v_info['statistics'].get('viewCount')
    published_date = v_info['snippet'].get('publishedAt')
    duration = v_info['contentDetails'].get('duration')  # ISO 8601

    # --- Get transcript and save to file ---
    yt = YouTubeTranscript(video_id=None)
    transcript_data = yt.get_transcript(vid)
    has_transcript = bool(transcript_data)

    transcript_filename = ""
    if has_transcript:
        # Save to file: e.g., OXV3AKneBtE.json
        transcript_filename = yt.save_transcript(vid, transcript_data)
        print(f"✅ Transcript saved: {transcript_filename}")

    # --- Build JSON object ---
    video_json = {
        "VideoURL": f"https://www.youtube.com/watch?v={vid}",
        "Video_title": title,
        "Description": description,
        "Channel_Name": channel,
        "Views": views,
        "Runtime": duration,
        "published_Date": published_date,
        "transcript": {
            "hasTranscript": has_transcript,
            "formattedContent": transcript_filename if has_transcript else ""
        }
    }

    all_videos_data.append(video_json)

# --- Step 3: Save entire playlist index to one file ---
with open("playlist_transcripts.json", "w", encoding="utf-8") as f:
    json.dump(all_videos_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ All done! Saved {len(all_videos_data)} entries to playlist_transcripts.json")

