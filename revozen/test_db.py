from db.connector import db

# Example test query
try:
    # Test finding documents
    results = list(db.tyres.find({"size": "265/65R17"}).limit(5))
    print("Query Results:", results)
    
    # Test aggregation
    pipeline = [
        {"$group": {"_id": "$brand", "count": {"$sum": 1}}}
    ]
    agg_results = list(db.tyres.aggregate(pipeline))
    print("Aggregation Results:", agg_results)
    
except Exception as e:
    print("Test failed:", e)