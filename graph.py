from dotenv import load_dotenv
import os
load_dotenv(override=True)
google_api_key = os.getenv('GOOGLE_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

from typing import List, Optional, Tuple
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field
from prompts import PROMPT_ORGANIZADOR
from modelo import session, Informacao, Ideia, Tarefa, CaixaEntrada

llmodel = init_chat_model("google_genai:gemini-2.0-flash-lite")

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

def processar_item_com_llm(conteudo: str, messages_history: Optional[List] = None) -> SuggestionClasses:
    """Processa um item da CaixaEntrada usando LLM e retorna a proposta estruturada."""
    if messages_history is None:
        messages = [
            SystemMessage(content=PROMPT_ORGANIZADOR),
            HumanMessage(content=f"\nTexto para análise:\n{conteudo}")
        ]
    else:
        messages = messages_history
    
    structured_llm = llmodel.with_structured_output(SuggestionClasses)
    suggestion = structured_llm.invoke(messages)
    return suggestion

def exibir_proposta_para_revisao(proposal: SuggestionClasses) -> Tuple[bool, Optional[str]]:
    """Exibe a proposta para revisão humana e retorna (aprovado, feedback)."""
    print(f"\n=== PROPOSTA PARA REVISÃO ===")
    print(f"Informações: {proposal.informacoes}")
    print(f"Ideias: {proposal.ideias}")
    print(f"Tarefas: {proposal.tarefas}")
    print("=" * 50)
    
    while True:
        resposta = input("\nAprovar esta proposta? (s/n/feedback): ").strip()
        resposta_lower = resposta.lower()
        
        if resposta_lower in ['s', 'sim', 'y', 'yes', 'ok']:
            return True, None
        elif resposta_lower in ['n', 'não', 'nao', 'no']:
            return False, None
        elif resposta:
            # Feedback fornecido - retorna o feedback para reprocessamento
            print("📝 Feedback recebido, reprocessando...")
            return False, resposta
        else:
            print("Por favor, responda com 's' para aprovar, 'n' para rejeitar, ou forneça feedback.")

def salvar_proposta(proposal: SuggestionClasses) -> bool:
    """Salva a proposta aprovada no banco de dados."""
    try:
        for info_conteudo in proposal.informacoes:
            session.add(Informacao(conteudo=info_conteudo))
        for ideia_conteudo in proposal.ideias:
            session.add(Ideia(conteudo=ideia_conteudo))
        for tarefa_conteudo in proposal.tarefas:
            session.add(Tarefa(conteudo=tarefa_conteudo))
        session.commit()
        print("✅ Objetos criados com sucesso no banco de dados.")
        return True
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao salvar no banco de dados: {e}")
        return False

def remover_item_da_caixa_entrada(item_id: int) -> bool:
    """Remove o item processado da CaixaEntrada."""
    try:
        item = session.get(CaixaEntrada, item_id)
        if item is not None:
            session.delete(item)
            session.commit()
            print(f"✅ Item {item_id} removido da Caixa de Entrada.")
            return True
        else:
            print(f"⚠️ Item {item_id} não encontrado para remoção.")
            return False
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao remover item {item_id}: {e}")
        return False

def processar_caixa_entrada():
    """Processa todos os itens da CaixaEntrada sequencialmente."""
    print("=== Iniciando processamento da Caixa de Entrada ===")
    
    while True:
        # 1. Buscar próximo item
        item = session.query(CaixaEntrada).order_by(CaixaEntrada.id.asc()).first()
        if not item:
            print("✅ Nenhum item na Caixa de Entrada. Processamento encerrado.")
            break
            
        print(f"\n🔄 Processando Item {item.id}")
        print(f"Conteúdo: {item.conteudo_bruto[:100]}...")
        
        # Inicializar histórico de mensagens
        messages_history = [
            SystemMessage(content=PROMPT_ORGANIZADOR),
            HumanMessage(content=f"\nTexto para análise:\n{item.conteudo_bruto}")
        ]
        
        # 2. Loop de processamento com feedback
        while True:
            try:
                proposal = processar_item_com_llm(item.conteudo_bruto, messages_history)
            except Exception as e:
                print(f"❌ Erro ao processar item com LLM: {e}")
                break
            
            # 3. Review gate (sempre necessário)
            if not proposal.aprovado:
                aprovado, feedback = exibir_proposta_para_revisao(proposal)
                
                if aprovado:
                    # Aprovado pelo usuário
                    break
                elif feedback:
                    # Feedback fornecido - adicionar ao histórico e reprocessar
                    # Adiciona a resposta anterior da IA
                    ai_response = f"Sugestão anterior:\nInformações: {proposal.informacoes}\nIdeias: {proposal.ideias}\nTarefas: {proposal.tarefas}"
                    messages_history.append(AIMessage(content=ai_response))
                    # Adiciona o feedback do usuário
                    messages_history.append(HumanMessage(content=f"Feedback do usuário: {feedback}\n\nPor favor, revise e melhore a análise considerando este feedback."))
                    print("🔄 Reprocessando com feedback...")
                    continue
                else:
                    # Rejeitado sem feedback
                    print("❌ Item rejeitado, mantido na Caixa de Entrada.")
                    proposal = None
                    break
            else:
                # Já aprovado pelo LLM
                break
        
        # Se não temos proposta aprovada, pular para próximo item
        if proposal is None:
            continue
            
        # 4. Salvar apenas se aprovado
        if salvar_proposta(proposal):
            # 5. Remover da CaixaEntrada APÓS confirmação de salvamento
            if remover_item_da_caixa_entrada(item.id):
                print(f"✅ Item {item.id} processado com sucesso!")
            else:
                print(f"⚠️ Item {item.id} salvo mas não removido da Caixa de Entrada.")
        else:
            print(f"❌ Falha ao salvar item {item.id}, mantido na Caixa de Entrada.")

if __name__ == "__main__":
    processar_caixa_entrada()