# Fluxo global do aplicaitvo

# Por um bot do Telegram o usuário envia uma mensagem especificando o que quer fazer
# Exemplo: "Oi, tenho um novo item para minha caixa de entrada." ou "Coloca isso na minha caixa de entrada"
# E o aplicativo, suportado nessa etapa por um llm, entende e aguarda o tal item.

# Seguindo esse fluxo o usuário escreve o tal conteúdo para a caixa de entrada
# O llm capta o tal conteúdo e grava na base de dados conforme a classe CaixaEntrada definida em modelo.py

# Em seguida o llm informa o usuário do estado da caixa de entrada: quantos itens, última vez que processou os itens de lá, etc.
# O llm também oferece de processar os itens agora

# O usuário envia uma mensagem pelo bot Telegram informando que quer processar a caixa de entrada agora
# O llm inicia o loop de processamento da Caixa de entrada conforme existente no graph.py ou graph_langgraph_backup.py
# O processamento acontece pelo chat do bot Telegram


import os
from dotenv import load_dotenv
from typing import Optional
from modelo import session, CaixaEntrada
from graph import processar_item_com_llm, salvar_proposta, remover_item_da_caixa_entrada
from pydantic import BaseModel, Field
from functools import wraps

# Telegram bot (python-telegram-bot v21+)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# LLM setup
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv(override=True)
allowed_user = int(os.getenv("TELEGRAM_ALLOWED_USER"))
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize LLM
llm = init_chat_model("google_genai:gemini-2.0-flash-lite")

# System prompt for the Telegram bot
SYSTEM_PROMPT = """Você é um assistente pessoal para gestão de informações, ideias e tarefas.

Você pode ajudar o usuário a:
- Adicionar itens à Caixa de Entrada
- Verificar o status da Caixa de Entrada
- Processar itens da Caixa de Entrada

Quando o usuário quiser adicionar algo à Caixa de Entrada, use a ferramenta disponível.
Seja amigável e útil nas suas respostas."""

class EstadoProcessamento:
    def __init__(self):
        self.processando = False
        self.aguardando_revisao = False
        self.proposta_atual = None
        self.item_atual = None
        self.messages_history = None

# Instância global
estado_processamento = EstadoProcessamento()

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id != allowed_user:
            await update.message.reply_text(f"Desculpe, não tenho permissão para falar com você: {user_id}")
            print(f"Acesso negado para o User ID: {user_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapped

# Tool definition for adding to Caixa de Entrada
@tool
def adicionar_na_caixa_entrada(conteudo: str) -> str:
    """Adiciona um item à Caixa de Entrada do usuário.
    
    Args:
        conteudo: O texto a ser adicionado à Caixa de Entrada
        
    Returns:
        Confirmação da adição com o ID do item
    """
    item = CaixaEntrada(conteudo_bruto=conteudo.strip())
    session.add(item)
    session.commit()
    return f"Item adicionado à Caixa de Entrada com ID {item.id}"

@tool
def verificar_status_caixa_entrada() -> str:
    """Verifica quantos itens há na Caixa de Entrada.
    
    Returns:
        Número de itens na Caixa de Entrada
    """
    total = session.query(CaixaEntrada).count()
    return f"Há {total} itens na Caixa de Entrada"

@tool
def processar_caixa_entrada() -> str:
    """Processa todos os itens da Caixa de Entrada.
    
    Returns:
        Confirmação do processamento
    """
    return "Iniciando processamento da Caixa de Entrada via Telegram..."

# Bind tools to LLM
llm_with_tools = llm.bind_tools([adicionar_na_caixa_entrada, verificar_status_caixa_entrada, processar_caixa_entrada])
# Global conversation history (single user)
conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]

