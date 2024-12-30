from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")