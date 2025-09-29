#!/usr/bin/env python3
"""Setup script for DataAgent CLI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dataagent-cli",
    version="1.0.0",
    author="DataAgent Team",
    description="Natural language data analysis powered by Claude subscriptions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jmanhype/multi-agent-system",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Data Scientists",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "requests>=2.28.0",
        "pandas>=1.5.0",
        "numpy>=1.20.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "charts": [
            "matplotlib>=3.5.0",
            "seaborn>=0.12.0",
            "plotly>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dataagent=agents.data_agent.cli:cli",
            "da=agents.data_agent.cli:cli",  # Short alias
        ],
    },
)