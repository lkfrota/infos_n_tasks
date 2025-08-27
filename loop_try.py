from agno.workflow.v2 import Loop, Step, Workflow
from agno.workflow.v2.types import StepOutput
from agno.memory.v2 import Memory

from agno.agent import Agent
from agno.models.google import Gemini

from typing import List, Literal
from pydantic import BaseModel, Field

from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')

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

class ApprovalDecision(BaseModel):
    decision: Literal['aprovar', 'revisar'] = Field(
        ...,
        description="A decisão do usuário, deve ser 'aprovar' ou 'revisar'."
    )
    motivo: str = Field(
        ...,
        description="O motivo da decisão. Se for 'aprovar', descreva brevemente. Se for 'revisar', explique o que precisa ser ajustado."
    )

INSTRUCOES_SUGESTOES = """
Você é um assistente especializado em processar pequenos textos de visões cotidianas do usuário e classificá-los
em Informações, Ideias e Tarefas.
 
Sua tarefa é analisar o conteúdo e extrair todas as Informações, Ideias e Tarefas
relevantes.

As Informações são fatos ou dados objetivos do mundo real.
As Ideias são pensamentos e desejos, vagos ou indecisos.
As Tarefas são ações claras, definidas e executáveis.
 
Seja detalhado e extraia todos os itens relevantes para cada categoria.
Cada item deve ser completo com seu contexto, para ser compreendido isoladamente dos outros itens extraidos.
"""

INSTRUCOES_APROVACAO = """
Você é um avaliador de aprovação. Sua única tarefa é analisar a última mensagem do usuário.
A mensagem de entrada é a resposta do usuário a uma sugestão que você fez.
 
- Se a mensagem expressar aprovação de forma clara (ex: 'sim', 'ok', 'está bom', 'concordo', 'pode seguir em frente'),
  sua decisão deve ser 'aprovar'.
- Se a mensagem pedir por revisão ou modificação (ex: 'mude isso', 'não concordo', 'adicione aquilo', 'remova', 'descarte', 'não gostei'),
  sua decisão deve ser 'revisar'.

A sua resposta deve ser estritamente um objeto JSON com as chaves 'decision' e 'motivo',
de acordo com o modelo de dados fornecido.

Priorize a intenção de revisão sobre a aprovação. Por exemplo, se a mensagem for "Ok, mas remova a tarefa",
a decisão deve ser "revisar".

Na sua resposta passe a instrução completa e explícita da correção/alteração/supressão/adição se houver.
"""

deco_agent = Agent(
    model=Gemini(id="gemini-2.0-flash-lite"),
    role="Especialista em categorizar textos.",
    description="Agente que processa textos brutos e gera sugestões estruturadas.",
    instructions=INSTRUCOES_SUGESTOES,
    markdown=True,
    response_model=Suggestion,
    add_history_to_messages=True,
    num_history_runs=3,
    #debug_mode=True
)

apro_agent = Agent(
    model=Gemini(id="gemini-2.0-flash-lite"),
    role="Especialista em verificar aprovação de usuário.",
    description="Agente que determina se a resposta do usuário é uma aprovação.",
    instructions=INSTRUCOES_APROVACAO,
    markdown=True,
    response_model=ApprovalDecision,
    add_history_to_messages=True,
    num_history_runs=3,
    debug_mode=True
)

'''deco_step = Step(
    name="Melhorando",
    agent=deco_agent,
    description="Processa textos brutos e gera sugestões estruturadas.",
)

def end_condition(outputs: List[StepOutput]) -> bool:
    """
    Condição de encerramento simples que verifica apenas se foi aprovado.
    """
    if not outputs:
        return False
        
    last_output = outputs[-1]
    # O content agora é diretamente o output do agente unificado
    aprovado = last_output.content.aprovado
    print(f"\n--- DEBUG: End Condition ---")
    print(f"Aprovado: {aprovado}")
    print(f"Motivo: {last_output.content.motivo}")
    print("---------------------------")
    return aprovado

def mock_salva_dado():
    return print("Dado Salvo!")

workflow = Workflow(
    name="Processamento da Caixa de Entrada.",
    description="Processa texto até aprovação e salva.",
    steps=[
        Loop(
            name="Loop melhorando",
            steps=[deco_step],
            end_condition=end_condition,
            max_iterations=3,  # Maximum 3 iterations
        ),
        mock_salva_dado,
    ],
)'''

item_teste = "Copel afirma não haver créditos para realocar do apartamento antigo, e indeferiu meu pedido. Preciso entender o que a Copel está fazendo."
resposta = deco_agent.run(message=item_teste)
sugestao = resposta.content
approved = False
while not approved:
    print(sugestao)
    usur = input('Esse arranjo está bom? ')
    
    # Cria uma mensagem para o agente de aprovação
    mensagem_usuario = f"""
    Perguntado se o arranjo ficou bom, o usuário manifestou o seguinte:
    {usur}
    """
    
    resposta = apro_agent.run(message=mensagem_usuario)
    aprovacao = resposta.content
    approved = True if aprovacao.decision == 'aprovar' else False
    print(aprovacao)
    
    if not approved:
        # Se não foi aprovado, processa novamente com o feedback
        resposta = deco_agent.run(message=aprovacao)
        sugestao = resposta.content

#print(response)