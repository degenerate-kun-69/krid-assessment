"""
app/services/langgraph_agent.py — LangGraph stateful pipeline definition.

Graph topology:
    acknowledge → context_retriever → llm_reasoning → dispatcher → END

AgentState is the shared state dict passed between all nodes.
Call `agent.ainvoke(initial_state)` to run the full pipeline.
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator




class AgentState(TypedDict):
    """
    Shared state object threaded through every node in the graph.
    Each node receives this dict and returns a (partial) dict of updates.
    LangGraph merges the updates back into the state automatically.
    """
    
    tenant_id: str
    customer_phone: str
    wa_message_id: str          
    inbound_text: str           
    inbound_media_url: Optional[str]  

    
    tenant_doc: Optional[dict]   
    chat_history: list           

    
    llm_reply: Optional[str]     
    media_attachment: Optional[dict]
    
    
    
    
    
    
    

    
    session_id: Optional[str]    




def build_graph():
    """
    Assemble and compile the LangGraph StateGraph.
    Nodes are imported here (lazy) to avoid circular imports at module load.
    Returns a compiled runnable graph.
    """
    from app.nodes.acknowledge import acknowledge_node
    from app.nodes.context_retriever import context_retriever_node
    from app.nodes.llm_reasoning import llm_reasoning_node
    from app.nodes.dispatcher import dispatcher_node

    graph = StateGraph(AgentState)

    
    graph.add_node("acknowledge", acknowledge_node)
    graph.add_node("context_retriever", context_retriever_node)
    graph.add_node("llm_reasoning", llm_reasoning_node)
    graph.add_node("dispatcher", dispatcher_node)

    
    graph.set_entry_point("acknowledge")
    graph.add_edge("acknowledge", "context_retriever")
    graph.add_edge("context_retriever", "llm_reasoning")
    graph.add_edge("llm_reasoning", "dispatcher")
    graph.add_edge("dispatcher", END)

    return graph.compile()





_agent = None


def get_agent():
    """
    Get the compiled LangGraph agent (lazy singleton).
    Built on first call, then cached.
    """
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent
