"""
Unit tests for HazardRateEngine
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_provider import CreditDataProvider
from hazard_rate import HazardRateEngine


class TestHazardRateEngine:
    """Test suite for HazardRateEngine class."""
    
    @pytest.fixture
    def market_data(self):
        """Provide market data for testing."""
        provider = CreditDataProvider(mode='dummy')
        return provider.get_market_snapshot('INTC')
    
    @pytest.fixture
    def engine(self, market_data):
        """Provide initialized engine for testing."""
        return HazardRateEngine(market_data)
    
    def test_initialization(self, market_data):
        """Test engine initialization."""
        engine = HazardRateEngine(market_data)
        
        assert engine.recovery == market_data['bond']['recovery_rate']
        assert len(engine.hazard_rates) > 0
        assert isinstance(engine.hazard_rates, dict)
    
    def test_invalid_market_data(self):
        """Test that invalid market data raises ValueError."""
        invalid_data = {'bond': {}}
        
        with pytest.raises(ValueError):
            HazardRateEngine(invalid_data)
    
    def test_hazard_rates_positive(self, engine):
        """Test that all hazard rates are positive."""
        for tenor, hazard in engine.hazard_rates.items():
            assert hazard > 0, f"Hazard rate for tenor {tenor} should be positive"
    
    def test_hazard_rates_bounded(self, engine):
        """Test that hazard rates are within reasonable bounds."""
        for tenor, hazard in engine.hazard_rates.items():
            assert engine.MIN_HAZARD_RATE <= hazard <= engine.MAX_HAZARD_RATE, \
                f"Hazard rate {hazard} for tenor {tenor} out of bounds"
    
    def test_survival_prob_at_zero(self, engine):
        """Test that survival probability at time 0 is 1."""
        assert engine.survival_prob(0) == 1.0
    
    def test_survival_prob_decreasing(self, engine):
        """Test that survival probability decreases over time."""
        times = [1, 2, 3, 5, 7, 10]
        probs = [engine.survival_prob(t) for t in times]
        
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i+1], \
                f"Survival prob should decrease: {probs[i]} >= {probs[i+1]}"
    
    def test_survival_prob_bounded(self, engine):
        """Test that survival probabilities are between 0 and 1."""
        for t in [1, 3, 5, 7, 10, 15, 20]:
            prob = engine.survival_prob(t)
            assert 0 <= prob <= 1, \
                f"Survival prob {prob} at time {t} should be in [0,1]"
    
    def test_default_prob(self, engine):
        """Test default probability calculation."""
        for t in [1, 5, 10]:
            surv = engine.survival_prob(t)
            default = engine.default_prob(t)
            
            assert abs(surv + default - 1.0) < 1e-10, \
                f"Survival + default should equal 1 at time {t}"
    
    def test_forward_hazard_rate(self, engine):
        """Test forward hazard rate calculation."""
        forward = engine.get_forward_hazard_rate(1.0, 5.0)
        
        assert forward > 0
        assert forward <= engine.MAX_HAZARD_RATE
    
    def test_forward_hazard_invalid_times(self, engine):
        """Test that invalid time ordering raises ValueError."""
        with pytest.raises(ValueError):
            engine.get_forward_hazard_rate(5.0, 1.0)
    
    def test_curve_summary(self, engine):
        """Test curve summary generation."""
        summary = engine.get_curve_summary()
        
        assert 'tenors' in summary
        assert 'hazard_rates' in summary
        assert 'survival_probs' in summary
        assert 'default_probs' in summary
        assert 'avg_hazard_rate' in summary
        
        assert len(summary['tenors']) == len(summary['hazard_rates'])
        assert len(summary['survival_probs']) == len(summary['tenors'])
    
    def test_survival_prob_interpolation(self, engine):
        """Test survival probability interpolation between tenors."""
        # Get survival at a non-tenor point
        t = 6.0  # Between 5Y and 7Y tenors typically
        
        prob = engine.survival_prob(t)
        prob_5y = engine.survival_prob(5.0)
        prob_7y = engine.survival_prob(7.0)
        
        # Should be between adjacent tenors
        assert prob_7y <= prob <= prob_5y
    
    def test_hazard_rate_consistency(self, engine, market_data):
        """Test that hazard rates are consistent with input CDS spreads."""
        # First tenor should approximately follow credit triangle
        # λ ≈ Spread / (1 - R)
        
        first_tenor = min(market_data['cds_curve'].keys())
        spread = market_data['cds_curve'][first_tenor] / 10000
        recovery = market_data['bond']['recovery_rate']
        
        expected_hazard = spread / (1 - recovery)
        actual_hazard = engine.hazard_rates[first_tenor]
        
        # Should be close (within 10%)
        assert abs(actual_hazard - expected_hazard) / expected_hazard < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
