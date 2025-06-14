"""
setup.py

Defines package metadata and installation requirements.
"""
from setuptools import setup, find_packages

setup(
    name="sample-project",
    version="0.1.0",
    author="Your Name",
    author_email="you@example.com",
    description="A sample modular Python project.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
)
