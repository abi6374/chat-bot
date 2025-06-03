import os
from groq import Groq
from dotenv import load_dotenv
import json
import re

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_query_info(user_question, previous_context=None):
    prompt = f"""
    For a tyre management system database, extract the following from the user question:
    - brand (e.g., MRF, Michelin)
    - intent: "list_models" if the user wants to know all models for a brand, "list_sizes" if the user wants to know sizes for a brand/model, "get_type_by_size" if the user wants to know the type of a tyre for a specific size, or "get_sales" for sales-related questions.
    - size (if mentioned, e.g., 195/65R15)
    Return ONLY valid JSON with keys: brand, intent, size. Do not include any explanation or text before or after the JSON.
    User question: {user_question}
    """
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_completion_tokens=256,
        top_p=1,
        stream=False,
        stop=None,
    )
    content = completion.choices[0].message.content
    print("LLAMA RAW RESPONSE:", content)
    # Extract JSON from code block if present
    if content and "```" in content:
        json_str = content.split("```", 1)[1]
        if json_str.startswith("json"):
            json_str = json_str[4:]
        json_str = json_str.strip(" \n`")
    else:
        json_str = content
    try:
        info = json.loads(json_str)
        # Add post-processing for count intent
        if isinstance(info, dict):
            q = user_question.lower()
            if re.search(r"(type count|number of types|how many types)", q):
                info["intent"] = "count_type_by_size"
            # Detect queries for models for a specific size
            elif re.search(r"models? (available|for|with)? ?(size)? ?[0-9]+/[0-9]+r[0-9]+", q):
                info["intent"] = "models_and_types_by_size"
            # Detect queries for tubeless and their sizes for a brand
            elif re.search(r"tubeless.*sizes?", q) or ("tubeless" in q and "size" in q):
                info["intent"] = "tubeless_sizes_by_brand"
            # Fill missing fields from previous_context
            if previous_context:
                for key in ["brand", "size"]:
                    if (key not in info or info[key] is None) and previous_context.get(key):
                        info[key] = previous_context[key]
        return info
    except Exception as e:
        print("Groq/Llama API error:", e)
        return None 