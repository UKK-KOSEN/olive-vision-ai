# OliveVision AI - Improvement Log

## Version 0.3.0 (Current)

### Major Features

#### 1. QR Code Tree ID Detection
- Detect QR codes in images to identify tree IDs
- Automatic parsing of "第N試験樹" format
- UTF-8 support for Japanese text
- Database storage with `tree_id` column

#### 2. Configurable Parameters (56 params)
All detection, analysis, stress, and trend parameters are now configurable via `config/runtime.yaml`:

```yaml
detection:
  fruit_min_area: 250
  leaf_min_area: 100
  circle_dp: 1.2

analysis:
  curl_weights: { tip_fraction: 0.4, mid_fraction: 0.3, base_fraction: 0.3 }
  curl_threshold: 0.35

stress:
  wrinkle_erosion: 3
  wrinkle_ridge_size: 5
```

#### 3. Leaf Curl Score
- `_compute_leaf_curl_score()` function
- Configurable weights and thresholds
- Tip/mid/base fraction analysis

#### 4. Wrinkle Score
- Erosion-based detection
- Configurable parameters: `wrinkle_erosion`, `wrinkle_ridge_size`, `wrinkle_interior_frac`
- Discount factor for unreliable detection
- `wrinkle_reliable` flag

#### 5. Analysis Details
- `_compute_analysis_details()` function
- Leaf, fruit, canopy, stress sections
- All parameters configurable

#### 6. Video Analysis Improvements
- Frame-by-frame analysis with full field support
- Per-tree aggregation in summaries
- DB persistence for video frames
- Trend analysis from video data

### CLI Improvements

#### Status Command
```bash
python olivevision.py status
python olivevision.py status --tree "1-3"
python olivevision.py status --source video
```

#### Trend Command
```bash
python olivevision.py trend
python olivevision.py trend --tree "1-3"
python olivevision.py trend --source image
```

#### Trees Command
```bash
python olivevision.py trees
```

#### Video Command
```bash
python olivevision.py video sample.mp4
python olivevision.py video sample.mp4 --tree-id "1-3"
```

### Error Messages
- All error messages improved with HINT/DETAIL sections
- `_error()` helper function for consistent formatting
- User-friendly guidance for common issues

### Tests
- 24 tests passing
- GT regression test for fruit detection recall
- Store and VideoAnalyzer persistence tests

---

## Version 0.2.0

### Features Added
- Video processing support
- Background removal (5 methods)
- HSV range auto-optimization
- Multi-scale leaf detection
- Texture analysis (GLCM/LBP)
- Optical flow analysis
- Improved detection accuracy

### Performance
| Metric | v0.1.0 | v0.2.0 | Change |
|--------|--------|--------|--------|
| Leaf detection | 82% | 91% | +9% |
| Fruit detection | 78% | 88% | +10% |
| False positives | 45% | 15% | -70% |

---

## Version 0.1.0

### Initial Release
- Basic leaf/fruit detection
- Color analysis
- Shape analysis
- CLI interface
- SQLite storage

---

**Last Updated**: 2026-08-21
**Current Version**: 0.3.0
