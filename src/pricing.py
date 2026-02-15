"""
Synthetic Bond Pricing Module
Values bonds using credit-adjusted cash flows from CDS-implied hazard rates.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class SyntheticPricer:
    """
    Price bonds synthetically using CDS-implied credit curves.
    
    Methodology:
    1. Generate bond cash flow schedule
    2. Apply survival probabilities to each cash flow
    3. Discount at risk-free rate
    4. Sum to get synthetic price
    
    Attributes:
        engine: HazardRateEngine instance
        bond_data: Bond characteristics
        rf: Risk-free rate
        face_value: Bond face value
    """
    
    def __init__(self, engine, market_data: Dict):
        """
        Initialize the synthetic pricer.
        
        Args:
            engine: HazardRateEngine with bootstrapped hazard rates
            market_data: Market snapshot containing bond and treasury data
        """
        self.engine = engine
        self.bond_data = market_data['bond']
        self.rf_curve = market_data['treasury_curve']
        self.face_value = market_data['bond'].get('face_value', 100.0)
        
        logger.info(
            f"Initialized SyntheticPricer for {self.bond_data.get('name', 'Bond')} "
            f"with {self.bond_data['years_to_maturity']:.1f}Y maturity"
        )
    
    def _get_risk_free_rate(self, t: float) -> float:
        """Interpolate risk-free rate for time t."""
        sorted_tenors = sorted(self.rf_curve.keys())
        
        if t <= sorted_tenors[0]:
            return self.rf_curve[sorted_tenors[0]]
        if t >= sorted_tenors[-1]:
            return self.rf_curve[sorted_tenors[-1]]
        
        # Linear interpolation
        for i in range(len(sorted_tenors) - 1):
            t1, t2 = sorted_tenors[i], sorted_tenors[i + 1]
            if t1 <= t <= t2:
                r1, r2 = self.rf_curve[t1], self.rf_curve[t2]
                return r1 + (r2 - r1) * (t - t1) / (t2 - t1)
        
        return self.rf_curve[sorted_tenors[-1]]
    
    def calculate_synthetic_price(
        self, 
        include_accrued: bool = False
    ) -> Tuple[float, pd.DataFrame]:
        """
        Calculate synthetic bond price using CDS-implied survival probabilities.
        
        Args:
            include_accrued: Whether to include accrued interest
            
        Returns:
            Tuple of (synthetic_price, cash_flow_schedule_dataframe)
        """
        coupon_rate = self.bond_data['coupon']
        years = self.bond_data['years_to_maturity']
        frequency = self.bond_data.get('frequency', 2)  # Default semi-annual
        
        # Generate cash flow schedule
        payment_interval = 1.0 / frequency
        times = np.arange(payment_interval, years + payment_interval, payment_interval)
        
        coupon_payment = (coupon_rate / frequency) * self.face_value
        
        cash_flows = []
        total_pv = 0.0
        
        for t in times:
            is_maturity = np.isclose(t, times[-1])
            
            # Cash flow: coupon + principal (if maturity)
            payment = coupon_payment + (self.face_value if is_maturity else 0)
            
            # Risk-free discounting
            rf_rate = self._get_risk_free_rate(t)
            discount_factor = np.exp(-rf_rate * t)
            
            # Credit adjustment: survival probability
            survival_prob = self.engine.survival_prob(t)
            
            # Present value of this cash flow
            pv = payment * survival_prob * discount_factor
            total_pv += pv
            
            cash_flows.append({
                'Time': t,
                'Payment': payment,
                'Coupon': coupon_payment,
                'Principal': self.face_value if is_maturity else 0,
                'Risk_Free_Rate': rf_rate,
                'Discount_Factor': discount_factor,
                'Survival_Prob': survival_prob,
                'Default_Prob': 1 - survival_prob,
                'PV': pv
            })
        
        df_cash_flows = pd.DataFrame(cash_flows)
        
        # Add accrued interest if requested
        if include_accrued:
            accrued = self._calculate_accrued_interest()
            total_pv += accrued
            logger.debug(f"Added accrued interest: {accrued:.4f}")
        
        logger.info(f"Synthetic price calculated: {total_pv:.4f}")
        
        return total_pv, df_cash_flows
    
    def _calculate_accrued_interest(self) -> float:
        """
        Calculate accrued interest since last coupon date.
        
        Returns:
            Accrued interest amount
        """
        # Simplified: assume we're at a coupon date
        # In production, would calculate days since last payment
        return 0.0
    
    def calculate_duration(self, price: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate duration metrics.
        
        Args:
            price: Bond price (uses synthetic if not provided)
            
        Returns:
            Dictionary with Macaulay and Modified duration
        """
        if price is None:
            price, _ = self.calculate_synthetic_price()
        
        coupon_rate = self.bond_data['coupon']
        years = self.bond_data['years_to_maturity']
        frequency = self.bond_data.get('frequency', 2)
        
        payment_interval = 1.0 / frequency
        times = np.arange(payment_interval, years + payment_interval, payment_interval)
        
        coupon_payment = (coupon_rate / frequency) * self.face_value
        
        weighted_pv_sum = 0.0
        pv_sum = 0.0
        
        for t in times:
            is_maturity = np.isclose(t, times[-1])
            payment = coupon_payment + (self.face_value if is_maturity else 0)
            
            rf_rate = self._get_risk_free_rate(t)
            discount_factor = np.exp(-rf_rate * t)
            survival_prob = self.engine.survival_prob(t)
            
            pv = payment * survival_prob * discount_factor
            weighted_pv_sum += t * pv
            pv_sum += pv
        
        macaulay_duration = weighted_pv_sum / pv_sum if pv_sum > 0 else 0
        
        # Modified duration: Macaulay / (1 + y/n)
        ytm = self.calculate_ytm(price)
        modified_duration = macaulay_duration / (1 + ytm / frequency)
        
        return {
            'macaulay_duration': macaulay_duration,
            'modified_duration': modified_duration,
            'dv01': modified_duration * price / 10000  # Dollar value of 1bp
        }
    
    def calculate_ytm(self, price: float) -> float:
        """
        Calculate yield-to-maturity using Newton-Raphson.
        
        Args:
            price: Current bond price
            
        Returns:
            Yield to maturity (decimal)
        """
        coupon_rate = self.bond_data['coupon']
        years = self.bond_data['years_to_maturity']
        frequency = self.bond_data.get('frequency', 2)
        
        payment_interval = 1.0 / frequency
        times = np.arange(payment_interval, years + payment_interval, payment_interval)
        coupon_payment = (coupon_rate / frequency) * self.face_value
        
        def bond_price_at_ytm(ytm):
            pv = 0
            for t in times:
                is_maturity = np.isclose(t, times[-1])
                payment = coupon_payment + (self.face_value if is_maturity else 0)
                pv += payment / ((1 + ytm / frequency) ** (t * frequency))
            return pv
        
        # Newton-Raphson
        ytm_guess = coupon_rate  # Initial guess
        tolerance = 1e-6
        max_iter = 100
        
        for _ in range(max_iter):
            price_calc = bond_price_at_ytm(ytm_guess)
            
            if abs(price_calc - price) < tolerance:
                return ytm_guess
            
            # Numerical derivative
            epsilon = 1e-6
            derivative = (bond_price_at_ytm(ytm_guess + epsilon) - price_calc) / epsilon
            
            if abs(derivative) < 1e-10:
                break
            
            ytm_guess = ytm_guess - (price_calc - price) / derivative
        
        logger.warning("YTM calculation did not converge, returning approximation")
        return ytm_guess
    
    def calculate_convexity(self, price: Optional[float] = None) -> float:
        """
        Calculate bond convexity.
        
        Args:
            price: Bond price (uses synthetic if not provided)
            
        Returns:
            Convexity value
        """
        if price is None:
            price, _ = self.calculate_synthetic_price()
        
        coupon_rate = self.bond_data['coupon']
        years = self.bond_data['years_to_maturity']
        frequency = self.bond_data.get('frequency', 2)
        
        payment_interval = 1.0 / frequency
        times = np.arange(payment_interval, years + payment_interval, payment_interval)
        coupon_payment = (coupon_rate / frequency) * self.face_value
        
        convexity_sum = 0.0
        
        for t in times:
            is_maturity = np.isclose(t, times[-1])
            payment = coupon_payment + (self.face_value if is_maturity else 0)
            
            rf_rate = self._get_risk_free_rate(t)
            discount_factor = np.exp(-rf_rate * t)
            survival_prob = self.engine.survival_prob(t)
            
            pv = payment * survival_prob * discount_factor
            convexity_sum += t * (t + payment_interval) * pv
        
        convexity = convexity_sum / (price * frequency ** 2) if price > 0 else 0
        
        return convexity
    
    def calculate_credit_spread(self, market_price: float) -> float:
        """
        Calculate implied credit spread (spread over Treasuries).
        
        Args:
            market_price: Observed market price
            
        Returns:
            Credit spread in basis points
        """
        ytm = self.calculate_ytm(market_price)
        
        # Average risk-free rate weighted by duration
        tenor = self.bond_data['years_to_maturity']
        rf_rate = self._get_risk_free_rate(tenor)
        
        credit_spread_bps = (ytm - rf_rate) * 10000
        
        return credit_spread_bps
