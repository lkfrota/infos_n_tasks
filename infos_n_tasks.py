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

# Bind tools to LLM
llm_with_tools = llm.bind_tools([adicionar_na_caixa_entrada, verificar_status_caixa_entrada])

# Global conversation history (single user)
conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]

@restricted
async def process_message_with_llm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user message with LLM and handle tool calls."""
    if update.message is None or update.message.text is None:
        return
    
    user_message = update.message.text.strip()
    
    if not user_message:
        return
    
    # Add user message to conversation
    conversation_history.append(HumanMessage(content=user_message))
    print(f"🤖 Usuário enviou: {user_message}\n==============")

    try:
        # Get LLM response
        response = llm_with_tools.invoke(conversation_history)
        
        # Add AI response to conversation
        conversation_history.append(response)
        if response.content:
            print(f"🤖 LLM respondeu: {response.content}\n===============")
        
        # Check if LLM wants to call tools
        if response.tool_calls:
            # Execute tool calls
            for tool_call in response.tool_calls:
                print(f"�� LLM quer chamar ferramentas: {[tc['name'] for tc in response.tool_calls]}\n================")
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name == "adicionar_na_caixa_entrada":
                    result = adicionar_na_caixa_entrada.invoke(tool_args)
                elif tool_name == "verificar_status_caixa_entrada":
                    result = verificar_status_caixa_entrada.invoke(tool_args)
                else:
                    result = f"Ferramenta {tool_name} não reconhecida"
                
                # Add tool result to conversation
                conversation_history.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                print(f"A ferramenta respondeu: {result}")
            
            # Get final response after tool execution
            final_response = llm_with_tools.invoke(conversation_history)
            conversation_history.append(final_response)
            print(f"🤖 LLM respondeu: {final_response.content}\n===============")
            
            await update.message.reply_text(final_response.content)
        else:
            # No tool calls, just respond
            await update.message.reply_text(response.content)
            
    except Exception as e:
        await update.message.reply_text(f"Erro ao processar mensagem: {str(e)}")

@restricted
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Comandos disponíveis:\n"
        "/help - Ver esta ajuda\n\n"
        "Ou simplesmente converse comigo em linguagem natural!\n"
        "Exemplos:\n"
        "• 'Adicione à caixa de entrada: preciso comprar leite'\n"
        "• 'Quantos itens tenho pendentes?'\n"
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
