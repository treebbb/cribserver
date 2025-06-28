from setuptools import setup, find_packages

setup(
    name="cribserver",
    version="0.1.0",
    description="A FastAPI-based server for a multiplayer Cribbage game over a household LAN",
    author="Your Name",  # Replace with your name or organization
    author_email="your.email@example.com",  # Replace with your email
    url="https://github.com/yourusername/cribserver",  # Optional: replace with repo URL
    license="MIT",  # SPDX license identifier
    packages=find_packages(where="src/python"),
    package_dir={"": "src/python"},
    include_package_data=True,
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "pydantic>=2.8.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cribserver=cribserver.server:run_server",
            "cribclient=cribserver.client:run_client",
        ],
    },
)
