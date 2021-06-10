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
        "feeds.alchemyapi",
        "feeds.fixtures",
        "feeds.management",
        "feeds.management.commands",
    ],
    package_data={
        'feeds': ['fixtures/*.json']
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "Django==2.2.24",
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