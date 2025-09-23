
from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

from typing import List, Optional, TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field
from prompts import PROMPT_ORGANIZADOR
from modelo import session, Informacao, Ideia, Tarefa, CaixaEntrada

#item_teste = "Copel afirma não haver créditos para realocar do apartamento antigo, e indeferiu meu pedido. Preciso entender o que a Copel está fazendo."

llmodel = init_chat_model("google_genai:gemini-2.0-flash-lite") # Use temperature aqui se quiser

class SuggestionClasses(BaseModel):
    """Estrutura de saída do LLM com fatos (informações), ideias, tarefas e status de aprovação."""
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

class AppState(MessagesState):
    """Estado do grafo estendendo MessagesState com a proposta atual estruturada e id do item atual."""
    current_proposal: Optional[SuggestionClasses] = None
    current_input_id: Optional[int] = None

class LlmOutput(TypedDict):
    """Payload retornado pelo nó LLM."""
    messages: List[AIMessage]
    current_proposal: SuggestionClasses

class ReviewGateOutput(TypedDict):
    """Payload retornado pelo nó de revisão com feedback opcional do usuário."""
    messages: List[HumanMessage]

class StoreOutput(TypedDict):
    """Payload retornado pelo nó de armazenamento (mensagem de confirmação)."""
    messages: List[AIMessage]

class FetchOutput(TypedDict):
    """Payload retornado pelo nó de busca do próximo item da caixa de entrada."""
    messages: List[SystemMessage | HumanMessage | AIMessage]
    current_input_id: Optional[int]

class ConsumeOutput(TypedDict):
    """Payload retornado pelo nó de consumo/remoção do item processado."""
    messages: List[AIMessage]
    current_input_id: Optional[int]

# Node
def fetch_input(state: AppState) -> FetchOutput:
    """Busca o próximo item da CaixaEntrada. Se houver, injeta mensagens iniciais e armazena o id; caso contrário, informa que não há itens."""
    next_item = session.query(CaixaEntrada).order_by(CaixaEntrada.id.asc()).first()
    if next_item is None:
        return {
            "messages": [AIMessage(content="Nenhum item na Caixa de Entrada. Processamento encerrado.")],
            "current_input_id": None,
        }
    # Usar o campo correto 'conteudo_bruto' do modelo
    content = next_item.conteudo_bruto
    initial_messages: List[SystemMessage | HumanMessage] = [
        SystemMessage(content=PROMPT_ORGANIZADOR),
        HumanMessage(content=f"\nTexto para análise:\n{content}")
    ]
    return {"messages": initial_messages, "current_input_id": next_item.id}


def llm(state: AppState) -> LlmOutput:
    """Gera uma proposta estruturada via LLM e adiciona uma mensagem do assistente ao histórico."""
    structured_llm = llmodel.with_structured_output(SuggestionClasses)
    suggestion = structured_llm.invoke(state["messages"])
    return {
        "messages": [AIMessage(content=f"Proposta estruturada: {suggestion.model_dump_json()}")],
        "current_proposal": suggestion
    }

def review_gate(state: AppState) -> ReviewGateOutput | None:
    """Exibe a proposta para revisão humana e captura feedback opcional; retorna mensagem de feedback quando houver."""
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

# Persistência real usando modelo.py
def store(state: AppState) -> StoreOutput:
    """Cria registros em banco para a proposta aprovada e retorna confirmação ou erro."""
    proposal = state["current_proposal"]
    if proposal is None:
        return {"messages": [AIMessage(content="Nenhuma proposta presente para armazenar.")]}
    try:
        for info_conteudo in proposal.informacoes:
            session.add(Informacao(conteudo=info_conteudo))
        for ideia_conteudo in proposal.ideias:
            session.add(Ideia(conteudo=ideia_conteudo))
        for tarefa_conteudo in proposal.tarefas:
            session.add(Tarefa(conteudo=tarefa_conteudo))
        session.commit()
        return {"messages": [AIMessage(content="Objetos criados com sucesso no banco de dados.")]}
    except Exception as e:
        session.rollback()
        return {"messages": [AIMessage(content=f"Erro ao salvar no banco de dados: {e}")]}


def consume_input(state: AppState) -> ConsumeOutput:
    """Remove o item atual da CaixaEntrada após processamento bem-sucedido."""
    item_id = state["current_input_id"]
    if item_id is None:
        return {"messages": [AIMessage(content="Nenhum item para consumir.")], "current_input_id": None}
    try:
        item = session.get(CaixaEntrada, item_id)
        if item is not None:
            session.delete(item)
            session.commit()
            return {"messages": [AIMessage(content=f"Item {item_id} removido da Caixa de Entrada.")], "current_input_id": None}
        return {"messages": [AIMessage(content=f"Item {item_id} não encontrado para remoção.")], "current_input_id": None}
    except Exception as e:
        session.rollback()
        return {"messages": [AIMessage(content=f"Erro ao remover item {item_id}: {e}")], "current_input_id": None}


def input_decision(state: AppState) -> str:
    """Decide se há item para processar: 'llm' quando há, 'end' quando acabou."""
    return "llm" if state.get("current_input_id") else "end"


def decision(state: AppState) -> str:
    """Define o próximo passo: retorna 'store' se aprovado; caso contrário, retorna 'llm'."""
    if state["current_proposal"].aprovado:
        return "store"
    else:
        return "llm"

# Build graph
builder = StateGraph(AppState)
# Nodes
builder.add_node("fetch_input", fetch_input)
builder.add_node("llm", llm)
builder.add_node("review_gate", review_gate)
builder.add_node("store", store)
builder.add_node("consume_input", consume_input)
# Edges
builder.add_edge(START, "fetch_input")

builder.add_conditional_edges("fetch_input", input_decision, {"llm": "llm", "end": END})

builder.add_edge("llm", "review_gate")

builder.add_conditional_edges("review_gate", decision, {"llm": "llm","store": "store"})

builder.add_edge("store", "consume_input")

builder.add_edge("consume_input", "fetch_input")

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

def maybe_generate_grafo_png_with_fallback() -> None:
    """Pergunta ao usuário se deseja gerar o PNG do grafo; em erro, imprime o Mermaid como fallback."""
    user_input = input("\nGerar grafo como PNG? (enter para não / nome do arquivo para sim): ").strip()
    if not user_input:
        return
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=user_input,  max_retries=3, retry_delay=2.0)
        print(f"Grafo salvo como {user_input}")
    except Exception as e:
        print(f"Erro ao gerar PNG: {e}")
        mermaid_code = graph.get_graph().draw_mermaid()
        print("=== CÓDIGO MERMAID ===")
        print(mermaid_code)
        print("Abra em: https://mermaid.live/")
    raise SystemExit

config = {"configurable": {"thread_id": "1"}}

def stream_graph_updates(message_list: List[SystemMessage | HumanMessage]) -> Optional[str]:
    """Executa o grafo em stream e retorna o último conteúdo de mensagem produzido pelo assistente."""
    last_content = None
    for chunk in graph.stream({"messages": message_list}, config, stream_mode="values"):
        if isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]:
            last_content = chunk["messages"][-1].content
    if last_content is not None:
        print("Assistant:", last_content)
    return last_content

maybe_generate_grafo_png_with_fallback()
print("=== Iniciando análise (loop CaixaEntrada) ===")
# Inicia com histórico vazio; fetch_input irá abastecer
stream_graph_updates([])

