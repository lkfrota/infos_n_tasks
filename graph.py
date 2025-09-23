
from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

from typing import List, Optional
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field
from prompts import PROMPT_ORGANIZADOR

item_teste = "Copel afirma não haver créditos para realocar do apartamento antigo, e indeferiu meu pedido. Preciso entender o que a Copel está fazendo."

llmodel = init_chat_model("google_genai:gemini-2.0-flash-lite") # Use temperature aqui se quiser

class SuggestionClasses(BaseModel):
    informacoes: List[str] = Field(
        default_factory=list,
        description="Uma lista de fatos ou dados objetivos extraídos do texto."
    )
    ideias: List[str] = Field(
        default_factory=list,
        description="Uma lista de pensamentos de alto nível que precisam ser amadurecidos."
    )
    tarefas: List[str] = Field(
        default_factory=list,
        description="Uma lista de ações concretas e executáveis extraídas do texto."
    )
    aprovado: bool = Field(
        default=False,
        description="False inicialmente ou se precisa de revisão, True se a sugestão foi aprovada pelo usuário."
    )

class MessagesState(MessagesState):
    current_proposal: Optional[SuggestionClasses] = None

# Node
def llm(state: MessagesState):
    structured_llm = llmodel.with_structured_output(SuggestionClasses)
    suggestion = structured_llm.invoke(state["messages"])
    return {
        "messages": [HumanMessage(content=f"Proposta estruturada: {suggestion.model_dump_json()}")],
        "current_proposal": suggestion
    }

def review_gate(state: MessagesState):
    proposal = state["current_proposal"]
    if proposal.aprovado:
        return
    print(f"\n=== PROPOSTA PARA REVISÃO ===")
    print(f"Informações: {proposal.informacoes}")
    print(f"Ideias: {proposal.ideias}")
    print(f"Tarefas: {proposal.tarefas}")
    print("=" * 50)
    
    feedback = input("\nSeu feedback (enter para pular): ")
    if feedback.strip():
        return {"messages": [HumanMessage(content=f"Feedback do usuário: {feedback}")]}
    return {"messages": []}

def decision(state: MessagesState):
    if state["current_proposal"].aprovado:
        return "end"
    else:
        return "llm"

# Build graph
builder = StateGraph(MessagesState)
# Nodes
builder.add_node("llm", llm)
builder.add_node("review_gate", review_gate)
# Edges
builder.add_edge(START, "llm")
builder.add_edge("llm", "review_gate")

builder.add_conditional_edges("review_gate", decision, {"llm": "llm","end": END})
#builder.add_edge("review_gate", END) 

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

if False:
    try:
        graph.get_graph().draw_mermaid_png(output_file_path="grafo.png",  max_retries=3, retry_delay=2.0)
        print("Grafo salvo como grafo.png")
    except Exception as e:
        print(f"Erro ao gerar PNG: {e}")
        mermaid_code = graph.get_graph().draw_mermaid()
        print("=== CÓDIGO MERMAID ===")
        print(mermaid_code)
        print("Abra em: https://mermaid.live/")
    raise SystemExit
config = {"configurable": {"thread_id": "1"}}

def stream_graph_updates(message_list):
    for chunk in graph.stream({"messages": message_list}, config, stream_mode="values"):
        if isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]:
            last_content = chunk["messages"][-1].content
    if last_content is not None:
        print("Assistant:", last_content)
    return last_content

print("=== Iniciando análise ===")
stream_graph_updates([SystemMessage(content=PROMPT_ORGANIZADOR),
                     HumanMessage(content=f'\nTexto para análise:\n{item_teste}')])

