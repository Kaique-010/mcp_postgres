from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

load_dotenv()

llm = init_chat_model(
    ("google_genai:gemini-2.5-flash-lite"),
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
