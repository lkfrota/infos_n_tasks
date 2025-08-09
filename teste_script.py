# test_script.py

# Importar as classes e a sessão do banco de dados
from main import Informacao, Ideia, Tarefa, Plano, session

# --- Limpeza de dados (opcional, para testes recorrentes) ---
# Você pode descomentar as linhas abaixo para limpar as tabelas antes de cada teste
# session.query(Informacao).delete()
# session.query(Ideia).delete()
# session.query(Tarefa).delete()
# session.query(Plano).delete()
# session.commit()
# print("Tabelas limpas para o teste.")

# --- 1. Adicionar Informações ---
print("\n--- Adicionando informações ---")
info1 = Informacao(conteudo="Patagônia é linda e selvagem")
info2 = Informacao(conteudo="Viagens desafiadoras são muito legais")
info3 = Informacao(conteudo="Dia 25/12/2025 será feriado")

session.add_all([info1, info2, info3])
session.commit()
print("Informações adicionadas com sucesso.")

# --- 2. Adicionar uma Ideia e vincular Informações ---
print("\n--- Adicionando uma ideia e vinculando informações ---")
ideia1 = Ideia(conteudo="Planejar viagem para um local selvagem")
ideia1.informacoes.append(info1)
ideia1.informacoes.append(info2)
session.add(ideia1)
session.commit()
print(f"Ideia '{ideia1.conteudo}' criada e vinculada a 2 informações.")

# --- 3. Criar uma Tarefa diretamente de uma Informação ---
print("\n--- Criando uma tarefa diretamente de uma informação ---")
tarefa1 = Tarefa(conteudo="Pesquisar sobre viagens à Patagônia")
tarefa1.informacoes.append(info1)
session.add(tarefa1)
session.commit()
print(f"Tarefa '{tarefa1.conteudo}' criada e vinculada a uma informação.")

# --- 4. Criar um Plano a partir da Ideia ---
# Em um sistema real, essa lógica seria mais elaborada.
# Aqui, simulamos a criação do Plano com algumas tarefas.
print("\n--- Criando um plano a partir da ideia ---")
plano1 = Plano(ideia=ideia1)
session.add(plano1)
session.commit()
print(f"Plano criado para a ideia '{ideia1.conteudo}'.")

# Vincular tarefas ao plano
tarefa2 = Tarefa(conteudo="Checar manutenção do carro para a viagem")
tarefa3 = Tarefa(conteudo="Fazer orçamento de acampamentos")

plano1.tarefas.append(tarefa2)
plano1.tarefas.append(tarefa3)
session.add_all([tarefa2, tarefa3])
session.commit()
print(f"Plano agora tem {len(plano1.tarefas)} tarefas.")

# --- 5. Consulta e Verificação ---
print("\n--- Verificando os dados ---")
# Consultar a ideia1
ideia_salva = session.query(Ideia).filter_by(conteudo="Planejar viagem para um local selvagem").first()
print(f"Conteúdo da Ideia: {ideia_salva.conteudo}")
print(f"Informações relacionadas à Ideia:")
for info in ideia_salva.informacoes:
    print(f"  - {info.conteudo}")

# Consultar a tarefa1
tarefa_salva = session.query(Tarefa).filter_by(conteudo="Pesquisar sobre viagens à Patagônia").first()
print(f"Conteúdo da Tarefa: {tarefa_salva.conteudo}")
print(f"Informações relacionadas à Tarefa:")
for info in tarefa_salva.informacoes:
    print(f"  - {info.conteudo}")

# Consultar o plano1
plano_salvo = session.query(Plano).filter_by(id=plano1.id).first()
print(f"Plano para a Ideia: {plano_salvo.ideia.conteudo}")
print(f"Tarefas no Plano:")
for tarefa in plano_salvo.tarefas:
    print(f"  - {tarefa.conteudo}")
    
# Fechar a sessão
session.close()
print("\nSessão do banco de dados fechada.")