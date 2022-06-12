import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

requirements = [
    'requests>=2.4',
    'pyotp>=2.0',
    'beautifulsoup4>=4.0'
    ]

setuptools.setup(
    name="ItchClaim",
    version="0.0.1",
    packages=['ItchClaim'],
    install_requires=requirements,
    author="Smart123s",
    author_email="public@tmbpeter.com",
    description="Automatically claim free itch.io games.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Smart123s/ItchClaim",
    project_urls={
        "Bug Tracker": "https://github.com/Smart123s/ItchClaim/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)