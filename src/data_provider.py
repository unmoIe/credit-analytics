"""
Data Provider Module
Handles market data acquisition from multiple sources with failover and caching.
"""

import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CreditDataProvider:
    """
    Unified interface for credit market data acquisition.
    
    Supports multiple modes:
    - dummy: Static data for testing
    - live: Real-time market data (requires API keys)
    - cached: Uses cached data with TTL
    
    Attributes:
        mode (str): Data source mode
        cache_dir (Path): Directory for caching market data
        cache_ttl (int): Time-to-live for cached data in seconds
    """
    
    VALID_MODES = ['dummy', 'live', 'cached']
    DEFAULT_CACHE_TTL = 3600  # 1 hour
    
    def __init__(
        self, 
        mode: str = "dummy",
        cache_dir: Optional[Path] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        api_config: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the data provider.
        
        Args:
            mode: Data source mode ('dummy', 'live', 'cached')
            cache_dir: Directory for caching data
            cache_ttl: Cache time-to-live in seconds
            api_config: API credentials for live data sources
            
        Raises:
            ValueError: If mode is not valid
        """
        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {self.VALID_MODES}"
            )
        
        self.mode = mode
        self.cache_dir = cache_dir or Path.home() / '.credit_analytics' / 'cache'
        self.cache_ttl = cache_ttl
        self.api_config = api_config or {}
        
        # Create cache directory if it doesn't exist
        if mode == 'cached':
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache directory initialized at {self.cache_dir}")
    
    def get_market_snapshot(self, ticker: str = "INTC") -> Dict[str, Any]:
        """
        Retrieve current market snapshot for a given issuer.
        
        Args:
            ticker: Issuer ticker symbol
            
        Returns:
            Dictionary containing bond, CDS, and treasury data
            
        Raises:
            RuntimeError: If data retrieval fails in live mode
        """
        logger.info(f"Fetching market snapshot for {ticker} in {self.mode} mode")
        
        if self.mode == "dummy":
            return self._get_dummy_data(ticker)
        elif self.mode == "cached":
            return self._get_cached_data(ticker)
        else:
            return self._get_live_data(ticker)
    
    def _get_dummy_data(self, ticker: str = "INTC") -> Dict[str, Any]:
        """
        Generate realistic dummy data for testing.
        
        Args:
            ticker: Issuer ticker symbol
            
        Returns:
            Mock market data snapshot
        """
        # Realistic dummy data as of Feb 2026
        dummy_data = {
            "bond": {
                "ticker": ticker,
                "name": f"{ticker} 5.200% 02/10/2033",
                "price": 94.50,
                "coupon": 0.052,
                "years_to_maturity": 7.0,
                "recovery_rate": 0.40,
                "face_value": 100.0,
                "frequency": 2  # Semi-annual
            },
            "cds_curve": {
                1.0: 80,    # 1Y Spread in bps
                3.0: 110,   # 3Y
                5.0: 140,   # 5Y (The Benchmark)
                7.0: 160,   # 7Y
                10.0: 180   # 10Y
            },
            "treasury_curve": {
                0.25: 0.0495,
                0.5: 0.0490,
                1.0: 0.0480,
                2.0: 0.0460,
                5.0: 0.0440,
                10.0: 0.0425,
                30.0: 0.0450
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source": "dummy",
                "ticker": ticker
            }
        }
        
        logger.debug(f"Generated dummy data for {ticker}")
        return dummy_data
    
    def _get_live_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch live market data from financial APIs.
        
        Args:
            ticker: Issuer ticker symbol
            
        Returns:
            Live market data snapshot
            
        Raises:
            RuntimeError: If API calls fail
        """
        try:
            # Fetch Treasury yields using yfinance proxies
            treasury_data = self._fetch_treasury_curve()
            
            # Note: In production, you would integrate with:
            # - Bloomberg API for CDS spreads
            # - TRACE/FINRA for bond prices
            # - Refinitiv/FactSet for comprehensive data
            
            logger.warning(
                "Live CDS and bond data require Bloomberg/Refinitiv APIs. "
                "Using fallback dummy data for demonstration."
            )
            
            # Fallback to dummy with live treasury data
            data = self._get_dummy_data(ticker)
            data['treasury_curve'] = treasury_data
            data['metadata']['source'] = 'live_partial'
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch live data: {str(e)}")
            raise RuntimeError(f"Live data fetch failed: {str(e)}")
    
    def _fetch_treasury_curve(self) -> Dict[float, float]:
        """
        Fetch current US Treasury yield curve.
        
        Returns:
            Dictionary mapping tenors to yields
        """
        treasury_proxies = {
            0.25: "^IRX",   # 13-week
            2.0: "^FVX",    # 5-year (proxy)
            10.0: "^TNX",   # 10-year
            30.0: "^TYX"    # 30-year
        }
        
        curve = {}
        for tenor, symbol in treasury_proxies.items():
            try:
                ticker_data = yf.Ticker(symbol)
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    curve[tenor] = hist['Close'].iloc[-1] / 100
                    logger.debug(f"Fetched {tenor}Y Treasury: {curve[tenor]:.4f}")
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {str(e)}")
                # Use dummy fallback
                curve[tenor] = 0.045
        
        # Interpolate missing tenors
        if curve:
            curve[1.0] = curve.get(2.0, 0.048)
            curve[5.0] = curve.get(10.0, 0.044)
        
        return curve or self._get_dummy_data()['treasury_curve']
    
    def _get_cached_data(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieve data from cache or fetch new data if stale.
        
        Args:
            ticker: Issuer ticker symbol
            
        Returns:
            Cached or fresh market data
        """
        cache_file = self.cache_dir / f"{ticker}_market_data.json"
        
        # Check if cache exists and is fresh
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(
                cache_file.stat().st_mtime
            )
            
            if cache_age.total_seconds() < self.cache_ttl:
                logger.info(f"Using cached data for {ticker} (age: {cache_age})")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        # Fetch fresh data and cache it
        logger.info(f"Cache miss or stale. Fetching fresh data for {ticker}")
        data = self._get_live_data(ticker)
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return data
    
    def clear_cache(self, ticker: Optional[str] = None):
        """
        Clear cached data.
        
        Args:
            ticker: Specific ticker to clear, or None for all
        """
        if ticker:
            cache_file = self.cache_dir / f"{ticker}_market_data.json"
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for {ticker}")
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all cached data")
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate market data structure and values.
        
        Args:
            data: Market data dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ['bond', 'cds_curve', 'treasury_curve']
        
        # Check structure
        if not all(key in data for key in required_keys):
            logger.error("Missing required data keys")
            return False
        
        # Validate bond data
        bond_keys = ['price', 'coupon', 'years_to_maturity', 'recovery_rate']
        if not all(key in data['bond'] for key in bond_keys):
            logger.error("Incomplete bond data")
            return False
        
        # Validate ranges
        if not (0 < data['bond']['price'] < 200):
            logger.error(f"Invalid bond price: {data['bond']['price']}")
            return False
        
        if not (0 <= data['bond']['recovery_rate'] <= 1):
            logger.error(f"Invalid recovery rate: {data['bond']['recovery_rate']}")
            return False
        
        logger.debug("Data validation passed")
        return True
