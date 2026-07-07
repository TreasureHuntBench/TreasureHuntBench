from setuptools import setup, find_packages

setup(
    name="treasurehuntbench",
    version="0.1.0",
    description=(
        "TreasureHuntBench: a world-simulation benchmark for "
        "long-horizon agentic investigation"
    ),
    python_requires=">=3.8",
    packages=find_packages(include=["thb", "thb.*"]),
    include_package_data=True,
    package_data={"thb.sources": ["data/*"]},
    install_requires=[
        "requests>=2.25",
        "PyYAML>=5.4",
        "Pillow>=8.0",
    ],
    extras_require={"dev": ["pytest>=6.0"]},
    entry_points={"console_scripts": ["thb=thb.cli:main"]},
)
