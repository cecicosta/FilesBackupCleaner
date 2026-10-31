"""
Feature Extraction Script v2.0 - Backup Junk Classification Metadata Collection
Adds NAME PATTERN FEATURES to baseline features from v1.0

New features added:
- filename (base name)
- has_numeric_prefix (bool)
- has_generic_name (bool)
- underscore_ratio (float)
- trailing_chars (bool)

Total features per file: 9
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

# Configuration
BACKUP_DIR = "/home/cc/Documents/Backup novo"
OUTPUT_FILE = "junk_classification_metadata_v2.json"


def get_file_extension(filepath):
    """Get lowercase extension."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() if ext else ""


def analyze_name_patterns(filename):
    """Analyze filename patterns for junk indicators.

    Returns dict with:
    - has_numeric_prefix: bool (starts with digits)
    - has_generic_name: bool (matches common junk patterns)
    - underscore_ratio: float (underscores / word count)
    - trailing_chars: bool (ends with ~, ., space)
    """
    name_lower = filename.lower().strip()
    
    # 1. Numeric prefix check
    has_numeric_prefix = filename[0].isdigit() if filename else False
    
    # 2. Generic name patterns
    generic_patterns = [
        'download', 'untitled', 'temp', 'image', 'screenshot', 
        'clipboard', 'capture', 'copy', '(1)', '(2)', '(3)'
    ]
    has_generic_name = any(pat in name_lower for pat in generic_patterns)
    
    # 3. Underscore ratio (underscores / word count)
    underscore_count = name_lower.count('_')
    # Split by underscore, space, or dash to get "words"
    words = re.split(r'[_\-\s]', name_lower.replace('.', ''))
    word_count = len([w for w in words if w])  # exclude empty strings
    
    underscore_ratio = underscore_count / word_count if word_count > 0 else 0.0
    
    # 4. Trailing characters
    trailing_chars = filename[-1] in ['~', '.', ' ', '\t']
    
    return {
        "has_numeric_prefix": has_numeric_prefix,
        "has_generic_name": has_generic_name,
        "underscore_ratio": round(underscore_ratio, 3),
        "trailing_chars": trailing_chars,
    }


def collect_all_features(filepath):
    """Collect all features for a single file (v1.0 + v2.0 name patterns)."""
    rel_path = os.path.relpath(filepath, BACKUP_DIR)
    filename = os.path.basename(filepath)
    
    # Basic file info (from v1.0)
    stat_info = os.stat(filepath)
    dirname = os.path.dirname(rel_path) or "."
    ext = get_file_extension(filepath)
    size = stat_info.st_size
    
    # Content analysis (from v1.0)
    import math
    try:
        # Compute entropy
        with open(filepath, 'rb') as f:
            data = f.read(min(10240, size))  # Read first 10KB for entropy
        
        if not data or len(data) == 0:
            entropy = 0.0
        else:
            freq = {}
            for byte in data:
                freq[byte] = freq.get(byte, 0) + 1
            
            entropy = 0.0
            length = len(data)
            for count in freq.values():
                p = count / length
                if p > 0:
                    entropy -= p * math.log2(p)
        
        # Text detection
        ascii_count = sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13))
        is_text = (ascii_count / len(data) > 0.7) if len(data) > 0 else False
        
    except Exception:
        entropy = 0.0
        is_text = False
    
    # Name patterns (NEW in v2.0)
    name_patterns = analyze_name_patterns(filename)
    
    return {
        "file": {
            "path": rel_path,
            "filename": filename,
            "dirname": dirname,
            "extension": ext,
            "size": size,
        },
        "content": {
            "entropy": round(entropy, 4),
            "is_text": is_text,
        },
        "name_patterns": name_patterns,
    }


def main():
    print("=" * 60)
    print("Feature Extraction Script v2.0")
    print("Adding NAME PATTERN FEATURES")
    print("=" * 60)
    
    all_files = []
    feature_stats = {
        "numeric_prefix_count": 0,
        "generic_name_count": 0,
        "high_underscore_ratio_count": 0,
        "trailing_chars_count": 0,
    }
    
    print(f"\nScanning: {BACKUP_DIR}")
    print(f"Target output: {OUTPUT_FILE}")
    
    # Walk through backup directory
    for root, dirs, files in os.walk(BACKUP_DIR):
        if '.git' in root.split(os.sep):
            continue
        
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                features = collect_all_features(filepath)
                all_files.append(features)
                
                # Update stats
                np = features["name_patterns"]
                if np["has_numeric_prefix"]:
                    feature_stats["numeric_prefix_count"] += 1
                if np["has_generic_name"]:
                    feature_stats["generic_name_count"] += 1
                if np["underscore_ratio"] > 0.3:
                    feature_stats["high_underscore_ratio_count"] += 1
                if np["trailing_chars"]:
                    feature_stats["trailing_chars_count"] += 1
                    
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    # Compute summary statistics
    total_files = len(all_files)
    
    # Count by extension
    ext_counts = {}
    for f in all_files:
        ext = f["file"]["extension"] or "(no_ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
    
    # Sort extensions by count (top 20)
    top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:20]
    
    print("\n" + "=" * 60)
    print("FEATURE EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"\nTotal files processed: {total_files}")
    
    # Show feature statistics
    print("\nName Pattern Feature Statistics:")
    for feat, count in feature_stats.items():
        pct = (count / total_files * 100) if total_files > 0 else 0
        print(f"  - {feat}: {count} files ({pct:.1f}%)")
    
    # Show top extensions
    print("\nTop 20 Extensions:")
    for ext, count in top_exts:
        print(f"  {ext}: {count} files")
    
    # Save to JSON
    output_data = {
        "version": "2.0",
        "features_added": ["filename", "has_numeric_prefix", "has_generic_name", 
                          "underscore_ratio", "trailing_chars"],
        "total_files": total_files,
        "name_pattern_stats": feature_stats,
        "top_extensions": top_exts,
        "all_files_metadata": all_files,
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nMetadata saved to: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.2f} MB")
    print("\nNext steps:")
    print("  1. Review the new features in the JSON file")
    print("  2. Proceed to Version 3.0 (Extension & Category features)")
    print("  3. Or start ML training with these 9 features per file")


if __name__ == "__main__":
    main()