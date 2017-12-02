from setuptools import setup

setup(
    # Application name:
    name="GPSTracker Server",

    # Version number (initial):
    version="0.0.1",

    # Application author details:
    author="Tamas Jos",
    author_email="info@skelsec.com",

    # Packages
    packages=["gpstracker_server"],

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="https://github.com/skelsec/GPSTrackerServer",

    #
    # license="LICENSE.txt",
    description="Server part of the GPS Tracker framework",

    # long_description=open("README.txt").read(),

    zip_safe=False,
    # Dependent packages (distributions)
    install_requires=[
        "flask",
        "sqlalchemy",
        "flask-restful",
        "flask-sqlalchemy",
        "flask-bootstrap",
        "flask-security",
        "flask-cors",
        "flask-mail",
        "flask-assets",
        "python-dateutil",
        "pytz",
        "geopy",
        "gpxpy",
        "rdp",
        "pyOpenSSL",
        "pathlib;python_version<'3'",
    ],
)
