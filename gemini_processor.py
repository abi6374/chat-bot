import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="gemini-1.5-pro")

def extract_query_info(user_question):
    prompt = f"""
    Extract the following from the user question for a tyre sales database:
    - product (e.g., tyre brand)
    - date range (e.g., last year, 2023, etc.)
    Return as JSON with keys: product, date_range.
    User question: {user_question}
    """
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)
    except Exception:
        return None 