import pandas as pd
import yfinance as yf
from datetime import datetime
import numpy as np
from scipy.optimize import fsolve,brentq

class CreditDataProvider:
    def __init__(self, mode="dummy"):
        self.mode = mode

    def get_market_snapshot(self):
        if self.mode == "dummy":
            return self._get_dummy_data()
        else:
            return self._get_live_data()

    def _get_dummy_data(self):
        return {
            "bond": {
                "name": "INTC 5.200% 02/10/2033",
                "price": 94.50,
                "coupon": 0.052,
                "years_to_maturity": 7.0, # As of Feb 2026
                "recovery_rate": 0.40
            },
            "cds_curve": {
                1.0: 80,   # 1Y Spread in bps
                3.0: 110,  # 3Y
                5.0: 140,  # 5Y (The Benchmark)
                10.0: 180  # 10Y (Foundry 2030 Risk)
            },
            "treasury_curve": {
                1.0: 0.0480, # 4.80%
                5.0: 0.0440, # 4.40%
                10.0: 0.0425 # 4.25%
            }
        }

    def _get_live_data(self):
        """Placeholder for live API integration (e.g., yfinance for Benchmarks)"""
        # Example: Fetching actual 10Y Treasury proxy
        tnx = yf.Ticker("^TNX")
        live_rf = tnx.history(period="1d")['Close'].iloc[-1] / 100
        
        # Note: Bond and CDS live data usually requires a Bloomberg/Refinitiv API
        # or a custom scraper for FINRA TRACE.
        return {
            "bond": {"ticker": "INTC", "coupon": 0.052, "price": 94.50}, # Static for now
            "cds": {"5Y": 140, "10Y": 180},
            "rf_10y": live_rf
        }
    
class HazardRateEngine:
    def __init__(self, market_data):
        self.bond_data = market_data['bond']
        self.cds_curve = market_data['cds_curve']
        self.rf_curve = market_data['treasury_curve']
        self.recovery = market_data['bond']['recovery_rate']
        
        # This dictionary will store our bootstrapped hazard rates
        # Key: Tenor, Value: Lambda (hazard rate) for that interval
        self.hazard_rates = {} 
        self._bootstrap()

    def survival_prob(self, t):
        """Returns the probability of surviving up to time t: e^(-sum(lambda_i * delta_t_i))"""
        if t <= 0: return 1.0
        
        cumulative_hazard = 0
        sorted_tenors = sorted(self.hazard_rates.keys())
        prev_t = 0
        
        for tenor in sorted_tenors:
            if t <= tenor:
                cumulative_hazard += self.hazard_rates[tenor] * (t - prev_t)
                return np.exp(-cumulative_hazard)
            else:
                cumulative_hazard += self.hazard_rates[tenor] * (tenor - prev_t)
                prev_t = tenor
        
        # Extrapolate using the last known hazard rate
        cumulative_hazard += self.hazard_rates[sorted_tenors[-1]] * (t - prev_t)
        return np.exp(-cumulative_hazard)

    def _bootstrap(self):
        """Iteratively solves for hazard rates at each tenor point."""
        sorted_tenors = sorted(self.cds_curve.keys())
        
        for i, T in enumerate(sorted_tenors):
            spread = self.cds_curve[T] / 10000 # Convert bps to decimal
            
            # Simple approximation for T=1, use numerical solver for subsequent nodes
            if i == 0:
                # Basic Credit Triangle: lambda = Spread / (1 - R)
                self.hazard_rates[T] = spread / (1 - self.recovery)
            else:
                # Solve for lambda_i such that PV(Premium) = PV(Protection)
                # We use the previous nodes' survival probabilities as constants
                def objective_function(current_lambda):
                    self.hazard_rates[T] = current_lambda
                    
                    # Simplify: Use annual steps for the summation
                    # In a real desk, you'd use quarterly steps matching CDS payment dates
                    premium_leg = 0
                    protection_leg = 0
                    dt = 0.25 # Quarterly steps
                    
                    for time_step in np.arange(dt, T + dt, dt):
                        surv = self.survival_prob(time_step)
                        prev_surv = self.survival_prob(time_step - dt)
                        df = np.exp(-self.rf_curve.get(10.0, 0.04) * time_step) # Use 10Y Rf as proxy
                        
                        premium_leg += spread * dt * surv * df
                        protection_leg += (1 - self.recovery) * (prev_surv - surv) * df
                    
                    return premium_leg - protection_leg

                # Find the root (where the difference is zero)
                initial_guess = self.hazard_rates[sorted_tenors[i-1]]
                solved_lambda = fsolve(objective_function, initial_guess)[0]
                self.hazard_rates[T] = solved_lambda

