"""
app/nodes/context_retriever.py — Node 2: Context Retriever

Responsibilities:
1. Fetch the full tenant document (system_prompt + media_library) from MongoDB.
2. Fetch the last 5 messages for this session to build chat history.
3. Return updated state with tenant_doc and chat_history.
"""

from app.database.mongo import get_tenants_col, get_messages_col


async def context_retriever_node(state: dict) -> dict:
    """
    LangGraph node function.
    Returns a dict with 'tenant_doc' and 'chat_history' state updates.
    """
    tenant_id = state["tenant_id"]
    session_id = state["session_id"]

    
    tenants_col = get_tenants_col()
    tenant_doc = await tenants_col.find_one(
        {"tenant_id": tenant_id},
        {"_id": 0},  
    )
    if tenant_doc is None:
        
        print(f"[Context] WARNING: Tenant '{tenant_id}' not found in DB.")
        tenant_doc = {
            "tenant_id": tenant_id,
            "name": "Unknown Tenant",
            "system_prompt": "You are a helpful assistant.",
            "media_library": {},
        }

    
    messages_col = get_messages_col()
    cursor = (
        messages_col
        .find({"session_id": session_id}, {"_id": 0})
        .sort("timestamp", -1)   
        .limit(5)
    )
    recent_msgs = await cursor.to_list(length=5)
    
    chat_history = list(reversed(recent_msgs))

    print(
        f"[Context] tenant={tenant_id} | "
        f"history_len={len(chat_history)} | "
        f"media_library_keys={list(tenant_doc.get('media_library', {}).keys())}"
    )

    return {
        "tenant_doc": tenant_doc,
        "chat_history": chat_history,
    }
