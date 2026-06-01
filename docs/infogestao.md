# Documentação Técnica: vendas.html e clientes.html

## 1. Descrição Geral
Estes dois arquivos gerenciam a visualização e edição dos registros. O `vendas.html` foca no funil (Kanban), enquanto o `clientes.html` foca nos contratos ativos.

## 2. Processo de Criação
1. **Estrutura de Colunas**: No `vendas.html`, criamos colunas fixas para cada etapa (Lead, Negociação, etc.).
2. **Modais de Edição**: Desenvolvemos janelas flutuantes (`fixed inset-0`) que contêm formulários detalhados.
3. **Upload de Foto**: Configuramos os formulários com `enctype="multipart/form-data"` para permitir o envio de imagens.

## 3. Explicação Detalhada

### Tags de Formulário
- `<form method="post" enctype="multipart/form-data">`: 
    - `method="post"`: Envia dados de forma segura.
    - `enctype`: Crucial para o funcionamento do upload de fotos. Sem isso, o navegador envia apenas o nome do arquivo, não a imagem em si.
- `<input type="date">`: Abre o calendário nativo do sistema operacional para escolha de datas.

### JavaScript de Modais e Ações
- `openEditLeadModal(...)`: 
    - **O que faz**: Recebe todos os dados do lead, preenche os campos do formulário automaticamente e remove a classe `hidden` para mostrar o modal.
- `confirmDelete(...)`:
    - **Lógica**: Exibe um aviso, oculta o card visualmente e inicia um cronômetro de 10 segundos. Se o usuário não clicar em "Desfazer", a exclusão é enviada ao servidor.

### Lógica Kanban e Movimentação
- **Sincronização**: A movimentação entre abas é baseada exclusivamente no campo `status`. Status "Fechado" = Aba Clientes. Qualquer outro status = Aba Vendas. Isso simplifica a integridade dos dados e garante que o histórico do lead nunca seja perdido ao fechar um negócio.
- `{% for lead in leads if lead.status == column %}`: 
    - Este comando filtra os leads em tempo real enquanto a página é carregada, colocando cada card na coluna correta.

## 4. Dependências
- **Tailwind CSS Forms**: Para estilização dos campos de input.
- **main.py**: Para processar as rotas de atualização (`/update_lead` e `/update_client`).
