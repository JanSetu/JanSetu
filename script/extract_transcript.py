#!/usr/bin/env python3
"""
Using youtube_transcript_api extract the transcript of a video from YouTube.

"""

import os
import sys
import json # used to store data in json format
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build


load_dotenv()


api_key = os.getenv('GOOGLE_API_KEY')  # 🔑 Put your API key here

# Directory where you want to store transcripts
TRANSCRIPTS_DIR = "transcripts"

# Create the folder if it doesn't exist
if not os.path.exists(TRANSCRIPTS_DIR):
    os.makedirs(TRANSCRIPTS_DIR)
    print(f"📁 Created folder: {TRANSCRIPTS_DIR}")

class YouTubeTranscript:
    def __init__(self, video_id):
        self.video_id = video_id
        self.transcript = None
        self.api = YouTubeTranscriptApi()

    @staticmethod
    def extract_video_id(url_or_id: str) -> str:
        """Extract the video ID from a URL or ID string."""
        if len(url_or_id) == 11 and ('/' not in url_or_id or '.' not in url_or_id):
            return url_or_id

        parsed_url = urlparse(url_or_id)

        # Short URL format: https://youtu.be/VIDEO_ID
        if parsed_url.hostname == 'youtu.be':
            parsed_url= parsed_url.path.lstrip('/')
        
        elif 'youtube.com' in parsed_url.hostname:

            # Embed URL format: https://www.youtube.com/embed/VIDEO_ID
            if '/embed/' in parsed_url.path:
                parsed_url= parsed_url.path.split('/embed')[1].split('/')[0]
            
            # Standard URL format: https://www.youtube.com/watch?v=VIDEO_ID
            else:
                query = parse_qs(parsed_url.query)
                if 'v' in query:
                    parsed_url= query['v'][0]
                else:
                    raise ValueError("Could not extract video ID from YouTube URL")  
        
        else:
            # Assume it's already a video ID
            parsed_url= url_or_id
        
        parsed_url = parsed_url.split('?')[0].split('&')[0]
        
        if len(parsed_url) != 11:
            raise ValueError(f"Invalid YouTube video ID: {parsed_url} (should be 11 characters)")
        
        return parsed_url
    
    @staticmethod
    def get_transcript(video_id: str, languages=['hi','en']):
        """
        Fetches the transcript for the given video ID.
        """
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

            if not transcript:
                raise Exception("No transcript data returned")
            else:
                return transcript
            
        except Exception as e:
            print(f"Error scraping transcript : {e}")
            return None


    #to save file in json format in form of list
    @staticmethod    
    def save_transcript(video_id: str, transcript: list,output_dir="transcripts"):
        """
        Save transcript data to a JSON file.
        Args:
        transcript_data: The transcript list to save.

        Returns:
        The path to the saved JSON file.
        """

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)


        # Use the output_dir                                            
        filename =os.path.join(output_dir, f"{video_id}.json")  
        print(f"Saving transcript to: {filename}")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, indent=2, ensure_ascii=False)

            file_size = os.path.getsize(filename)
            print(f"Transcript saved successfully ({file_size} bytes)")

            return filename

            #to print the extacted transcript
            #with open(filename, "r", encoding="utf-8") as f:
                #data = json.load(f)

            #print(json.dumps(data, indent=2, ensure_ascii=False))

        except Exception as e:
            raise Exception(f"Error saving transcript: {str(e)}")


    #to save the file in srt format
    """
    @staticmethod
    def save_as_srt(video_id: str, transcript: list):
        
        #Save the transcript to an SRT subtitle file.
        
        def format_timestamp(seconds: float) -> str:
            td = timedelta(seconds=seconds)
            total_seconds = int(td.total_seconds())
            millis = int((td.total_seconds() - total_seconds) * 1000)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

        filename = f"{video_id}.srt"
        with open(filename, "w", encoding="utf-8") as f:
            for index, item in enumerate(transcript, start=1):
                start = format_timestamp(item['start'])
                end = format_timestamp(item['start'] + item['duration'])
                text = item['text']

                f.write(f"{index}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

        print(f"SRT file saved: {filename}")
        return filename
    """

    def process_video(self, video_input: str) -> str:
        """
        Process a YouTube video to extract and save its transcript.

        Args:
            video_input: YouTube URL or video ID

        Returns:
            Path to saved transcript file
        """
        # Extract clean video ID
        video_id = self.extract_video_id(video_input)
        self.video_id = video_id  # Update instance variable if needed
        print(f"Processing video ID: {video_id}")

        output_file = f"{video_id}.json"
        if Path(output_file).exists():
            print(f"Transcript file already exists: {output_file}")
            response = input("Overwrite existing file? (y/N): ").strip().lower()
            if response != 'y':
                print("Skipping download.")
                return output_file

        # Fetch transcript
        transcript_data = self.get_transcript(video_id)
        if not transcript_data:
            raise Exception("No transcript data fetched.")

        # Save to file to json
        saved_file = self.save_transcript(video_id,transcript_data,output_dir=TRANSCRIPTS_DIR)

        # Save SRT
        #srt_file = self.save_as_srt(video_id, transcript_data)
        
        # Fetch metadata
        metadata = self.get_video_metadata(video_id)
        if metadata:
            meta_file = os.path.join(TRANSCRIPTS_DIR, f"{video_id}_meta.json")
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"Metadata saved to: {meta_file}")


        # Display summary
        if isinstance(transcript_data, list):
            total_segments = len(transcript_data)
            print(f"Transcript contains {total_segments} segments")

            if total_segments > 0:
                first = transcript_data[0]
                last = transcript_data[-1]
                try:
                    duration = float(last['start']) + float(last['duration'])
                    print(f"Total duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
                except (ValueError, TypeError, KeyError):
                    pass

        return saved_file

        
    def split_large_transcript_file(input_file, max_lines=5000):
        """
        Split a large JSON transcript file into smaller parts if needed.
        """
        input_path = Path(input_file)
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected JSON to be a list.")

        total_segments = len(data)
        if total_segments <= max_lines:
            return []  # No splitting needed

        chunks = [
            data[i:i + max_lines]
            for i in range(0, total_segments, max_lines)
        ]

        base_name = input_path.stem

        new_files = []
        for idx, chunk in enumerate(chunks, start=1):
            output_file = input_path.parent / f"{base_name}_part{idx}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            new_files.append(output_file)
            print(f"Created chunk: {output_file} with {len(chunk)} segments")

        return new_files
    
    def get_video_metadata(self, video_id: str):
        """
        Fetch video metadata using YouTube Data API v3.
        Returns: dict with title, description, channel, publish date, etc.
        """
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            request = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = request.execute()

            if not response['items']:
                raise Exception("No metadata found for video")

            item = response['items'][0]
            metadata = {
                "video_id": video_id,
                "title": item['snippet']['title'],
                "description": item['snippet']['description'],
                "channel_title": item['snippet']['channelTitle'],
                "publish_time": item['snippet']['publishedAt'],
                "tags": item['snippet'].get('tags', []),
                "view_count": item['statistics'].get('viewCount'),
                "like_count": item['statistics'].get('likeCount'),
                "duration": item['contentDetails']['duration']
            }
            return metadata

        except Exception as e:
            print(f"Error fetching metadata: {e}")
            return None


def main():
    """
    Main entry point: 
    - Accepts YouTube URL or video ID from command line.
    - Processes the video: extract ID, get transcript, save JSON.
    """
    if len(sys.argv) != 2:
        print("Usage: python your_script_name.py <video_url_or_id>")
        print("\nExample:")
        print("   python your_script_name.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)

    if not api_key:
        print("❌ GOOGLE_API_KEY not found. Please set it in your .env file.")
        sys.exit(1)


    video_input = sys.argv[1]
    #api_key = sys.argv[2]

    try:
        # Create a YouTubeTranscript instance
        yt = YouTubeTranscript(video_id=None)  # You'll extract it in process_video()

        # Process the video (extract + scrape + save)
        saved_file = yt.process_video(video_input)

        print(f"\n✅ Success! Transcript saved to: {saved_file}")

    except ValueError as ve:
        print(f"Invalid input: {ve}")
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()