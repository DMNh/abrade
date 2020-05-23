import setuptools

with open("README.md", 'r') as f:
    long_description = f.read(
)

setuptools.setup(
    name="abrade",
    version="0.1.0",
    author="Dan Lewis",
    author_email="D@nLew.is",
    description="A simple, generic web scraper and parser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DMNh/abrade",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "requests",
        "bs4"
    ]
)
