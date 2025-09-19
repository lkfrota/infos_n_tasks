from email import message
from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

from typing import List
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

class MessagesState(MessagesState):
    # Add any keys needed beyond messages, which is pre-built 
    pass

# Node
def llm(state: MessagesState):
    structured_llm = llmodel.with_structured_output(SuggestionClasses)
    suggestion = structured_llm.invoke(state["messages"])
    return {"messages": [HumanMessage(content=f"Proposta estruturada: {suggestion.model_dump_json()}")]}
    
# Build graph
builder = StateGraph(MessagesState)
builder.add_node("llm", llm)
builder.add_edge(START, "llm")
builder.add_edge("llm", END)
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "1"}}


def stream_graph_updates(message_list):
    for event in graph.stream({"messages": message_list}, config):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

stream_graph_updates([SystemMessage(content=PROMPT_ORGANIZADOR),
                                HumanMessage(content=f'\nTexto para análise:\n{item_teste}')])

while True:
    user_input = input('User: ')
    if user_input.lower() in ['quit', 'q']:
        break
    stream_graph_updates([HumanMessage(content=user_input),])




"""from typing_extensions import TypedDict

class State(TypedDict):
    graph_state: str

def node_1(state: State) -> State:
    print("---Node 1---")
    return {"graph_state": state['graph_state'] +" I am"}

def node_2(state: State) -> State:
    print("---Node 2---")
    return {"graph_state": state['graph_state'] +" happy!"}

def node_3(state: State) -> State:
    print("---Node 3---")
    return {"graph_state": state['graph_state'] +" sad!"}

import random
from typing import Literal

def decide_mood(state: State) -> Literal["node_2", "node_3"]:
    
    # Often, we will use state to decide on the next node to visit
    user_input = state['graph_state'] 
    
    # Here, let's just do a 50 / 50 split between nodes 2, 3
    if random.random() < 0.5:

        # 50% of the time, we return Node 2
        return "node_2"
    
    # 50% of the time, we return Node 3
    return "node_3"


from langgraph.graph import StateGraph, START, END

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

output = graph.invoke({"graph_state": "Hi, this is me."})
print(output['graph_state'])"""