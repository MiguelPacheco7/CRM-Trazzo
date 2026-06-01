# Documentação Técnica: layout.html

## 1. Descrição Geral
O arquivo `layout.html` é o "Template Mestre" do sistema. Ele contém a estrutura que se repete em todas as páginas (Cabeçalho, Menu, Barras Laterais e Scripts base). Utilizamos o conceito de **Herança de Templates** do Jinja2, permitindo que outras páginas apenas "preencham" o conteúdo central.

## 2. Processo de Criação
1. **Estrutura Base**: Criamos um documento HTML5 padrão com Tailwind CSS para estilização rápida.
2. **Navegação Superior**: Implementamos a logo "Trazzo" e os links principais.
3. **Componentes Laterais**: Desenvolvemos as **Sidebars** de Notificações e Configurações como divs escondidas fora da tela.
4. **Interatividade**: Criamos funções JavaScript para animar a abertura e fechamento dessas barras.

## 3. Explicação Detalhada

### Tags e Elementos HTML
- `<nav>`: Barra de navegação superior. Contém a logo e os botões de ação.
- `<div id="sidebarOverlay">`: Uma camada escura que aparece atrás das barras laterais para dar foco e permitir fechar ao clicar fora.
- `{% block content %}`: Tag especial do Jinja2. É aqui que o conteúdo das outras páginas (como o gráfico do dashboard) será inserido.

### Estilização (Tailwind CSS)
- `backdrop-blur-md`: Cria o efeito de vidro embaçado na barra superior, seguindo tendências modernas de UI.
- `translate-x-full`: Esconde as barras laterais movendo-as para fora da tela (à direita).
- `transition-transform`: Faz com que a barra lateral deslize suavemente em vez de aparecer instantaneamente.

### Scripts (JavaScript)
- `toggleSidebar(id)`: 
    - **Lógica**: Verifica se a barra está aberta ou fechada e altera as classes CSS para movê-la.
    - **Uso**: Chamada pelos ícones de sino e engrenagem.
- `location.reload()`: Comando atrelado à logo para atualizar a página.

## 4. Dependências
- **Tailwind CSS**: Para todo o design visual.
- **Google Fonts (Inter)**: Para a tipografia limpa.
- **Icons8**: Para os ícones de menu.
- **Jinja2**: Para a lógica de herança de blocos.
