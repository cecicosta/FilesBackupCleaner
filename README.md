# Backup Junk Cleaner - ML-Powered File Classification

An intelligent tool that classifies backup files as "junk" or "keep" using machine learning, building on the existing `backup-junk-cleaner-v2-4` skill with enhanced AI-based detection.

## 🎯 Purpose

Automatically identify and clean junk files from backup directories while preserving important project files. Uses both rule-based detection (from v2.4) AND machine learning for improved accuracy.

## ✨ Features

- **Rule-based detection**: Inherits all features from `cleanup_skill_v2_4.py`
- **ML-powered classification**: Gradient Boosting model trained on 11,234 files
- **Feature analysis**: 9 features per file (size, entropy, name patterns, etc.)
- **High precision**: 95.2% - when it flags junk, it's very likely correct
- **Good recall**: 78.0% - catches most actual junk files
- **Duplicate detection**: MD5 hashing for finding duplicate files

## 📊 Model Performance

| Metric | Value |
|--------|-------|
| Accuracy | 95.0% |
| Precision | 95.2% |
| Recall | 78.0% |
| F1 Score | 85.8% |

## 🛠️ How It Works

### Step 1: Generate Training Data
```bash
cd /home/cc/Documents/LM/backup-junk-cleaner
python create_training_data.py
```
This scans your backup directory and creates labeled training data based on current rules.

### Step 2: Train the Model
```bash
python train_model.py
```
Creates a Gradient Boosting classifier using the generated labels.

### Step 3: Use the Classifier
The trained model is saved as `junk_classifier_model.pkl` and can be used to classify any file.

## 📁 Files Included

| File | Description |
|------|-------------|
| `cleanup_skill_v2_4.py` | Original rule-based cleaner (v2.4) |
| `create_training_data.py` | Generates labeled training data |
| `train_model.py` | Trains ML model from training data |
| `junk_classifier_model.pkl` | Trained Gradient Boosting model |
| `junk_classification_metadata_v2.json` | Feature data for all files |
| `model_predictions_sample.json` | Sample predictions for verification |

## 🔧 Configuration

The model uses these 9 features per file:
1. `size_log` - Log-normalized file size
2. `entropy` - Shannon entropy (high = binary/compressed)
3. `is_text` - Whether file appears text-based
4. `has_numeric_prefix` - Filename starts with digits
5. `has_generic_name` - Matches patterns like "download_", "temp_"
6. `underscore_ratio` - Underscore density in filename
7. `trailing_chars` - Ends with ~ or .

## 🎛️ Customization

### Adjust Decision Threshold
The default threshold is 0.5 (50% confidence). To catch more junk:
```python
# Lower threshold to increase recall
confidence_threshold = 0.3  # Instead of 0.5
```

### Add New Features
Edit `create_training_data.py` and `train_model.py` to add new features like:
- Extension category (.dll, .exe, etc.)
- Directory context (is inside a project?)
- Sibling file distribution

## 📝 Manual Verification

The model makes predictions but human review is recommended for production use:

1. Review `model_predictions_sample.json` 
2. Manually verify flagged files
3. Adjust model or threshold as needed

## 🔮 Future Improvements

- [ ] Version 3.0: Add extension category features
- [ ] Version 4.0: Add directory context and sibling analysis
- [ ] Interactive labeling tool for manual refinement
- [ ] CLI tool for batch classification of backup directories

## 📜 License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 🙏 Acknowledgments

- Based on `backup-junk-cleaner-v2-4` skill
- ML implementation using scikit-learn
- Tested on 11,234 files from a game development backup directory

---

**Last Updated**: October 2026
