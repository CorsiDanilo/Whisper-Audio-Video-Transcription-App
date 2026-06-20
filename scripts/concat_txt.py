"""
Concatenates all .txt files in a directory sorted by modification time (newest first).

Usage:
    python scripts/concat_txt.py /path/to/directory

Example:
    python scripts/concat_txt.py ./audio/transcripts
"""
import argparse
from pathlib import Path

def merge_txt_files(directory):
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: Directory '{directory}' does not exist.")
        return

    # Get all .txt files
    txt_files = list(dir_path.glob("*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in '{directory}'.")
        return

    # Sort files by modification time (newest to oldest)
    txt_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    output_file = dir_path / "merged_output.txt"
    
    print(f"Found {len(txt_files)} text files. Merging into {output_file.name}...")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in txt_files:
            # Skip the output file if it's in the same directory and already exists
            if file_path == output_file:
                continue
                
            outfile.write(f"--- File: {file_path.name} ---\n")
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
            except UnicodeDecodeError:
                # Fallback to latin-1 if utf-8 fails
                try:
                    with open(file_path, 'r', encoding='latin-1') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"[Error reading file: {e}]\n")
            except Exception as e:
                outfile.write(f"[Error reading file: {e}]\n")
            outfile.write("\n\n")

    print(f"Merge complete. Output saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge all .txt files in a directory sorted by modification time (newest first).")
    parser.add_argument("directory", help="The directory containing the .txt files")
    args = parser.parse_args()
    
    merge_txt_files(args.directory)
