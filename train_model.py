"""
Train ML model using v3.0 feature set (23 features + labels)
Enhanced version that uses all features from training_data_with_labels_v3_labeled.json
"""

import os
import json
import pickle
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report


def extract_features_v3(file_data):
    """
    Extract feature vector for ML training using v3.0 features (23 total).
    
    Feature order:
    1. path (string - will be excluded from numerical features)
    2. extension (string - will be encoded as categorical)
    3-9. Basic features: size, entropy, is_text, name patterns
    10-14. Size features: category, log size, is_small/medium/large
    15-16. Extension features: category, is_known_junk_ext
    17-18. Directory context: parent_depth, is_root_level
    19-23. Age features: age_days, is_ancient
    """
    
    # Extract numerical and boolean features
    features = {
        'size': file_data['size'],
        'entropy': file_data['entropy'],
        'is_text': int(file_data['is_text']),
        
        # Name pattern features
        'has_numeric_prefix': int(file_data['has_numeric_prefix']),
        'has_generic_name': int(file_data['has_generic_name']),
        'underscore_ratio': float(file_data['underscore_ratio']),
        'trailing_chars': int(file_data['trailing_chars']),
        
        # Size features
        'size_category': file_data['size_category'],  # categorical
        'size_log': file_data['size_log'],
        'is_small': int(file_data['is_small']),
        'is_medium': int(file_data['is_medium']),
        'is_large': int(file_data['is_large']),
        
        # Extension features
        'extension_category': file_data['extension_category'],  # categorical
        'is_known_junk_ext': int(file_data['is_known_junk_ext']),
        
        # Directory context
        'parent_depth': int(file_data['parent_depth']),
        'is_root_level': int(file_data['is_root_level']),
        
        # Age features
        'age_days': int(file_data['age_days']),
        'is_ancient': int(file_data['is_ancient']),
    }
    
    return features


def encode_categorical_features(features):
    """Convert categorical features to numerical encoding."""
    
    # Size categories: small=0, medium=1, large=2
    size_cat_map = {'small': 0, 'medium': 1, 'large': 2}
    features['size_category_encoded'] = size_cat_map.get(features['size_category'], -1)
    
    # Extension categories (one-hot style encoding using first letter hash for simplicity)
    ext_cat_map = {
        'source_code': 0, 'binary_executable': 1, 'media_asset': 2,
        'config_data': 3, 'archive': 4, 'no_extension': 5, 'other': 6
    }
    features['extension_category_encoded'] = ext_cat_map.get(features['extension_category'], -1)
    
    return features


