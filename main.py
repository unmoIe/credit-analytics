"""
Main Application Entry Point
Production-ready credit analytics platform.
"""

import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_provider import CreditDataProvider
from hazard_rate import HazardRateEngine
from pricing import SyntheticPricer
from basis_analysis import BasisAnalyzer
from visualizations import CreditVisualizer


def setup_logging(log_level: str = 'INFO', log_file: Path = None):
    """Configure logging for the application."""
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def run_analysis(
    ticker: str = "INTC",
    mode: str = "dummy",
    output_dir: Path = None,
    visualize: bool = True,
    verbose: bool = False
):
    """
    Run complete credit analysis workflow.
    
    Args:
        ticker: Issuer ticker symbol
        mode: Data mode ('dummy', 'live', 'cached')
        output_dir: Directory for outputs
        visualize: Whether to generate visualizations
        verbose: Enable verbose logging
        
    Returns:
        Dictionary containing all analysis results
    """
    # Setup
    log_level = 'DEBUG' if verbose else 'INFO'
    output_dir = output_dir or Path.cwd() / 'output'
    log_file = output_dir / f'analysis_{datetime.now():%Y%m%d_%H%M%S}.log'
    
    logger = setup_logging(log_level, log_file)
    logger.info("="*60)
    logger.info("CREDIT ANALYTICS PLATFORM - Analysis Starting")
    logger.info("="*60)
    logger.info(f"Ticker: {ticker} | Mode: {mode} | Output: {output_dir}")
    
    try:
        # Step 1: Data Acquisition
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Data Acquisition")
        logger.info("="*60)
        
        provider = CreditDataProvider(mode=mode)
        market_data = provider.get_market_snapshot(ticker)
        
        # Validate data
        if not provider.validate_data(market_data):
            raise ValueError("Market data validation failed")
        
        logger.info(f"✓ Market data acquired successfully")
        logger.info(f"  - Bond: {market_data['bond'].get('name', ticker)}")
        logger.info(f"  - Price: ${market_data['bond']['price']:.2f}")
        logger.info(f"  - CDS Tenors: {list(market_data['cds_curve'].keys())}")
        
        # Step 2: Hazard Rate Bootstrapping
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Hazard Rate Bootstrapping")
        logger.info("="*60)
        
        engine = HazardRateEngine(market_data)
        
        logger.info(f"✓ Hazard rates bootstrapped")
        for tenor in sorted(engine.hazard_rates.keys()):
            hazard = engine.hazard_rates[tenor]
            survival = engine.survival_prob(tenor)
            logger.info(f"  - {tenor}Y: λ={hazard:.6f}, S(t)={survival:.2%}")
        
        # Step 3: Synthetic Pricing
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Synthetic Bond Pricing")
        logger.info("="*60)
        
        pricer = SyntheticPricer(engine, market_data)
        synthetic_price, cf_schedule = pricer.calculate_synthetic_price()
        market_price = market_data['bond']['price']
        
        price_diff = market_price - synthetic_price
        signal = "CHEAP (Buy)" if price_diff < 0 else "RICH (Sell)"
        
        logger.info(f"✓ Pricing completed")
        logger.info(f"  - Market Price:    ${market_price:.4f}")
        logger.info(f"  - Synthetic Price: ${synthetic_price:.4f}")
        logger.info(f"  - Difference:      {price_diff:+.4f} points")
        logger.info(f"  - Signal:          Bond is {signal}")
        
        # Calculate additional metrics
        duration_metrics = pricer.calculate_duration(market_price)
        logger.info(f"  - Modified Duration: {duration_metrics['modified_duration']:.2f}")
        logger.info(f"  - DV01: ${duration_metrics['dv01']:.4f}")
        
        # Step 4: Basis Analysis
        logger.info("\n" + "="*60)
        logger.info("STEP 4: CDS-Bond Basis Analysis")
        logger.info("="*60)
        
        analyzer = BasisAnalyzer(market_data, pricer)
        basis_results = analyzer.analyze()
        
        logger.info(f"✓ Basis analysis completed")
        logger.info(f"  - Z-Spread:   {basis_results['Z_Spread_bps']:.2f} bps")
        logger.info(f"  - CDS Spread: {basis_results['CDS_Spread_bps']:.1f} bps ({basis_results['CDS_Tenor']}Y)")
        logger.info(f"  - Basis:      {basis_results['Basis_bps']:+.2f} bps")
        logger.info(f"  - Signal:     {basis_results['Trade_Signal']}")
        
        # Step 5: Visualization
        if visualize:
            logger.info("\n" + "="*60)
            logger.info("STEP 5: Generating Visualizations")
            logger.info("="*60)
            
            viz = CreditVisualizer(output_dir=output_dir)
            
            # Generate all plots
            viz.plot_credit_curve(market_data, engine, save=True, show=False)
            logger.info("  ✓ Credit curve plot saved")
            
            viz.plot_basis_analysis(market_data, basis_results, save=True, show=False)
            logger.info("  ✓ Basis analysis plot saved")
            
            viz.plot_cash_flow_waterfall(cf_schedule, save=True, show=False)
            logger.info("  ✓ Cash flow waterfall saved")
            
            viz.plot_survival_curve(engine, save=True, show=False)
            logger.info("  ✓ Survival curve saved")
            
            viz.plot_comprehensive_dashboard(
                market_data, engine, basis_results, cf_schedule,
                save=True, show=False
            )
            logger.info("  ✓ Comprehensive dashboard saved")
        
        # Generate report
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Generating Report")
        logger.info("="*60)
        
        report_df = analyzer.generate_report()
        report_path = output_dir / f'{ticker}_basis_report.csv'
        report_df.to_csv(report_path, index=False)
        logger.info(f"✓ Report saved to {report_path}")
        
        # Compile results
        results = {
            'market_data': market_data,
            'hazard_engine': engine,
            'synthetic_price': synthetic_price,
            'market_price': market_price,
            'cash_flows': cf_schedule,
            'basis_analysis': basis_results,
            'duration_metrics': duration_metrics,
            'report': report_df
        }
        
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"All outputs saved to: {output_dir}")
        
        return results
        
    except Exception as e:
        logger.error(f"\n{'='*60}")
        logger.error(f"ANALYSIS FAILED: {str(e)}")
        logger.error(f"{'='*60}", exc_info=True)
        raise


