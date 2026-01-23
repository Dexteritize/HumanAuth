#!/usr/bin/env python3
"""
HumanAuth Types Module

This module contains shared data types used across the HumanAuth system.
It helps avoid circular dependencies between modules.

Author: Jason Dank (2026)
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AuthResult:
    """Result of human authentication check"""
    authenticated: bool
    confidence: float
    details: Dict[str, Any]
    message: str