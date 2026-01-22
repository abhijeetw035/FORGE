import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any


class RiskPredictor:
    """
    AI-powered risk prediction using Isolation Forest for anomaly detection.
    Identifies files that are statistically abnormal in terms of complexity, churn, and authorship.
    """
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize the predictor.
        
        Args:
            contamination: Expected proportion of outliers (0.0 to 0.5). Default 0.1 = 10% anomalies.
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
    
    def predict_risk(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict risk probability for files based on their metrics.
        
        Args:
            data: List of file metrics with keys: file_path, churn, complexity, author_count
            
        Returns:
            List of files with added risk_score (0-100) and risk_level, sorted by risk descending
        """
        if not data or len(data) < 2:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure we have the required columns
        required_cols = ['churn', 'complexity', 'author_count']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Extract features for training
        features = df[required_cols].copy()
        
        # Handle missing values
        features = features.fillna(0)
        
        # Normalize features (0-1 scale)
        features_scaled = self.scaler.fit_transform(features)
        
        # Train the model and get anomaly scores
        self.model.fit(features_scaled)
        anomaly_scores = self.model.decision_function(features_scaled)
        
        # Convert anomaly scores to risk probability (0-100)
        # Isolation Forest: lower score = more anomalous = higher risk
        # decision_function returns values typically in range [-0.5, 0.5]
        # We invert and normalize to 0-100 scale
        min_score = anomaly_scores.min()
        max_score = anomaly_scores.max()
        
        if max_score - min_score == 0:
            normalized_risk = np.full(len(anomaly_scores), 50.0)
        else:
            # Invert: lower anomaly score = higher risk
            normalized_risk = 100 * (1 - (anomaly_scores - min_score) / (max_score - min_score))
        
        # Add risk scores to original data
        df['risk_score'] = normalized_risk.round(2)
        
        # Determine risk level
        df['risk_level'] = df['risk_score'].apply(self._get_risk_level)
        
        # Add reasoning
        df['reason'] = df.apply(self._generate_reason, axis=1)
        
        # Sort by risk descending
        df = df.sort_values('risk_score', ascending=False)
        
        # Convert back to list of dicts
        result = df.to_dict('records')
        
        return result
    
    def _get_risk_level(self, score: float) -> str:
        """
        Convert numeric risk score to categorical level.
        
        Args:
            score: Risk score (0-100)
            
        Returns:
            Risk level string
        """
        if score >= 80:
            return 'critical'
        elif score >= 50:
            return 'warning'
        else:
            return 'watchlist'
    
    def _generate_reason(self, row: pd.Series) -> str:
        """
        Generate human-readable reason for high risk.
        
        Args:
            row: DataFrame row with metrics
            
        Returns:
            Reason string
        """
        reasons = []
        
        # High churn
        if row['churn'] > row['churn'].mean() if hasattr(row['churn'], 'mean') else row['churn'] > 10:
            reasons.append('High Churn')
        
        # High complexity
        if row['complexity'] > 10:
            reasons.append('High Complexity')
        
        # Multiple authors (knowledge scattered)
        if row['author_count'] > 3:
            reasons.append('Multiple Authors')
        elif row['author_count'] == 1:
            reasons.append('Single Author Risk')
        
        # Low activity but high complexity (abandoned complex code)
        if row['churn'] < 3 and row['complexity'] > 15:
            reasons.append('Complex Legacy Code')
        
        if not reasons:
            reasons.append('Statistical Anomaly')
        
        return ' + '.join(reasons)
