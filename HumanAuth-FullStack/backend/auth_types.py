#!/usr/bin/env python3
"""
HumanAuth Types Module

This module contains shared data types used across the HumanAuth system.
It helps avoid circular dependencies between modules.

Author: Jason Dank (2026)
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class SessionSummary:
    """Comprehensive session results for authentication transparency"""
    # Authentication Decision
    auth_method: str  # "confidence_threshold" or "challenge_count"
    final_confidence: float
    auth_threshold: float
    challenges_completed: int
    challenges_required: int
    
    # Confidence Breakdown
    passive_base: float
    challenge_boost: float
    detector_contributions: Dict[str, float]  # weight * score for each detector
    
    # Challenge History
    completed_challenges: List[Dict[str, Any]]  # challenge, response_time, score
    
    # Final Detector Scores
    final_scores: Dict[str, float]
    
    # Weights Used
    weights: Dict[str, float]
    
    # Session Duration
    session_duration: float
    frames_processed: int

@dataclass
class AuthResult:
    """Result of human authentication check"""
    authenticated: bool
    confidence: float
    details: Dict[str, Any]
    message: str
    session_summary: Optional[SessionSummary] = None  # Only populated on final auth