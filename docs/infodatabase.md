# Documentação Técnica: database.py

## 1. Descrição Geral
O arquivo `database.py` é responsável pela camada de persistência de dados do sistema Trazzo CRM. Ele utiliza a biblioteca **SQLAlchemy** para mapear objetos Python em tabelas do banco de dados **SQLite**. Sua função principal é definir a estrutura (esquema) das informações de Leads e Clientes que o sistema gerencia.

## 2. Processo de Criação
A criação deste arquivo seguiu os seguintes passos:
1. **Escolha do Banco de Dados**: Optamos pelo SQLite por ser um banco de dados baseado em arquivo, facilitando a portabilidade e dispensando a configuração de servidores complexos para este estágio do projeto.
2. **Definição da Engine**: Configuramos a conexão com o arquivo `crm.db`.
3. **Criação da Base**: Utilizamos `declarative_base()` para que nossas classes Python possam herdar as funcionalidades do SQLAlchemy.
4. **Mapeamento de Entidades**: Criamos as classes `Lead` e `Client` com campos que refletem as necessidades de negócio identificadas nos documentos de referência (fotos, contatos, status, valores).

## 3. Explicação Detalhada

### Importações
- `from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text`:
    - `create_engine`: Cria a conexão principal com o banco de dados.
    - `Column`: Define que um atributo da classe será uma coluna na tabela.
    - `Integer, String, Float, DateTime, Text`: Tipos de dados para números, textos curtos, decimais, datas e textos longos.
    - `ForeignKey`: Estabelece um vínculo entre a tabela de Clientes e a de Leads.
- `from sqlalchemy.ext.declarative import declarative_base`: Função que cria a classe base para nossos modelos.
- `from sqlalchemy.orm import sessionmaker`: Cria uma fábrica de "sessões" para conversarmos com o banco.

### Comandos e Configurações
- `SQLALCHEMY_DATABASE_URL = "sqlite:///./crm.db"`: Define o endereço do arquivo do banco. O prefixo `sqlite:///` indica que é um banco local.
- `engine = create_engine(...)`: O motor que executa os comandos SQL. O parâmetro `check_same_thread: False` é necessário para o SQLite funcionar corretamente com o FastAPI (que é assíncrono).
- `SessionLocal = sessionmaker(...)`: Cria instâncias de conexão temporárias para cada requisição.

### Classes (Modelos)

#### Classe `Lead`
Representa um potencial cliente no funil de vendas.
- `id`: Chave primária (única).
- `temperature`: Indica se o lead é "Quente", "Morno" ou "Frio".
- `photo_path`: Guarda o caminho da imagem salva no servidor.

#### Classe `Client`
Representa um cliente que já fechou contrato.
- `start_date` / `end_date`: Datas de vigência do projeto.
- `lead_id`: Referência ao lead original que gerou este cliente.

## 4. Dependências
- **SQLAlchemy**: Para tradução de Python para SQL.
- **SQLite3**: Driver padrão do Python para o banco de dados.
