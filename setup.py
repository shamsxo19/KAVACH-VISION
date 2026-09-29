from setuptools import setup, find_packages

setup(
    name="zenora",
    version="1.0.0",
    description="Trustworthy Computer Vision Integrity Assurance Framework",
    author="Team Zenora",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "zenora=zenora.cli:main",
        ],
    },
    include_package_data=True,
)