def main():
    """Command-line interface for the credit analytics platform."""
    
    parser = argparse.ArgumentParser(
        description='Credit Analytics Platform - Professional CDS-Bond Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run analysis on Intel with dummy data
  python main.py --ticker INTC --mode dummy
  
  # Run with live data (requires API keys)
  python main.py --ticker AAPL --mode live --verbose
  
  # Run without visualizations
  python main.py --ticker MSFT --no-visualize
  
  # Custom output directory
  python main.py --ticker TSLA --output ./reports/tsla
        """
    )
    
    parser.add_argument(
        '--ticker',
        type=str,
        default='INTC',
        help='Issuer ticker symbol (default: INTC)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['dummy', 'live', 'cached'],
        default='dummy',
        help='Data source mode (default: dummy)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path.cwd() / 'output',
        help='Output directory for results (default: ./output)'
    )
    
    parser.add_argument(
        '--no-visualize',
        action='store_true',
        help='Skip visualization generation'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Run analysis
    try:
        results = run_analysis(
            ticker=args.ticker,
            mode=args.mode,
            output_dir=args.output,
            visualize=not args.no_visualize,
            verbose=args.verbose
        )
        
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        print(f"Ticker:          {args.ticker}")
        print(f"Market Price:    ${results['market_price']:.4f}")
        print(f"Synthetic Price: ${results['synthetic_price']:.4f}")
        print(f"Basis:           {results['basis_analysis']['Basis_bps']:+.2f} bps")
        print(f"Trade Signal:    {results['basis_analysis']['Trade_Signal']}")
        print(f"\nOutputs saved to: {args.output}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
