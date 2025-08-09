# run_agente.py

from main import Informacao, Ideia, Tarefa, session, processar_informacao, criar_tarefa_sugerida

# --- Limpar dados para um teste limpo ---
session.query(Informacao).delete()
session.query(Ideia).delete()
session.query(Tarefa).delete()
session.commit()
print("Banco de dados limpo para o teste.")

# --- Cenário de Teste ---
print("\n--- Cenário: Adicionando uma ideia existente ---")
ideia_viagens = Ideia(conteudo="Planejar viagens desafiadoras para locais selvagens")
session.add(ideia_viagens)
session.commit()
print(f"Ideia '{ideia_viagens.conteudo}' adicionada.")

print("\n--- Cenário: Adicionando uma nova informação ---")
nova_info = Informacao(conteudo="A Patagônia é um local selvagem e ideal para aventuras")
session.add(nova_info)
session.commit()
print(f"Informação '{nova_info.conteudo}' adicionada.")

# --- Simular o processamento pelo agente ---
print("\n--- Agente em ação! ---")
sugestoes = processar_informacao(nova_info)

# --- Simular o "Human in the loop" ---
if sugestoes:
    print("\n--- Validação humana: Analisando sugestões ---")
    # Aqui, você validaria se a sugestão é útil. Vamos aceitar a primeira.
    tarefa_sugerida = sugestoes[0]
    
    print(f"Aceitando a sugestão: '{tarefa_sugerida}'")
    tarefa_criada = criar_tarefa_sugerida(tarefa_sugerida, nova_info)

    # Verificação
    print("\n--- Verificação final ---")
    tarefa_do_db = session.query(Tarefa).filter_by(id=tarefa_criada.id).first()
    print(f"Tarefa criada: '{tarefa_do_db.conteudo}'")
    print(f"Fonte da tarefa: '{tarefa_do_db.informacoes[0].conteudo}'")

else:
    print("Nenhuma sugestão de tarefa gerada.")

session.close()