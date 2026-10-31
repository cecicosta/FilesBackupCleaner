"""
Generate training data with features AND labels (v3.0 + classification rules)
Extends v3.0 feature extraction with pseudo-labels based on cleanup_skill_v2_4.py rules.
"""

import os
import json
import numpy as np
import math
from datetime import datetime, timedelta

# Configuration
BACKUP_DIR = "/home/cc/Documents/Backup novo"
METADATA_FILE_V2 = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classification_metadata_v2.json"
OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels_v3_labeled.json"


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
    
    code_exts = {'.c', '.cpp', '.h', '.hpp', '.cs', '.java', '.kt', '.py', 
                 '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.swift', '.dart',
                 '.lua', '.rb', '.php', '.sql', '.sh', '.cmake', '.pro', '.fgl'}
    
    binary_exts = {'.exe', '.dll', '.so', '.a', '.lib', '.dylib', '.bin', 
                   '.out', '.class', '.wasm', '.jar', '.war', '.o', '.pyc', '.pyo'}
    
    media_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico', 
                  '.svg', '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.docx', '.xlsx'}
    
    config_exts = {'.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', 
                   '.conf', '.env', '.properties', '.plist', '.log', '.txt'}
    
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


def create_pseudo_labels(all_files):
    """
    Create labels based on current cleanup_skill_v2_4.py rules.
    
    Classification logic:
    1. Files with known junk extensions → JUNK
    2. Files with junk name patterns (download_, temp_, copy, etc.) → JUNK
    3. Files with high underscore ratio (>0.5) AND small size (<1MB) → JUNK
    4. Otherwise → NOT_JUNK
    
    This is a simplified version of the actual cleanup rules for training purposes.
    """
    
    # Known junk extensions from cleanup_skill_v2_4.py
    JUNK_EXTENSIONS = {
        '.cbp', '.layout', '.depend', '.pro.user', 
        '.o', '.dll', '.so', '.a', '.lib', '.dylib', '.bin', '.out', '.class',
        '.wasm', '.jar', '.war', '.pyc', '.pyo', '.ilk', '.pdb', '.exp', 
        '.exe', '.blend1',
    }
    
    # Name patterns that indicate junk
    JUNK_NAME_PATTERNS = ['download', 'untitled', 'temp', 'screenshot', '(1)', '(2)']
    
    labels = []
    
    for file_data in all_files:
        filename_lower = file_data['file']['filename'].lower()
        ext = file_data['file']['extension'].lower() or ''
        
        is_junk = False
        
        # Rule 1: Known junk extension
        if ext in JUNK_EXTENSIONS:
            is_junk = True
        
        # Rule 2: Junk name patterns
        elif any(pat in filename_lower for pat in JUNK_NAME_PATTERNS):
            is_junk = True
        
        # Rule 3: High underscore ratio + small size
        elif (file_data['name_patterns'].get('underscore_ratio', 0) > 0.5 and 
              file_data['file']['size'] < 1024 * 1024):
            is_junk = True
        
        labels.append(int(is_junk))
    
    return np.array(labels)