def main():
    print("=" * 70)
    print("Model Training Script - VERSION 3.0 (ENHANCED)")
    print("Using all 23 features from training_data_with_labels_v3_labeled.json")
    print("=" * 70)
    
    # Load v3.0 labeled training data
    TRAINING_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels_v3_labeled.json"
    
    if not os.path.exists(TRAINING_FILE):
        print(f"\nERROR: Training file not found: {TRAINING_FILE}")
        print("Please run create_training_data_v3_labeled.py first")
        return
    
    with open(TRAINING_FILE, 'r') as f:
        data = json.load(f)
    
    all_files = data['all_files']
    y_list = np.array(data['labels'])
    
    print(f"\nLoaded {len(all_files)} files from v3.0 labeled dataset")
    print(f"Labels: {np.sum(y_list)} junk ({np.sum(y_list)/len(all_files)*100:.1f}%), " + 
          f"{len(y_list) - np.sum(y_list)} not-junk ({(1-np.sum(y_list)/len(all_files))*100:.1f}%)")
    
    # Extract features for all files
    print("\nExtracting features (v3.0, 23 features per file)...")
    X_list = []
    feature_names = []
    
    for i, file_data in enumerate(all_files):
        features = extract_features_v3(file_data)
        features = encode_categorical_features(features)
        
        # Create feature vector (exclude path which is a string)
        vector = [
            features['size'],                    # 0
            features['entropy'],                 # 1
            features['is_text'],                 # 2
            features['has_numeric_prefix'],      # 3
            features['has_generic_name'],        # 4
            features['underscore_ratio'],        # 5
            features['trailing_chars'],           # 6
            features['size_category_encoded'],   # 7
            features['size_log'],                # 8
            features['is_small'],                # 9
            features['is_medium'],               # 10
            features['is_large'],                # 11
            features['extension_category_encoded'],  # 12
            features['is_known_junk_ext'],       # 13
            features['parent_depth'],            # 14
            features['is_root_level'],           # 15
            features['age_days'],                # 16
            features['is_ancient'],              # 17
        ]
        
        X_list.append(np.array(vector))
        feature_names = [
            'size', 'entropy', 'is_text', 
            'has_numeric_prefix', 'has_generic_name', 
            'underscore_ratio', 'trailing_chars',
            'size_category_enc', 'size_log',
            'is_small', 'is_medium', 'is_large',
            'extension_category_enc', 'is_known_junk_ext',
            'parent_depth', 'is_root_level',
            'age_days', 'is_ancient'
        ]
    
    X = np.vstack(X_list)
    
    print(f"  Feature matrix shape: {X.shape} ({len(feature_names)} features)")
    
    # Train-test split with stratification
    print("\nSplitting data (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_list, test_size=0.2, random_state=42, stratify=y_list
    )
    
    print(f"  Training set: {len(X_train)} samples ({np.sum(y_train)} junk)")
    print(f"  Test set:     {len(X_test)} samples ({np.sum(y_test)} junk)")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Hyperparameter tuning with GridSearchCV
    print("\n" + "=" * 70)
    print("Hyperparameter Tuning (GridSearchCV)...")
    print("=" * 70)
    
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.05, 0.1, 0.2],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }
    
    base_model = GradientBoostingClassifier(random_state=42)
    grid_search = GridSearchCV(
        base_model, param_grid, 
        cv=5, scoring='f1', n_jobs=-1
    )
    
    print("  Searching parameter space...")
    grid_search.fit(X_train_scaled, y_train)
    
    best_params = grid_search.best_params_
    best_score = grid_search.best_score_
    
    print(f"\nBest parameters: {best_params}")
    print(f"Best CV F1 Score: {best_score:.4f}")
    
    # Train final model with best parameters
    print("\nTraining final model with best parameters...")
    model = GradientBoostingClassifier(**best_params, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Evaluate on test set
    print("\nEvaluating on test set...")
    y_pred = model.predict(X_test_scaled)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, pos_label=1)
    recall = recall_score(y_test, y_pred, pos_label=1)
    f1 = f1_score(y_test, y_pred, pos_label=1)
    
    cm = confusion_matrix(y_test, y_pred)
    TP = cm[0][1]  # True Positives (junk correctly predicted as junk)
    FP = cm[1][1]  # False Positives (not-junk predicted as junk)
    FN = cm[0][0]  # False Negatives (junk predicted as not-junk)
    TN = cm[1][0]  # True Negatives (not-junk correctly predicted)
    
    print(f"\n  Accuracy:     {accuracy:.3f} ({accuracy*100:.1f}%)")
    print(f"  Precision:    {precision:.3f} ({precision*100:.1f}%)")
    print(f"  Recall:       {recall:.3f} ({recall*100:.1f}%)")
    print(f"  F1 Score:     {f1:.3f} ({f1*100:.1f}%)")
    
    # Confusion matrix breakdown
    print(f"\n  Confusion Matrix:")
    print(f"    True Junk (1->1):     {TP}")
    print(f"    False Positive (0->1): {FP}")
    print(f"    True Not-Junk (0->0): {TN}")
    print(f"    False Negative (1->0): {FN}")
    
    # Classification report
    print("\n  Classification Report:")
    report = classification_report(y_test, y_pred, target_names=['not-junk', 'junk'], digits=3)
    print(report)
    
    # Interpretation
    print("\n  Interpretation:")
    if precision < 0.85:
        print(f"    ⚠️  Precision is moderate - model makes some false positives")
    else:
        print(f"    ✓  Good precision - most predicted junk files are actually junk")
    
    if recall < 0.8:
        print(f"    ⚠️  Recall is moderate - missing some actual junk files")
    else:
        print(f"    ✓  Good recall - catching most actual junk files")
    
    # Feature importance
    importances = model.feature_importances_
    feature_importance = list(zip(feature_names, importances))
    feature_importance.sort(key=lambda x: -x[1])
    
    print("\n  Top 10 Feature Importances:")
    for i, (name, imp) in enumerate(feature_importance[:10]):
        bar_len = int(imp / max(importances) * 30)
        bar = '█' * bar_len + '░' * (30 - bar_len)
        print(f"    {i+1}. {name}: {imp:.4f} {bar}")
    
    # Save model
    MODEL_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classifier_model_v3.pkl"
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': feature_names,
            'best_params': best_params,
            'classes': np.array([0, 1]),
        }, f)
    
    print(f"\n  Model saved to: {MODEL_PATH}")
    
    # Save model metadata
    meta_path = "/home/cc/Documents/LM/backup-junk-cleaner/model_metadata_v3.json"
    with open(meta_path, 'w') as f:
        json.dump({
            'feature_names': feature_names,
            'best_params': best_params,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
        }, f, indent=2)
    
    print(f"  Model metadata saved to: {meta_path}")
    
    # Save sample predictions for verification
    SAMPLE_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/model_predictions_sample_v3.json"
    sample_data = []
    for i in range(min(200, len(X))):
        sample_data.append({
            'features': X[i].tolist(),
            'true_label': int(y_list[i]),
            'predicted_label': int(y_pred[i]),
            'path': all_files[i]['file']['path'],
            'filename': all_files[i]['file']['filename'],
            'extension': all_files[i]['extension'],
        })
    
    with open(SAMPLE_PATH, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"  Sample predictions saved to: {SAMPLE_PATH}")
    
    # Save feature importance
    IMP_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/feature_importance_v3.json"
    with open(IMP_PATH, 'w') as f:
        json.dump({
            'feature_names': feature_names,
            'importances': importances.tolist(),
            'sorted_importances': [(name, float(imp)) for name, imp in feature_importance],
        }, f, indent=2)
    
    print(f"  Feature importance saved to: {IMP_PATH}")


if __name__ == "__main__":
    main()
