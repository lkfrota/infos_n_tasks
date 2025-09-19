from modelo import CaixaEntrada, Informacao, Ideia, Tarefa, Plano, session
import sys


# --- Limpeza de dados (opcional, para testes recorrentes) ---
# Você pode descomentar as linhas abaixo para limpar as tabelas antes de cada teste
# session.query(Informacao).delete()
# session.query(Ideia).delete()
# session.query(Tarefa).delete()
# session.query(Plano).delete()
# session.commit()
# print("Tabelas limpas para o teste.")

def adicionar_item():
    """
    Adiciona um novo item à Caixa de Entrada.
    """
    try:
        conteudo = input("Digite o conteúdo do item para a Caixa de Entrada: ")
        if not conteudo:
            print("O conteúdo não pode estar vazio.")
            return

        novo_item = CaixaEntrada(conteudo_bruto=conteudo)
        session.add(novo_item)
        session.commit()
        print(f"Item '{conteudo}' adicionado com sucesso à Caixa de Entrada.")
    except Exception as e:
        session.rollback()
        print(f"Erro ao adicionar item: {e}")

def deletar_item_generico(tabela_classe, nome_tabela):
    """
    Deleta um item específico de qualquer tabela pelo ID.
    """
    try:
        item_id_str = input(f"Digite o ID do item de '{nome_tabela}' que deseja deletar: ")
        if not item_id_str.isdigit():
            print("Por favor, digite um ID válido (número inteiro).")
            return

        item_id = int(item_id_str)
        item_a_deletar = session.query(tabela_classe).filter_by(id=item_id).first()

        if item_a_deletar:
            session.delete(item_a_deletar)
            session.commit()
            print(f"Item com ID {item_id} da tabela '{nome_tabela}' deletado com sucesso.")
        else:
            print(f"Nenhum item encontrado com o ID {item_id} na tabela '{nome_tabela}'.")
    except Exception as e:
        session.rollback()
        print(f"Erro ao deletar item: {e}")

def consultar_tabela(tabela_classe, nome_tabela):
    """
    Função genérica para consultar e exibir todos os itens de uma tabela.
    """
    try:
        itens = session.query(tabela_classe).all()
        if not itens:
            print(f"Nenhum item encontrado na tabela '{nome_tabela}'.")
            return

        print(f"\n--- Itens em {nome_tabela} ---")
        for item in itens:
            conteudo = ""
            detalhes = ""
            
            if tabela_classe == CaixaEntrada:
                conteudo = item.conteudo_bruto
            elif tabela_classe == Informacao:
                conteudo = item.conteudo
            elif tabela_classe == Ideia:
                conteudo = item.conteudo
                detalhes = f" | Informações vinculadas: {len(item.informacoes)}"
            elif tabela_classe == Tarefa:
                conteudo = item.conteudo
                plano_id = item.plano.id if item.plano else "N/A"
                detalhes = f" | Plano ID: {plano_id} | Informações vinculadas: {len(item.informacoes)}"
            elif tabela_classe == Plano:
                ideia_conteudo = item.ideia.conteudo if item.ideia else "N/A"
                conteudo = f"Plano para a Ideia: {ideia_conteudo}"
                detalhes = f" | Tarefas: {len(item.tarefas)}"

            print(f"ID: {item.id} | Conteúdo: {conteudo}{detalhes}")
        print("-------------------------------")
    except Exception as e:
        print(f"Erro ao consultar tabela '{nome_tabela}': {e}")

def compor_plano():
    """
    Cria um Plano a partir de uma Ideia e pelo menos duas Tarefas, com validação.
    """
    try:
        consultar_tabela(Ideia, "Ideias")
        ideia_id_str = input("Digite o ID da Ideia para a qual deseja criar um plano: ")
        if not ideia_id_str.isdigit():
            print("ID de Ideia inválido.")
            return
        
        ideia = session.query(Ideia).filter_by(id=int(ideia_id_str)).first()
        if not ideia:
            print("Ideia não encontrada.")
            return

        tarefas_para_plano = []
        while True:
            consultar_tabela(Tarefa, "Tarefas")
            tarefa_id_str = input("Digite o ID da Tarefa a ser adicionada ao plano (ou 'f' para finalizar): ")
            if tarefa_id_str.lower() == 'f':
                break
            
            if not tarefa_id_str.isdigit():
                print("ID de Tarefa inválido.")
                continue

            tarefa = session.query(Tarefa).filter_by(id=int(tarefa_id_str)).first()
            if tarefa and tarefa not in tarefas_para_plano:
                tarefas_para_plano.append(tarefa)
                print(f"Tarefa '{tarefa.conteudo}' adicionada. Total de tarefas: {len(tarefas_para_plano)}")
            elif tarefa:
                print("Tarefa já foi adicionada.")
            else:
                print("Tarefa não encontrada.")
        
        novo_plano = Plano(ideia=ideia, tarefas=tarefas_para_plano)
        session.add(novo_plano)
        session.commit()
        print(f"\nPlano criado com sucesso para a Ideia '{ideia.conteudo}' com {len(tarefas_para_plano)} tarefas.")

    except ValueError as ve:
        session.rollback()
        print(f"Erro: {ve}")
    except Exception as e:
        session.rollback()
        print(f"Erro ao compor plano: {e}")

def menu():
    """
    Função principal que exibe o menu e gerencia as opções.
    """
    print("\n--- Menu da Interface de Dados ---")
    print("1. Adicionar novo item na Caixa de Entrada")
    print("2. Consultar itens na Caixa de Entrada")
    print("3. Deletar item da Caixa de Entrada por ID")
    print("4. Consultar Informações")
    print("5. Consultar Ideias")
    print("6. Consultar Tarefas")
    print("7. Consultar Planos")
    print("8. Deletar item de uma tabela")
    print("9. Compor um Plano")
    print("10. Sair")
    return input("Escolha uma opção: ")

if __name__ == "__main__":
    try:
        while True:
            opcao = menu()
            if opcao == '1':
                adicionar_item()
            elif opcao == '2':
                consultar_tabela(CaixaEntrada, "Caixa de Entrada")
            elif opcao == '3':
                deletar_item_generico(CaixaEntrada, "Caixa de Entrada")
            elif opcao == '4':
                consultar_tabela(Informacao, "Informações")
            elif opcao == '5':
                consultar_tabela(Ideia, "Ideias")
            elif opcao == '6':
                consultar_tabela(Tarefa, "Tarefas")
            elif opcao == '7':
                consultar_tabela(Plano, "Planos")
            elif opcao == '8':
                print("\n--- Escolha a tabela para deletar ---")
                print("1. Caixa de Entrada")
                print("2. Informações")
                print("3. Ideias")
                print("4. Tarefas")
                print("5. Planos")
                escolha_tabela = input("Digite o número da tabela: ")
                if escolha_tabela == '1':
                    deletar_item_generico(CaixaEntrada, "Caixa de Entrada")
                elif escolha_tabela == '2':
                    deletar_item_generico(Informacao, "Informações")
                elif escolha_tabela == '3':
                    deletar_item_generico(Ideia, "Ideias")
                elif escolha_tabela == '4':
                    deletar_item_generico(Tarefa, "Tarefas")
                elif escolha_tabela == '5':
                    deletar_item_generico(Plano, "Planos")
                else:
                    print("Opção de tabela inválida.")
            elif opcao == '9':
                compor_plano()
            elif opcao == '10':
                print("Saindo...")
                break
            else:
                print("Opção inválida. Por favor, tente novamente.")
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma interrompido. Saindo...")
    finally:
        session.close()
        sys.exit(0)