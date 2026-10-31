"""
Generate training data with enhanced features (v3.0)
Extends v2.0 with extension categories, size features, and age analysis.
Does NOT include classification rules - pure feature extraction only.
"""

import os
import json
import numpy as np
import math
from datetime import datetime, timedelta

# Configuration
BACKUP_DIR = "/home/cc/Documents/Backup novo"
METADATA_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classification_metadata_v2.json"
OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels_v3.json"


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
        
        math
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


def categorize_extension(ext):
    """Categorize file extension into broad types."""
    if not ext:
        return "no_extension"
    
    # Source code extensions
    code_exts = {'.c', '.cpp', '.h', '.hpp', '.cs', '.java', '.kt', '.py', 
                 '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.swift', '.dart',
                 '.lua', '.rb', '.php', '.sql', '.sh', '.cmake', '.pro', '.fgl'}
    
    # Binary/executable extensions
    binary_exts = {'.exe', '.dll', '.so', '.a', '.lib', '.dylib', '.bin', 
                   '.out', '.class', '.wasm', '.jar', '.war', '.o', '.pyc', '.pyo'}
    
    # Image/media extensions
    media_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico', 
                  '.svg', '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.docx', '.xlsx'}
    
    # Config/data extensions
    config_exts = {'.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', 
                   '.conf', '.env', '.properties', '.plist', '.log', '.txt'}
    
    # Archive/extensions
    archive_exts = {'.zip', '.rar', '.7z', '.tar.gz', '.tar.bz2', '.gz', '.xz'}
    
    if ext in code_exts:
        return "source_code"
    elif ext in binary_exts:
        return "binary_executable"
    elif ext in media_exts:
        return "media_asset"
    elif ext in config_exts:
        return "config_data"
    elif ext in archive_exts:
        return "archive"
    else:
        return "other"


def is_known_junk_extension(ext):
    """Check if extension matches known junk patterns from cleanup_skill_v2_4."""
    JUNK_EXTENSIONS = {
        '.cbp', '.layout', '.depend', '.pro.user', 
        '.o', '.dll', '.so', '.a', '.lib', '.dylib', '.bin', '.out', '.class',
        '.wasm', '.jar', '.war', '.pyc', '.pyo', '.ilk', '.pdb', '.exp', 
        '.exe', '.blend1',
    }
    return ext in JUNK_EXTENSIONS


def add_age_features(file_data):
    """Add temporal/age features to file data."""
    mtime_str = file_data['file'].get('mtime', '')
    
    age_days = 0
    is_ancient = False
    
    if mtime_str:
        try:
            mtime = datetime.fromisoformat(mtime_str.replace('Z', '+00:00'))
            age_days = (datetime.now() - mtime).days
            is_ancient = age_days > 1825  # Older than 5 years
        except Exception:
            pass
    
    file_data['age'] = {
        "age_days": age_days,
        "is_ancient": is_ancient,
    }
    return file_data


def add_size_features(file_data):
    """Add size-based features to file data."""
    size = file_data['file']['size']
    
    # Size categories
    if size < 1024:
        size_category = "small"
    elif size < 1024 * 1024:
        size_category = "medium"
    else:
        size_category = "large"
    
    # Log-normalized size (for ML)
    if size > 0:
        size_log = math.log2(size)
    else:
        size_log = 0
    
    file_data['size_features'] = {
        "size_category": size_category,
        "size_log": round(size_log, 4),
        "is_small": size < 1024,
        "is_medium": 1024 <= size < 1024 * 1024,
        "is_large": size >= 1024 * 1024,
    }
    
    return file_data


def add_extension_features(file_data):
    """Add extension-based features to file data."""
    ext = file_data['file']['extension'] or ''
    category = categorize_extension(ext)
    
    file_data['extension_features'] = {
        "extension_category": category,
        "is_known_junk_ext": is_known_junk_extension(ext),
    }
    
    return file_data


