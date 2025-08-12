from typing import Literal
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.google import Gemini

from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')

# Define o modelo Pydantic para a saída estruturada do Agente.
# A resposta deve ser estritamente 'aprovar' ou 'revisar'.
class ApprovalDecision(BaseModel):
    decision: Literal['aprovar', 'revisar'] = Field(
        ...,
        description="A decisão do usuário, deve ser 'aprovar' ou 'revisar'."
    )
    motivo: str = Field(
        ...,
        description="O motivo da decisão. Se for 'aprovar', descreva brevemente. Se for 'revisar', explique o que precisa ser ajustado."
    )

# Instruções para o agente.
PROMPT_INSTRUCOES = """
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

# Criação do Agente com o modelo do Gemini e o response_model Pydantic.
agente_aprovacao = Agent(
    model=Gemini(id="gemini-2.0-flash-lite"),
    description="Agente que determina se a resposta do usuário é uma aprovação.",
    instructions=PROMPT_INSTRUCOES,
    response_model=ApprovalDecision,
    stream=False
)

if __name__ == "__main__":
    # Exemplo de uso para demonstração
    texto_aprovacao = "Sim, está perfeito, pode seguir em frente."
    texto_revisao = "Não concordo com a ideia, por favor remova."
    texto_revisao_nuancada = "Ok, mas pode discartar a info de indeferimento."
    
    print("Processando aprovação...")
    decisao_aprovacao = agente_aprovacao.run(message=texto_aprovacao)
    print(f"Decisão: {decisao_aprovacao.content.decision}, Motivo: {decisao_aprovacao.content.motivo}")
    
    print("\nProcessando revisão...")
    decisao_revisao = agente_aprovacao.run(message=texto_revisao)
    print(f"Decisão: {decisao_revisao.content.decision}, Motivo: {decisao_revisao.content.motivo}")

    print("\nProcessando revisão (nuançado)...")
    decisao_revisao_nuancada = agente_aprovacao.run(message=texto_revisao_nuancada)
    print(f"Decisão: {decisao_revisao_nuancada.content.decision}, Motivo: {decisao_revisao_nuancada.content.motivo}")
