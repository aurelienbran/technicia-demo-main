from setuptools import setup, find_packages

setup(
    name="technicia-demo",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "anthropic",
        "httpx",
        "qdrant-client",
        "watchdog",
        "PyMuPDF"
    ],
)