import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="youtube-rss-subscriber",
    version="0.0.1",
    author="Miquel Ruiz",
    author_email="self@miquelruiz.net",
    description="Subscribe to YouTube channels without a YouTube account",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/miquelruiz/youtube-rss-subscriber",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "beautifulsoup4", "click", "lxml", "pyyaml", "python-dateutil", "sqlalchemy", "tabulate", "youtube-dl"
    ],
    entry_points={"console_scripts": ["yrs=youtube_rss_subscriber:main"]},
)
