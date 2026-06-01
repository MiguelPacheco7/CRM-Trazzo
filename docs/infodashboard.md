# Documentação Técnica: dashboard.html

## 1. Descrição Geral
Este arquivo renderiza o painel de controle financeiro do sistema. Sua função é transformar dados brutos do banco de dados em informações visuais compreensíveis, como porcentagens de conversão e tendências de faturamento.

## 2. Processo de Criação
1. **Layout em Grid**: Usamos o sistema de grade do Tailwind (`grid-cols-12`) para organizar os cards em diferentes tamanhos.
2. **Implementação de Gráficos**: Integramos o **Chart.js** para desenhar a linha de faturamento.
3. **Lógica de Filtros**: Criamos funções JavaScript que recalculam o gráfico quando o usuário clica em "1A", "6M" ou "3M".

## 3. Explicação Detalhada

### Tags e Componentes
- `<canvas id="revenueChart">`: O elemento onde o JavaScript desenha o gráfico.
- `{{ total_leads }}`: Tag de interpolação do Jinja2 que insere o número vindo do Python diretamente no texto do HTML.
- `{% for month in [...] %}`: Loop que gera automaticamente os cards do calendário.

### Gráficos (Chart.js)
- `type: 'line'`: Define que queremos um gráfico de linhas.
- `tension: 0.4`: Comando que cria as curvas suaves na linha do gráfico, dando um aspecto orgânico.
- `|tojson`: Filtro do Jinja2 que transforma listas do Python em formatos que o JavaScript consegue ler.

### JavaScript de Filtragem
- `const currentMonth = new Date().getMonth()`: Captura o mês atual do sistema do usuário para que o gráfico "6M" sempre termine no mês correto.
- `filteredData.push(...)`: Lógica que reconstrói a lista de valores baseada no período selecionado.

## 4. Dependências
- **Chart.js**: Biblioteca externa para renderização de gráficos.
- **layout.html**: Este arquivo estende a base comum do sistema.