@restricted
async def process_message_with_llm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user message with LLM and handle tool calls."""
    
    # Se está aguardando revisão, processar resposta
    if estado_processamento.aguardando_revisao:
        await processar_resposta_revisao(update, context)
        return
    
    if update.message is None or update.message.text is None:
        return
    
    user_message = update.message.text.strip()
    
    if not user_message:
        return
    
    # Add user message to conversation
    conversation_history.append(HumanMessage(content=user_message))
    
    try:
        # Get LLM response
        response = llm_with_tools.invoke(conversation_history)
        
        # Add AI response to conversation
        conversation_history.append(response)
        
        # Check if LLM wants to call tools
        if response.tool_calls:
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name == "adicionar_na_caixa_entrada":
                    result = adicionar_na_caixa_entrada.invoke(tool_args)
                elif tool_name == "verificar_status_caixa_entrada":
                    result = verificar_status_caixa_entrada.invoke(tool_args)
                elif tool_name == "processar_caixa_entrada":
                    result = await processar_caixa_entrada_telegram(update, context)
                else:
                    result = f"Ferramenta {tool_name} não reconhecida"
                
                # Add tool result to conversation
                conversation_history.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
            
            # Get final response after tool execution
            final_response = llm_with_tools.invoke(conversation_history)
            conversation_history.append(final_response)
            
            await update.message.reply_text(final_response.content)
        else:
            # No tool calls, just respond
            await update.message.reply_text(response.content)
            
    except Exception as e:
        await update.message.reply_text(f"Erro ao processar mensagem: {str(e)}")

@restricted
async def processar_resposta_revisao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa resposta do usuário à revisão."""
    resposta = update.message.text.strip().lower()
    
    if resposta in ['s', 'sim', 'y', 'yes', 'ok']:
        # Aprovado - salvar e continuar
        from graph import salvar_proposta, remover_item_da_caixa_entrada
        if salvar_proposta(estado_processamento.proposta_atual):
            if remover_item_da_caixa_entrada(estado_processamento.item_atual.id):
                await update.message.reply_text("✅ Item aprovado e salvo! Continuando processamento...")
                # Continuar processamento
                await processar_caixa_entrada_telegram(update, context)
    elif resposta in ['n', 'não', 'nao', 'no']:
        # Rejeitado
        await update.message.reply_text("❌ Item rejeitado, mantido na Caixa de Entrada.")
        estado_processamento.aguardando_revisao = False
    else:
        # Feedback - reprocessar
        await update.message.reply_text("📝 Feedback recebido, reprocessando...")
        # Adicionar feedback ao histórico e reprocessar
        estado_processamento.messages_history.append(AIMessage(content=f"Sugestão anterior: {estado_processamento.proposta_atual.model_dump_json()}"))
        estado_processamento.messages_history.append(HumanMessage(content=f"Feedback do usuário: {resposta}"))
        await processar_caixa_entrada_telegram(update, context)

@restricted
async def processar_caixa_entrada_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa Caixa de Entrada via Telegram."""
    from graph import processar_item_com_llm, salvar_proposta, remover_item_da_caixa_entrada
    from modelo import session, CaixaEntrada
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from prompts import PROMPT_ORGANIZADOR
    
    print("=== Iniciando processamento da Caixa de Entrada ===")
    
    while True:
        # 1. Buscar próximo item
        item = session.query(CaixaEntrada).order_by(CaixaEntrada.id.asc()).first()
        if not item:
            print("✅ Nenhum item na Caixa de Entrada. Processamento encerrado.")
            await update.message.reply_text("✅ Processamento concluído! Nenhum item restante na Caixa de Entrada.")
            return "Processamento concluído!"
            
        print(f"\n�� Processando Item {item.id}")
        print(f"Conteúdo: {item.conteudo_bruto[:100]}...")
        
        # 2. Processar com LLM
        messages_history = [
            SystemMessage(content=PROMPT_ORGANIZADOR),
            HumanMessage(content=f"\nTexto para análise:\n{item.conteudo_bruto}")
        ]
        
        # 3. Loop de processamento com feedback
        while True:
            try:
                proposal = processar_item_com_llm(item.conteudo_bruto, messages_history)
            except Exception as e:
                print(f"❌ Erro ao processar item com LLM: {e}")
                break
            
            # 4. Review gate - AGORA VIA TELEGRAM
            if not proposal.aprovado:
                # Configurar estado para aguardar revisão
                estado_processamento.aguardando_revisao = True
                estado_processamento.proposta_atual = proposal
                estado_processamento.item_atual = item
                estado_processamento.messages_history = messages_history
                
                # Enviar proposta via Telegram
                await update.message.reply_text(
                    f"📋 **PROPOSTA PARA REVISÃO**\n\n"
                    f"**Informações:** {proposal.informacoes}\n"
                    f"**Ideias:** {proposal.ideias}\n"
                    f"**Tarefas:** {proposal.tarefas}\n\n"
                    f"Sua aprovação: ('s', 'n' ou feedback)"
                )
                
                # SAIR do loop e aguardar resposta do usuário
                return "Aguardando revisão e resposta do usuário."
            
            else:
                # Já aprovado pelo LLM
                break
        
        # 5. Salvar e remover item
        if salvar_proposta(proposal):
            if remover_item_da_caixa_entrada(item.id):
                print(f"✅ Item {item.id} processado com sucesso!")
                await update.message.reply_text(f"✅ Item {item.id} processado e salvo!")
    
    return "Processamento concluído!"

@restricted
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Comandos disponíveis:\n"
        "/help - Ver esta ajuda\n\n"
        "Ou simplesmente converse comigo em linguagem natural!\n"
        "Exemplos:\n"
        "• 'Adicione à caixa de entrada: preciso comprar leite'\n"
        "• 'Quantos itens tenho pendentes?'\n"
        "• 'Processe minha caixa de entrada'\n"
        "• 'Coloque na minha lista que vou viajar em dezembro'"
    )

def main(token: Optional[str] = None) -> None:
    
    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("help", cmd_help))
    
    # Process all text messages with LLM
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message_with_llm))

    print("Bot iniciado com LLM. Converse naturalmente no Telegram!")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
