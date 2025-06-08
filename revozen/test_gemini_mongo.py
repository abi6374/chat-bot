import json
from llm.gemini_query import generate_mongo_query
from db.connector import db

# Test query
def test_gemini_mongo_interaction():
    user_query = "provide me all the tyre brands in the company"
    
    # Get query from Gemini
    try:
        query = generate_mongo_query(user_query)
        print(f"Generated query: {json.dumps(query, indent=2)}")
        
        # Determine collection and execute query
        if isinstance(query, dict) and "find" in query:
            collection_name = query["find"]
            filter_query = query.get("filter", {})
            projection = query.get("projection", None)
            collection = db[collection_name]
            result = list(collection.find(filter_query, projection))
        elif isinstance(query, list):
            # Assume aggregation pipeline on addtyres collection
            collection = db["addtyres"]
            result = list(collection.aggregate(query))
        elif isinstance(query, dict):
            # Simple find query on addtyres collection
            collection = db["addtyres"]
            result = list(collection.find(query))
        else:
            raise ValueError("Invalid query format returned by Gemini.")
        
        print(f"Query results: {json.dumps(result, indent=2, default=str)}")
        return result
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    test_gemini_mongo_interaction()