def main():
    print("=" * 70)
    print("Training Data Generation Script - VERSION 3.0 (WITH LABELS)")
    print("Features: v3.0 + Pseudo-labels based on cleanup_skill_v2_4.py rules")
    print("=" * 70)
    
    # Load existing metadata from v2.0
    print("\nLoading metadata from v2.0...")
    with open(METADATA_FILE_V2, 'r') as f:
        v2_data = json.load(f)
    
    all_files = v2_data.get('all_files_metadata', [])
    
    if not all_files:
        print("ERROR: No files found in metadata file!")
        return
    
    print(f"  Loaded {len(all_files)} files from v2.0")
    
    # Add enhanced features to each file (size, age, extension, etc.)
    print("\nAdding enhanced features (v3.0)...")
    
    for file_data in all_files:
        try:
            # Size features
            size = file_data['file']['size']
            if size > 0:
                size_log = math.log2(size)
            else:
                size_log = 0
            
            if size < 1024:
                size_category = "small"
            elif size < 1024 * 1024:
                size_category = "medium"
            else:
                size_category = "large"
            
            file_data['size_features'] = {
                "size_category": size_category,
                "size_log": round(size_log, 4),
                "is_small": size < 1024,
                "is_medium": 1024 <= size < 1024 * 1024,
                "is_large": size >= 1024 * 1024,
            }
            
            # Extension features
            ext = file_data['file']['extension'] or ''
            category = categorize_extension(ext)
            is_junk_ext = is_known_junk_extension(ext)
            
            file_data['extension_features'] = {
                "extension_category": category,
                "is_known_junk_ext": is_junk_ext,
            }
            
        except Exception as e:
            print(f"  Error adding features to {file_data['file']['path']}: {e}")
    
    print(f"  Enhanced {len(all_files)} files")
    
    # Create labels based on cleanup rules
    print("\nCreating pseudo-labels...")
    y_list = create_pseudo_labels(all_files)
    
    # Compute statistics
    junk_count = int(np.sum(y_list))
    not_junk_count = int(len(y_list) - np.sum(y_list))
    junk_pct = (junk_count / len(all_files) * 100) if all_files else 0
    
    print(f"\nLabel Statistics:")
    print(f"  Total files: {len(all_files)}")
    print(f"  Labeled as JUNK: {junk_count} ({junk_pct:.1f}%)")
    print(f"  Labeled as NOT_JUNK: {not_junk_count} ({100-junk_pct:.1f}%)")
    
    # Show label distribution by extension category
    print("\nLabel distribution by extension category:")
    ext_cat_labels = {}
    for i, file_data in enumerate(all_files):
        cat = file_data.get('extension_features', {}).get('extension_category', 'unknown')
        is_junk = y_list[i]
        
        key = (cat, is_junk)
        ext_cat_labels[key] = ext_cat_labels.get(key, 0) + 1
    
    for (cat, junk_flag), count in sorted(ext_cat_labels.items()):
        pct = (count / len(all_files) * 100) if all_files else 0
        print(f"  {cat} (junk={junk_flag}): {count} files ({pct:.1f}%)")
    
    # Save to JSON
    OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels_v3_labeled.json"
    
    # Flatten file data for easier ML consumption
    flat_files = []
    for i, file_data in enumerate(all_files):
        flat_file = {
            "path": file_data['file']['path'],
            "extension": file_data['file']['extension'] or '(none)',
            "size": file_data['file']['size'],
            "entropy": file_data['content']['entropy'],
            "is_text": int(file_data['content']['is_text']),
            # Name patterns
            "has_numeric_prefix": int(file_data['name_patterns'].get('has_numeric_prefix', False)),
            "has_generic_name": int(file_data['name_patterns'].get('has_generic_name', False)),
            "underscore_ratio": file_data['name_patterns'].get('underscore_ratio', 0),
            "trailing_chars": int(file_data['name_patterns'].get('trailing_chars', False)),
            # Size features
            "size_category": file_data.get('size_features', {}).get('size_category', 'medium'),
            "size_log": file_data.get('size_features', {}).get('size_log', 0),
            "is_small": int(file_data.get('size_features', {}).get('is_small', False)),
            "is_medium": int(file_data.get('size_features', {}).get('is_medium', False)),
            "is_large": int(file_data.get('size_features', {}).get('is_large', False)),
            # Extension features
            "extension_category": file_data.get('extension_features', {}).get('extension_category', 'other'),
            "is_known_junk_ext": int(file_data.get('extension_features', {}).get('is_known_junk_ext', False)),
            # Directory context
            "parent_depth": file_data.get('directory_context', {}).get('parent_depth', 0),
            "is_root_level": int(file_data.get('directory_context', {}).get('is_root_level', False)),
            # Age features
            "age_days": file_data.get('age', {}).get('age_days', 0),
            "is_ancient": int(file_data.get('age', {}).get('is_ancient', False)),
        }
        flat_files.append(flat_file)
    
    output_data = {
        "version": "3.0-labeled",
        "total_files": len(all_files),
        "junk_count": junk_count,
        "not_junk_count": not_junk_count,
        "all_files": flat_files,
        "labels": y_list.tolist(),
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f)
    
    print(f"\nTraining data saved to: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.2f} MB")
    
    # Show sample labeled files
    print("\n\n🔍 SAMPLE LABELED FILES:")
    print("=" * 70)
    
    for i in [0, 50, 100]:
        if i < len(flat_files):
            f = flat_files[i]
            label = y_list[i]
            
            print(f"\nFile {i}:")
            print(f"  Path: {f['path']}")
            print(f"  Extension: {f['extension']}")
            print(f"  Size: {f['size']} bytes")
            print(f"  Underscore ratio: {f['underscore_ratio']:.3f}")
            print(f"  Label: {'JUNK' if label == 1 else 'NOT_JUNK'}")


if __name__ == "__main__":
    main()
