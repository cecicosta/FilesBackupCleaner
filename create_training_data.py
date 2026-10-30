"""Generate training data with features and pseudo-labels."""

import os
import json
import numpy as np

# Configuration
BACKUP_DIR = "/home/cc/Documents/Backup novo"
METADATA_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classification_metadata_v2.json"
OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels.json"


def get_file_extension(filepath):
    """Get lowercase extension."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() if ext else ""


def analyze_name_patterns(filename):
    """Analyze filename patterns for junk indicators."""
    name_lower = filename.lower().strip()
    
    has_numeric_prefix = filename[0].isdigit() if filename else False
    
    generic_patterns = [
        'download', 'untitled', 'temp', 'image', 'screenshot', 
        'clipboard', 'capture', 'copy', '(1)', '(2)', '(3)'
    ]
    has_generic_name = any(pat in name_lower for pat in generic_patterns)
    
    underscore_count = name_lower.count('_')
    words = __import__('re').split(r'[_\-\s]', name_lower.replace('.', ''))
    word_count = len([w for w in words if w])
    
    underscore_ratio = underscore_count / word_count if word_count > 0 else 0.0
    
    trailing_chars = filename[-1] in ['~', '.', ' ', '\t']
    
    return {
        "has_numeric_prefix": has_numeric_prefix,
        "has_generic_name": has_generic_name,
        "underscore_ratio": round(underscore_ratio, 3),
        "trailing_chars": trailing_chars,
    }


def compute_entropy(filepath):
    """Compute Shannon entropy of file content."""
    try:
        with open(filepath, 'rb') as f:
            data = f.read(min(10240, os.path.getsize(filepath)))
        
        if not data or len(data) == 0:
            return 0.0
        
        import math
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        
        entropy = 0.0
        length = len(data)
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        
        return round(entropy, 4)
    except Exception:
        return 0.0


def is_text_file(filepath):
    """Check if file appears to be text-based."""
    try:
        with open(filepath, 'rb') as f:
            sample = f.read(8192)
        
        if not sample or len(sample) == 0:
            return False
        
        ascii_count = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
        ascii_ratio = ascii_count / len(sample)
        
        return ascii_ratio > 0.7
    except Exception:
        return False


def create_pseudo_labels(all_files):
    """Create labels based on current cleanup_skill_v2_4.py rules."""
    JUNK_EXTENSIONS = {
        '.cbp', '.layout', '.depend', '.pro.user', 
        '.o', '.dll', '.so', '.a', '.lib', '.dylib', '.bin', '.out', '.class',
        '.wasm', '.jar', '.war', '.pyc', '.pyo', '.ilk', '.pdb', '.exp', 
        '.exe', '.blend1',
    }
    
    JUNK_NAME_PATTERNS = ['download', 'untitled', 'temp', '(1)', '(2)']
    
    labels = []
    
    for file_data in all_files:
        filename = file_data['file']['filename'].lower()
        ext = file_data['file']['extension'].lower() or ''
        
        is_junk = False
        
        if ext in JUNK_EXTENSIONS:
            is_junk = True
        
        if any(pat in filename for pat in JUNK_NAME_PATTERNS):
            is_junk = True
        
        if file_data['name_patterns'].get('underscore_ratio', 0) > 0.5 and file_data['file']['size'] < 1024 * 1024:
            is_junk = True
        
        labels.append(int(is_junk))
    
    return np.array(labels)


def main():
    print("=" * 70)
    print("Training Data Generation Script")
    print("=" * 70)
    
    # Walk through backup directory and collect file info
    print("\nScanning backup directory...")
    all_files = []
    
    for root, dirs, files in os.walk(BACKUP_DIR):
        if '.git' in root.split(os.sep):
            continue
        
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                rel_path = os.path.relpath(filepath, BACKUP_DIR)
                stat_info = os.stat(filepath)
                ext = get_file_extension(filepath)
                
                entropy = compute_entropy(filepath)
                is_text = is_text_file(filepath)
                name_patterns = analyze_name_patterns(filename)
                
                all_files.append({
                    "file": {
                        "path": rel_path,
                        "filename": filename,
                        "dirname": os.path.dirname(rel_path) or ".",
                        "extension": ext,
                        "size": stat_info.st_size,
                    },
                    "content": {
                        "entropy": entropy,
                        "is_text": is_text,
                    },
                    "name_patterns": name_patterns,
                })
            except Exception as e:
                pass
    
    print(f"  Collected {len(all_files)} files")
    
    # Create labels
    print("\nCreating pseudo-labels...")
    y_list = create_pseudo_labels(all_files)
    
    # Save to JSON
    OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels.json"
    output_data = {
        "total_files": len(all_files),
        "junk_count": int(np.sum(y_list)),
        "not_junk_count": int(len(y_list) - np.sum(y_list)),
        "all_files": all_files,
        "labels": y_list.tolist(),
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f)
    
    print(f"\nTraining data saved to: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.2f} MB")
    
    # Show summary
    print("\nSummary:")
    print(f"  Total files: {len(all_files)}")
    print(f"  Labeled as junk: {int(np.sum(y_list))}")
    print(f"  Labeled as not-junk: {int(len(y_list) - np.sum(y_list))}")


if __name__ == "__main__":
    main()