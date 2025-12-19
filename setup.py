from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="schedarray",
    version="0.1.0",
    author="Mark Brooks",
    author_email="",
    description="Cross-platform job scheduler using SQLite, providing SLURM/SGE-like functionality on Windows, macOS, and Linux.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mxflask/schedarray",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=[
        "decologr",
    ],
    extras_require={
        "numpy": ["numpy>=1.20.0"]
    },
    entry_points={
        "console_scripts": [
            "schedarray=schedarray.cli:main",
        ],
    },
)

