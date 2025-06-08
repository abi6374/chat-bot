from fastapi import FastAPI, Request
from db.connector import db
from llm.gemini_query import generate_mongo_query
from llm.gemini_response import generate_friendly_response
from llm.memory import memory
import json

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Revozen Admin Chatbot API is running."}

# Helper function to clean and safely parse Gemini query
def clean_and_parse_query(query_str):
    query_str = query_str.replace("ISODate(", "").replace(")", "").strip()
    try:
        return json.loads(query_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Failed to parse Gemini query: {e}\nRaw response: {query_str}")

# Simplified and improved logic to determine target collection
def detect_collection(parsed_query):
    if isinstance(parsed_query, list):
        # Check for clientorders references in aggregation pipeline
        for stage in parsed_query:
            if "$lookup" in stage and stage["$lookup"].get("from") == "clientorders":
                return "clientorders"
            if "$match" in stage and "clientType" in stage["$match"]:
                return "clientorders"
        return "addtyres"
    elif isinstance(parsed_query, dict):
        if "userId" in parsed_query or "clientType" in parsed_query:
            return "clientorders"
        if "find" in parsed_query:
            return parsed_query["find"]
        return "addtyres"
    else:
        # Default fallback
        return "addtyres"

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_input = body.get("message", "")

    # 1. Add user query to memory
    memory.chat_memory.add_user_message(user_input)

    # 2. Generate MongoDB query using Gemini
    try:
        mongo_query = generate_mongo_query(user_input)
    except Exception as e:
        return {"error": f"Failed to generate MongoDB query: {str(e)}"}

    try:
        # 3. Clean and parse the Gemini query output only if it's a string
        if isinstance(mongo_query, str):
            parsed_query = clean_and_parse_query(mongo_query)
        else:
            parsed_query = mongo_query

        # 4. Determine collection dynamically
        collection_name = detect_collection(parsed_query)
        collection = db[collection_name]

        # 5. Execute the MongoDB query
        if isinstance(parsed_query, list):
            result = list(collection.aggregate(parsed_query))
        elif isinstance(parsed_query, dict):
            if "find" in parsed_query:
                filter_query = parsed_query.get("filter", {})
                projection = parsed_query.get("projection", None)
                result = list(collection.find(filter_query, projection))
            else:
                result = list(collection.find(parsed_query))
        else:
            return {"error": "Invalid MongoDB query format returned by Gemini."}

    except Exception as e:
        return {"error": f"Query execution failed: {str(e)}"}

    # 6. Format the result using Gemini with user question context
    try:
        final_response = generate_friendly_response(user_input, json.dumps(result, default=str))
    except Exception as e:
        final_response = f"Failed to generate friendly response: {str(e)}"

    # 7. Save response to memory
    memory.chat_memory.add_ai_message(final_response)

    return {
        "mongo_query": mongo_query,
        "raw_result": result,
        "friendly_response": final_response
    }