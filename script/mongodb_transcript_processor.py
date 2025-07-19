#!/usr/bin/env python3
"""
MongoDB Parliamentary Transcript Processor

This script processes raw AI-transcribed parliamentary session data from MongoDB
using LangChain and Google's Gemini model to clean, correct, and format the text
for Knowledge Graph extraction.

Requirements:
- langchain-google-genai
- pymongo
- python-dotenv (optional, for environment variables)

Usage:
    python mongodb_transcript_processor.py --database parliamentary_graph
"""

import sys
import os
import argparse
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage, SystemMessage
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages:")
    print("pip install langchain-google-genai pymongo python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

class MongoDBTranscriptProcessor:
    def __init__(self, connection_string: str = None, database_name: str = "parliamentary_graph", api_key: str = None):
        """
        Initialize the processor with MongoDB connection and Gemini model.
        
        Args:
            connection_string: MongoDB connection string. If None, will try to get from environment.
            database_name: Name of the MongoDB database to use
            api_key: Google API key. If None, will try to get from environment.
        """
        # Setup MongoDB connection
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
        self.raw_videos = self.db.raw_videos
        self.videos = self.db.videos
        
        # Setup Gemini model
        if api_key is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            
        if not api_key:
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=1.0,
            thinking_budget=0  # Disable thinking mode
        )
        
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Return the comprehensive system prompt for transcript processing."""
        return """**Objective:**
The primary objective of this task is to transform raw, AI-transcribed parliamentary session data from Barbados into a clean, accurate, and time-aligned textual format suitable for subsequent Knowledge Graph (KG) extraction. This involves precise sentence segmentation, robust transcription correction, and careful handling of names and parliamentary conventions.

**Input Format:**
The input will be XML-formatted transcript data with time-aligned text segments in the format:
`<text start="[seconds]" dur="[duration]">[transcribed text]</text>`

**Processing Instructions:**

1. **Comprehensive Transcription Correction:**
   - **Error Identification:** Thoroughly review the text content of all segments for transcription errors. These typically include spelling mistakes, grammatical inaccuracies, missing punctuation, and mishearings (e.g., homophones, words incorrectly segmented or combined by the AI).
   - **Clarity & Accuracy:** Correct all identified errors to ensure the text is grammatically sound, correctly spelled, and accurately reflects the likely spoken content. The goal is to produce highly readable and semantically coherent sentences.
   - **Indian English & Context:** Be mindful of Indian English nuances, common parliamentary terminology, and the formal tone expected in parliamentary proceedings. Ensure corrections align with this context (e.g., "Honourable" vs. "Honorable" - prefer "Honourable" as per Indian spelling).

2. **Strict Name & Entity Handling:**
   - **Extreme Caution with Proper Nouns:** Exercise the utmost caution with proper nouns, especially names of individuals (e.g., Members of Parliament, ministers, citizens mentioned), constituencies, specific legislation, or organizations.
   - **Ambiguity Resolution:** If there is *any* doubt regarding the correct spelling of a proper noun, or if the transcribed name sounds ambiguous or could be mistaken, **replace it with `[unknown]`**. This is crucial to prevent the propagation of factual errors into the Knowledge Graph.
   - **Parliamentary Titles:** Accurately identify and correctly spell common parliamentary titles and forms of address, such as "Mr. Speaker," "Mr. President," "Honourable Member for [Constituency Name]," "Minister [Name]," "Prime Minister," "Leader of the Opposition," etc., ensuring they are capitalized correctly. Do *not* use `[unknown]` for these if their context is clear.

3. **Accurate Sentence Segmentation (NLP-driven):**
   - **Complete Sentences:** Using advanced Natural Language Processing (NLP) techniques, accurately identify and segment complete sentences. This will often involve merging text segments from multiple input XML elements to form a single, coherent sentence, or occasionally splitting a single text segment if it contains more than one complete sentence.
   - **Logical Flow:** Ensure that each output line represents a complete, grammatically correct, and logically coherent sentence. Avoid creating fragmented sentences or run-on sentences.
   - **Punctuation:** Insert appropriate punctuation marks (periods, question marks, exclamation points, commas, etc.) to ensure sentence clarity and correctness.

4. **Timecode Assignment:**
   - **Sentence Start Time:** For each identified complete sentence, assign the start time (in integer seconds) of the *first* input XML segment that contributes to that sentence.
   - **Rounding:** Convert the start time from the original string (e.g., "103.840") to an integer number of seconds, rounding *down* to the nearest whole second (e.g., "103.840" becomes 103, "109.360" becomes 109).

**Output Format:**
The output should be plain text, where each line represents a single, complete, time-aligned, and corrected sentence. The format for each line must be:

