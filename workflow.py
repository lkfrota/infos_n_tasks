from agno.workflow.v2 import Loop, Step, Workflow
from agno.workflow.v2.types import StepOutput, StepInput, RunResponse
from agente_real import agente_real, Suggestion
from agente_aprovacao import agente_aprovacao, ApprovalDecision
from modelo import session, Informacao, Ideia, Tarefa
from typing import List, Dict, Any

# Vari\u00e1vel global para armazenar o hist\u00f3rico da conversa e do loop.
# Esta \u00e9 a solu\u00e7\u00e3o para garantir que o estado \u00e9 persistido entre as itera\u00e7\u00f5es do Loop.
historico_de_interacoes: List[Dict[str, Any]] = []

def interagir_com_usuario_e_sugerir(step_input: StepInput) -> StepOutput:
    """
    Fun\u00e7\u00e3o que executa o agente real, interage com o usu\u00e1rio e gerencia
    o hist\u00f3rico da conversa usando a vari\u00e1vel global.
    """
    global historico_de_interacoes
    
    prompt_estruturado = ""
    if not historico_de_interacoes:
        # Se for a primeira rodada, use a mensagem original.
        prompt_estruturado = f"Mensagem original da caixa de entrada: {step_input.message}"
    else:
        # Se for uma itera\u00e7\u00e3o seguinte, use o \u00faltimo estado do hist\u00f3rico global.
        previous_state = historico_de_interacoes[-1]
        sugestao_anterior = previous_state.get("sugestao")
        feedback_usuario = previous_state.get("feedback_usuario")
        decisao_agente = previous_state.get("decisao_agente")
        
        # Constr\u00f3i um prompt detalhado com o hist\u00f3rico da conversa.
        prompt_estruturado = f"""
        Mensagem original da caixa de entrada: {step_input.message}

        Sugest\u00e3o do agente na rodada anterior:
        Informa\u00e7\u00f5es: {sugestao_anterior.get('informacoes')}
        Ideias: {sugestao_anterior.get('ideias')}
        Tarefas: {sugestao_anterior.get('tarefas')}

        O usu\u00e1rio deu o seguinte feedback para revis\u00e7\u00e3o:
        "{feedback_usuario}"
        Decis\u00e3o do agente de aprova\u00e7\u00e3o: {decisao_agente.get('decision')}, Motivo: {decisao_agente.get('motivo')}

        Gere uma nova sugest\u00e3o revisada com base na mensagem original e no feedback do usu\u00e1rio.
        """
        
    # --- LOG DE DEBBUGING ---
    print("\n--- DEBUG: Prompt enviado para o Agente Real ---")
    print(prompt_estruturado)
    print("-------------------------------------------------")
    # --- FIM DO LOG DE DEBBUGING ---

    # Executa o agente real com o prompt estruturado.
    sugestao_do_agente: RunResponse = agente_real.run(message=prompt_estruturado)
    
    # Imprime a sugest\u00e3o do agente para o usu\u00e1rio
    print("\n--- Sugest\u00e3o do Agente ---")
    print("\nInformacoes:")
    for info in sugestao_do_agente.content.informacoes:
        print(f"- {info}")
    print("\nIdeias:")
    for ideia in sugestao_do_agente.content.ideias:
        print(f"- {ideia}")
    print("\nTarefas:")
    for tarefa in sugestao_do_agente.content.tarefas:
        print(f"- {tarefa}")
    
    # Pede a valida\u00e7\u00e3o do usu\u00e1rio
    feedback = input("\nA sugest\u00e3o est\u00e1 correta? (sim/n\u00e3o) ")

    # Adiciona a decis\u00e3o do agente de aprova\u00e7\u00e3o aqui, para ser usada no pr\u00f3ximo prompt e na condi\u00e7\u00e3o de parada.
    decisao_agente = agente_aprovacao.run(message=feedback).content.model_dump()
    print(f"\nAgente de Aprova\u00e7\u00e3o: Decis\u00e3o: {decisao_agente.get('decision')}, Motivo: {decisao_agente.get('motivo')}")

    # Adiciona o estado completo da rodada ao hist\u00f3rico global.
    historico_de_interacoes.append({
        "sugestao": sugestao_do_agente.content.model_dump(),
        "feedback_usuario": feedback,
        "decisao_agente": decisao_agente
    })

    # Retorna o \u00faltimo estado para que o pr\u00f3ximo passo externo ao loop tenha acesso.
    return StepOutput(content=historico_de_interacoes[-1])

