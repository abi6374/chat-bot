from fastapi import FastAPI
from pydantic import BaseModel
from llama_processor import extract_query_info
from mongo_utils import get_sales, get_models_and_sizes, get_type_by_size, db
from typing import Optional

app = FastAPI()

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

# In-memory session context store
session_context = {}

@app.post("/ask")
async def ask_question(req: QueryRequest):
    # Retrieve previous context for this session, or empty dict
    context = session_context.get(req.session_id, {}) if req.session_id else {}
    info = extract_query_info(req.question, previous_context=context)
    if not info:
        return {"message": "Sorry, I couldn't understand your request."}

    # Update context with new info (fill in missing from previous context)
    updated_context = context.copy()
    for key in ["brand", "intent", "size"]:
        if info.get(key):
            updated_context[key] = info[key]
        elif context.get(key):
            info[key] = context[key]
    # Save updated context
    if req.session_id:
        session_context[req.session_id] = updated_context

    brand = info.get("brand")
    intent = info.get("intent")
    size = info.get("size")

    # Handle different intents
    if intent == "get_type_by_size":
        result = get_type_by_size(size)
        if result.get("types"):
            types_str = ", ".join(result["types"])
            return {"message": f"The type(s) of tyre used for size {result['size']} is/are: {types_str}."}
        else:
            return {"message": result.get("message", "Could not determine the tyre type for this size.")}

    elif intent == "list_models":
        result = get_models_and_sizes(brand, intent)
        if result.get("models"):
            models_str = ", ".join(result["models"])
            return {"message": f"Models available for {result.get('brand', 'the specified brand')}: {models_str}."}
        else:
            return {"message": f"No models found for the brand {result.get('brand', 'specified')}. "}

    elif intent == "list_sizes":
        result = get_models_and_sizes(brand, intent, size)
        if result.get("model_sizes"):
            response_parts = []
            for item in result["model_sizes"]:
                if item["sizes"]:
                    sizes_str = ", ".join(item["sizes"])
                    response_parts.append(f"Model {item['model']} ({item['brand']}): Sizes {sizes_str}")
            if response_parts:
                return {"message": "Available sizes:\n" + "\n".join(response_parts)}
            else:
                return {"message": f"No sizes found for {result.get('brand', 'the specified brand')} models."}
        elif result.get("tyres"): # Case where size was specified
            tyre_list = [f"{t['brand']} {t['model']} ({t['size']})" for t in result['tyres']]
            joined_tyres = ", ".join(tyre_list)
            return {"message": f"Tyres found for size {size}: {joined_tyres}."}
        else:
            return {"message": f"No sizes found for {result.get('brand', 'the specified brand')}. "}

    elif intent == "count_type_by_size":
        result = get_type_by_size(size)
        if result.get("types"):
            count = len(result["types"])
            return {"message": f"There {'is' if count == 1 else 'are'} {count} type{'s' if count != 1 else ''} of tyre used for size {result['size']} in the inventory."}
        else:
            return {"message": result.get("message", "Could not determine the tyre type count for this size.")}

    elif intent == "models_and_types_by_size":
        # Get models for the size
        models_result = get_models_and_sizes(None, "list_sizes", size)
        # Get types for the size
        types_result = get_type_by_size(size)
        models = []
        if models_result.get("tyres"):
            models = [f"{t['brand']} {t['model']}" for t in models_result["tyres"]]
        types = types_result.get("types", [])
        response = []
        if models:
            response.append(f"Models available for size {size}: {', '.join(models)}.")
        if types:
            response.append(f"Tyre type(s) for size {size}: {', '.join(types)}.")
        if response:
            return {"message": " ".join(response)}
        else:
            return {"message": f"No models or types found for size {size}."}

    elif intent == "tubeless_sizes_by_brand":
        # Find all tyres for the brand with type 'tubeless'
        query = {"type": {"$regex": "tubeless", "$options": "i"}}
        if brand:
            query["brand"] = {"$regex": brand, "$options": "i"}
        tyres = list(db.addtyres.find(query))
        sizes = set()
        for tyre in tyres:
            for stock_item in tyre.get("stock", []):
                if stock_item.get("size"):
                    sizes.add(stock_item["size"])
        count = len(tyres)
        if count > 0:
            return {"message": f"There are {count} tubeless tyres for {brand}. Sizes: {', '.join(sorted(sizes))}."}
        else:
            return {"message": f"No tubeless tyres found for {brand}."}

    # Default to sales logic if intent is not recognized or is get_sales
    else:
        product = brand # assuming brand is the product for sales query
        date_range = info.get("date_range")
        result = get_sales(product, date_range)
        if result["total_orders"] > 0:
            # Format message based on sales results
            message_parts = []
            if result["tyre_names"]:
                joined_tyre_names = ", ".join(result["tyre_names"])
                message_parts.append(f"Found orders for tyres: {joined_tyre_names}")
            if result["total_quantity"] > 0:
                message_parts.append(f"Total quantity ordered: {result['total_quantity']}")
            if result["total_sales"] > 0:
                message_parts.append(f"Total sales amount: {result['total_sales']}")
            if not message_parts:
                return {"message": f"Found {result['total_orders']} orders, but no quantity or sales data."}
            joined_message_parts = " ".join(message_parts)
            return {"message": f"Found {result['total_orders']} orders. {joined_message_parts}"}
        else:
            return {"message": f"No orders found for {product} in the specified period."} 