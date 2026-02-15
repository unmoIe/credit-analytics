# Credit Analytics Platform

**Production-ready credit risk analysis and CDS-Bond basis trading system**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

A professional-grade quantitative platform for credit market analysis, implementing industry-standard models for:

- **CDS Curve Bootstrapping**: Hazard rate extraction from credit default swap spreads
- **Synthetic Bond Pricing**: Credit-adjusted valuation using survival probabilities
- **Basis Analysis**: Relative value identification between bond and CDS markets
- **Risk Metrics**: Duration, convexity, DV01, and credit spread calculations

### Key Features

✅ **Production-Ready Architecture**
- Modular design with clear separation of concerns
- Comprehensive error handling and logging
- Extensible data provider interface (dummy, live, cached)
- Full unit test coverage

✅ **Industry-Standard Models**
- Bootstrap hazard rates from CDS term structure
- Risky discounting with survival probabilities
- Z-spread and asset swap spread calculation
- Basis trading signal generation

✅ **Professional Visualizations**
- Credit curve analysis
- CDS-Bond basis charts
- Cash flow waterfalls
- Survival/default probability curves
- Comprehensive dashboards

✅ **Flexible Data Sources**
- Dummy mode for testing and demonstration
- Live market data integration (yfinance, Bloomberg API ready)
- Caching layer with configurable TTL

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/credit-analytics.git
cd credit-analytics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Requirements

- Python 3.8 or higher
- pip (package installer)
- Virtual environment (recommended)

## Usage

### Command Line Interface

```bash
# Basic usage with dummy data
python main.py --ticker INTC --mode dummy

# Verbose output for debugging
python main.py --ticker INTC --mode dummy --verbose

# Custom output directory
python main.py --ticker AAPL --output ./reports/apple

# Skip visualizations for faster execution
python main.py --ticker MSFT --no-visualize

# Use live market data (requires API configuration)
python main.py --ticker TSLA --mode live
```

### Python API

```python
from src.data_provider import CreditDataProvider
from src.hazard_rate import HazardRateEngine
from src.pricing import SyntheticPricer
from src.basis_analysis import BasisAnalyzer
from src.visualizations import CreditVisualizer

# Initialize data provider
provider = CreditDataProvider(mode='dummy')
market_data = provider.get_market_snapshot('INTC')

# Bootstrap hazard rates
engine = HazardRateEngine(market_data)

# Price bond synthetically
pricer = SyntheticPricer(engine, market_data)
synthetic_price, cash_flows = pricer.calculate_synthetic_price()

# Analyze basis
analyzer = BasisAnalyzer(market_data, pricer)
results = analyzer.analyze()

print(f"Basis: {results['Basis_bps']} bps")
print(f"Signal: {results['Trade_Signal']}")

# Generate visualizations
viz = CreditVisualizer(output_dir='./output')
viz.plot_basis_analysis(market_data, results)
```

## Architecture

```
credit_analytics/
├── src/                          # Source code
│   ├── __init__.py              # Package initialization
│   ├── data_provider.py         # Market data acquisition
│   ├── hazard_rate.py           # CDS curve bootstrapping
│   ├── pricing.py               # Synthetic bond pricing
│   ├── basis_analysis.py        # Relative value analysis
│   └── visualizations.py        # Charts and dashboards
├── tests/                        # Unit tests
├── data/                         # Data storage
├── config/                       # Configuration files
├── docs/                         # Documentation
├── output/                       # Generated reports & charts
├── main.py                       # CLI entry point
├── requirements.txt              # Dependencies
├── setup.py                      # Package configuration
└── README.md                     # This file
```

## Methodology

### 1. Hazard Rate Bootstrapping

Extract credit risk from CDS spreads using the survival probability framework:

```
S(t) = exp(-∫λ(s)ds)  from 0 to t
```

Where λ is the hazard rate (instantaneous default probability).

For each CDS tenor, solve:
```
PV(Premium Leg) = PV(Protection Leg)
```

**Premium Leg**: Σ Spread × Δt × S(t) × D(t)
**Protection Leg**: Σ (1-R) × (S(t-Δt) - S(t)) × D(t)

### 2. Synthetic Pricing

Value bonds by applying survival probabilities to cash flows:

```
Price = Σ CF(t) × S(t) × D(t)
```

Where:
- CF(t) = Cash flow at time t
- S(t) = Survival probability to time t
- D(t) = Risk-free discount factor

### 3. Basis Analysis

**Basis = CDS Spread - Z-Spread**

- **Negative Basis**: Bond is cheap → Long bond, Buy CDS protection
- **Positive Basis**: Bond is rich → Short bond, Sell CDS protection

The Z-spread is solved numerically:
```
Market Price = Σ CF(t) × exp(-(RF(t) + Z) × t)
```