def add_sibling_context(file_data):
    """Add sibling context features to file data."""
    # This would require scanning parent directories for each file
    # For now, we'll estimate based on directory structure
    
    dirname = file_data['file']['dirname'] or "."
    depth = dirname.count(os.sep) + 1 if dirname != "." else 0
    
    file_data['directory_context'] = {
        "parent_depth": depth,
        "is_root_level": depth == 1,
    }
    
    return file_data


def main():
    print("=" * 70)
    print("Training Data Generation Script - VERSION 3.0")
    print("Enhanced features: extension categories, size, age, sibling context")
    print("Classification rules: NOT INCLUDED (pure feature extraction)")
    print("=" * 70)
    
    # Load existing metadata from v2.0
    print("\nLoading metadata from v2.0...")
    with open(METADATA_FILE, 'r') as f:
        v2_data = json.load(f)
    
    all_files = v2_data.get('all_files_metadata', [])
    
    if not all_files:
        print("ERROR: No files found in metadata file!")
        return
    
    print(f"  Loaded {len(all_files)} files from v2.0")
    
    # Add new features to each file
    print("\nAdding enhanced features...")
    math
    
    enhanced_count = 0
    skipped_count = 0
    
    for i, file_data in enumerate(all_files):
        try:
            # Add age features
            file_data = add_age_features(file_data)
            
            # Add size features
            file_data = add_size_features(file_data)
            
            # Add extension features
            file_data = add_extension_features(file_data)
            
            # Add directory context
            file_data = add_sibling_context(file_data)
            
            enhanced_count += 1
            
        except Exception as e:
            print(f"  Error processing {file_data['file']['path']}: {e}")
            skipped_count += 1
    
    print(f"  Enhanced {enhanced_count} files")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} files due to errors")
    
    # Compute statistics
    print("\nFeature Statistics:")
    
    # Extension category distribution
    ext_cats = {}
    for f in all_files:
        cat = f.get('extension_features', {}).get('extension_category', 'unknown')
        ext_cats[cat] = ext_cats.get(cat, 0) + 1
    
    print("  Extension categories:")
    for cat, count in sorted(ext_cats.items(), key=lambda x: -x[1]):
        pct = (count / len(all_files) * 100) if all_files else 0
        print(f"    - {cat}: {count} files ({pct:.1f}%)")
    
    # Size distribution
    size_cats = {"small": 0, "medium": 0, "large": 0}
    for f in all_files:
        sf = f.get('size_features', {})
        cat = sf.get('size_category', 'unknown')
        if cat in size_cats:
            size_cats[cat] += 1
    
    print("  Size categories:")
    for cat, count in size_cats.items():
        pct = (count / len(all_files) * 100) if all_files else 0
        print(f"    - {cat}: {count} files ({pct:.1f}%)")
    
    # Age statistics
    ancient_count = sum(1 for f in all_files if f.get('age', {}).get('is_ancient', False))
    avg_age_days = sum(f.get('age', {}).get('age_days', 0) for f in all_files) / len(all_files) if all_files else 0
    
    print("  Age statistics:")
    print(f"    - Average age: {avg_age_days:.0f} days")
    print(f"    - Ancient files (>5 years): {ancient_count} ({ancient_count/len(all_files)*100:.1f}%)")
    
    # Save to JSON
    OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels_v3.json"
    output_data = {
        "version": "3.0",
        "total_files": len(all_files),
        "all_files": all_files,
        # Feature counts for reference
        "feature_counts": {
            "numeric_prefix_count": v2_data.get('name_pattern_stats', {}).get('numeric_prefix_count', 0),
            "generic_name_count": v2_data.get('name_pattern_stats', {}).get('generic_name_count', 0),
            "high_underscore_ratio_count": v2_data.get('name_pattern_stats', {}).get('high_underscore_ratio_count', 0),
        },
        "extension_categories": ext_cats,
        "size_distribution": size_cats,
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f)
    
    print(f"\nTraining data saved to: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.2f} MB")
    
    # Show sample file with all features
    if all_files:
        print("\nSample file with all v3.0 features:")
        print(json.dumps(all_files[0], indent=2))


if __name__ == "__main__":
    main()
