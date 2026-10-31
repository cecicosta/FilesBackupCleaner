"""
Classify all files in backup directory using trained ML model.

This script applies the Gradient Boosting classifier (trained with version 3.0 features)
to predict which files are junk vs not-junk based on file characteristics.
"""

import os
import math
import json
import pickle
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classifier_model_v3.pkl"
BACKUP_DIR = "/home/cc/Documents/Backup novo"
OUTPUT_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/classification_results.json"


def extract_features_for_file(filepath):
    """
    Extract feature vector for a single file (matching training data format).
    
    Returns 18 features in the same order as training data.
    Simplified version - you can enhance this with actual file content analysis.
    """
    stat_info = os.stat(filepath)
    filename = os.path.basename(filepath).lower()
    
    # Basic file info
    size = stat_info.st_size
    
    # Name pattern features (simplified)
    has_numeric_prefix = filename[0].isdigit() if filename else False
    underscore_count = filename.count('_')
    words = [w for w in filename.replace('.', '').replace('-', ' ').split() if w]
    word_count = len(words)
    underscore_ratio = underscore_count / word_count if word_count > 0 else 0.0
    
    # Create feature vector (18 features, matching training format)
    # Order matches: size, entropy, is_text, name_patterns, size_features, 
    #                extension_features, directory_context, age_features
    
    # Simplified values - you can enhance with actual content analysis
    features = [
        size,                          # 0: size
        6.5,                           # 1: entropy (approximate for images)
        0,                             # 2: is_text
        int(has_numeric_prefix),       # 3: has_numeric_prefix
        int('copy' in filename or 'download' in filename),  # 4: has_generic_name
        underscore_ratio,              # 5: underscore_ratio
        0,                             # 6: trailing_chars
        1,                             # 7: size_category_enc (medium=1)
        math.log2(size) if size > 0 else 0,  # 8: size_log
        int(size < 1024),              # 9: is_small
        int(1024 <= size < 1024 * 1024),  # 10: is_medium
        int(size >= 1024 * 1024),     # 11: is_large
        2,                             # 12: extension_category_enc (media=2)
        0,                             # 13: is_known_junk_ext
        0,                             # 14: parent_depth
        0,                             # 15: is_root_level
        0,                             # 16: age_days
        0,                             # 17: is_ancient
    ]
    
    return features


def main():
    print("=" * 70)
    print("Backup Junk Classification - Using ML Model v3.0")
    print("=" * 70)
    
    # Load trained model
    if not os.path.exists(MODEL_PATH):
        print(f"\nERROR: Model file not found: {MODEL_PATH}")
        return
    
    print(f"\nLoading model from: {MODEL_PATH}")
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    scaler = model_data['scaler']
    feature_names = model_data['feature_names']
    best_params = model_data.get('best_params', {})
    
    print(f"  Model loaded successfully")
    print(f"  Feature names: {len(feature_names)} features")
    print(f"  Best params: {best_params}")
    
    # Walk through backup directory
    print(f"\nScanning backup directory: {BACKUP_DIR}")
    
    all_files = []
    predictions = []
    junk_count = 0
    not_junk_count = 0
    
    for root, dirs, files in os.walk(BACKUP_DIR):
        # Skip .git directories
        if '.git' in root.split(os.sep):
            continue
        
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                features = extract_features_for_file(filepath)
                
                # Scale features and predict
                features_scaled = scaler.transform([features])
                pred_prob = model.predict_proba(features_scaled)[0]
                pred_label = int(model.predict(features_scaled)[0])
                
                # Get extension from path
                ext = os.path.splitext(filename)[1] or '(none)'
                
                predictions.append({
                    'filename': filename,
                    'path': os.path.relpath(filepath, BACKUP_DIR),
                    'extension': ext,
                    'size': features[0],  # First feature is size
                    'predicted': pred_label,
                    'confidence': float(pred_prob[pred_label]),
                })
                
                if pred_label == 1:
                    junk_count += 1
                else:
                    not_junk_count += 1
                    
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    # Sort predictions by confidence (junk first, highest confidence first)
    predictions.sort(key=lambda x: (-x['predicted'], -x['confidence']))
    
    # Calculate statistics
    total = len(predictions)
    junk_pct = (junk_count / total * 100) if total > 0 else 0
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(predictions, f, indent=2)
    
    print(f"\nClassification complete!")
    print(f"  Total files processed: {total}")
    print(f"  Predicted as JUNK:   {junk_count} ({junk_pct:.1f}%)")
    print(f"  Predicted not-junk:  {not_junk_count} ({100-junk_pct:.1f}%)")
    print(f"\nResults saved to: {OUTPUT_FILE}")
    
    # Show top 20 junk predictions
    if junk_count > 0:
        print("\nTop 20 Junk Predictions (by confidence):")
        print("-" * 70)
        for i, p in enumerate(predictions[:20]):
            print(f"{i+1}. {p['filename']} ({p['extension']})")
            print(f"    Path: {p['path']}")
            print(f"    Size: {p['size']} bytes")
            print(f"    Confidence: {p['confidence']:.2%}")
            print()


if __name__ == "__main__":
    main()
