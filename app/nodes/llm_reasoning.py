"""
app/nodes/llm_reasoning.py — Node 3: LLM Reasoning

Responsibilities:
1. Build a prompt from the tenant's system_prompt + chat_history + inbound_text.
2. Give the LLM two tools: attach_image and attach_document.
3. Run the Ollama LLM (llama3.1:8b supports tool calling).
4. If LLM calls a tool → populate state["media_attachment"].
5. Always populate state["llm_reply"] with the text response.

Tool calling with Ollama:
  - ChatOllama from langchain_ollama supports .bind_tools()
  - If the model calls a tool, the response has .tool_calls populated
  - We extract the tool arguments and look up the URL in tenant's media_library
"""

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from app.config import settings


# ── Tool definitions ───────────────────────────────────────────────────────────
# These are passed to the LLM via bind_tools(). The LLM decides whether to
# call them based on the conversation context.

@tool
def attach_image(keyword: str, message: str) -> str:
    """
    Use this tool when the customer requests an image such as a product photo,
    showroom picture, or repair diagram. Provide the keyword that matches a
    term in the media library (e.g. 'sofa', 'showroom', 'repair', 'diagram')
    AND a conversational 'message' to send to the customer alongside the image.
    """
    return json.dumps({"keyword": keyword, "message": message})


@tool
def attach_document(keyword: str, message: str, filename: str = "document.pdf") -> str:
    """
    Use this tool when the customer requests a document such as a catalog,
    invoice, service manual, or PDF. Provide the keyword that matches a term
    in the media library AND a conversational 'message' to send alongside it.
    """
    return json.dumps({"keyword": keyword, "message": message, "filename": filename})


TOOLS = [attach_image, attach_document]


# ── Helper: build chat history for the LLM ────────────────────────────────────

def _build_messages(tenant_doc: dict, chat_history: list, inbound_text: str) -> list:
    """
    Convert DB message dicts into LangChain message objects.
    The system prompt includes the tenant's identity AND its available media
    library keywords so the LLM knows what tools it can trigger.
    """
    media_library = tenant_doc.get("media_library", {})
    base_prompt = tenant_doc.get("system_prompt", "You are a helpful assistant.")

    # Build a media library description so the LLM knows what's available
    if media_library:
        media_section = "\n\nYou have access to the following media library. " \
                        "When a customer asks for any of these items, use the appropriate tool " \
                        "to attach the media to your reply:\n"
        for keyword, url in media_library.items():
            # Determine if it's a document or image based on URL extension
            if url.endswith(".pdf"):
                media_section += f"  - \"{keyword}\" → a PDF document (use attach_document tool with keyword='{keyword}')\n"
            else:
                media_section += f"  - \"{keyword}\" → an image (use attach_image tool with keyword='{keyword}')\n"
        system_prompt = base_prompt + media_section
    else:
        system_prompt = base_prompt

    messages = [SystemMessage(content=system_prompt)]

    # Add chat history (skip messages with no text to avoid empty content errors)
    for msg in chat_history:
        text = msg.get("text") or ""
        if not text.strip():
            continue
        if msg.get("direction") == "inbound":
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))

    # Add the current inbound message
    messages.append(HumanMessage(content=inbound_text))
    return messages


# ── Node ───────────────────────────────────────────────────────────────────────

async def llm_reasoning_node(state: dict) -> dict:
    """
    LangGraph node function.
    Calls Gemini LLM with tool support. Returns llm_reply and optionally media_attachment.
    """
    tenant_doc = state.get("tenant_doc") or {}
    chat_history = state.get("chat_history", [])
    inbound_text = state.get("inbound_text", "")
    media_library: dict = tenant_doc.get("media_library", {})

    # ── Initialise the LLM with tools ──────────────────────────────
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
    ).bind_tools(TOOLS)

    # ── Build message list and invoke ──────────────────────────────
    messages = _build_messages(tenant_doc, chat_history, inbound_text)

    try:
        # ChatGoogleGenerativeAI.ainvoke is async
        response = await llm.ainvoke(messages)
    except Exception as exc:
        print(f"[LLM] Error calling Gemini: {exc}")
        return {
            "llm_reply": "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.",
            "media_attachment": None,
        }

    llm_reply = response.content or ""
    media_attachment = None

    # ── Check if LLM called a tool ─────────────────────────────────
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_call = response.tool_calls[0]  # Handle the first tool call
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        keyword = args.get("keyword", "").lower()
        url = media_library.get(keyword)

        if url:
            # We use the LLM-generated message as the text reply
            llm_reply = args.get("message", "")
            
            if tool_name == "attach_image":
                media_attachment = {
                    "type": "image",
                    "url": url,
                    "caption": "",
                }
            elif tool_name == "attach_document":
                media_attachment = {
                    "type": "document",
                    "url": url,
                    "filename": args.get("filename", "document.pdf"),
                    "caption": "",
                }
            print(f"[LLM] Tool called: {tool_name} | keyword={keyword} | url={url}")
        else:
            print(f"[LLM] Tool called but keyword '{keyword}' not in media_library — skipping media.")

    # If the LLM didn't generate any text (and no tool message was provided), fallback
    if not llm_reply.strip():
        llm_reply = "I'm here to help! Could you please tell me more about what you're looking for?"

    print(f"[LLM] Reply preview: {llm_reply[:80]}...")

    return {
        "llm_reply": llm_reply,
        "media_attachment": media_attachment,
    }
