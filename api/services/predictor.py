import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any


# Feature columns fed into the Isolation Forest.
# Using 9 dimensions instead of the original 3 makes the model
# sensitive to signals that a simple linear formula cannot capture
FEATURE_COLS = [
    'churn',             # total commits touching the file
    'complexity',        # avg cyclomatic complexity of its functions
    'author_count',      # distinct authors
    'lines_added',       # cumulative insertions
    'lines_deleted',     # cumulative deletions
    'commit_frequency',  # commits / day  (burst vs steady change rate)
    'recent_churn',      # commits in the last 90 days
    'ownership_entropy', # Shannon entropy of authorship fractions
    'dependency_count',  # import/require statements (coupling proxy)
]


class RiskPredictor:
    """
    AI-powered risk prediction using Isolation Forest for anomaly detection.

    With 9 features the model captures compound risk patterns that a simple
    weighted formula like  risk = 0.5*churn + 0.3*complexity + 0.2*authors
    cannot express:

    - A file can be *low-churn but high-complexity* (abandoned legacy code).
    - A file can have *high ownership_entropy + high recent_churn* (no single
      owner + recent burst → classic defect predictor).
    - A file can have *high dependency_count + low author_count* (critical hub
      maintained by one person → bus-factor risk).

    The Isolation Forest detects whichever *combination* of signals is
    statistically unusual for this particular codebase.
    """

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=200,
            max_features=0.8,
        )
        self.scaler = StandardScaler()

    def predict_risk(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict risk for a list of file-metric dicts.

        Required keys (missing keys are filled with 0):
            churn, complexity, author_count, lines_added, lines_deleted,
            commit_frequency, recent_churn, ownership_entropy, dependency_count

        Returns the same list enriched with:
            risk_score   (float 0–100)
            risk_level   ('critical' | 'warning' | 'watchlist')
            reason       (human-readable explanation)
        Sorted by risk_score descending.
        """
        if not data or len(data) < 2:
            return []

        df = pd.DataFrame(data)

        # Fill any missing feature columns with 0
        for col in FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0

        features = df[FEATURE_COLS].copy().fillna(0)

        # Normalise so no single feature dominates by scale
        features_scaled = self.scaler.fit_transform(features)

        self.model.fit(features_scaled)
        anomaly_scores = self.model.decision_function(features_scaled)

        # Invert & normalise to 0–100 (lower IF score = more anomalous = higher risk)
        lo, hi = anomaly_scores.min(), anomaly_scores.max()
        if hi - lo == 0:
            normalized_risk = np.full(len(anomaly_scores), 50.0)
        else:
            normalized_risk = 100.0 * (1.0 - (anomaly_scores - lo) / (hi - lo))

        df['risk_score'] = normalized_risk.round(2)
        df['risk_level'] = df['risk_score'].apply(self._get_risk_level)
        df['reason'] = df.apply(self._generate_reason, axis=1)

        df = df.sort_values('risk_score', ascending=False)
        return df.to_dict('records')

    @staticmethod
    def _get_risk_level(score: float) -> str:
        if score >= 80:
            return 'critical'
        elif score >= 50:
            return 'warning'
        return 'watchlist'

    def _generate_reason(self, row: pd.Series) -> str:
        """
        Generate a human-readable reason string by checking each feature
        against the median of that feature across the dataset.
        Because the medians are computed per-row we pass the whole DataFrame
        via a closure captured in predict_risk — here we use fixed thresholds
        that are reasonable across most codebases.
        """
        reasons = []

        # --- churn / change rate ---
        if row.get('churn', 0) > 20:
            reasons.append('Very High Churn')
        elif row.get('churn', 0) > 10:
            reasons.append('High Churn')

        # --- complexity ---
        if row.get('complexity', 0) > 15:
            reasons.append('High Complexity')
        elif row.get('complexity', 0) > 10:
            reasons.append('Moderate Complexity')

        # --- authorship / knowledge concentration ---
        if row.get('author_count', 1) > 5:
            reasons.append('Many Authors (knowledge fragmentation)')
        elif row.get('author_count', 1) == 1:
            reasons.append('Single Author (bus-factor risk)')

        # --- ownership entropy ---
        # High entropy (>1.5 bits) + several authors = no clear owner
        if row.get('ownership_entropy', 0) > 1.5 and row.get('author_count', 1) > 2:
            reasons.append('Diffuse Ownership')
        # Low entropy + 1 author = knowledge silo
        elif row.get('ownership_entropy', 0) < 0.3 and row.get('author_count', 1) == 1:
            reasons.append('Knowledge Silo')

        # --- lines added/deleted (churn volume) ---
        if row.get('lines_added', 0) > 5000:
            reasons.append('High Volume Additions')
        if row.get('lines_deleted', 0) > 3000:
            reasons.append('High Volume Deletions')

        # --- recent activity ---
        if row.get('recent_churn', 0) > 10:
            reasons.append('Recent Hot Spot')
        elif row.get('recent_churn', 0) == 0 and row.get('complexity', 0) > 10:
            reasons.append('Complex Untouched Code')

        # --- commit frequency (burst changes) ---
        if row.get('commit_frequency', 0) > 1.0:
            reasons.append('High Change Frequency')

        # --- dependency coupling ---
        if row.get('dependency_count', 0) > 20:
            reasons.append('High Coupling (many imports)')

        if not reasons:
            reasons.append('Statistical Anomaly')

        return ' · '.join(reasons)
