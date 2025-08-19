import random
from agno.agent.agent import Agent
from agno.models.google import Gemini
from agno.workflow.v2 import Loop, Step, Workflow
from agno.workflow.v2.types import StepOutput, StepInput
from typing import Dict, Any, List
import json

from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')
gemini = Gemini(id="gemini-2.0-flash-lite")

# --- 2. Funções Auxiliares (ferramentas e lógica) ---

def user_feedback_simulator(input_message: str) -> str:
    """
    Simula a interação do usuário. 
    A primeira interação reprova a proposta. A segunda reprova. A terceira aprova.
    """
    if "Frase 1: Amanhã iremos viajar. Frase 2: Iremos para a praia onde tenho casa. Frase 3: Iremos após o café da manhã." in input_message:
        return "Não, pode juntar as frases 1 e 3."
    elif "Frase 1: Amanhã iremos viajar e depois tomaremos o café da manhã. Frase 2: Iremos para a praia onde tenho casa." in input_message:
        return "Não, tá errado."
    elif "Frase 1: Amanhã iremos viajar depois do café da manhã. Frase 2: Iremos para a praia onde tenho casa." in input_message:
        return "Agora sim, perfeito!"
    else:
        return "Gostei. Aprovado!"


# --- 3. Lógica do Workflow ---

def loop_end_condition(step_input: StepInput) -> bool:
    """
    Função para a end_condition do Loop.
    Usa o 'evaluator_agent' para decidir se o Loop deve parar.
    """
    # Acessa o estado compartilhado para o histórico
    state = step_input.workflow_session_state
    
    # Constrói o prompt para o agente avaliador com todo o histórico
    prompt_for_evaluator = (
        f"A frase original era: {state['original_phrase']}\n"
        f"Histórico de propostas e feedbacks:\n"
    )
    for i, historical_entry in enumerate(state.get('history', [])):
        prompt_for_evaluator += f"- Rodada {i+1}:\n"
        prompt_for_evaluator += f"  Proposta do agente: {historical_entry['proposal']}\n"
        prompt_for_evaluator += f"  Feedback do usuário: {historical_entry['user_feedback']}\n"
    
    # Simula a resposta do usuário para a última proposta
    last_proposal = step_input.previous_step_content
    user_response = user_feedback_simulator(last_proposal)
    
    # Adiciona a rodada atual ao histórico no estado
    if 'history' not in state:
        state['history'] = []
    
    state['history'].append({
        'proposal': last_proposal,
        'user_feedback': user_response,
    })
    
    # Chama o agente avaliador para tomar a decisão
    decision_response = evaluator_agent.run(prompt=f"{prompt_for_evaluator}\nÚltima proposta: {last_proposal}\nFeedback do usuário: {user_response}")

    # Verifica se a decisão foi 'Aprovado' para sair do loop
    is_approved = "Aprovado" in decision_response.content
    
    # Se não foi aprovado, salva a orientação para a próxima rodada
    if not is_approved:
        state['next_instruction'] = decision_response.content
    
    print(f"\n--- Agente Avaliador ({'Aprovado' if is_approved else 'Rejeitado'}) ---")
    print(decision_response.content)
    print("-------------------------------------------\n")
    
    return is_approved


def reducer_step_function(step_input: StepInput) -> StepOutput:
    """
    Função que processa o input e chama o agente redutor.
    Ela acumula o histórico e as instruções do avaliador na workflow_session_state.
    """
    state = step_input.workflow_session_state
    
    # Constrói o prompt inicial ou aprimorado com base no histórico
    prompt_for_reducer = (
        f"Você é um reduzidor de frases. Divida a frase abaixo em frases menores:\n"
        f"\"{state['original_phrase']}\"\n"
    )
    
    # Adiciona o histórico e as instruções da rodada anterior, se existirem
    if 'history' in state:
        for i, historical_entry in enumerate(state['history']):
            prompt_for_reducer += f"\nNa rodada {i+1} você propôs: \"{historical_entry['proposal']}\""
            prompt_for_reducer += f"\nMas foi reprovado. Feedback do usuário: \"{historical_entry['user_feedback']}\""
            if i > 0:
              prompt_for_reducer += f"\nMinha orientação anterior a você foi: \"{state['history'][i-1]['next_instruction']}\""
    
    if 'next_instruction' in state:
        prompt_for_reducer += f"\nInstrução da rodada anterior: \"{state['next_instruction']}\"\n"
        prompt_for_reducer += "Tente novamente."
    
    print(f"--- Agente Redutor recebe o prompt ---")
    print(prompt_for_reducer)
    print("-------------------------------------------\n")

    # Executa o agente redutor
    reducer_response = reducer_agent.run(prompt=prompt_for_reducer)
    
    return StepOutput(content=reducer_response.content)


