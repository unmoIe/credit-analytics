# Quick Start Guide

Get started with the Credit Analytics Platform in 5 minutes.

## Installation

```bash
# Clone or download the project
cd credit_analytics

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## First Run

```bash
# Run basic analysis
python main.py --ticker INTC --mode dummy

# This will:
# 1. Load market data for Intel
# 2. Bootstrap hazard rates from CDS curve
# 3. Price bond synthetically
# 4. Calculate CDS-bond basis
# 5. Generate visualizations
# 6. Save results to ./output/
```

## Expected Output

You should see output like this:

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
  ...

============================================================
ANALYSIS SUMMARY
============================================================
Ticker:          INTC
Market Price:    $94.5000
Synthetic Price: $94.8234
Basis:           +1.27 bps
Trade Signal:    Neutral Basis → No Clear Trade

Outputs saved to: ./output
```

## Explore Results

Navigate to the `output/` directory to find:

- **PNG files**: Credit curves, basis analysis, survival curves, dashboards
- **CSV file**: Detailed basis analysis report
- **LOG file**: Complete execution log

## Try Examples

```bash
# Run comprehensive examples
python examples.py

# This demonstrates:
# - Basic workflow
# - Risk metrics (duration, DV01, convexity)
# - Survival probability analysis
# - Basis trading signals
# - Stress testing
# - Visualization generation
```

## Using as a Library

```python
from src.data_provider import CreditDataProvider
from src.hazard_rate import HazardRateEngine
from src.pricing import SyntheticPricer
from src.basis_analysis import BasisAnalyzer

# Get market data
provider = CreditDataProvider(mode='dummy')
data = provider.get_market_snapshot('INTC')

# Bootstrap hazard rates
engine = HazardRateEngine(data)

# Price bond
pricer = SyntheticPricer(engine, data)
price, cf = pricer.calculate_synthetic_price()

# Analyze basis
analyzer = BasisAnalyzer(data, pricer)
results = analyzer.analyze()

print(f"Basis: {results['Basis_bps']} bps")
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Next Steps

1. **Read the full README.md** for detailed documentation
2. **Explore the code** in the `src/` directory
3. **Customize analysis** by modifying parameters
4. **Integrate live data** using the data provider interface
5. **Add new analytics** by extending the classes

## Common Commands

```bash
# Verbose output
python main.py --verbose

# Different ticker
python main.py --ticker AAPL

# Custom output directory
python main.py --output ./my_reports

# Skip visualizations (faster)
python main.py --no-visualize

# Get help
python main.py --help
```

## Troubleshooting

**Import errors:**
```bash
# Make sure you're in the credit_analytics directory
# and virtual environment is activated
pip install -r requirements.txt
```

**No output files:**
```bash
# Check that output directory has write permissions
ls -la ./output/

# Try specifying a different output directory
python main.py --output ~/credit_reports
```

**Plotting errors:**
```bash
# Install matplotlib backend
pip install PyQt5
# Or use Agg backend (no display)
export MPLBACKEND=Agg
```

## Support

- Check **README.md** for full documentation
- Review **examples.py** for usage patterns
- Examine **tests/** for code examples
- Open an issue on GitHub for bugs

Happy analyzing! 🚀
