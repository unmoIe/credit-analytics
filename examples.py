"""
Example Usage Script
Demonstrates how to use the Credit Analytics Platform.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_provider import CreditDataProvider
from hazard_rate import HazardRateEngine
from pricing import SyntheticPricer
from basis_analysis import BasisAnalyzer
from visualizations import CreditVisualizer


def example_basic_analysis():
    """
    Example 1: Basic credit analysis workflow
    """
    print("="*60)
    print("EXAMPLE 1: Basic Credit Analysis")
    print("="*60)
    
    # Step 1: Get market data
    provider = CreditDataProvider(mode='dummy')
    market_data = provider.get_market_snapshot('INTC')
    
    print(f"\nBond: {market_data['bond']['name']}")
    print(f"Price: ${market_data['bond']['price']:.2f}")
    
    # Step 2: Bootstrap hazard rates
    engine = HazardRateEngine(market_data)
    
    print("\nHazard Rates:")
    for tenor, hazard in sorted(engine.hazard_rates.items()):
        print(f"  {tenor}Y: {hazard:.6f} ({hazard*10000:.2f} bps)")
    
    # Step 3: Price synthetically
    pricer = SyntheticPricer(engine, market_data)
    synthetic_price, cf_schedule = pricer.calculate_synthetic_price()
    
    print(f"\nSynthetic Price: ${synthetic_price:.4f}")
    print(f"Market Price: ${market_data['bond']['price']:.4f}")
    print(f"Difference: {market_data['bond']['price'] - synthetic_price:+.4f}")
    
    # Step 4: Basis analysis
    analyzer = BasisAnalyzer(market_data, pricer)
    results = analyzer.analyze()
    
    print(f"\nBasis Analysis:")
    print(f"  Z-Spread: {results['Z_Spread_bps']:.2f} bps")
    print(f"  CDS Spread: {results['CDS_Spread_bps']:.1f} bps")
    print(f"  Basis: {results['Basis_bps']:+.2f} bps")
    print(f"  Signal: {results['Trade_Signal']}")


def example_risk_metrics():
    """
    Example 2: Calculate risk metrics
    """
    print("\n\n" + "="*60)
    print("EXAMPLE 2: Risk Metrics Calculation")
    print("="*60)
    
    provider = CreditDataProvider(mode='dummy')
    market_data = provider.get_market_snapshot('INTC')
    engine = HazardRateEngine(market_data)
    pricer = SyntheticPricer(engine, market_data)
    
    market_price = market_data['bond']['price']
    
    # Duration metrics
    duration = pricer.calculate_duration(market_price)
    print(f"\nDuration Metrics:")
    print(f"  Macaulay Duration: {duration['macaulay_duration']:.2f} years")
    print(f"  Modified Duration: {duration['modified_duration']:.2f}")
    print(f"  DV01: ${duration['dv01']:.4f}")
    
    # YTM and spread
    ytm = pricer.calculate_ytm(market_price)
    credit_spread = pricer.calculate_credit_spread(market_price)
    
    print(f"\nYield Metrics:")
    print(f"  YTM: {ytm*100:.2f}%")
    print(f"  Credit Spread: {credit_spread:.2f} bps")
    
    # Convexity
    convexity = pricer.calculate_convexity(market_price)
    print(f"  Convexity: {convexity:.2f}")


def example_survival_analysis():
    """
    Example 3: Analyze survival probabilities
    """
    print("\n\n" + "="*60)
    print("EXAMPLE 3: Credit Survival Analysis")
    print("="*60)
    
    provider = CreditDataProvider(mode='dummy')
    market_data = provider.get_market_snapshot('INTC')
    engine = HazardRateEngine(market_data)
    
    print("\nSurvival Probabilities:")
    for year in [1, 2, 3, 5, 7, 10]:
        surv = engine.survival_prob(year)
        default = engine.default_prob(year)
        
        print(f"  Year {year:2d}: S(t)={surv:.2%}, PD={default:.2%}")
    
    # Forward default probabilities
    print("\nForward Default Probabilities:")
    periods = [(0, 1), (1, 3), (3, 5), (5, 10)]
    
    for t1, t2 in periods:
        s1 = engine.survival_prob(t1)
        s2 = engine.survival_prob(t2)
        forward_pd = (s1 - s2) / s1 if s1 > 0 else 0
        
        print(f"  Year {t1}-{t2}: {forward_pd:.2%}")


def example_basis_trading_signals():
    """
    Example 4: Generate basis trading signals
    """
    print("\n\n" + "="*60)
    print("EXAMPLE 4: Basis Trading Signals")
    print("="*60)
    
    provider = CreditDataProvider(mode='dummy')
    market_data = provider.get_market_snapshot('INTC')
    engine = HazardRateEngine(market_data)
    pricer = SyntheticPricer(engine, market_data)
    analyzer = BasisAnalyzer(market_data, pricer)
    
    # Generate detailed report
    report = analyzer.generate_report()
    
    print("\nDetailed Basis Report:")
    print(report.to_string(index=False))
    
    # Stress test
    print("\n\nBasis Stress Test:")
    stress_results = analyzer.stress_test_basis(
        spread_shocks=[-50, -25, 0, 25, 50]
    )
    
    print(stress_results.to_string(index=False))


def example_visualizations():
    """
    Example 5: Generate visualizations
    """
    print("\n\n" + "="*60)
    print("EXAMPLE 5: Generating Visualizations")
    print("="*60)
    
    provider = CreditDataProvider(mode='dummy')
    market_data = provider.get_market_snapshot('INTC')
    engine = HazardRateEngine(market_data)
    pricer = SyntheticPricer(engine, market_data)
    synthetic_price, cf_schedule = pricer.calculate_synthetic_price()
    analyzer = BasisAnalyzer(market_data, pricer)
    results = analyzer.analyze()
    
    # Create visualizer
    output_dir = Path(__file__).parent / 'output' / 'examples'
    viz = CreditVisualizer(output_dir=output_dir)
    
    print(f"\nSaving visualizations to: {output_dir}")
    
    # Generate plots
    viz.plot_credit_curve(market_data, engine, save=True, show=False)
    print("  ✓ Credit curve saved")
    
    viz.plot_basis_analysis(market_data, results, save=True, show=False)
    print("  ✓ Basis analysis saved")
    
    viz.plot_cash_flow_waterfall(cf_schedule, save=True, show=False)
    print("  ✓ Cash flow waterfall saved")
    
    viz.plot_survival_curve(engine, save=True, show=False)
    print("  ✓ Survival curve saved")
    
    viz.plot_comprehensive_dashboard(
        market_data, engine, results, cf_schedule,
        save=True, show=False
    )
    print("  ✓ Comprehensive dashboard saved")
    
    print(f"\nAll visualizations saved successfully!")


def main():
    """Run all examples."""
    
    print("\n" + "="*60)
    print("CREDIT ANALYTICS PLATFORM - USAGE EXAMPLES")
    print("="*60)
    
    try:
        example_basic_analysis()
        example_risk_metrics()
        example_survival_analysis()
        example_basis_trading_signals()
        example_visualizations()
        
        print("\n\n" + "="*60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
