# Documentação Técnica: Arquivos de Configuração

## 1. Descrição Geral
Este guia cobre os arquivos de infraestrutura e instalação do projeto: `requirements.txt`, `Procfile` e `populate_db.py`.

## 2. Processo de Criação
1. **requirements.txt**: Gerado via comando `pip freeze` para listar todas as ferramentas necessárias.
2. **Procfile**: Criado para que plataformas de nuvem saibam como "ligar" o sistema.
3. **populate_db.py**: Criado como um script de utilidade para preencher o banco com dados de teste.

## 3. Explicação Detalhada

### `requirements.txt`
Contém a lista de bibliotecas:
- `fastapi`: O motor do sistema.
- `uvicorn`: O servidor que roda o Python.
- `sqlalchemy`: O tradutor para banco de dados.
- `python-multipart`: O módulo que processa arquivos de imagem.

### `Procfile`
- `web: uvicorn main:app --host 0.0.0.0 --port $PORT`:
    - `web`: Indica que é um serviço web.
    - `$PORT`: Variável dinâmica usada por servidores de hospedagem.

### `populate_db.py`
- `db.add_all(leads)`: Comando do SQLAlchemy que insere vários registros de uma vez.
- `datetime.utcnow()`: Gera a data atual no formato padrão internacional para o banco de dados.

## 4. Dependências
- **PIP**: Gerenciador de pacotes do Python.
- **Venv (Opcional)**: Recomendado criar um ambiente virtual antes de instalar as dependências.
