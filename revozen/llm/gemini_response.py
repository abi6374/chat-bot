import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

response_prompt = """
You are a helpful assistant for Revozen. Format the following MongoDB output into a friendly, accurate message for an admin.
Avoid unnecessary jargon. Mention tyre size, order status, price, warranty, etc., if available.
Use the user's original question to provide context and tailor the response accordingly.
"""

llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-002", temperature=0.4, google_api_key=os.getenv("GOOGLE_API_KEY"))

def generate_friendly_response(user_question: str, mongo_data: str):
    prompt = response_prompt + f"\n\nUser Question:\n{user_question}\n\nRaw MongoDB Data:\n{mongo_data}"
    response = llm.invoke(prompt)
    return response.content.strip()