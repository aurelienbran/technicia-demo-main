from setuptools import setup, find_packages

setup(
    name="technicia-demo",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-dotenv==1.0.0",
        "anthropic>=0.7.8",
        "qdrant-client==1.6.4",
        "voyageai>=0.1.0",
        "watchdog==3.0.0",
        "PyMuPDF==1.23.7",
        "pydantic==2.5.1",
        "python-multipart==0.0.6",
        "aiohttp==3.9.1",
        "asyncio==3.4.3",
        "black==23.11.0"
    ],
)