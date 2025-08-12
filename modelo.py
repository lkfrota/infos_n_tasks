import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# Definir o caminho do arquivo do banco de dados
database_path = os.path.join(os.getcwd(), 'conceitos.db')
database_url = f'sqlite:///{database_path}'

# Criar o motor do banco de dados (SQLite)
engine = create_engine(database_url)

# Declarar a base para as classes
Base = declarative_base()

# Tabela de associação para o relacionamento N:N entre Informacao e Ideia
ideia_informacao_association_table = Table(
    'ideia_informacao_association',
    Base.metadata,
    Column('ideia_id', Integer, ForeignKey('ideias.id')),
    Column('informacao_id', Integer, ForeignKey('informacoes.id'))
)

# Tabela de associação para o relacionamento N:N entre Informacao e Tarefa
tarefa_informacao_association_table = Table(
    'tarefa_informacao_association',
    Base.metadata,
    Column('tarefa_id', Integer, ForeignKey('tarefas.id')),
    Column('informacao_id', Integer, ForeignKey('informacoes.id'))
)

class Informacao(Base):
    __tablename__ = 'informacoes'
    id = Column(Integer, primary_key=True)
    conteudo = Column(String, nullable=False, unique=True)

    def __repr__(self):
        return f"<Informacao(conteudo='{self.conteudo}')>"

class Ideia(Base):
    __tablename__ = 'ideias'
    id = Column(Integer, primary_key=True)
    conteudo = Column(String, nullable=False)

    # Relacionamento N:N com Informacao
    informacoes = relationship("Informacao",
                               secondary=ideia_informacao_association_table,
                               backref="ideias")

    # Relacionamento 1:N com Plano
    plano = relationship("Plano", uselist=False, backref="ideia")

    def __repr__(self):
        return f"<Ideia(conteudo='{self.conteudo}')>"

class Tarefa(Base):
    __tablename__ = 'tarefas'
    id = Column(Integer, primary_key=True)
    conteudo = Column(String, nullable=False)
    
    # Relacionamento N:N com Informacao
    informacoes = relationship("Informacao",
                               secondary=tarefa_informacao_association_table,
                               backref="tarefas")
    
    # Relacionamento N:1 com Plano (várias Tarefas podem pertencer a um Plano)
    plano_id = Column(Integer, ForeignKey('planos.id'))

    def __repr__(self):
        return f"<Tarefa(conteudo='{self.conteudo}')>"

class Plano(Base):
    __tablename__ = 'planos'
    id = Column(Integer, primary_key=True)
    # Relacionamento N:1 com Ideia (um Plano tem uma Ideia)
    ideia_id = Column(Integer, ForeignKey('ideias.id'))

    # Relacionamento 1:N com Tarefa (um Plano tem várias Tarefas)
    tarefas = relationship("Tarefa", backref="plano", cascade="all, delete-orphan")

    def __init__(self, ideia: Ideia, tarefas: list):
        if len(tarefas) < 2:
            raise ValueError("Um Plano deve ter no mínimo duas Tarefas.")
        
        # Chama o construtor da classe base para inicializar os atributos
        super().__init__(ideia=ideia, tarefas=tarefas)
        
    def __repr__(self):
        return f"<Plano(ideia_id='{self.ideia_id}')>"

class CaixaEntrada(Base):
    __tablename__ = 'caixa_de_entrada'
    id = Column(Integer, primary_key=True)
    conteudo_bruto = Column(String, nullable=False)

    def __repr__(self):
        return f"<CaixaEntrada(conteudo_bruto='{self.conteudo_bruto}')>"

# Criar o banco de dados e as tabelas
Base.metadata.create_all(engine)

# Iniciar uma sessão para interagir com o banco de dados
Session = sessionmaker(bind=engine)
session = Session()

### LÓGICA DO AGENTE DE TRANSFORMAÇÃO ###

def processar_informacao(nova_informacao: Informacao):
    """
    Processa uma nova Informação e a relaciona com Ideias existentes
    para sugerir novas Tarefas.
    """
    print(f"\n--- Agente processando a nova informação: '{nova_informacao.conteudo}' ---")
    
    # 1. Obter todas as ideias existentes
    ideias_existentes = session.query(Ideia).all()
    
    sugestoes_geradas = []

    # 2. Iterar sobre as ideias para encontrar correspondências
    for ideia in ideias_existentes:
        # Lógica de correspondência simples: verificar se uma palavra da informação está na ideia.
        # Em um sistema real, isso seria mais sofisticado (NLP, embeddings, etc.).
        palavras_info = set(nova_informacao.conteudo.lower().split())
        palavras_ideia = set(ideia.conteudo.lower().split())

        palavras_comuns = palavras_info.intersection(palavras_ideia)
        
        if palavras_comuns:
            # 3. Gerar uma sugestão de Tarefa
            sugestao_tarefa_conteudo = f"Pesquisar sobre a conexão de '{', '.join(palavras_comuns)}' com a ideia '{ideia.conteudo}'"
            sugestoes_geradas.append(sugestao_tarefa_conteudo)
            
            print(f"  -> Sugestão gerada: '{sugestao_tarefa_conteudo}'")
            
    return sugestoes_geradas

def criar_tarefa_sugerida(conteudo_tarefa: str, informacao_fonte: Informacao):
    """
    Cria e persiste uma Tarefa sugerida pelo agente, vinculando-a à Informacao original.
    """
    nova_tarefa = Tarefa(conteudo=conteudo_tarefa)
    nova_tarefa.informacoes.append(informacao_fonte)
    
    session.add(nova_tarefa)
    session.commit()
    print(f"  -> Tarefa '{nova_tarefa.conteudo}' criada e vinculada a uma informação.")
    return nova_tarefa

'''def main():
    print("Hello from infos-n-tasks!")


if __name__ == "__main__":
    main()'''