`[integer_seconds] [Complete and corrected sentence]`

**Key Considerations:**
- **Precision is Paramount:** Every correction and segmentation decision impacts the quality of the downstream Knowledge Graph.
- **Contextual Understanding:** Leverage the context of parliamentary proceedings to inform decisions, especially regarding names and formal language.
- **Balance of Correction and Preservation:** While fixing errors, avoid altering the fundamental meaning or intent of the speaker's original words.
- **No Interpretation:** Do not summarize, interpret, or add information not explicitly stated. Focus solely on cleaning and structuring the transcript.

Process the following XML transcript data and return ONLY the formatted output with no additional commentary or explanation:"""

    def extract_text_from_xml(self, xml_content: str) -> str:
        """
        Extract text content from XML transcript format for display purposes.
        
        Args:
            xml_content: XML-formatted transcript content
            
        Returns:
            Plain text content extracted from XML
        """
        if not xml_content:
            return ""
        
        # Remove XML tags and extract text content
        text_content = re.sub(r'<[^>]+>', '', xml_content)
        # Clean up whitespace
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        return text_content

    def get_videos_with_transcripts(self) -> List[Dict[str, Any]]:
        """
        Get all videos from raw_videos collection that have transcripts.
        
        Returns:
            List of video documents with transcripts
        """
        query = {
        "transcript.0": {"$exists": True},  # transcript is a non-empty array
        "hasTranscript": True
    }
        # Only fetch necessary fields
       
        projection = {
        "VideoURL": 1,
        "title": 1,  # Use 'title' instead of 'Video_title' or 'metadata.title'
        "video_id": 1,
        "transcript": 1,  # entire transcript array
        "_id": 1
    }


        videos = list(self.raw_videos.find(query, projection))
        print(f"Found {len(videos)} videos with transcripts in raw_videos collection")
        
        return videos

    def check_if_processed(self, video_url: str) -> bool:
        """
        Check if a video has already been processed and stored in the videos collection.
        
        Args:
            video_url: URL of the video to check
            
        Returns:
            True if already processed, False otherwise
        """
        existing = self.videos.find_one({"VideoURL": video_url, "transcript": {"$exists": True}})
        return existing is not None


    def chunk_xml_content(self, xml_content: str, max_chars: int = 10000) -> List[str]:
        """Split XML content into chunks no larger than max_chars."""
        chunks = []
        current_chunk = ""
        for line in re.findall(r'<text[^>]*>.*?</text>', xml_content, re.DOTALL):
            if len(current_chunk) + len(line) > max_chars:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += line
        if current_chunk:
            chunks.append(current_chunk)
        return chunks





    def process_single_transcript(self, xml_content: str, video_title: str) -> str:
        chunks = self.chunk_xml_content(xml_content)
        full_result = ""
        
        for i, chunk in enumerate(chunks):
            print(f"    🔹 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} characters)...")
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Video Title: {video_title}\n\nXML Transcript Data:\n\n{chunk}")
            ]
            try:
                response = self.llm.invoke(messages)
                result = response.content.strip() if response.content else ""
                if not result:
                    raise Exception("Model returned empty content for chunk")
                full_result += result + "\n"
            except Exception as e:
                print(f"    ❌ Error processing chunk {i+1}: {e}")
                continue
        
        return full_result.strip()

    def save_processed_transcript(self, video_url: str, video_title: str, video_id: str, processed_transcript: List[Dict[str, Any]]) -> bool:
        """
        Save the structured processed transcript to the videos collection.
        """
        try:
            document = {
                "VideoURL": video_url,
                "Video_title": video_title,
                "video_id": video_id,
                "processed_transcript": processed_transcript,
                "processed_at": datetime.now(timezone.utc),
                "processor_version": "mongodb_transcript_processor_v1.1",
                "hasTranscript": True,
                "hasSegments": True,
                "kg_extracted": False
            }

            result = self.videos.update_one(
                {"VideoURL": video_url},
                {"$set": document},
                upsert=True
            )
            return True

        except Exception as e:
            print(f"Error saving processed transcript: {e}")
            return False


    def process_all_transcripts(self, skip_existing: bool = True, limit: Optional[int] = None):
        """
        Process all transcripts from raw_videos and save to videos collection.
        
        Args:
            skip_existing: Whether to skip videos already processed
            limit: Maximum number of videos to process (None for all)
        """
        print("Starting transcript processing...")
        query = {
            "transcript.0": {"$exists": True},
            "hasTranscript": True
        }
        videos_with_transcripts = list(self.raw_videos.find(query))


        print(f"✅ Found {len(videos_with_transcripts)} videos with transcripts in raw_videos collection")

        
        # Apply limit if specified
       # Apply limit if specified
        videos_to_process = videos_with_transcripts[:limit] if limit else videos_with_transcripts
        if limit:
            print(f"Processing limited to first {limit} videos")

        
        stats = {
            "total": len(videos_to_process),
            "processed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for i, video in enumerate(videos_to_process, 1):
            video_url = video.get("VideoURL", "")
            video_title = (
                video.get("title") or
                video.get("Video_title") or
                video.get("metadata", {}).get("title") or
                "Unknown Title"
            )


            video_id = video.get("video_id", "")
            
            print(f"\n[{i}/{stats['total']}] Processing: {video_title[:80]}...")
            print(f"  🆔 Video ID: {video_id}")
            
            # Check if already processed
            if skip_existing and self.check_if_processed(video_url):
                print("  ⏭️  Already processed, skipping")
                stats["skipped"] += 1
                continue
            
            try:
                # Get transcript content
                segments = video.get("transcript", [])
                if not isinstance(segments, list):
                    print("  ⚠️ Transcript is not a list")
                    stats["errors"] += 1
                    continue

            # Reconstruct XML from segment list
                xml_content = ""
                for seg in segments:
                    start = seg.get("start", "0.0")
                    dur = seg.get("dur", "0.0")
                    text = seg.get("#text", "")
                    xml_content += f'<text start="{start}" dur="{dur}">{text}</text>\n'


                
                if not xml_content:
                    print("  ⚠️  No transcript content found")
                    stats["errors"] += 1
                    continue
                
                # Show content preview
                text_preview = self.extract_text_from_xml(xml_content)
                print(f"  📝 Content preview: {text_preview[:100]}...")
                print(f"  📊 XML content length: {len(xml_content)} characters")
                
                # Process transcript
                # Process transcript
                print("  🤖 Processing with Gemini...")
                raw_output = self.process_single_transcript(xml_content, video_title)

                # Convert Gemini output (e.g., "103 Sentence here") into structured format
                structured = []
                for line in raw_output.splitlines():
                    match = re.match(r"^(\d+)\s+(.+)", line.strip())
                    if match:
                        start, text = int(match.group(1)), match.group(2).strip()
                        structured.append({"start": start, "text": text})
                    else:
                        print(f"  ⚠️ Skipped malformed line: {line}")

                 # Save structured output to videos collection
                 # Save structured output to videos collection
                print("  💾 Saving processed transcript...")
                if self.save_processed_transcript(video_url, video_title, video_id, structured):
                    print(f"  ✅ Successfully processed and saved ({len(structured)} sentences)")
                    stats["processed"] += 1
                else:
                    print("  ❌ Failed to save processed transcript")
                    stats["errors"] += 1
                    
            except Exception as e:
                print(f"  ❌ Error processing video: {e}")
                stats["errors"] += 1
                continue
        
        # Print final statistics
        print(f"\n📊 Processing Complete!")
        print(f"  Total videos: {stats['total']}")
        print(f"  Successfully processed: {stats['processed']}")
        print(f"  Skipped (already processed): {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")

    def get_processing_stats(self) -> Dict[str, int]:
        """Get statistics about processed transcripts."""
        raw_with_transcripts = self.raw_videos.count_documents({
            "transcript.formattedContent": {"$exists": True, "$ne": ""},
            "hasTranscript": True
        })
        
        processed_count = self.videos.count_documents({
            "transcript": {"$exists": True, "$ne": ""}
        })
        
        return {
            "raw_videos_with_transcripts": raw_with_transcripts,
            "processed_transcripts": processed_count,
            "remaining": raw_with_transcripts - processed_count
        }

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Process parliamentary transcripts from MongoDB")
    parser.add_argument("--database", default="parliamentary_graph", help="MongoDB database name")
    parser.add_argument("--limit", type=int, help="Limit number of videos to process")
    parser.add_argument("--force", action="store_true", help="Reprocess already processed videos")
    parser.add_argument("--stats", action="store_true", help="Show processing statistics only")
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = MongoDBTranscriptProcessor(database_name=args.database)
        
        if args.stats:
            # Show statistics only
            stats = processor.get_processing_stats()
            print("📊 Processing Statistics:")
            print(f"  Raw videos with transcripts: {stats['raw_videos_with_transcripts']}")
            print(f"  Already processed: {stats['processed_transcripts']}")
            print(f"  Remaining to process: {stats['remaining']}")
            return
        
        # Process transcripts
        processor.process_all_transcripts(
            skip_existing=not args.force,
            limit=args.limit
        )
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nTo set up required credentials:")
        print("1. MongoDB: Set MONGODB_CONNECTION_STRING environment variable")
        print("2. Google API: Set GOOGLE_API_KEY environment variable")
        print("3. Or create a .env file with both values")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()