def end_condition_semantica(outputs: List[StepOutput]) -> bool:
    """
    Condi\u00e7\u00e3o de encerramento do loop. Agora, usa a vari\u00e1vel global.
    """
    global historico_de_interacoes
    if not historico_de_interacoes:
        return False
        
    last_state = historico_de_interacoes[-1]
    decisao_agente = last_state.get("decisao_agente")
    
    return decisao_agente.get('decision') == 'aprovar'

def criar_objetos_no_banco(step_input: StepInput) -> StepOutput:
    """
    Fun\u00e7\u00e3o final para criar os objetos no banco de dados.
    Verifica se a aprova\u00e7\u00e3o foi dada antes de persistir os dados.
    """
    global historico_de_interacoes
    try:
        # Acessa o estado final do hist\u00f3rico global.
        if not historico_de_interacoes:
            return StepOutput(
                success=False,
                content="Workflow finalizado sem hist\u00f3rico de intera\u00e7\u00f5es."
            )
            
        last_state = historico_de_interacoes[-1]
        decisao_final = last_state.get("decisao_agente")
        
        if decisao_final.get('decision') != 'aprovar':
            return StepOutput(
                success=False,
                content=f"Workflow finalizado sem aprova\u00e7\u00e3o. Decis\u00e3o final: '{decisao_final.get('decision')}'."
            )

        dados_validados_dict = last_state.get("sugestao")
        dados_validados: Suggestion = Suggestion.model_validate(dados_validados_dict)

        print("\nCriando objetos no banco de dados...")
        
        for info_conteudo in dados_validados.informacoes:
            nova_informacao = Informacao(conteudo=info_conteudo)
            session.add(nova_informacao)
        
        for ideia_conteudo in dados_validados.ideias:
            nova_ideia = Ideia(conteudo=ideia_conteudo)
            session.add(nova_ideia)
            
        for tarefa_conteudo in dados_validados.tarefas:
            nova_tarefa = Tarefa(conteudo=tarefa_conteudo)
            session.add(nova_tarefa)
        
        session.commit()
        
        # Limpa o hist\u00f3rico global ap\u00f3s a conclus\u00e3o do workflow.
        historico_de_interacoes = []
        
        return StepOutput(
            success=True,
            content="Objetos criados com sucesso!"
        )
    except Exception as e:
        session.rollback()
        # Limpa o hist\u00f3rico global em caso de erro.
        historico_de_interacoes = []
        return StepOutput(
            success=False,
            content=f"Erro ao salvar no banco de dados: {e}"
        )

# Define o fluxo de trabalho
workflow = Workflow(
    name="Workflow de Processamento da Caixa de Entrada",
    description="Processa um item da Caixa de Entrada, valida com o usu\u00e1rio e salva no banco de dados.",
    steps=[
        Loop(
            name="Validacao Humana",
            steps=[
                Step(
                    name="Sugestao e Interacao",
                    executor=interagir_com_usuario_e_sugerir,
                ),
            ],
            end_condition=end_condition_semantica,
            max_iterations=3
        ),
        Step(
            name="Criacao de Objetos",
            executor=criar_objetos_no_banco
        )
    ]
)

if __name__ == "__main__":
    # Teste o fluxo de trabalho com um item fictício da caixa de entrada
    item_teste = "Copel afirma não haver créditos para realocar do apartamento antigo, e indeferiu meu pedido. Preciso entender o que a Copel está fazendo."
    response = workflow.run(message=item_teste)
    
    print("\n--- Resultado do Workflow ---")
    print(response.content)
