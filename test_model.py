import pytest
import numpy as np
import pandas as pd
from src.models.classifier import CandidateClassifier
from src.features.extractor import FEATURE_NAMES

def test_candidate_classifier_fit_and_predict():
    np.random.seed(42)
    n_samples = 200
    n_stars = 20
    
    # Generate synthetic feature matrix
    data = {}
    for name in FEATURE_NAMES:
        data[name] = np.random.normal(0, 1, n_samples)
        
    # Make sde strongly correlate with label
    y = np.random.binomial(1, 0.3, n_samples)
    data["sde"] = np.where(y == 1, np.random.normal(15, 3, n_samples), np.random.normal(6, 2, n_samples))
    data["odd_even_consistency"] = np.where(y == 1, np.random.uniform(0.7, 1.0, n_samples), np.random.uniform(0.1, 0.9, n_samples))
    
    stars = [f"STAR_{i%n_stars:04d}" for i in range(n_samples)]
    df = pd.DataFrame(data)
    
    clf = CandidateClassifier(feature_names=FEATURE_NAMES)
    fit_metrics = clf.fit(df, y, groups=stars, n_splits=3)
    
    assert "oof_roc_auc" in fit_metrics
    assert fit_metrics["oof_roc_auc"] > 0.70
    
    # Test predict proba
    probs = clf.predict_proba(df)
    assert len(probs) == n_samples
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
