#!/usr/bin/env python3
"""Setup — registers 'mediavault' CLI command via pip install."""

from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).resolve().parent
README = HERE / "README.md"
LONG_DESC = README.read_text(encoding="utf-8") if README.exists() else ""

setup(
    name="media-vault",
    version="1.0.0",
    description="Auto search, save, and organize movies/TV shows to Quark cloud drive",
    long_description=LONG_DESC,
    long_description_content_type="text/markdown",
    url="https://github.com/qiwu7687-tech/Media-vault",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "qrcode>=7.4",
        "Pillow>=9.0",
        "quarkpan>=1.0.5",
    ],
    entry_points={
        "console_scripts": [
            "mediavault=scripts.mediavault:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Video",
    ],
)
