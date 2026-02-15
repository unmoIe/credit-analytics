"""
Basis Analysis Module
Analyzes the relationship between bond and CDS markets for relative value trading.
"""

import logging
import numpy as np
from scipy.optimize import brentq
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class BasisAnalyzer:
    """
    Analyze CDS-Bond basis for relative value opportunities.
    
    The basis is defined as: CDS Spread - Z-Spread
    
    - Negative Basis: Bond cheap vs CDS → Buy bond, buy CDS protection
    - Positive Basis: Bond rich vs CDS → Sell bond, sell CDS protection
    
    Attributes:
        market_data: Market snapshot
        pricer: SyntheticPricer instance
    """
    
    def __init__(self, market_data: Dict, pricer):
        """
        Initialize the basis analyzer.
        
        Args:
            market_data: Market snapshot containing bond and CDS data
            pricer: SyntheticPricer instance for bond analytics
        """
        self.market_data = market_data
        self.pricer = pricer
        
        logger.info("Initialized BasisAnalyzer")
    
    def calculate_z_spread(self, tolerance: float = 1e-6) -> float:
        """
        Calculate Z-spread (zero-volatility spread).
        
        Z-spread is the constant spread that, when added to the risk-free
        curve, equates the bond's PV to its market price.
        
        Args:
            tolerance: Convergence tolerance for solver
            
        Returns:
            Z-spread in decimal form
            
        Raises:
            RuntimeError: If solver fails to converge
        """
        target_price = self.market_data['bond']['price']
        coupon_rate = self.market_data['bond']['coupon']
        years = self.market_data['bond']['years_to_maturity']
        frequency = self.market_data['bond'].get('frequency', 2)
        face_value = self.market_data['bond'].get('face_value', 100.0)
        
        payment_interval = 1.0 / frequency
        times = np.arange(payment_interval, years + payment_interval, payment_interval)
        coupon_payment = (coupon_rate / frequency) * face_value
        
        def price_with_spread(z: float) -> float:
            """Calculate bond price with given Z-spread."""
            pv = 0.0
            for t in times:
                is_maturity = np.isclose(t, times[-1])
                cash_flow = coupon_payment + (face_value if is_maturity else 0)
                
                # Get risk-free rate for this time
                rf_rate = self.pricer._get_risk_free_rate(t)
                
                # Discount at (risk-free + z-spread)
                discount_rate = rf_rate + z
                pv += cash_flow * np.exp(-discount_rate * t)
            
            return pv
        
        def objective(z: float) -> float:
            """Objective: price difference."""
            return price_with_spread(z) - target_price
        
        try:
            # Solve for Z-spread (search between -10% and +20%)
            z_spread = brentq(objective, -0.10, 0.20, xtol=tolerance)
            logger.info(f"Z-spread calculated: {z_spread * 10000:.2f} bps")
            return z_spread
            
        except ValueError as e:
            logger.error(f"Z-spread solver failed: {str(e)}")
            # Fallback: approximate using YTM - RF
            ytm = self.pricer.calculate_ytm(target_price)
            rf = self.pricer._get_risk_free_rate(years)
            approx_z = ytm - rf
            logger.warning(f"Using approximate Z-spread: {approx_z * 10000:.2f} bps")
            return approx_z
    
    def calculate_asset_swap_spread(self) -> float:
        """
        Calculate asset swap spread.
        
        Asset swap spread is another measure of credit spread,
        representing the spread over LIBOR/SOFR in an asset swap structure.
        
        Returns:
            Asset swap spread in basis points
        """
        # Simplified calculation
        # In practice, this involves swap curve bootstrapping
        market_price = self.market_data['bond']['price']
        par_value = self.market_data['bond'].get('face_value', 100.0)
        
        # ASW spread ≈ (Par - Price) / Duration + Coupon - Swap Rate
        duration_metrics = self.pricer.calculate_duration(market_price)
        modified_duration = duration_metrics['modified_duration']
        
        coupon_rate = self.market_data['bond']['coupon']
        years = self.market_data['bond']['years_to_maturity']
        swap_rate = self.pricer._get_risk_free_rate(years)  # Proxy
        
        asw_spread = ((par_value - market_price) / modified_duration / par_value 
                      + coupon_rate - swap_rate)
        
        return asw_spread * 10000  # Convert to bps
    
    def analyze(self, reference_cds_tenor: Optional[float] = None) -> Dict:
        """
        Perform comprehensive basis analysis.
        
        Args:
            reference_cds_tenor: CDS tenor to use for basis calc (uses closest if None)
            
        Returns:
            Dictionary containing analysis results
        """
        # Calculate Z-spread
        z_spread = self.calculate_z_spread()
        z_spread_bps = z_spread * 10000
        
        # Find appropriate CDS tenor to compare
        bond_maturity = self.market_data['bond']['years_to_maturity']
        
        if reference_cds_tenor is None:
            # Use closest CDS tenor to bond maturity
            cds_tenors = list(self.market_data['cds_curve'].keys())
            reference_cds_tenor = min(cds_tenors, key=lambda x: abs(x - bond_maturity))
        
        cds_spread = self.market_data['cds_curve'].get(reference_cds_tenor, 0)
        
        # Calculate basis
        basis = cds_spread - z_spread_bps
        
        # Determine trading signal
        if basis < -20:
            trade_signal = "Strong Negative Basis → Long Bond/Buy CDS Protection"
            trade_rationale = "Bond is cheap relative to CDS. Potential arbitrage."
        elif basis < 0:
            trade_signal = "Negative Basis → Long Bond/Buy CDS (Moderate)"
            trade_rationale = "Bond slightly cheap vs CDS."
        elif basis > 20:
            trade_signal = "Strong Positive Basis → Short Bond/Sell CDS Protection"
            trade_rationale = "Bond is rich relative to CDS. Potential arbitrage."
        elif basis > 0:
            trade_signal = "Positive Basis → Short Bond/Sell CDS (Moderate)"
            trade_rationale = "Bond slightly rich vs CDS."
        else:
            trade_signal = "Neutral Basis → No Clear Trade"
            trade_rationale = "Bond and CDS are fairly priced relative to each other."
        
        # Additional metrics
        synthetic_price, _ = self.pricer.calculate_synthetic_price()
        market_price = self.market_data['bond']['price']
        price_diff = market_price - synthetic_price
        
        asw_spread = self.calculate_asset_swap_spread()
        
        results = {
            'Z_Spread_bps': round(z_spread_bps, 2),
            'CDS_Spread_bps': cds_spread,
            'CDS_Tenor': reference_cds_tenor,
            'Basis_bps': round(basis, 2),
            'Trade_Signal': trade_signal,
            'Trade_Rationale': trade_rationale,
            'Market_Price': market_price,
            'Synthetic_Price': round(synthetic_price, 4),
            'Price_Difference': round(price_diff, 4),
            'Asset_Swap_Spread_bps': round(asw_spread, 2),
            'Bond_Maturity': bond_maturity
        }
        
        logger.info(f"Basis analysis complete: {basis:.2f} bps ({trade_signal})")
        
        return results
    
    def generate_report(self) -> pd.DataFrame:
        """
        Generate detailed basis analysis report.
        
        Returns:
            DataFrame with comprehensive metrics
        """
        analysis = self.analyze()
        
        report_data = []
        
        # Market Data Section
        report_data.append({
            'Category': 'Market Data',
            'Metric': 'Bond Price',
            'Value': f"${analysis['Market_Price']:.2f}",
            'Unit': 'USD'
        })
        
        report_data.append({
            'Category': 'Market Data',
            'Metric': f"{analysis['CDS_Tenor']}Y CDS Spread",
            'Value': f"{analysis['CDS_Spread_bps']:.1f}",
            'Unit': 'bps'
        })
        
        # Calculated Spreads
        report_data.append({
            'Category': 'Credit Spreads',
            'Metric': 'Z-Spread',
            'Value': f"{analysis['Z_Spread_bps']:.2f}",
            'Unit': 'bps'
        })
        
        report_data.append({
            'Category': 'Credit Spreads',
            'Metric': 'Asset Swap Spread',
            'Value': f"{analysis['Asset_Swap_Spread_bps']:.2f}",
            'Unit': 'bps'
        })
        
        # Basis Analysis
        report_data.append({
            'Category': 'Basis Analysis',
            'Metric': 'CDS-Bond Basis',
            'Value': f"{analysis['Basis_bps']:.2f}",
            'Unit': 'bps'
        })
        
        report_data.append({
            'Category': 'Basis Analysis',
            'Metric': 'Synthetic Price',
            'Value': f"${analysis['Synthetic_Price']:.2f}",
            'Unit': 'USD'
        })
        
        report_data.append({
            'Category': 'Basis Analysis',
            'Metric': 'Price Difference',
            'Value': f"{analysis['Price_Difference']:.2f}",
            'Unit': 'points'
        })
        
        # Trading Recommendation
        report_data.append({
            'Category': 'Trading',
            'Metric': 'Signal',
            'Value': analysis['Trade_Signal'],
            'Unit': ''
        })
        
        df_report = pd.DataFrame(report_data)
        
        return df_report
    
    def stress_test_basis(
        self, 
        spread_shocks: list = None
    ) -> pd.DataFrame:
        """
        Stress test the basis under different spread scenarios.
        
        Args:
            spread_shocks: List of spread changes to test (in bps)
            
        Returns:
            DataFrame with stress test results
        """
        if spread_shocks is None:
            spread_shocks = [-50, -25, 0, 25, 50, 100]
        
        results = []
        base_analysis = self.analyze()
        base_cds = base_analysis['CDS_Spread_bps']
        
        for shock in spread_shocks:
            # Temporarily shock CDS curve
            original_curve = self.market_data['cds_curve'].copy()
            
            for tenor in self.market_data['cds_curve']:
                self.market_data['cds_curve'][tenor] = base_cds + shock
            
            # Recalculate basis
            shocked_analysis = self.analyze()
            
            results.append({
                'CDS_Shock_bps': shock,
                'New_CDS_Spread': base_cds + shock,
                'Z_Spread_bps': shocked_analysis['Z_Spread_bps'],
                'Basis_bps': shocked_analysis['Basis_bps'],
                'Trade_Signal': shocked_analysis['Trade_Signal']
            })
            
            # Restore original curve
            self.market_data['cds_curve'] = original_curve
        
        return pd.DataFrame(results)
