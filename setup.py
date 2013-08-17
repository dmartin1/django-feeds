from setuptools import setup

import feeds

setup(
    name="django-feeds",
    version=feeds.__version__,
    license="MIT",
    url="https://github.com/dmartin1/django-feeds",
    author="David Martin",
    author_email="dmartin1@github",
    description="RSS/Atom feed scraper and entry speaker.",
    keywords="django RSS feeds speech",
    packages=[
        "feeds",
        "feeds.fixtures",
        "feeds.management",
        "feeds.management.commands",
    ],
    package_data={
        'feeds': ['*.json']
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "Django==1.4.5",
        "pytz>=2013b",
        "feedparser",
        "python-dateutil",
        "nltk",
        "requests",
        "beautifulsoup4",
        "lxml",
        "html5lib",
    ]
)