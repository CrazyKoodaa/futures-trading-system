from setuptools import setup, find_packages

setup(
    name="futures-trading-system",
    version="0.1.0",
    description="NQ/ES Futures Trading System with ML Predictions",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0,<1.27.0",
        "pandas>=1.5.0,<2.3.0",
        "scikit-learn>=1.1.0,<1.4.0",
        "psycopg2-binary>=2.9.7",
        "sqlalchemy>=1.4.0,<2.1.0",
        "fastapi>=0.100.0",
        "plotly>=5.15.0",
        "dash>=2.14.0",
        "xgboost>=1.6.0",
        "lightgbm>=3.3.0",
    ],
    python_requires=">=3.11,<3.13",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3.11",
    ],
)
