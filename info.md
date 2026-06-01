# Guia Completo: Criação do Trazzo CRM Full-Stack

Este documento detalha o processo de construção do sistema **Trazzo CRM**, desde a configuração do ambiente até as funcionalidades avançadas de dashboard e gestão de clientes.

---

## 1. Arquitetura do Sistema
O sistema foi construído utilizando uma arquitetura **Full-Stack Monolítica moderna**:
- **Backend**: Python com **FastAPI** (Rápido, moderno e fácil de documentar).
- **Banco de Dados**: **SQLite** com **SQLAlchemy** (ORM para manipulação de dados).
- **Frontend**: **HTML5** + **Tailwind CSS** (via CDN para agilidade) + **Jinja2** (Templates dinâmicos).
- **Gráficos**: **Chart.js** para visualização financeira.

---

## 2. Estrutura de Pastas
```text
/UI CRM
├── main.py              # Coração do sistema (Rotas e Lógica)
├── database.py          # Definição das tabelas (Modelos)
├── populate_db.py       # Script para criar dados iniciais
├── static/              # Arquivos estáticos
│   ├── css/
│   ├── js/
│   └── uploads/         # Fotos de perfil dos clientes
├── templates/           # Telas HTML (Jinja2)
│   ├── layout.html      # Base comum (Menu, Sidebars)
│   ├── dashboard.html   # Painel financeiro
│   ├── vendas.html      # Gestão de leads (Kanban)
│   └── clientes.html    # Gestão de clientes ativos
└── requirements.txt     # Dependências do projeto
```

---

## 3. Passo a Passo da Criação

### Passo 1: Configuração do Backend e Banco de Dados
No arquivo `database.py`, definimos as classes que o Python usa para falar com o banco de dados. Criamos duas tabelas principais:
- **Leads**: Para potenciais clientes (contém temperatura, problemas e soluções).
- **Clients**: Para projetos fechados (contém valores, datas de contrato e escopo).

### Passo 2: Construção da Interface Base (`layout.html`)
Para evitar repetir código, criamos um arquivo mestre que contém:
- O menu de navegação superior.
- Os painéis laterais (**Sidebars**) de Notificações e Configurações.
- A lógica JavaScript para abrir e fechar esses painéis com animações.

### Passo 3: O Dashboard Financeiro
A tela mais complexa. Ela recebe dados do Python e os exibe de três formas:
1. **Cards de Resumo**: Total de leads, clientes e faturamento.
2. **Gráfico de Linha**: Usa o `Chart.js` para mostrar a evolução mensal do faturamento. Implementamos um seletor (1A, 6M, 3M) que filtra os meses dinamicamente.
3. **Calendário**: Uma visualização rápida de projetos ativos por mês.

### Passo 4: Gestão de Vendas (Fluxo Kanban)
Implementamos a página de vendas onde os leads são organizados em colunas:
- **Lógica de Conversão**: Criamos uma função no `main.py` que, ao mudar o status de um lead para "Fechado", cria automaticamente uma cópia desse perfil na tabela de Clientes, preservando a foto e os dados.

### Passo 5: Funcionalidades Avançadas
- **Upload de Fotos**: Usamos o módulo `shutil` do Python para salvar imagens enviadas via formulário na pasta `static/uploads` e guardar apenas o caminho no banco de dados.
- **Concorrência**: Utilizamos o comando `.with_for_update()` nas consultas do banco. Isso garante que, se dois usuários salvarem o mesmo cliente ao mesmo tempo, o sistema não corrompa os dados.
- **Notificações Inteligentes**: O sistema calcula a diferença entre a data atual e a `end_date` do projeto. Se faltarem menos de 7 dias, um alerta é gerado automaticamente no painel lateral.

---

## 4. Como Executar e Evoluir
Para quem está aprendendo:
1. **Instalar Dependências**: `pip install fastapi uvicorn sqlalchemy jinja2 python-multipart`.
2. **Iniciar o Servidor**: `python main.py
3. **Evolução**: O próximo passo ideal seria trocar a autenticação básica por um sistema de login real com criptografia de senhas (BCrypt) e tokens JWT.

---
*Este sistema foi projetado para ser leve, escalável e extremamente visual, seguindo os padrões de UI/UX modernos.*
