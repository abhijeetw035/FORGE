# 🔮 The Oracle AI Risk Prediction Engine

## What You'll See

When you visit a repository detail page (e.g., `http://localhost:3001/repositories/5`), you'll now see a new section called **"AI Risk Forecast"** positioned between the Timeline and Contributors sections.

## Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 🧠 AI Risk Forecast              [🔴 X Critical] [🟠 Y Warning] │
│ Machine learning predictions for files at risk              │
├─────────────────────────────────────────────────────────────┤
│ 🔮 How it works                                             │
│ Using Isolation Forest algorithm to detect statistical     │
│ anomalies in code complexity, change frequency, and        │
│ authorship patterns.                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 🔴 example_file.py                                 92.3%   │
│    path/to/example_file.py                         CRITICAL│
│    [████████████████████░░░░] 92%                          │
│    Churn: 150 | Complexity: 12.5 | Authors: 3             │
│    Reason: High Churn + High Complexity                    │
│                                                             │
│ 🟠 another_file.py                                 78.1%   │
│    path/to/another_file.py                         WARNING │
│    [████████████████░░░░░░░] 78%                           │
│    Churn: 89 | Complexity: 8.46 | Authors: 2              │
│    Reason: High Complexity + Multiple Authors              │
│                                                             │
│ 🟡 some_file.py                                    45.2%   │
│    path/to/some_file.py                            WATCHLIST│
│    [████████░░░░░░░░░░░░░░] 45%                            │
│    Churn: 42 | Complexity: 5.58 | Authors: 1              │
│    Reason: High Churn + Single Author Risk                 │
│                                                             │
│ ... (showing top 5 of 20 analyzed files)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 💡 Interpretation Guide                                     │
│ • Critical (80-100%): Immediate attention required         │
│ • Warning (50-79%): Monitor closely, consider refactoring  │
│ • Watchlist (<50%): Keep an eye on these files             │
└─────────────────────────────────────────────────────────────┘
```

## How The AI Works

### Isolation Forest Algorithm

1. **Feature Extraction**: For each file, extract:
   - `churn`: Number of times the file was modified
   - `complexity`: Average cyclomatic complexity of functions
   - `author_count`: Number of unique developers who touched it

2. **Normalization**: Scale all features to 0-1 range using StandardScaler

3. **Anomaly Detection**: 
   - Train Isolation Forest with `contamination=0.1` (expects 10% outliers)
   - Files that are statistical outliers get flagged
   - Lower anomaly score = Higher risk

4. **Risk Scoring**:
   - Convert anomaly scores to 0-100% risk probability
   - Invert scores (lower anomaly score = higher risk)
   - Normalize to intuitive percentage

5. **Risk Levels**:
   - 🔴 **Critical (80-100%)**: Statistical outlier, needs immediate attention
   - 🟠 **Warning (50-79%)**: Abnormal patterns, monitor closely
   - 🟡 **Watchlist (<50%)**: Slightly unusual, keep watching

### Why These Files Are Risky

**High Churn Files:**
- Modified many times across commits
- Indicates either:
  - Unstable design (keeps needing fixes)
  - Rapidly evolving requirements
  - Core component that touches everything
- **Risk**: High chance of introducing bugs in future changes

**High Complexity Files:**
- High cyclomatic complexity (>10 is considered complex)
- When combined with frequent changes, it's both complex AND unstable
- **Risk**: Hard to maintain, easy to break

**Multiple Author Files:**
- Many developers have touched the code
- Knowledge is scattered across the team
- **Risk**: No single owner, harder to coordinate changes

## Colors & UI Theme

The Oracle uses the same industrial cyberpunk theme as the rest of FORGE:

- **Background**: `bg-zinc-950/40` with `backdrop-blur-md`
- **Borders**: `border-zinc-800/50`
- **Critical Files**: Red (`bg-red-950/30`, `border-red-800`, `text-red-400`)
- **Warning Files**: Orange (`bg-orange-950/30`, `border-orange-800`, `text-orange-400`)
- **Watchlist**: Yellow (`bg-yellow-950/30`, `border-yellow-800`, `text-yellow-400`)
- **Icon**: Brain emoji (🧠) + Lucide's `Brain` component
- **Info Panel**: Cyan (`bg-cyan-950/20`, `border-cyan-800`)

## Technical Details

### API Endpoint
```bash
GET /analytics/repositories/{id}/risk-prediction
Authorization: Bearer <token>
```

### Response Format
```json
[
  {
    "file_path": "path/to/file.py",
    "churn": 150,
    "complexity": 12.5,
    "author_count": 3,
    "risk_score": 92.34,
    "risk_level": "critical",
    "reason": "High Churn + Multiple Authors"
  },
  ...
]
```

### Dependencies Added
- `scikit-learn==1.4.0` - ML algorithms
- `pandas==2.2.0` - Data manipulation
- `numpy==1.26.3` - Numerical operations

## Use Cases

1. **Code Review Prioritization**: Focus reviews on high-risk files first
2. **Refactoring Decisions**: Data-driven "what to fix next"
3. **Knowledge Transfer**: Identify files with single-author risk
4. **Tech Debt Tracking**: Monitor risk scores over time
5. **Team Planning**: Spot files that need pair programming or documentation