class SyntheticPricer:
    def __init__(self, engine, market_data):
        self.engine = engine  # From Step 2
        self.bond_data = market_data['bond']
        self.rf = market_data['treasury_curve'].get(10.0, 0.0425)
        self.face_value = 100.0

    def calculate_synthetic_price(self):
        """
        Prices the bond by weighting each cash flow by its survival probability.
        """
        coupon_rate = self.bond_data['coupon']
        years = self.bond_data['years_to_maturity']
        freq = 2 # Semi-annual coupons
        
        # 1. Generate Cash Flow Schedule
        times = np.arange(0.5, years + 0.5, 0.5)
        coupon_payment = (coupon_rate / freq) * self.face_value
        
        cash_flows = []
        for t in times:
            is_last = (t == times[-1])
            payment = coupon_payment + (self.face_value if is_last else 0)
            
            # 2. Risk-Free Discounting: D(t)
            discount_factor = np.exp(-self.rf * t)
            
            # 3. Credit Weighting: P(t)
            survival_prob = self.engine.survival_prob(t)
            
            # 4. PV = Payment * P(t) * D(t)
            present_value = payment * survival_prob * discount_factor
            
            cash_flows.append({
                "Time": t,
                "Payment": payment,
                "Survival_Prob": f"{survival_prob:.2%}",
                "PV": present_value
            })
            
        df_cf = pd.DataFrame(cash_flows)
        synthetic_price = df_cf['PV'].sum()
        
        return synthetic_price, df_cf

class BasisAnalyzer:
    def __init__(self, market_data, pricer):
        self.market_data = market_data
        self.pricer = pricer # Inherit CF logic from Step 3

    def calculate_z_spread(self):
        """
        Solves for the Z-spread: The 'z' that equates Bond PV to Market Price.
        """
        target_price = self.market_data['bond']['price']
        coupon_rate = self.market_data['bond']['coupon']
        years = self.market_data['bond']['years_to_maturity']
        rf = self.market_data['treasury_curve'].get(10.0, 0.0425)
        
        # Define the objective function for the solver
        def price_error(z):
            times = np.arange(0.5, years + 0.5, 0.5)
            pv = 0
            for t in times:
                is_last = (t == times[-1])
                cash_flow = (coupon_rate / 2 * 100) + (100 if is_last else 0)
                # Discount by (Risk Free + Z-Spread)
                pv += cash_flow * np.exp(-(rf + z) * t)
            return pv - target_price

        # Solve for z (expecting a spread between 0% and 10%)
        z_solved = brentq(price_error, 0, 0.1)
        return z_solved

    def analyze(self):
        z_spread = self.calculate_z_spread() * 10000 # Convert to bps
        cds_10y = self.market_data['cds_curve'][10.0]
        
        basis = cds_10y - z_spread
        
        return {
            "Z-Spread (bps)": round(z_spread, 1),
            "10Y CDS (bps)": cds_10y,
            "Basis (bps)": round(basis, 1),
            "Trade Signal": "Negative Basis (Long Bond/Buy CDS)" if basis < 0 else "Positive Basis"
        }