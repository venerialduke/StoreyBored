import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')