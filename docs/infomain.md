# Documentação Técnica: main.py

## 1. Descrição Geral
O arquivo `main.py` é o núcleo operacional (Backend) do Trazzo CRM. Construído com o framework **FastAPI**, ele gerencia todas as rotas (URLs), processa os formulários de cadastro e edição, lida com o upload de arquivos e executa as regras de negócio, como a conversão automática de um Lead em Cliente.

## 2. Processo de Criação
1. **Inicialização do App**: Criamos a instância `app = FastAPI()`.
2. **Configuração de Estáticos e Templates**: Montamos a pasta `static` para fotos e configuramos o `Jinja2Templates` para as páginas HTML.
3. **Segurança**: Implementamos a autenticação `HTTPBasic` para proteger o acesso.
4. **Lógica de Fotos**: Criamos a função `save_photo` para processar uploads de forma assíncrona.
5. **Definição de Rotas**: Criamos os caminhos para o Dashboard, Vendas e Clientes, integrando-os com o banco de dados.

## 3. Explicação Detalhada

### Importações Principais
- `from fastapi import FastAPI, Request, Form, File, UploadFile`:
    - `FastAPI`: O framework web.
    - `Request`: Permite acessar dados da requisição do navegador.
    - `Form`: Captura dados de campos de texto de formulários.
    - `File / UploadFile`: Permite receber arquivos (fotos) via POST.
- `import shutil`: Utilizado para copiar o arquivo de foto recebido para o disco rígido de forma eficiente.
- `import secrets`: Para comparar senhas de forma segura, evitando ataques de tempo.

### Funções e Lógica

#### `get_current_user`
- **Função**: Valida se o usuário digitou `admin` e a senha correta.
- **Retorno**: O nome do usuário se ok, caso contrário, gera um erro `401 Unauthorized`.

#### `save_photo(photo: UploadFile)`
- **Lógica**: Gera um nome único (UUID) para a imagem para evitar que duas fotos com o mesmo nome se sobrescrevam. Salva o arquivo em `static/uploads/`.

#### `dashboard(request: Request, ...)`
- **Lógica**: Realiza cálculos matemáticos em tempo real (Soma de faturamento, taxa de conversão) e envia para o gráfico.

#### `update_lead`
- **Lógica de Movimentação**: O sistema agora utiliza apenas a tabela `Lead`. Se o status for alterado para "Fechado", o card aparece na aba de Clientes. Se for alterado para qualquer outro status, ele volta automaticamente para a aba de Vendas.
- **Comando Crucial**: `.with_for_update()`.
- **Por que usamos?**: Garante que o banco de dados "trave" o registro durante a edição. Isso impede que dois usuários salvem o mesmo cliente simultaneamente, o que poderia causar perda de informações.

#### `delete_lead`
- **Exclusão com Desfazer**: Implementa a remoção definitiva do banco. O frontend gerencia um delay de 10 segundos antes de chamar esta rota, permitindo que o usuário desfaça a ação.

## 4. Dependências
- **FastAPI**: Servidor web.
- **Uvicorn**: Executor do servidor Python.
- **python-multipart**: Necessário para que o FastAPI aceite arquivos e formulários.
- **Jinja2**: Motor de renderização das páginas.
