"""
Visualization Module
Production-quality charts for credit analytics.
"""

import logging
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Set professional style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 10


class CreditVisualizer:
    """
    Generate professional visualizations for credit analysis.
    
    Methods:
        - plot_credit_curve: CDS term structure
        - plot_basis_analysis: Bond vs CDS comparison
        - plot_cash_flow_waterfall: Bond cash flow breakdown
        - plot_survival_curve: Credit survival probabilities
        - plot_comprehensive_dashboard: Multi-panel overview
    """
    
    def __init__(self, output_dir: Optional[Path] = None, dpi: int = 300):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save plots
            dpi: Resolution for saved figures
        """
        self.output_dir = output_dir or Path.cwd() / 'output'
        self.dpi = dpi
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Visualizer initialized with output dir: {self.output_dir}")
    
    def plot_credit_curve(
        self,
        market_data: Dict,
        engine,
        save: bool = True,
        show: bool = False
    ) -> Optional[Path]:
        """
        Plot CDS spread curve and implied hazard rates.
        
        Args:
            market_data: Market snapshot
            engine: HazardRateEngine with bootstrapped rates
            save: Whether to save the plot
            show: Whether to display the plot
            
        Returns:
            Path to saved figure if save=True
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Left panel: CDS Curve
        tenors = sorted(market_data['cds_curve'].keys())
        spreads = [market_data['cds_curve'][t] for t in tenors]
        
        ax1.plot(tenors, spreads, marker='o', linewidth=2.5, 
                markersize=8, color='#2E86AB', label='CDS Spread')
        ax1.fill_between(tenors, spreads, alpha=0.3, color='#2E86AB')
        
        ax1.set_xlabel('Tenor (Years)', fontweight='bold')
        ax1.set_ylabel('Spread (Basis Points)', fontweight='bold')
        ax1.set_title('CDS Term Structure', fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(loc='best')
        
        # Right panel: Hazard Rates
        hazard_tenors = sorted(engine.hazard_rates.keys())
        hazard_values = [engine.hazard_rates[t] * 10000 for t in hazard_tenors]  # Convert to bps
        
        ax2.plot(hazard_tenors, hazard_values, marker='s', linewidth=2.5,
                markersize=8, color='#A23B72', label='Hazard Rate')
        ax2.fill_between(hazard_tenors, hazard_values, alpha=0.3, color='#A23B72')
        
        ax2.set_xlabel('Tenor (Years)', fontweight='bold')
        ax2.set_ylabel('Hazard Rate (bps)', fontweight='bold')
        ax2.set_title('Bootstrapped Hazard Rates', fontweight='bold', pad=15)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.legend(loc='best')
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / 'credit_curve.png'
            plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Saved credit curve plot to {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return filepath if save else None
    
    def plot_basis_analysis(
        self,
        market_data: Dict,
        results: Dict,
        save: bool = True,
        show: bool = False
    ) -> Optional[Path]:
        """
        Visualize CDS-Bond basis analysis.
        
        Args:
            market_data: Market snapshot
            results: Basis analysis results
            save: Whether to save the plot
            show: Whether to display the plot
            
        Returns:
            Path to saved figure if save=True
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Prepare data
        tenors = sorted(market_data['cds_curve'].keys())
        cds_spreads = [market_data['cds_curve'][t] for t in tenors]
        
        bond_tenor = market_data['bond']['years_to_maturity']
        z_spread = results['Z_Spread_bps']
        
        # Plot CDS curve
        ax.plot(tenors, cds_spreads, marker='o', linestyle='-', 
               color='#1f77b4', linewidth=2.5, markersize=10,
               label='CDS Curve', zorder=3)
        
        # Plot Bond Z-Spread
        ax.scatter(bond_tenor, z_spread, color='#d62728', s=200, 
                  label=f'Bond Z-Spread ({z_spread:.1f} bps)',
                  zorder=5, edgecolors='black', linewidths=1.5)
        
        # Draw basis gap
        reference_cds = results['CDS_Spread_bps']
        ax.vlines(bond_tenor, min(z_spread, reference_cds), 
                 max(z_spread, reference_cds),
                 linestyles='--', color='gray', linewidth=2, alpha=0.7)
        
        # Annotate basis
        basis = results['Basis_bps']
        mid_point = (z_spread + reference_cds) / 2
        
        annotation_text = f"Basis: {basis:+.1f} bps"
        if abs(basis) > 10:
            annotation_text += "\n" + ("Bond Cheap" if basis < 0 else "Bond Rich")
        
        ax.annotate(
            annotation_text,
            xy=(bond_tenor, mid_point),
            xytext=(bond_tenor + 0.5, mid_point),
            fontsize=11,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', color='black', linewidth=1.5)
        )
        
        # Formatting
        ticker = market_data['bond'].get('ticker', 'Bond')
        ax.set_title(
            f'{ticker} Relative Value Analysis: CDS-Bond Basis',
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        ax.set_xlabel('Tenor (Years)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Spread (Basis Points)', fontsize=12, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper left', frameon=True, shadow=True)
        
        # Add trade recommendation box
        signal = results['Trade_Signal']
        box_color = '#90EE90' if 'Long Bond' in signal else '#FFB6C1'
        
        textstr = f"Signal: {signal}\nBasis: {basis:+.1f} bps"
        props = dict(boxstyle='round', facecolor=box_color, alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes,
               fontsize=10, verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / 'basis_analysis.png'
            plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Saved basis analysis plot to {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return filepath if save else None
    
    def plot_cash_flow_waterfall(
        self,
        cf_schedule: pd.DataFrame,
        save: bool = True,
        show: bool = False
    ) -> Optional[Path]:
        """
        Create waterfall chart of bond cash flows.
        
        Args:
            cf_schedule: Cash flow schedule DataFrame
            save: Whether to save the plot
            show: Whether to display the plot
            
        Returns:
            Path to saved figure if save=True
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Top panel: Cash flows over time
        times = cf_schedule['Time'].values
        payments = cf_schedule['Payment'].values
        pv_values = cf_schedule['PV'].values
        
        ax1.bar(times, payments, width=0.2, alpha=0.6, 
               label='Nominal Cash Flow', color='#3498db')
        ax1.bar(times, pv_values, width=0.15, alpha=0.9,
               label='Credit-Adjusted PV', color='#e74c3c')
        
        ax1.set_xlabel('Time (Years)', fontweight='bold')
        ax1.set_ylabel('Cash Flow ($)', fontweight='bold')
        ax1.set_title('Bond Cash Flow Schedule', fontweight='bold', pad=15)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Bottom panel: Cumulative PV
        cumulative_pv = np.cumsum(pv_values)
        
        ax2.plot(times, cumulative_pv, marker='o', linewidth=2.5,
                markersize=6, color='#27ae60', label='Cumulative PV')
        ax2.fill_between(times, cumulative_pv, alpha=0.3, color='#27ae60')
        
        # Mark final price
        final_pv = cumulative_pv[-1]
        ax2.axhline(y=final_pv, color='r', linestyle='--', linewidth=1.5,
                   label=f'Synthetic Price: ${final_pv:.2f}')
        
        ax2.set_xlabel('Time (Years)', fontweight='bold')
        ax2.set_ylabel('Cumulative PV ($)', fontweight='bold')
        ax2.set_title('Cumulative Present Value Build-up', fontweight='bold', pad=15)
        ax2.legend(loc='lower right')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / 'cash_flow_waterfall.png'
            plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Saved cash flow waterfall to {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return filepath if save else None
    
    def plot_survival_curve(
        self,
        engine,
        max_time: float = 10.0,
        save: bool = True,
        show: bool = False
    ) -> Optional[Path]:
        """
        Plot survival and default probability curves.
        
        Args:
            engine: HazardRateEngine instance
            max_time: Maximum time to plot
            save: Whether to save the plot
            show: Whether to display the plot
            
        Returns:
            Path to saved figure if save=True
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Generate time grid
        times = np.linspace(0.25, max_time, 100)
        survival_probs = [engine.survival_prob(t) for t in times]
        default_probs = [1 - s for s in survival_probs]
        
        # Left panel: Survival probability
        ax1.plot(times, survival_probs, linewidth=2.5, color='#27ae60',
                label='Survival Probability')
        ax1.fill_between(times, survival_probs, alpha=0.3, color='#27ae60')
        
        # Mark key tenors
        for tenor in sorted(engine.hazard_rates.keys()):
            if tenor <= max_time:
                surv = engine.survival_prob(tenor)
                ax1.scatter(tenor, surv, s=80, color='#e74c3c', zorder=5)
                ax1.text(tenor, surv - 0.05, f'{surv:.1%}',
                        ha='center', fontsize=9)
        
        ax1.set_xlabel('Time (Years)', fontweight='bold')
        ax1.set_ylabel('Probability', fontweight='bold')
        ax1.set_title('Survival Probability Curve', fontweight='bold', pad=15)
        ax1.set_ylim([0, 1.05])
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='lower left')
        
        # Right panel: Default probability
        ax2.plot(times, default_probs, linewidth=2.5, color='#e74c3c',
                label='Cumulative Default Probability')
        ax2.fill_between(times, default_probs, alpha=0.3, color='#e74c3c')
        
        ax2.set_xlabel('Time (Years)', fontweight='bold')
        ax2.set_ylabel('Probability', fontweight='bold')
        ax2.set_title('Cumulative Default Probability', fontweight='bold', pad=15)
        ax2.set_ylim([0, 1.05])
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        plt.tight_layout()
        
        if save:
            filepath = self.output_dir / 'survival_curve.png'
            plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Saved survival curve to {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return filepath if save else None
    
    def plot_comprehensive_dashboard(
        self,
        market_data: Dict,
        engine,
        results: Dict,
        cf_schedule: pd.DataFrame,
        save: bool = True,
        show: bool = False
    ) -> Optional[Path]:
        """
        Create comprehensive 4-panel dashboard.
        
        Args:
            market_data: Market snapshot
            engine: HazardRateEngine instance
            results: Basis analysis results
            cf_schedule: Cash flow schedule
            save: Whether to save the plot
            show: Whether to display the plot
            
        Returns:
            Path to saved figure if save=True
        """
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)
        
        # Panel 1: CDS Curve
        ax1 = fig.add_subplot(gs[0, 0])
        tenors = sorted(market_data['cds_curve'].keys())
        spreads = [market_data['cds_curve'][t] for t in tenors]
        ax1.plot(tenors, spreads, marker='o', linewidth=2, color='#2E86AB')
        ax1.fill_between(tenors, spreads, alpha=0.3, color='#2E86AB')
        ax1.set_title('CDS Term Structure', fontweight='bold')
        ax1.set_xlabel('Tenor (Years)')
        ax1.set_ylabel('Spread (bps)')
        ax1.grid(True, alpha=0.3)
        
        # Panel 2: Basis Analysis
        ax2 = fig.add_subplot(gs[0, 1])
        bond_tenor = market_data['bond']['years_to_maturity']
        z_spread = results['Z_Spread_bps']
        ax2.plot(tenors, spreads, marker='o', linewidth=2, color='#1f77b4', label='CDS')
        ax2.scatter(bond_tenor, z_spread, s=150, color='#d62728', 
                   label=f'Z-Spread', zorder=5)
        ax2.set_title(f'Basis Analysis ({results["Basis_bps"]:+.1f} bps)', 
                     fontweight='bold')
        ax2.set_xlabel('Tenor (Years)')
        ax2.set_ylabel('Spread (bps)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Panel 3: Survival Curve
        ax3 = fig.add_subplot(gs[1, :])
        times = np.linspace(0.25, 10, 100)
        survival = [engine.survival_prob(t) for t in times]
        ax3.plot(times, survival, linewidth=2.5, color='#27ae60')
        ax3.fill_between(times, survival, alpha=0.3, color='#27ae60')
        ax3.set_title('Credit Survival Probability', fontweight='bold')
        ax3.set_xlabel('Time (Years)')
        ax3.set_ylabel('Survival Probability')
        ax3.set_ylim([0, 1.05])
        ax3.grid(True, alpha=0.3)
        
        # Panel 4: Cash Flow Waterfall
        ax4 = fig.add_subplot(gs[2, :])
        cf_times = cf_schedule['Time'].values
        cf_pv = cf_schedule['PV'].values
        cumulative_pv = np.cumsum(cf_pv)
        ax4.plot(cf_times, cumulative_pv, marker='o', linewidth=2.5, 
                color='#e74c3c')
        ax4.fill_between(cf_times, cumulative_pv, alpha=0.3, color='#e74c3c')
        ax4.axhline(y=cumulative_pv[-1], color='gray', linestyle='--',
                   label=f'Synthetic: ${cumulative_pv[-1]:.2f}')
        ax4.set_title('Cumulative Cash Flow PV', fontweight='bold')
        ax4.set_xlabel('Time (Years)')
        ax4.set_ylabel('Cumulative PV ($)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Overall title
        ticker = market_data['bond'].get('ticker', 'Bond')
        fig.suptitle(f'{ticker} Credit Analytics Dashboard', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        if save:
            filepath = self.output_dir / 'comprehensive_dashboard.png'
            plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Saved comprehensive dashboard to {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return filepath if save else None
