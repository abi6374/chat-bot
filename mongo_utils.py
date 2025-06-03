from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
import json
import re

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME", "tyres")]

def get_sales(product, date_range):
    # 1. Find all tyres matching the product (brand/name)
    tyre_query = {}
    if product:
        tyre_query["brand"] = {"$regex": product, "$options": "i"}
    tyre_docs = list(db.addtyres.find(tyre_query))
    tyre_ids = [tyre["_id"] for tyre in tyre_docs]

    # 2. Build order query for clientorders (search in orderItems.tyre)
    order_query = {}
    if tyre_ids:
        order_query["orderItems.tyre"] = {"$in": tyre_ids}
    if date_range and "last year" in date_range.lower():
        now = datetime.now()
        last_year = now.year - 1
        start = datetime(last_year, 1, 1)
        end = datetime(last_year, 12, 31, 23, 59, 59)
        order_query["createdAt"] = {"$gte": start, "$lte": end}

    # 3. Find matching orders
    orders = list(db.clientorders.find(order_query))

    # 4. Aggregate sales (sum quantity and totalPrice for matching orderItems)
    total_quantity = 0
    total_sales = 0
    for order in orders:
        for item in order.get("orderItems", []):
            if item.get("tyre") in tyre_ids:
                total_quantity += item.get("quantity", 0)
                total_sales += item.get("totalPrice", 0)

    tyre_names = [tyre.get("brand", str(tyre["_id"])) for tyre in tyre_docs]

    return {
        "tyre_names": tyre_names,
        "total_orders": len(orders),
        "total_quantity": total_quantity,
        "total_sales": total_sales,
        "orders": orders  # or summarize as needed
    }

def get_models_and_sizes(brand, intent, size=None):
    query = {}
    if brand:
        query["brand"] = {"$regex": brand, "$options": "i"}
    tyres = list(db.addtyres.find(query))
    if intent == "list_models":
        models = [tyre.get("model") for tyre in tyres]
        return {"models": models, "brand": brand}
    elif intent == "list_sizes":
        # If size is specified, filter tyres by size in stock array
        if size:
            matching_tyres = []
            for tyre in tyres:
                for stock_item in tyre.get("stock", []):
                    if stock_item.get("size") == size:
                        matching_tyres.append({
                            "model": tyre.get("model"),
                            "brand": tyre.get("brand"),
                            "size": size
                        })
            return {"tyres": matching_tyres}
        else:
            # Return all sizes for each model
            model_sizes = []
            for tyre in tyres:
                sizes = [stock_item.get("size") for stock_item in tyre.get("stock", []) if stock_item.get("size")]
                model_sizes.append({
                    "model": tyre.get("model"),
                    "brand": tyre.get("brand"),
                    "sizes": sizes
                })
            return {"model_sizes": model_sizes}
    else:
        return {"message": "Intent not recognized or not supported."}

def get_type_by_size(size):
    if not size:
        return {"message": "Please specify a tyre size."}

    # Find tyres that have the specified size in their stock array
    query = {"stock.size": size}
    tyres = list(db.addtyres.find(query))

    if not tyres:
        return {"message": f"No tyres found with size {size}."}

    # Extract and return the types found
    tyre_types = list(set([tyre.get("type") for tyre in tyres if tyre.get("type")]))

    if not tyre_types:
        return {"message": f"Found tyres with size {size}, but their type is not specified."}

    return {"size": size, "types": tyre_types} 