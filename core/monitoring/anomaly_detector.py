"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Детектор аномалий.
"""

import logging
import numpy as np

logger = logging.getLogger("anomaly_detector")

def detect_anomalies(data):
    """
    Обнаруживает аномалии в данных.
    """
    if len(data) == 0:
        return []
    
    mean = np.mean(data)
    std = np.std(data)
    
    anomalies = [i for i, x in enumerate(data) if abs(x - mean) > 2 * std]
    
    if anomalies:
        logger.warning(f"⚠️ Найдены аномалии: {anomalies}")
    
    return anomalies