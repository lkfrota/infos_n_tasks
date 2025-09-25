Este documento sintetiza sobre a modelagem de um sistema de gestão de informações, ideias e tarefas. O objetivo central é criar um sistema que não apenas armazena dados, mas também facilita a transformação de conhecimento em ações de forma estruturada.

O foco da discussão se concentrou na definição dos objetos, seus relacionamentos e o fluxo de trabalho, com o objetivo de construir um protótipo viável e útil.

É importante salientar que há um objetivo ainda maior: formar nesse aplicativo um sistema de curadoria e pré-gestão de Tarefas antes de criá-las no Google Tasks ou Google Calendar. A diferença desses dois deve-se concentrar em que para o Tasks pode ou não haver prazo enquanto que para o Calendar deve haver data (hora é facultativa caracterizando evento de dia inteiro) definida de realização com início e fim (ou um desses dois e tempo do evento).

1. Conceitos e Modelo de Objetos
O modelo de objetos foi refinado para representar com precisão a progressão do conhecimento e do planejamento, desde a sua forma mais básica até a sua concretização.

Informacao: Unidade elementar. Vem de fontes externas e representa algo que se passa a conhecer. Serve como a matéria-prima para outros objetos. Uma Informacao pode contribuir para a formação de uma Ideia ou Tarefa sem ser modificada.

Exemplos: "Patagônia é inexplorada, extensa e isolada", "O diesel na Argentina é barato" e "Meu passaporte vai vencer ano que vem."

Ideia: Objeto de alto nível que já possui mais vínculo com a minha cabeça que com o mundo externo. Representa uma demanda latente, imatura, vaga ou indecisa que precisa ser amadurecida.

Exemplos: "Gosto muito de viagens com aventuras e natureza", "Já estou há bastante tempo com meu carro" e "Renovar visto deve ser mais fácil que tirar um novo".

Tarefa: Objeto acionável, diretamente executável. Pode ser gerado a partir de uma Informacao ou Ideia e representa uma ação concreta.

Exemplos: "Pesquisar roteiros de viagem à Patagônia", "Anunciar meu carro para a venda no site" e "Ver no site da PF os procedimentos para renovar o passaporte."

Plano: Representa a estratégia. Um Plano é uma Ideia que foi amadurecida e decomposta em um conjunto estruturado de duas ou mais Tarefas. Isso formaliza a diferença entre uma ação única e uma estratégia multifacetada.

Exemplo: O plano "Viagem de carro para a Patagônia" seria a decomposição de uma ideia maior, contendo tarefas como "Planejar rota", "Checar manutenção do carro", etc.

2. Relacionamentos entre os Objetos
Os relacionamentos são de contribuição e transformação, o que os torna o cerne do sistema.

Informacao -> Ideia/Tarefa: Uma Informacao contribui para uma Ideia ou Tarefa. A Informacao fornece contexto e detalhes. Uma Informacao pode, inclusive, se transformar diretamente em uma Tarefa (ex: Informacao sobre um feriado resultando na Tarefa de antecipar uma compra).

Ideia -> Plano: Uma Ideia se transforma em um Plano quando é fragmentada em duas ou mais Tarefas. A ideia evolui para uma representação mais estruturada e executável.

Plano -> Projeto: Embora um Plano possa ser implementado por um Projeto em um sistema de execução, o foco do presente modelo é no gerenciamento do conhecimento e da incubação. Portanto, a transição para um Projeto seria o ponto de migração para outra ferramenta.

3. Aspectos de Implementação e Desafios
A implementação desse modelo se concentra na persistência de dados e, principalmente, na automação da lógica de evolução e relacionamento entre os Objetos.

Persistência de Dados
Tecnologia: A sugestão é usar Python com SQLAlchemy para ORM e SQLite para o banco de dados, ideal para prototipagem por ser leve e fácil de configurar.

Mecanismo: O ORM lida com a tradução entre as classes Python e as tabelas do banco de dados, salvando e recuperando os dados de forma transparente.

Lógica de Transformação (O "Motor")
A automação é o ponto mais inovador e diferenciado do presente conceito, e será implementada por um motor de regras inteligente.

Abordagem do Agente: A proposta é utilizar um agente, ou um time de agentes, para processar as informações e sugerir transformações e relações. Este agente iria analisar um novo dado de entrada (ainda sem classificação de é informação, ideia ou tarefa) e, com base em regras, propor a criação ou a atualização de outros objetos.

Human in the Loop: Para garantir a utilidade e a confiabilidade da automação, haverá um passo de validação humana. O agente pode, por exemplo, sugerir a criação de uma nova Tarefa, mas a decisão final é do usuário. Isso mitiga o risco de criar tarefas inúteis ou erradas.

Regras de Relacionamento: Um exemplo de regra seria:

SE ao adicionar a Informacao "Em Maio do ano que vem pegarei 20 dias de férias" já existe a Ideia "Gosto muito de viagens com aventuras e natureza" o agente sugere a criação de uma nova Ideia "Viajar para a Patagônia nas férias do ano que vem", aproveitando e vinculando a essa Ideia nova também outra informação já existente na base de dados que é "O diesel na Argentina é barato".

_________________________________________________________
Após alguns dias trabalhando no projeto já tenho:

