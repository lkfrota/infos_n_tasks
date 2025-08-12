from typing import List
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.google import Gemini

from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')

# Define o modelo Pydantic para a saída estruturada do Agente.
# Isso garante que a resposta do LLM seja sempre neste formato.
class Suggestion(BaseModel):
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

# Instruções para o agente.
# A instrução se concentra na lógica de negócio, não na formatação.
PROMPT_INSTRUCOES = """
Você é um assistente especializado em processar textos brutos e classificá-los
em Informações, Ideias e Tarefas.
 
Sua tarefa é analisar o conteúdo e extrair todas as Informações, Ideias e Tarefas
relevantes.

As Informações são fatos ou dados objetivos.
As Ideias são pensamentos de alto nível, vagos ou indecisos.
As Tarefas são ações concretas e executáveis.
 
Seja detalhado e extraia todos os itens relevantes para cada categoria.
Cada item deve ser completo com seu contexto, para ser compreendido isoladamente dos outros itens extraidos.
"""

# Criação do Agente com o modelo do Gemini e o response_model Pydantic.
agente_real = Agent(
    model=Gemini(id="gemini-2.0-flash-lite"),
    description="Agente que processa textos brutos e gera sugestões estruturadas.",
    instructions=PROMPT_INSTRUCOES,
    response_model=Suggestion,
    stream=False # Habilita o streaming para uma melhor experiência
)

if __name__ == "__main__":
    # Exemplo de uso para demonstração
    texto_exemplo = "A Patagônia é linda e selvagem. Preciso pesquisar sobre viagens para lá e preparar meu carro antes."
    
    print("Processando o texto de exemplo com o agente real...")
    
    # O método run retorna um objeto Suggestion diretamente
    resposta_agente = agente_real.run(message=texto_exemplo)
    
    print("\n--- Saída do Agente ---")
    print(f"Tipo do objeto: {type(resposta_agente)}")
    print("\nInformacoes:")
    for info in resposta_agente.informacoes:
        print(f"- {info}")
    
    print("\nIdeias:")
    for ideia in resposta_agente.ideias:
        print(f"- {ideia}")
        
    print("\nTarefas:")
    for tarefa in resposta_agente.tarefas:
        print(f"- {tarefa}")