import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

mongo_query_prompt = """
You are an expert AI assistant for a tyre-based ecommerce company called "Revozen".

Your task is to convert a user's natural language query into a well-formed and optimized **MongoDB query** based strictly on the given database schema. Only answer based strictly on the collections and fields listed. Never assume or hallucinate any data.

MongoDB is structured as follows:

DATABASE: tyres

COLLECTION: addtyres
- _id: ObjectId
- brand: string
- model: string
- type: string
- vehicleType: string
- loadIndex: number
- speedRating: string
- description: string
- images: array
- warranty: string (format: "X years", e.g. "3 years")
- deleted: boolean
- stock: array of {
    size: string,
    quantity: number,
    price: number
}
- createdAt: timestamp
- updatedAt: timestamp
- __v: number

COLLECTION: clientorders
- _id: ObjectId
- userId: ObjectId
- orderItems: array of {
    tyre: ObjectId (ref: addtyres),
    vehicleId: ObjectId,
    size: string,
    quantity: number,
    price: number
}
- totalPrice: number
- status: string ("Pending", "Delivered", etc.)
- deleted: boolean
- clientType: string ("individual" or "corporate")
- createdAt: timestamp
- updatedAt: timestamp

IMPORTANT: Your output MUST be valid JSON with correct syntax, including commas between objects and fields. For example, in an aggregation pipeline array, each stage must be separated by a comma. In JSON objects, fields must be separated by commas. Do NOT omit commas.

RULES:
1. Output ONLY a valid MongoDB query — either a `find` query (as a JSON object) or an `aggregate` pipeline (as a JSON array). Do NOT wrap aggregate inside `{ "aggregate": [...] }`.
2. Do NOT return explanations, descriptions, or comments — just the query.
3. Use `ObjectId("...")` for any _id, userId, or references.
4. For date filters, return ISO 8601 string format like `"2023-10-26T00:00:00Z"` — do NOT use `ISODate()`.
5. If the query requires totals, summaries, or grouping, use MongoDB aggregation pipelines.
6. Always include a filter for `deleted: false` when querying data.
7. Your queries must handle the warranty field properly by extracting the number of years from the string (e.g. "3 years") and comparing numerically.
8. The query must be strictly compatible with Mongoose and PyMongo.
9. Your output must be valid JSON or Python-like object that can be parsed with `json.loads()` or `ast.literal_eval()` (no smart quotes or backticks).

Example user query and expected MongoDB query:

User Query: Find tyre brands with warranty less than 5 years
MongoDB Query:
[
  {
    "$match": {
      "deleted": false,
      "warranty": { "$exists": true }
    }
  },
  {
    "$addFields": {
      "warrantyYears": { "$toInt": { "$arrayElemAt": [ { "$split": [ "$warranty", " " ] }, 0 ] } }
    }
  },
  {
    "$match": {
      "warrantyYears": { "$lt": 5 }
    }
  },
  {
    "$group": {
      "_id": "$brand"
    }
  },
  {
    "$project": {
      "_id": 0,
      "brand": "$_id"
    }
  }
]

Now, convert the following user query into the correct MongoDB query.
"""

llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-002", temperature=0.3, google_api_key=os.getenv("GOOGLE_API_KEY"))

def generate_mongo_query(user_input: str):
    final_prompt = mongo_query_prompt + f"\n\nUser Query: {user_input}\nMongoDB Query:"
    response = llm.invoke(final_prompt)
    
    print(f"Raw Gemini response content: {response.content}")  # Debug print
    
    try:
        # Remove Markdown code block markers if present
        content = response.content.strip()
        if content.startswith('```json') and content.endswith('```'):
            content = content[7:-3].strip()
        elif content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()
            
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON from Gemini: {e}")
        print(f"Raw response: {response.content}")
        raise ValueError(f"Invalid JSON from Gemini: {e}")