import json
import re
from pathlib import Path

def load_and_combine_transcripts(video_id, input_path):
    part_files = list(input_path.glob(f"{video_id}_part*.json"))

    if part_files:
        print(f"🔍 Found {len(part_files)} transcript parts for {video_id}: {[p.name for p in part_files]}")
        try:
            part_files.sort(key=lambda p: int(re.search(r'_part(\d+)', p.name).group(1)))
        except Exception as e:
            print(f"❌ Error sorting transcript parts for {video_id}: {e}")
            return None

        combined_transcript = []
        for part_file in part_files:
            with open(part_file, "r", encoding="utf-8") as f:
                try:
                    part_content = json.load(f)
                    if isinstance(part_content, list):
                        combined_transcript.extend(part_content)
                    elif isinstance(part_content, dict):
                        combined_transcript.append(part_content)
                except Exception as err:
                    print(f"❌ JSON decode error in {part_file.name}: {err}")
                    return None

        return combined_transcript

    # If no parts, fall back to full transcript
    full_transcript_file = input_path / f"{video_id}.json"
    if full_transcript_file.exists():
        print(f"📄 Using full transcript for {video_id}")
        with open(full_transcript_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"❌ No transcript found for {video_id}")
    return None


def load_and_combine_metadata(video_id, input_path):
    part_files = list(input_path.glob(f"{video_id}_meta_part*.json"))

    if part_files:
        print(f"🔍 Found {len(part_files)} metadata parts for {video_id}: {[p.name for p in part_files]}")
        try:
            part_files.sort(key=lambda p: int(re.search(r'_meta_part(\d+)', p.name).group(1)))
        except Exception as e:
            print(f"❌ Error sorting metadata parts for {video_id}: {e}")
            return None

        combined_metadata = {}
        for part_file in part_files:
            with open(part_file, "r", encoding="utf-8") as f:
                try:
                    part_content = json.load(f)
                    combined_metadata.update(part_content)  # Assuming parts contain disjoint keys
                except Exception as err:
                    print(f"❌ JSON decode error in {part_file.name}: {err}")
                    return None

        return combined_metadata

    # If no parts, fall back to single metadata file
    meta_file = input_path / f"{video_id}_meta.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"❌ No metadata found for {video_id}")
    return None


def merge_files_to_output_folder(input_folder, output_folder="new_data"):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    all_meta_files = list(input_path.glob("*_meta.json")) + list(input_path.glob("*_meta_part*.json"))
    all_video_ids = set()

    # Extract unique video IDs from all meta filenames
    for meta_file in all_meta_files:
        match = re.match(r"(.*)_meta(?:_part\d+)?\.json", meta_file.name)
        if match:
            all_video_ids.add(match.group(1))

    merged_count = 0

    for video_id in sorted(all_video_ids):
        output_file = output_path / f"{video_id}_combined.json"

        metadata = load_and_combine_metadata(video_id, input_path)
        transcript = load_and_combine_transcripts(video_id, input_path)

        if not metadata or not transcript:
            print(f"⚠️ Skipping {video_id}, incomplete metadata or transcript.")
            continue

        combined = metadata.copy()
        combined["transcript"] = transcript

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)

        print(f"✅ Merged: {output_file.name}")
        merged_count += 1

    print(f"\n🎉 Done. Total videos merged: {merged_count}")
    print(f"📁 Output in: {output_path.resolve()}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python merge_metadata_transcript.py <input_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]
    merge_files_to_output_folder(input_folder)