Arquivo chamado modelo.py que possui imports do sqlalchemy como create_engine, Column, Integer, String, ForeignKey, Table, sessionmaker, relationship, declarative_base. Possui ainda a criação das classes Informacao, Ideia, Tarefa, Plano, CaixaEntrada e algumas tabelas de associação para o relacionamento N:N entre Informacao e Ideia e Informacao e Tarefa. Há ainda outras regras como um Plano deve ter 2 ou mais Tarefas.

Aquivo chamado agente_real.py que possui imports pydantic e agno como BaseModel, Field, Agent, Gemini. Possui ainda a criação da classe Suggestion com o modelo Pydantic para saída estruturada do Agente. Também entancia o agente com seu prompt de instruções.

Arquivo chamado agente_aprovacao que possui imports iguais do agente_real e também classe com o modelo Pydantic para saída estruturada. O agente é estanciado com seu prompt de instruções.

Arquivo workflow.py com imports do agno, e dos demais arquivos do projeto. Do Agno são importados Loop, Step, Workflow, StepOutput, StepInput, RunResponse. Esse arquivo ainda precisa ser melhorado para usar workflow_session_state ao invés de variável global. O workflow do Agno é estanciado com um loop com um step e uma end_condition seguido de outro step. Para o step dentro do loop é desejado o uso do agente real que ao receber o texto bruto da Caixa de entrada, faz sugestões de itens para as categorias Informacao, Ideia e Tarefa. O usuário recebe e interaje respondendo por aprovação ou solicitando ajustes. O conjunto de informação até aqui é enviado para o agente aprovação que julga a resposta do usuário e retorna True or False, e no caso de False, acumula no conjunto de informações do loop que deve retornar ao agente_real. No caso de True, as sugestões são encaminhadas para o step seguinte que é uma função que armazena as sugestões no banco de dados.

Mais imediatamente ainda falta construir:
1. Uma interface para input de insights brutos do usuário para dentro do aplicativo através da caixa de entrada. Baseado no princípio do GTD (Getting Things Done) de liberar a mente de lembrar de coisas. Possivelmente em nuvem e através do Telegram;
2. Definir uma sistemática ou gatilho de esvaziamento da caixa de entrada através do processamento dos itens brutos em itens categorizados (Informacao, Ideia e Tarefa através do workflow.py). Essa parte pode ser local e rodar somente quando o computador do usuário estiver ligado;
3. Para os itens Tarefa um processamento seguinte deve pedir o atributo tempo de realização;
4. Se o tempo de realização for inferior a 2 minutos o aplicativo sugere de realizar imediatamente;
5. Se o tempo de realização for superior a 2 minutos o aplicativo pede mais atributos como importância e urgência (matriz Eisenhower), data para realização, local para realização, etc.
6. Com esses atributos o aplicativo define outros como "fazer imdediatamente", "delegar", "agendar", "eliminar";
7. O aplicativo envia as tarefas resultantes desse processo ao Google Calendar ou Google Tasks;

Depois a evolução do aplicativo será:
8. Um destino tipo arquivo morto ou simplesmente um atributo "feito/agendado" para as tarefas enviadas aos aplicativos Google;
9. O aplicativo buscar relações e oportunidades entre todo o conjunto de informações, ideias, tarefas e planos e sugerir vínculos entre esses elementos;

________________________________________________________
Após mais alguns dias trabalhando o estado do projeto é o seguinte:

Abandonei o Agno depois de muitas tentativas para ter o workflow_session_state como input no loop e não consegui. Tive avanços interessantes e aprendi um monte sobre o framework mas escolhi mudar para o Langgraph para tentar controlar mais a solução. O aprendizado mais marcante nessa fase com o Agno foi o de criar Step customizado com função Python onde um dos inputs é o pŕoprio objeto Workflow.

Com o Langgraph construí 2 soluções distintas o graph_langgraph_backup.py com um loop completo em grafo e o graph.py que usa o langchain só para acessar o llm mas todo o loop acontece em fluxo Python alheio aos recursos langgraph. Ambos arquivos criam o fluxo desde consultar os itens na Caixa de Entrada até salvar os itens processados e classificados nas respectivas classes previstas em modelo.py.

Agora comecei a esboçar os itens 1 e 2. Em umas reflexões com assistente de programação entendi que devo convergir logo para um MVP, ou seja, um fluxo completo da ideia do aplicativo mesmo que sem profundidade. Os recursos mais avançados e flexibilidades ficarão para um momento seguinte.

Acabei de pedir para a IA para me ajudar a criar o framework global do aplicativo:
Com input do usuário popular a Caixa de Entrada (CE);
Fazer, com supervisão humana, pré-processamento dos itens da CE fragmentando conforme claasificações estabelecidas;
Fazer processamento principal dos itens classificados, consultando usuário conforme regras e atributos;
Após passar por esse fluxo com sucesso, as Tarefas serão enviadas para o Google Calendar ou Google Tasks;
Obtendo sucesso no item anterior essas Tarefas serão reclassificadas como arquivo morto ou arquivado;

O fluxo descrito acima é desde a entrada até a saída. Mas haverá um fluxo rotativo interno com inteligência para encontrar relações, oportunidades, desdobramentos, redundâncias, etc, sugerindo para o usuário transformações nos itens conforme esses achados. Esse fluxo será um fase avançada.