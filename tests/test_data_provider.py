"""
Unit tests for CreditDataProvider
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_provider import CreditDataProvider


class TestCreditDataProvider:
    """Test suite for CreditDataProvider class."""
    
    def test_initialization_dummy_mode(self):
        """Test provider initialization in dummy mode."""
        provider = CreditDataProvider(mode='dummy')
        assert provider.mode == 'dummy'
        assert provider.cache_ttl == CreditDataProvider.DEFAULT_CACHE_TTL
    
    def test_initialization_invalid_mode(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            CreditDataProvider(mode='invalid_mode')
    
    def test_get_dummy_data_structure(self):
        """Test that dummy data has correct structure."""
        provider = CreditDataProvider(mode='dummy')
        data = provider.get_market_snapshot('INTC')
        
        # Check top-level keys
        assert 'bond' in data
        assert 'cds_curve' in data
        assert 'treasury_curve' in data
        assert 'metadata' in data
        
        # Check bond data
        assert 'price' in data['bond']
        assert 'coupon' in data['bond']
        assert 'years_to_maturity' in data['bond']
        assert 'recovery_rate' in data['bond']
        
        # Check CDS curve is dict
        assert isinstance(data['cds_curve'], dict)
        assert len(data['cds_curve']) > 0
        
        # Check treasury curve
        assert isinstance(data['treasury_curve'], dict)
        assert len(data['treasury_curve']) > 0
    
    def test_dummy_data_values(self):
        """Test that dummy data values are reasonable."""
        provider = CreditDataProvider(mode='dummy')
        data = provider.get_market_snapshot('INTC')
        
        # Bond price should be reasonable
        assert 0 < data['bond']['price'] < 200
        
        # Coupon should be between 0 and 20%
        assert 0 <= data['bond']['coupon'] <= 0.20
        
        # Recovery rate should be between 0 and 1
        assert 0 <= data['bond']['recovery_rate'] <= 1
        
        # CDS spreads should be positive
        for spread in data['cds_curve'].values():
            assert spread > 0
        
        # Treasury rates should be positive
        for rate in data['treasury_curve'].values():
            assert rate > 0
    
    def test_validate_data_valid(self):
        """Test validation of valid data."""
        provider = CreditDataProvider(mode='dummy')
        data = provider.get_market_snapshot('INTC')
        
        assert provider.validate_data(data) is True
    
    def test_validate_data_missing_keys(self):
        """Test validation fails with missing keys."""
        provider = CreditDataProvider(mode='dummy')
        
        # Missing bond key
        invalid_data = {
            'cds_curve': {1.0: 100},
            'treasury_curve': {1.0: 0.05}
        }
        
        assert provider.validate_data(invalid_data) is False
    
    def test_validate_data_invalid_price(self):
        """Test validation fails with invalid bond price."""
        provider = CreditDataProvider(mode='dummy')
        
        invalid_data = {
            'bond': {
                'price': -10,  # Invalid negative price
                'coupon': 0.05,
                'years_to_maturity': 5,
                'recovery_rate': 0.4
            },
            'cds_curve': {1.0: 100},
            'treasury_curve': {1.0: 0.05}
        }
        
        assert provider.validate_data(invalid_data) is False
    
    def test_validate_data_invalid_recovery(self):
        """Test validation fails with invalid recovery rate."""
        provider = CreditDataProvider(mode='dummy')
        
        invalid_data = {
            'bond': {
                'price': 100,
                'coupon': 0.05,
                'years_to_maturity': 5,
                'recovery_rate': 1.5  # Invalid > 1
            },
            'cds_curve': {1.0: 100},
            'treasury_curve': {1.0: 0.05}
        }
        
        assert provider.validate_data(invalid_data) is False
    
    def test_metadata_present(self):
        """Test that metadata is included in data snapshot."""
        provider = CreditDataProvider(mode='dummy')
        data = provider.get_market_snapshot('AAPL')
        
        assert 'metadata' in data
        assert 'timestamp' in data['metadata']
        assert 'source' in data['metadata']
        assert data['metadata']['ticker'] == 'AAPL'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
