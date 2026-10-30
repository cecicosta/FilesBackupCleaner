"""Train ML model using generated training data (with Recall & Precision)."""

import os
import json
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix


def extract_features(file_data):
    """Extract feature vector for ML training."""
    features = {
        'size_log': np.log2(file_data['file']['size'] + 1),
        'entropy': file_data['content']['entropy'],
        'is_text': int(file_data['content']['is_text']),
        'has_numeric_prefix': int(file_data['name_patterns'].get('has_numeric_prefix', False)),
        'has_generic_name': int(file_data['name_patterns'].get('has_generic_name', False)),
        'underscore_ratio': file_data['name_patterns'].get('underscore_ratio', 0.0),
        'trailing_chars': int(file_data['name_patterns'].get('trailing_chars', False)),
    }
    return np.array([list(features.values())])


def main():
    print("=" * 70)
    print("Model Training Script")
    print("=" * 70)
    
    # Load training data
    TRAINING_FILE = "/home/cc/Documents/LM/backup-junk-cleaner/training_data_with_labels.json"
    
    with open(TRAINING_FILE, 'r') as f:
        data = json.load(f)
    
    all_files = data['all_files']
    y_list = np.array(data['labels'])
    
    print(f"\nLoaded {len(all_files)} files")
    print(f"Labels: {np.sum(y_list)} junk, {len(y_list) - np.sum(y_list)} not-junk")
    
    # Extract features
    print("\nExtracting features...")
    X_list = []
    for file_data in all_files:
        X_list.append(extract_features(file_data))
    
    X = np.vstack(X_list)
    
    print(f"  Feature matrix shape: {X.shape}")
    
    # Train-test split
    print("\nSplitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_list, test_size=0.2, random_state=42, stratify=y_list
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    print("\nTraining Gradient Boosting model...")
    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    print("\nEvaluating model...")
    y_pred = model.predict(X_test_scaled)
    
    accuracy = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    # Calculate metrics for "junk" class (positive class = 1)
    TP = cm[0][0]  # True Positives: junk correctly predicted as junk
    FP = cm[0][1]  # False Positives: not-junk incorrectly predicted as junk
    FN = cm[1][1]  # False Negatives: junk incorrectly predicted as not-junk
    TN = cm[1][0]  # True Negatives: not-junk correctly predicted as not-junk
    
    # Recall (Sensitivity) for junk class
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    
    # Precision for junk class
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    
    # F1 Score
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print(f"\n  Accuracy: {accuracy:.3f}")
    print(f"  Precision: {precision:.3f} ({precision*100:.1f}%)")
    print(f"  Recall:    {recall:.3f} ({recall*100:.1f}%)")
    print(f"  F1 Score:  {f1:.3f} ({f1*100:.1f}%)")
    
    # Confusion matrix breakdown
    print(f"\n  Confusion Matrix:")
    print(f"    True Junk (0->0):     {TP}")
    print(f"    False Positive (1->1): {FP}")
    print(f"    True Not-Junk (1->0): {TN}")
    print(f"    False Negative (1->1): {FN}")
    
    # Interpretation
    print("\n  Interpretation:")
    if precision < 0.9:
        print(f"    ⚠️  Precision is low - model makes many false positives")
        print(f"       Consider adjusting decision threshold or adding more features")
    else:
        print(f"    ✓  Good precision - most predicted junk files are actually junk")
    
    if recall < 0.8:
        print(f"    ⚠️  Recall is moderate - missing some actual junk files")
        print(f"       Consider lowering decision threshold to catch more junk")
    else:
        print(f"    ✓  Good recall - catching most actual junk files")
    
    # Feature importance
    feature_names = ['size_log', 'entropy', 'is_text', 
                    'has_numeric_prefix', 'has_generic_name', 
                    'underscore_ratio', 'trailing_chars']
    importances = model.feature_importances_
    feature_importance = list(zip(feature_names, importances))
    feature_importance.sort(key=lambda x: -x[1])
    
    print("\n  Feature Importance:")
    for name, imp in feature_importance:
        print(f"    {name}: {imp:.3f}")
    
    # Save model
    MODEL_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/junk_classifier_model.pkl"
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': feature_names,
        }, f)
    
    print(f"\n  Model saved to: {MODEL_PATH}")
    
    # Save sample predictions for verification
    SAMPLE_PATH = "/home/cc/Documents/LM/backup-junk-cleaner/model_predictions_sample.json"
    sample_data = []
    for i in range(min(200, len(X))):
        sample_data.append({
            'features': X[i].tolist(),
            'true_label': int(y_list[i]),
            'predicted_label': int(y_pred[i]),
            'path': all_files[i]['file']['path'],
            'filename': all_files[i]['file']['filename'],
        })
    
    with open(SAMPLE_PATH, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"  Sample predictions saved to: {SAMPLE_PATH}")


if __name__ == "__main__":
    main()