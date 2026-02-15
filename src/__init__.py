"""
Credit Analytics Platform
A production-ready system for credit risk analysis, basis trading, and synthetic bond pricing.

Author: Credit Analytics Team
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Credit Analytics Team"

from .data_provider import CreditDataProvider
from .hazard_rate import HazardRateEngine
from .pricing import SyntheticPricer
from .basis_analysis import BasisAnalyzer
from .visualizations import CreditVisualizer

__all__ = [
    'CreditDataProvider',
    'HazardRateEngine', 
    'SyntheticPricer',
    'BasisAnalyzer',
    'CreditVisualizer'
]
