from dotenv import load_dotenv # type: ignore
load_dotenv()
import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# List all available models and their exact API names
response = client.models.generate_content(
    model="gemini-3.1-flash-lite-preview",
    contents="say hi"
)
print(response.text)