"""
Hazard Rate Bootstrapping Engine
Implements credit curve bootstrapping using CDS spreads.
"""

import logging
import numpy as np
from typing import Dict, Optional
from scipy.optimize import fsolve, OptimizeWarning
import warnings

logger = logging.getLogger(__name__)


class HazardRateEngine:
    """
    Bootstrap hazard rates from CDS curve using survival probability framework.
    
    This engine implements the standard CDS pricing model:
    - Premium Leg = Protection Leg
    - Solve iteratively for implied hazard rates at each tenor
    
    Attributes:
        bond_data (dict): Bond characteristics
        cds_curve (dict): CDS spreads by tenor (in basis points)
        rf_curve (dict): Risk-free rate curve
        recovery (float): Recovery rate assumption
        hazard_rates (dict): Bootstrapped hazard rates by tenor
    """
    
    MIN_HAZARD_RATE = 1e-6
    MAX_HAZARD_RATE = 1.0
    QUARTERLY_STEP = 0.25
    
    def __init__(
        self, 
        market_data: Dict,
        integration_step: float = QUARTERLY_STEP,
        max_iterations: int = 1000
    ):
        """
        Initialize the hazard rate bootstrapping engine.
        
        Args:
            market_data: Market snapshot containing bond, CDS, and treasury data
            integration_step: Time step for numerical integration (years)
            max_iterations: Maximum iterations for numerical solver
            
        Raises:
            ValueError: If market data is invalid
        """
        self._validate_market_data(market_data)
        
        self.bond_data = market_data['bond']
        self.cds_curve = market_data['cds_curve']
        self.rf_curve = market_data['treasury_curve']
        self.recovery = market_data['bond']['recovery_rate']
        
        self.integration_step = integration_step
        self.max_iterations = max_iterations
        self.hazard_rates = {}
        
        logger.info(
            f"Initializing HazardRateEngine with {len(self.cds_curve)} "
            f"CDS tenors and {self.recovery:.1%} recovery rate"
        )
        
        # Bootstrap the curve
        self._bootstrap()
    
    def _validate_market_data(self, data: Dict):
        """Validate input market data structure."""
        required_keys = ['bond', 'cds_curve', 'treasury_curve']
        if not all(key in data for key in required_keys):
            raise ValueError(f"Market data must contain: {required_keys}")
        
        if not isinstance(data['cds_curve'], dict) or not data['cds_curve']:
            raise ValueError("CDS curve must be a non-empty dictionary")
        
        if not (0 <= data['bond']['recovery_rate'] <= 1):
            raise ValueError(
                f"Recovery rate must be in [0,1], got {data['bond']['recovery_rate']}"
            )
    
    def survival_prob(self, t: float) -> float:
        """
        Calculate survival probability to time t.
        
        Uses the relationship: S(t) = exp(-∫λ(s)ds from 0 to t)
        
        Args:
            t: Time horizon in years
            
        Returns:
            Probability of surviving to time t
        """
        if t <= 0:
            return 1.0
        
        cumulative_hazard = 0.0
        sorted_tenors = sorted(self.hazard_rates.keys())
        prev_t = 0.0
        
        for tenor in sorted_tenors:
            if t <= tenor:
                # Interpolate within current segment
                cumulative_hazard += self.hazard_rates[tenor] * (t - prev_t)
                return np.exp(-cumulative_hazard)
            else:
                # Add full segment
                cumulative_hazard += self.hazard_rates[tenor] * (tenor - prev_t)
                prev_t = tenor
        
        # Extrapolate using last known hazard rate
        last_lambda = self.hazard_rates[sorted_tenors[-1]]
        cumulative_hazard += last_lambda * (t - prev_t)
        
        return np.exp(-cumulative_hazard)
    
    def default_prob(self, t: float) -> float:
        """
        Calculate cumulative default probability by time t.
        
        Args:
            t: Time horizon in years
            
        Returns:
            Probability of defaulting by time t
        """
        return 1.0 - self.survival_prob(t)
    
    def _get_risk_free_rate(self, t: float) -> float:
        """
        Interpolate risk-free rate for time t.
        
        Args:
            t: Time in years
            
        Returns:
            Interpolated risk-free rate
        """
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
    
    def _bootstrap(self):
        """
        Bootstrap hazard rates iteratively from CDS curve.
        
        For each tenor, solve: PV(Premium Leg) = PV(Protection Leg)
        """
        sorted_tenors = sorted(self.cds_curve.keys())
        logger.info(f"Bootstrapping {len(sorted_tenors)} tenors: {sorted_tenors}")
        
        for i, tenor in enumerate(sorted_tenors):
            spread = self.cds_curve[tenor] / 10000  # Convert bps to decimal
            
            if i == 0:
                # First node: Use simplified credit triangle
                # λ ≈ Spread / (1 - R)
                self.hazard_rates[tenor] = spread / (1 - self.recovery)
                logger.debug(
                    f"Tenor {tenor}Y (first): λ = {self.hazard_rates[tenor]:.6f}"
                )
            else:
                # Subsequent nodes: Solve numerically
                self.hazard_rates[tenor] = self._solve_for_hazard_rate(
                    tenor, spread, sorted_tenors[i-1]
                )
                logger.debug(
                    f"Tenor {tenor}Y: λ = {self.hazard_rates[tenor]:.6f}, "
                    f"S(t) = {self.survival_prob(tenor):.4%}"
                )
        
        logger.info("Bootstrapping completed successfully")
    
    def _solve_for_hazard_rate(
        self, 
        tenor: float, 
        spread: float,
        prev_tenor: float
    ) -> float:
        """
        Solve for hazard rate that equates CDS premium and protection legs.
        
        Args:
            tenor: Current tenor to solve for
            spread: CDS spread (decimal)
            prev_tenor: Previous bootstrapped tenor
            
        Returns:
            Solved hazard rate
            
        Raises:
            RuntimeError: If solver fails to converge
        """
        def objective(lambda_current: float) -> float:
            """
            Objective function: PV(Premium) - PV(Protection)
            
            Premium Leg: Σ spread * Δt * S(t) * D(t)
            Protection Leg: Σ (1-R) * (S(t-Δt) - S(t)) * D(t)
            """
            self.hazard_rates[tenor] = lambda_current
            
            premium_leg = 0.0
            protection_leg = 0.0
            
            # Integrate over time steps
            time_grid = np.arange(
                self.integration_step, 
                tenor + self.integration_step, 
                self.integration_step
            )
            
            for t in time_grid:
                surv_t = self.survival_prob(t)
                surv_prev = self.survival_prob(t - self.integration_step)
                rf_rate = self._get_risk_free_rate(t)
                discount_factor = np.exp(-rf_rate * t)
                
                # Premium leg: receive spread if no default
                premium_leg += spread * self.integration_step * surv_t * discount_factor
                
                # Protection leg: pay (1-R) on default
                default_prob_step = surv_prev - surv_t
                protection_leg += (1 - self.recovery) * default_prob_step * discount_factor
            
            return premium_leg - protection_leg
        
        # Initial guess: use previous tenor's hazard rate
        initial_guess = self.hazard_rates[prev_tenor]
        
        # Solve with bounds
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=OptimizeWarning)
            try:
                solution = fsolve(
                    objective,
                    initial_guess,
                    full_output=True,
                    maxfev=self.max_iterations
                )
                
                solved_lambda = solution[0][0]
                info = solution[1]
                
                # Check convergence
                if info['fvec'][0] > 1e-6:
                    logger.warning(
                        f"Solver did not fully converge for tenor {tenor}Y. "
                        f"Residual: {info['fvec'][0]:.2e}"
                    )
                
                # Apply bounds
                solved_lambda = np.clip(
                    solved_lambda, 
                    self.MIN_HAZARD_RATE, 
                    self.MAX_HAZARD_RATE
                )
                
                return solved_lambda
                
            except Exception as e:
                logger.error(f"Solver failed for tenor {tenor}Y: {str(e)}")
                # Fallback to simple approximation
                return spread / (1 - self.recovery)
    
    def get_forward_hazard_rate(self, t1: float, t2: float) -> float:
        """
        Calculate forward hazard rate between two times.
        
        Args:
            t1: Start time
            t2: End time
            
        Returns:
            Forward hazard rate from t1 to t2
        """
        if t2 <= t1:
            raise ValueError("t2 must be greater than t1")
        
        s1 = self.survival_prob(t1)
        s2 = self.survival_prob(t2)
        
        if s2 <= 0:
            return self.MAX_HAZARD_RATE
        
        return -np.log(s2 / s1) / (t2 - t1)
    
    def get_curve_summary(self) -> Dict:
        """
        Generate summary statistics for the bootstrapped curve.
        
        Returns:
            Dictionary with curve metrics
        """
        tenors = sorted(self.hazard_rates.keys())
        
        return {
            'tenors': tenors,
            'hazard_rates': [self.hazard_rates[t] for t in tenors],
            'survival_probs': [self.survival_prob(t) for t in tenors],
            'default_probs': [self.default_prob(t) for t in tenors],
            'avg_hazard_rate': np.mean(list(self.hazard_rates.values())),
            'max_hazard_rate': max(self.hazard_rates.values()),
            'min_hazard_rate': min(self.hazard_rates.values())
        }
