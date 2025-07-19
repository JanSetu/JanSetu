#!/usr/bin/env python3
"""
YouTube Data to MongoDB Uploader

This script loads YouTube video data from JSON files and saves them to MongoDB
for search and analysis, with support for full-text search and efficient querying.

Requirements:
- pymongo
- python-dotenv (optional, for environment variables)
- dateutil

Usage:
    python youtube_uploader.py <json_file.json>
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

try:
    from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING
    from pymongo.errors import ConnectionFailure, DuplicateKeyError, BulkWriteError
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages:")
    print("pip install pymongo python-dotenv python-dateutil")
    sys.exit(1)

try:
    from dateutil.parser import parse as parse_date
except ImportError:
    print("Warning: python-dateutil not available. Date parsing may be limited.")
    parse_date = None

# Load environment variables
load_dotenv()

class YouTubeToMongoUploader:
    def __init__(self, connection_string: str = None, database_name: str = "youtube_data"):
        """
        Initialize the YouTube to MongoDB uploader.
        
        Args:
            connection_string: MongoDB connection string. If None, will try to get from environment.
            database_name: Name of the MongoDB database to use
        """
        if connection_string is None:
            connection_string = os.getenv('MONGODB_CONNECTION_STRING')
            
        if not connection_string:
            raise ValueError(
                "MongoDB connection string is required. Set MONGODB_CONNECTION_STRING environment variable "
                "or pass connection_string parameter."
            )
        
        try:
            self.client = MongoClient(connection_string)
            # Test connection
            self.client.admin.command('ping')
            print("✅ Successfully connected to MongoDB")
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")
        
        self.db = self.client[database_name]
        self.setup_collections()
    
    def setup_collections(self):
        """Set up MongoDB collections with appropriate indexes."""
        
        # Raw videos collection
        self.videos = self.db.raw_videos
        
        # Create indexes for efficient querying
        indexes_to_create = [
            # Index on Channel ID for channel-based queries
            {"keys": [("Channel_Id", ASCENDING)], "name": "channel_id_idx"},
            
            # Index on published date for time-based queries
            {"keys": [("published_Date", DESCENDING)], "name": "published_date_idx"},
            
            # Index on views (converted to numeric) for sorting
            {"keys": [("views_numeric", DESCENDING)], "name": "views_numeric_idx"},
            
            # Text index for full-text search on title and description
            {"keys": [("Video_title", TEXT), ("Description", TEXT), ("Channel_Name", TEXT)], "name": "text_search_idx"},
            
            # Index on category for filtering
            {"keys": [("category", ASCENDING)], "name": "category_idx"},
            
            # Index on hasTranscript for filtering videos with transcripts
            {"keys": [("hasTranscript", ASCENDING)], "name": "transcript_idx"},
            
            # Compound index for common query patterns
            {"keys": [("Channel_Id", ASCENDING), ("published_Date", DESCENDING)], "name": "channel_date_idx"},
        ]
        
        # Try to create unique index on VideoURL, but handle existing null values
        try:
            # Use sparse index to skip documents with missing or null VideoURL
            self.videos.create_index(
                [("VideoURL", ASCENDING)],
                unique=True,
                name="video_url_unique",
                sparse=True
            )
        except Exception as e:
            print(f"⚠️ Warning: Could not create index video_url_unique: {e}")

        
        for index_spec in indexes_to_create:
            try:
                self.videos.create_index(
                    index_spec["keys"], 
                    unique=index_spec.get("unique", False),
                    name=index_spec["name"]
                )
            except Exception as e:
                # Index might already exist
                if "already exists" not in str(e):
                    print(f"Warning: Could not create index {index_spec['name']}: {e}")
        
        print("✅ Collections and indexes set up successfully")
    
    def extract_numeric_views(self, views_str: str) -> Optional[int]:
        """Extract numeric value from views string like '1348 views'."""
        if not views_str:
            return None
        
        # Remove 'views' and any commas, then extract number
        numeric_part = re.sub(r'[^\d]', '', views_str)
        try:
            return int(numeric_part) if numeric_part else None
        except ValueError:
            return None
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string like '200:24' to total seconds."""
        if not duration_str:
            return None
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return None
        except (ValueError, AttributeError):
            return None
    
    def parse_published_date(self, date_str: str) -> Optional[datetime]:
        """Parse published date string to datetime object."""
        if not date_str:
            return None
        
        if parse_date:
            try:
                return parse_date(date_str)
            except Exception:
                pass
        
        # Fallback parsing for ISO format
        try:
            # Handle timezone format like '2024-10-08T17:05:23-07:00'
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            pass
        
        return None
    
    def process_transcript(self,transcript_data):
        """
        Processes transcript data from either:
        - List of segments: [{"text": ..., "start": ..., "duration": ...}]
        - Dict with full transcript: {"formattedContent": "...", ...}

        Returns a dictionary containing normalized transcript metadata.
        """
        processed = {}

        # ✅ Case 1: List-based segmented transcript
        if isinstance(transcript_data, list) and all(isinstance(seg, dict) and "text" in seg for seg in transcript_data):
            texts = [seg.get("text", "").strip() for seg in transcript_data if "text" in seg]
            joined = " ".join(texts)
            processed["transcript_text"] = joined.strip()
            processed["transcript_length"] = len(joined)
            processed["word_count"] = len(joined.split())
            processed["segment_count"] = len(transcript_data)
            processed["has_transcript"] = True
            processed["format"] = "segments"
            processed["segments"] = transcript_data  # 👈 this line adds the segments
            return processed

        # ✅ Case 2: Dict-based transcript (LLM or Gemini format)
        elif isinstance(transcript_data, dict):
            transcript_text = transcript_data.get("formattedContent") \
                            or transcript_data.get("transcript_text") \
                            or transcript_data.get("text", "")
            if transcript_text:
                processed["transcript_text"] = transcript_text.strip()
                processed["transcript_length"] = len(transcript_text)
                processed["word_count"] = len(transcript_text.split())
                processed["segment_count"] = len(transcript_text.split("\n"))  # rough guess
                processed["has_transcript"] = True
                processed["is_auto_generated"] = transcript_data.get("isAutoGenerated", False)
                processed["is_translated"] = transcript_data.get("isTranslated", False)
                processed["is_caption"] = transcript_data.get("isCaption", False)
                processed["format"] = "formattedContent"
                return processed

        # ❌ Unrecognized format
        return {}


    
    def clean_and_enhance_video_data(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and enhance video data with additional processed fields."""
        cleaned = video_data.copy()

        # Normalize video ID and URL
        video_id = video_data.get("video_id")
        video_url = video_data.get("VideoURL", "").strip()

        # Extract video ID from URL if needed
        if not video_id:
            if "watch?v=" in video_url:
                video_id = video_url.split("watch?v=")[-1].split("&")[0]
            elif "youtu.be/" in video_url:
                video_id = video_url.split("youtu.be/")[-1].split("?")[0]

        # Rebuild URL if missing or malformed
        if not video_url or not video_url.startswith("http"):
            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                video_id = f"unknown_{datetime.now().isoformat()}"
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"⚠️ Rebuilt VideoURL: {video_url}")

        cleaned["video_id"] = video_id
        cleaned["VideoURL"] = video_url

        # Numeric views handling
        cleaned["views_numeric"] = (
            self.extract_numeric_views(video_data.get("Views")) or
            self.extract_numeric_views(video_data.get("view_count")) or 0
        )

        # Duration parsing
        duration_str = video_data.get("Runtime") or video_data.get("duration")
        cleaned["duration_seconds"] = (
            self.parse_duration(duration_str) or
            self.parse_iso_duration(duration_str) or 0
        )

        # Published datetime
        date_str = video_data.get("published_Date") or video_data.get("publish_time")
        cleaned["published_datetime"] = self.parse_published_date(date_str) or datetime.now(timezone.utc)

        # Transcript processing
        transcript_info = self.process_transcript(video_data.get("transcript", {}))
        cleaned["transcript_info"] = transcript_info
        cleaned["hasTranscript"] = bool(transcript_info.get("transcript_text"))

        # Add searchable text (title, description, channel + partial transcript)
        searchable_parts = []
        for field in ["Video_title", "Description", "Channel_Name"]:
            if video_data.get(field):
                searchable_parts.append(str(video_data[field]))

        if transcript_info.get("transcript_text"):
            searchable_parts.append(transcript_info["transcript_text"][:1000])

        cleaned["searchable_text"] = " ".join(searchable_parts)

        # Metadata
        cleaned["processed_at"] = datetime.now(timezone.utc)
        cleaned["data_source"] = "youtube_scraper"

        return cleaned

       
    def parse_iso_duration(self, iso_str: str) -> Optional[int]:
        """Parse ISO 8601 duration like 'PT3M40S' to total seconds."""
        import re
        if not iso_str or not iso_str.startswith("PT"):
            return None
        try:
            minutes = seconds = 0
            match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', iso_str)
            if match:
                minutes = int(match.group(1)) if match.group(1) else 0
                seconds = int(match.group(2)) if match.group(2) else 0
            return minutes * 60 + seconds
        except Exception:
            return None


    
    def load_json_file(self, json_file: str) -> List[Dict[str, Any]]:
        """Load and parse JSON file containing YouTube data."""
        print(f"Loading JSON file: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both single video object and list of videos
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON file must contain a video object or list of videos")
            
            print(f"✅ Loaded {len(data)} video records from JSON file")
            return data
        except Exception as e:
            raise Exception(f"Error loading JSON file: {e}")
    
    def upload_videos(self, videos_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Upload video data to MongoDB with bulk operations for efficiency."""
        print(f"Processing {len(videos_data)} videos...")
        
        processed_videos = []
        stats = {"processed": 0, "inserted": 0, "updated": 0, "errors": 0}
        
        # Process each video
        for video_data in videos_data:
            try:
                cleaned_video = self.clean_and_enhance_video_data(video_data)
                
                # Validate that required fields are present and not None
                if not cleaned_video.get("VideoURL"):
                    print(f"Warning: Skipping video with no VideoURL: {video_data}")
                    stats["errors"] += 1
                    continue
                
                processed_videos.append(cleaned_video)
                stats["processed"] += 1
            except Exception as e:
                print(f"Warning: Error processing video {video_data.get('VideoURL', 'https://www.youtube.com/watch?v=')}: {e}")
                stats["errors"] += 1
        
        if not processed_videos:
            print("No videos to upload after processing")
            return stats
        
        # Process videos one by one to handle errors gracefully
        print(f"Uploading {len(processed_videos)} processed videos...")
        
        for video in processed_videos:
            try:
                # Use update_one with upsert instead of bulk operations for better error handling
                result = self.videos.update_one(
                    {"VideoURL": video["VideoURL"]},
                    {"$set": video},
                    upsert=True
                )
                
                if result.upserted_id:
                    stats["inserted"] += 1
                elif result.modified_count > 0:
                    stats["updated"] += 1
                    
            except Exception as e:
                print(f"Error: {e}")
                stats["errors"] += 1
                continue
        
        print(f"✅ Upload complete:")
        print(f"   Processed: {stats['processed']} videos")
        print(f"   Inserted: {stats['inserted']} new videos")
        print(f"   Updated: {stats['updated']} existing videos")
        if stats["errors"] > 0:
            print(f"   Errors: {stats['errors']} videos failed processing")
        
        return stats
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the raw_videos collection."""
        total_videos = self.videos.count_documents({})
        videos_with_transcripts = self.videos.count_documents({"hasTranscript": True})
        
        # Get channel distribution
        pipeline = [
            {"$group": {"_id": "$Channel_Name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_channels = list(self.videos.aggregate(pipeline))
        
        # Get date range
        date_range = list(self.videos.aggregate([
            {"$match": {"published_datetime": {"$exists": True}}},
            {"$group": {
                "_id": None,
                "earliest": {"$min": "$published_datetime"},
                "latest": {"$max": "$published_datetime"}
            }}
        ]))
        
        stats = {
            "total_videos": total_videos,
            "videos_with_transcripts": videos_with_transcripts,
            "transcript_percentage": round((videos_with_transcripts / total_videos * 100), 2) if total_videos > 0 else 0,
            "top_channels": top_channels,
            "date_range": date_range[0] if date_range else None
        }
        
        return stats


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Upload YouTube video data to MongoDB")
    parser.add_argument("json_file", help="Path to the JSON file containing YouTube video data or transcript")
    parser.add_argument("--mode", choices=["video", "transcript"], default="video", help="Upload mode: 'video' (default) or 'transcript'")
    parser.add_argument("--database", default="youtube_data", help="MongoDB database name (default: youtube_data)")
    
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"Error: Input file '{args.json_file}' does not exist.")
        sys.exit(1)
    
    try:
        uploader = YouTubeToMongoUploader(database_name=args.database)

        if args.mode == "transcript":
            transcript_data = uploader.load_json_file(args.json_file)
            if isinstance(transcript_data, list):
                transcript = uploader.process_transcript(transcript_data)
                video_id = Path(args.json_file).stem

                video_data = {
                    "video_id": video_id,
                    "VideoURL": f"https://www.youtube.com/watch?v={video_id}",
                    "Video_title": f"Transcript for {video_id}",
                    "Description": "",
                    "Channel_Name": "",
                    "Channel_Id": "",
                    "Views": "",
                    "Runtime": "",
                    "published_Date": None,
                    "hasTranscript": True,
                    "transcript": transcript_data  # Keep raw segments
                }

                print(f"Uploading transcript as single document for video ID: {video_id}")
                uploader.upload_videos([video_data])
            else:
                print("Error: Transcript file must contain a list of transcript segments.")
        else:
            videos_data = uploader.load_json_file(args.json_file)
            uploader.upload_videos(videos_data)

        collection_stats = uploader.get_collection_stats()
        print(f"\n📊 Collection Statistics:")
        print(f"  Total videos in collection: {collection_stats['total_videos']:,}")
        print(f"  Videos with transcripts: {collection_stats['videos_with_transcripts']:,} ({collection_stats['transcript_percentage']}%)")
        
        if collection_stats["top_channels"]:
            print("  Top channels by video count:")
            for channel in collection_stats["top_channels"][:5]:
                print(f"    {channel['_id']}: {channel['count']} videos")
        
        if collection_stats["date_range"]:
            date_range = collection_stats["date_range"]
            if date_range["earliest"] and date_range["latest"]:
                print(f"  Date range: {date_range['earliest'].strftime('%Y-%m-%d')} to {date_range['latest'].strftime('%Y-%m-%d')}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()