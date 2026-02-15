"""
Configuration Module
Centralized configuration management for the credit analytics platform.
"""

import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    """Application configuration settings."""
    
    # Project paths
    ROOT_DIR = Path(__file__).parent.parent
    SRC_DIR = ROOT_DIR / 'src'
    DATA_DIR = ROOT_DIR / 'data'
    OUTPUT_DIR = ROOT_DIR / 'output'
    CACHE_DIR = ROOT_DIR / '.cache'
    
    # Data provider settings
    DEFAULT_MODE = 'dummy'
    CACHE_TTL = 3600  # seconds
    
    # Hazard rate engine settings
    INTEGRATION_STEP = 0.25  # quarterly
    MAX_ITERATIONS = 1000
    CONVERGENCE_TOLERANCE = 1e-6
    
    # Pricing settings
    DEFAULT_RECOVERY_RATE = 0.40
    DEFAULT_FREQUENCY = 2  # semi-annual
    
    # Visualization settings
    PLOT_DPI = 300
    FIGURE_SIZE = (12, 7)
    STYLE = 'seaborn-v0_8-whitegrid'
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # API Configuration (load from environment)
    BLOOMBERG_API_KEY = os.getenv('BLOOMBERG_API_KEY')
    BLOOMBERG_API_SECRET = os.getenv('BLOOMBERG_API_SECRET')
    REFINITIV_APP_KEY = os.getenv('REFINITIV_APP_KEY')
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.OUTPUT_DIR, cls.CACHE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and not callable(getattr(cls, key))
        }
    
    @classmethod
    def save(cls, filepath: Path):
        """Save configuration to JSON file."""
        config_dict = cls.to_dict()
        # Convert Path objects to strings
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load(cls, filepath: Path):
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)


# Market data configurations
MARKET_CONFIG = {
    'default_tickers': ['INTC', 'AAPL', 'MSFT', 'TSLA', 'AMZN'],
    'cds_tenors': [1.0, 3.0, 5.0, 7.0, 10.0],
    'treasury_tenors': [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    'typical_recovery_rates': {
        'senior_secured': 0.60,
        'senior_unsecured': 0.40,
        'subordinated': 0.30,
        'junior': 0.20
    }
}

# Basis trading thresholds
TRADING_CONFIG = {
    'basis_thresholds': {
        'strong_negative': -20,  # bps
        'moderate_negative': -10,
        'neutral': 0,
        'moderate_positive': 10,
        'strong_positive': 20
    },
    'position_limits': {
        'max_notional': 100_000_000,  # $100M
        'max_dv01': 100_000,  # $100K
    }
}


if __name__ == '__main__':
    # Create default configuration
    Config.create_directories()
    print("Configuration initialized successfully")
    print(f"Root directory: {Config.ROOT_DIR}")
    print(f"Output directory: {Config.OUTPUT_DIR}")