class MockDatabase:
    """Simula um banco de dados para armazenar os resultados."""
    def __init__(self):
        self.data = []

    def save(self, content: Dict[str, str]):
        self.data.append(content)
        print(f"\n✅ Frases aprovadas salvas no banco de dados!")
        print(json.dumps(content, indent=2))
        print("-------------------------------------------\n")

database = MockDatabase()

def post_loop_function(step_input: StepInput) -> StepOutput:
    """
    Função que é executada após o Loop.
    Ela armazena a última proposta aprovada no mock de banco de dados.
    """
    state = step_input.workflow_session_state
    last_approved_proposal = state['history'][-1]['proposal']
    
    # Processa a string para criar um dicionário
    processed_output = {}
    lines = last_approved_proposal.strip().split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            key = f"container_{i+1}"
            value = line.split(': ', 1)[1]
            processed_output[key] = value

    # Salva no "banco de dados"
    database.save(processed_output)
    
    return StepOutput(content="Processamento pós-loop concluído. Verifique o banco de dados.")

# Agente Redutor de Frases (dentro do Loop)
reducer_agent = Agent(
    name="Frase Reducer Agent",
    model=gemini,
    tools=[reducer_step_function],
    instructions=[
        "Você é um especialista em reescrever frases, capaz de dividi-las em sentenças menores e mais claras.",
        "Seu objetivo é dividir uma frase longa em frases menores, garantindo que o significado original seja mantido.",
        "Você receberá a frase original e, em rodadas subsequentes, as propostas anteriores e o feedback do usuário.",
        "Use o feedback do usuário para refinar suas propostas na próxima rodada.",
        "Sua resposta deve ser uma lista numerada das novas frases, formatada como 'Frase 1:', 'Frase 2:', etc."
    ],
)

# Agente Avaliador (para a end_condition)
evaluator_agent = Agent(
    name="User Feedback Evaluator Agent",
    model=gemini,
    tools=[loop_end_condition],
    instructions=[
        "Você é um avaliador neutro, que analisa a aprovação do usuário sobre a divisão de frases feita por outro agente.",
        "Sua tarefa é ler a frase original, a proposta do agente e o feedback do usuário. ",
        "Você deve decidir se a proposta foi 'Aprovada' ou 'Rejeitada'.",
        "Se for 'Aprovada', sua resposta deve ser a palavra 'Aprovado' e nada mais. Isso irá parar o Loop.",
        "Se for 'Rejeitada', sua resposta deve ser um novo prompt para o agente redutor, explicando o que precisa ser corrigido, no máximo 3 frases.",
    ],
)


# --- 4. Construção do Workflow ---

# Cria o Step que vai usar a função reducer_step_function
reducer_step = Step(
    name="Reducer Step",
    agent=reducer_agent
)

# Cria o Loop com o step do agente e a end_condition
loop_step = Loop(
    name="Research Loop",
    steps=[reducer_step],
    end_condition=loop_end_condition,
    max_iterations=5  # Limite para evitar loops infinitos
)

# Cria o Step que vai ser executado após o Loop
post_loop_step = Step(
    name="Post Loop Processing",
    executor=post_loop_function
)

# Define o Workflow
workflow = Workflow(
    name="Frase Reducer Workflow",
    steps=[
        loop_step,
        post_loop_step
    ],
    # Inicializa o estado compartilhado com a frase original
    workflow_session_state={
        "original_phrase": "Amanhã iremos viajar para a praia onde tenho casa após o café da manhã",
        "history": [],  # Para acumular as propostas e feedbacks
        "next_instruction": "" # Para a próxima instrução do loop
    }
)

# --- 5. Execução do Workflow ---
if __name__ == "__main__":
    print("Iniciando o Workflow de Redução de Frases...")
    workflow.print_response(
        message="Divida a frase: 'Amanhã iremos viajar para a praia onde tenho casa após o café da manhã'",
        markdown=True
    )
    print("\n--- Estado Final do Workflow ---")
    print(f"Estado final da workflow_session_state:\n{json.dumps(workflow.workflow_session_state, indent=2)}")
