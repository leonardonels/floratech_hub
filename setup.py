from setuptools import setup, find_packages

setup(
    name="floratech_hub",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "spidev",
        "gpiozero",
        "tinydb",
        "requests"
    ],
)