## Output Examples

### Console Output

```
============================================================
CREDIT ANALYTICS PLATFORM - Analysis Starting
============================================================
Ticker: INTC | Mode: dummy | Output: ./output

============================================================
STEP 1: Data Acquisition
============================================================
✓ Market data acquired successfully
  - Bond: INTC 5.200% 02/10/2033
  - Price: $94.50
  - CDS Tenors: [1.0, 3.0, 5.0, 7.0, 10.0]

============================================================
STEP 2: Hazard Rate Bootstrapping
============================================================
✓ Hazard rates bootstrapped
  - 1.0Y: λ=0.001333, S(t)=99.87%
  - 3.0Y: λ=0.001833, S(t)=99.45%
  - 5.0Y: λ=0.002333, S(t)=98.84%
  - 7.0Y: λ=0.002667, S(t)=98.16%
  - 10.0Y: λ=0.003000, S(t)=97.04%

============================================================
STEP 3: Synthetic Bond Pricing
============================================================
✓ Pricing completed
  - Market Price:    $94.5000
  - Synthetic Price: $94.8234
  - Difference:      -0.3234 points
  - Signal:          Bond is CHEAP (Buy)

============================================================
STEP 4: CDS-Bond Basis Analysis
============================================================
✓ Basis analysis completed
  - Z-Spread:   158.73 bps
  - CDS Spread: 160.0 bps (7.0Y)
  - Basis:      +1.27 bps
  - Signal:     Neutral Basis → No Clear Trade
```

### Generated Files

The platform generates the following outputs in the `./output` directory:

1. **credit_curve.png** - CDS term structure and hazard rates
2. **basis_analysis.png** - Bond vs CDS relative value chart
3. **cash_flow_waterfall.png** - Bond cash flow breakdown
4. **survival_curve.png** - Credit survival/default probabilities
5. **comprehensive_dashboard.png** - 4-panel overview
6. **{TICKER}_basis_report.csv** - Detailed metrics in CSV format
7. **analysis_YYYYMMDD_HHMMSS.log** - Execution log

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_hazard_rate.py -v
```

## Configuration

### Environment Variables

Create a `.env` file for API credentials:

```bash
# Bloomberg API
BLOOMBERG_API_KEY=your_key_here
BLOOMBERG_API_SECRET=your_secret_here

# Refinitiv/LSEG
REFINITIV_APP_KEY=your_app_key_here

# Cache settings
CACHE_TTL=3600
CACHE_DIR=/path/to/cache
```

### Logging Configuration

Adjust logging levels in `main.py`:

```python
setup_logging(log_level='DEBUG')  # For verbose output
setup_logging(log_level='INFO')   # For normal operation
setup_logging(log_level='WARNING') # For production
```

## Extending the Platform

### Adding New Data Sources

```python
# src/data_provider.py

class CreditDataProvider:
    def _get_bloomberg_data(self, ticker):
        """Implement Bloomberg API integration"""
        # Your Bloomberg API code here
        pass
```

### Custom Analytics

```python
from src.pricing import SyntheticPricer

class CustomPricer(SyntheticPricer):
    def calculate_convertible_bond_price(self):
        """Add convertible bond pricing"""
        # Your implementation
        pass
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest tests/`)
5. Format code with black (`black src/ tests/`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**For Educational and Research Purposes Only**

This software is provided for educational and research purposes. It is not intended for actual trading or investment decisions. The authors and contributors:

- Make no guarantees about accuracy or reliability
- Are not responsible for any financial losses
- Recommend consulting qualified professionals before making investment decisions
- Provide no warranty, express or implied

Always perform independent verification and consult with licensed financial professionals.

## References

### Academic Papers
- Duffie, D., & Singleton, K. J. (1999). "Modeling Term Structures of Defaultable Bonds"
- Hull, J., & White, A. (2000). "Valuing Credit Default Swaps I: No Counterparty Default Risk"
- O'Kane, D., & Turnbull, S. (2003). "Valuation of Credit Default Swaps"

### Industry Standards
- ISDA CDS Standard Model Documentation
- Bloomberg CDS Pricing Methodology
- Markit CDS Calculator Specification

### Books
- "Credit Derivatives Handbook" - J.P. Morgan
- "Modelling Single-name and Multi-name Credit Derivatives" - Dominic O'Kane
- "Credit Risk Modeling" - David Lando

## Contact

For questions, issues, or contributions:

- **GitHub Issues**: [github.com/yourusername/credit-analytics/issues](https://github.com/yourusername/credit-analytics/issues)
- **Email**: team@creditanalytics.com
- **Documentation**: [docs.creditanalytics.com](https://docs.creditanalytics.com)

---

**Built with ❤️ by the Credit Analytics Team**
