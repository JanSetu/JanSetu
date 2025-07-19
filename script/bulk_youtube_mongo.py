#!/usr/bin/env python3
"""
Bulk YouTube JSON Uploader (for already merged JSON files)

Usage:
    python bulk_youtube_mongo.py <input_folder>
"""

import argparse
from pathlib import Path

# Import your uploader class
from youtube_mongo import YouTubeToMongoUploader

def main():
    parser = argparse.ArgumentParser(description="Bulk upload all merged YouTube JSON files in a folder to MongoDB.")
    parser.add_argument("input_folder", help="Path to folder with merged JSON files (each containing metadata + transcript)")
    args = parser.parse_args()

    input_path = Path(args.input_folder)
    if not input_path.exists() or not input_path.is_dir():
        print(f"❌ Error: '{args.input_folder}' is not a valid folder.")
        return

    uploader = YouTubeToMongoUploader()
    json_files = sorted(input_path.glob("*.json"))

    if not json_files:
        print("⚠️ No JSON files found in the folder.")
        return

    total_stats = {"processed": 0, "inserted": 0, "updated": 0, "errors": 0}

    for json_file in json_files:
        print(f"\n📄 Processing: {json_file.name}")
        try:
            data = uploader.load_json_file(str(json_file))
            result = uploader.upload_videos(data)
            for key in total_stats:
                total_stats[key] += result.get(key, 0)
        except Exception as e:
            print(f"❌ Failed to upload {json_file.name}: {e}")
            total_stats["errors"] += 1

    print("\n✅ Bulk Upload Summary:")
    for key, val in total_stats.items():
        print(f"  {key.capitalize()}: {val}")

if __name__ == "__main__":
    main()
