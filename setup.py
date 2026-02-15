"""
Setup configuration for Credit Analytics Platform
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text() if readme_file.exists() else ''

setup(
    name='credit-analytics',
    version='1.0.0',
    author='Credit Analytics Team',
    author_email='team@creditanalytics.com',
    description='Production-ready credit risk analysis and basis trading platform',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/credit-analytics',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial :: Investment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.21.0,<2.0.0',
        'pandas>=1.3.0,<3.0.0',
        'scipy>=1.7.0,<2.0.0',
        'yfinance>=0.2.0,<1.0.0',
        'matplotlib>=3.4.0,<4.0.0',
        'seaborn>=0.11.0,<1.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
        'docs': [
            'sphinx>=4.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'credit-analytics=main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
