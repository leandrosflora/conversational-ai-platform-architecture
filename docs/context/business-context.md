# Contexto de Negócio

## Visão Geral

Instituições financeiras possuem grandes carteiras de clientes com contratos em atraso, parcelas vencidas e oportunidades de renegociação de dívidas.

Tradicionalmente, esses processos dependem de centrais de atendimento, operadores humanos e atividades de backoffice, gerando altos custos operacionais, baixa escalabilidade e experiências inconsistentes para os clientes.

A Plataforma de IA Conversacional tem como objetivo disponibilizar um canal de renegociação digital baseado em Inteligência Artificial Generativa, permitindo que clientes negociem seus débitos por meio de interações conversacionais, mantendo requisitos de segurança, auditoria, rastreabilidade e conformidade regulatória.

Embora a primeira versão utilize o WhatsApp como canal principal, a solução deve ser projetada de forma agnóstica ao canal, possibilitando sua reutilização futura em outros meios de comunicação.

!!! warning "Escopo dos dados demonstrados"
    A implementação executável deste repositório não acessa clientes, contratos, débitos, propostas, acordos, limites ou faturas reais. Os domínios funcionais de **recuperação/renegociação** e **cartão de crédito** operam com massas sintéticas e respostas determinísticas do `core-bancario-mock`. Os testes E2E demonstram a jornada, a integração e os controles arquiteturais; não representam processamento bancário produtivo nem validam regras financeiras reais.

!!! info "Arquitetura-alvo"
    Em uma implantação corporativa, o `core-bancario-mock` deve ser substituído por APIs reais e governadas dos sistemas bancários responsáveis por cadastro, contratos, débitos, elegibilidade, simulação, formalização, documentos, limite e fatura. Essa substituição deve preservar ou fortalecer autenticação de workload, autorização por operação, isolamento por tenant, idempotência, trilha de auditoria, contratos de API, observabilidade e tratamento de indisponibilidade.

---

## Problema de Negócio

Os processos atuais de renegociação apresentam diversos desafios:

- Elevada dependência de atendimento humano.
- Custos operacionais elevados.
- Disponibilidade limitada dos canais de atendimento.
- Baixa escalabilidade para campanhas de recuperação de crédito.
- Experiência do cliente fragmentada.
- Baixa personalização durante a negociação.
- Tempo elevado para conclusão de acordos.

Além disso, durante a jornada de renegociação, os clientes frequentemente possuem dúvidas relacionadas a:

- Valores em aberto.
- Composição da dívida.
- Juros e encargos.
- Regras de renegociação.
- Quantidade de parcelas.
- Condições de pagamento.
- Formalização do acordo.

Essas interações exigem suporte contínuo e representam uma oportunidade para utilização de agentes autônomos baseados em IA.

---

## Objetivos de Negócio

A plataforma deve permitir:

- Automatizar jornadas de renegociação de dívidas.
- Aumentar a conversão de acordos.
- Reduzir custos operacionais.
- Melhorar a experiência do cliente.
- Disponibilizar atendimento 24x7.
- Escalar campanhas de recuperação de crédito.
- Garantir rastreabilidade completa das interações.
- Atender requisitos regulatórios e de LGPD.
- Permitir expansão futura para múltiplos canais.

---

## Escopo

### Dentro do Escopo

#### Identificação do Cliente

A plataforma deve validar a identidade do cliente antes de disponibilizar informações sensíveis.

Exemplos:

- Confirmação de CPF.
- Confirmação de data de nascimento.
- Validação por OTP.
- Perguntas adicionais definidas pelas regras de negócio.

#### Consulta de Débitos

A plataforma deve consultar os contratos e débitos elegíveis para renegociação. Na implementação de referência, os dados retornados são sintéticos; na arquitetura-alvo, a consulta deve ocorrer nas APIs reais responsáveis pelo produto e pelo registro financeiro.

#### Atendimento Conversacional

A plataforma deve responder dúvidas dos clientes utilizando uma base de conhecimento corporativa contendo:

- FAQ de produtos.
- Políticas de renegociação.
- Regras operacionais.
- Informações contratuais.
- Procedimentos internos.

#### Simulação de Propostas

A plataforma deve gerar propostas de renegociação conforme regras de negócio e critérios de elegibilidade. A simulação atual usa valores e regras de teste; produção deve delegar cálculo, elegibilidade e persistência ao sistema bancário real ou ao motor corporativo autorizado.

#### Consulta de Fatura e Limite de Cartão de Crédito

Além da jornada de renegociação, a plataforma disponibiliza uma segunda skill de atendimento: consulta de limite total/disponível e de valor/vencimento da fatura atual do cartão de crédito do cliente, após identificação por CPF. É uma skill somente-leitura, sem simulação, negociação ou formalização — o cliente pergunta e recebe a informação. Quando o cliente pergunta algo fora desse escopo (ex.: renegociação) dentro dessa skill, a plataforma reconhece o desvio e permite reapresentar o menu de opções.

Os valores de limite, disponibilidade, fatura e vencimento demonstrados são dados sintéticos retornados pela Card API do `core-bancario-mock`. Na arquitetura-alvo, a skill deve consumir APIs reais do domínio de cartões, sem transformar o agente ou o Tool Service em fonte de verdade financeira.

#### Negociação

O cliente poderá:

- Aceitar uma proposta.
- Solicitar novas simulações.
- Comparar opções.
- Esclarecer dúvidas antes da contratação.

#### Formalização

A plataforma deve formalizar o acordo por meio da integração com sistemas internos do banco. A confirmação executada no ambiente de referência é simulada e não cria obrigação financeira real.

#### Transferência para Atendimento Humano

A plataforma deve permitir transferência para um atendente humano quando:

- O cliente solicitar.
- O agente não possuir confiança suficiente para responder.
- Houver falha operacional.
- Existirem restrições definidas pelo negócio.

#### Auditoria e Conformidade

Todas as interações relevantes devem ser registradas para fins de auditoria, compliance e rastreabilidade.

---

### Fora do Escopo

Os seguintes itens não fazem parte da primeira versão da solução:

- Processamento de dados bancários produtivos.
- Criação de acordos, contratos ou obrigações financeiras reais.
- Atendimento por voz.
- Gestão de estratégias de cobrança.
- Motores de política de crédito.
- Operações internas de backoffice.
- Abertura de contas.
- Venda de novos produtos financeiros.
- Integrações com outras instituições financeiras.

---

## Personas

### Cliente

Pessoa física ou jurídica que deseja consultar e renegociar débitos existentes.

#### Objetivos

- Entender sua situação financeira.
- Consultar contratos em atraso.
- Simular propostas.
- Formalizar acordos.
- Resolver pendências financeiras de forma rápida e simples.

---

### Gestor de Cobrança

Responsável pelos indicadores de recuperação de crédito.

#### Objetivos

- Aumentar a recuperação financeira.
- Melhorar taxas de conversão.
- Reduzir custos operacionais.
- Escalar campanhas de renegociação.

---

### Atendente Humano

Profissional responsável pelo tratamento de exceções e jornadas transferidas pela plataforma.

#### Objetivos

- Resolver situações complexas.
- Atender casos excepcionais.
- Dar continuidade às negociações iniciadas pela IA.

---

## Canais de Entrada

A primeira versão da solução terá como canal principal o WhatsApp.

Entretanto, a arquitetura deve suportar futura expansão para:

- Web Chat.
- Aplicativos Mobile.
- Sistemas de Franqueados.
- Redes Sociais.
- Canais de Voz.

---

## Jornadas de Negócio

### Jornada 1 — Campanha de Renegociação

1. O Salesforce CRM gera uma base de clientes elegíveis para campanha de renegociação.
2. A base é disponibilizada no Data Lake corporativo.
3. Um produto de dados ou automação de campanha consome essa base.
4. O cliente recebe uma comunicação por Email, SMS, Instagram, Facebook ou outro canal de ativação.
5. A comunicação direciona o cliente para o WhatsApp oficial do banco.
6. O cliente inicia a conversa.
7. A identidade é validada.
8. Os débitos elegíveis são consultados nas APIs reais do produto na arquitetura-alvo; no ambiente de referência, são retornados pelo mock.
9. As propostas disponíveis são apresentadas.
10. O cliente realiza perguntas e solicita simulações.
11. Uma proposta é selecionada.
12. O acordo é formalizado no sistema bancário real; no ambiente de referência, a confirmação é simulada.
13. O comprovante é disponibilizado ao cliente.

---

### Jornada 2 — Oferta Proativa via WhatsApp

1. O banco envia uma proposta de renegociação diretamente pelo WhatsApp.
2. O cliente responde à mensagem.
3. A identidade é validada.
4. Os débitos são apresentados.
5. O cliente negocia condições e simulações.
6. O acordo é aceito.
7. O contrato é formalizado.
8. A confirmação é enviada ao cliente.

Na referência executável, todas as informações financeiras e confirmações desta jornada são sintéticas.

---

### Jornada 3 — Consulta de Fatura e Limite de Cartão de Crédito

1. O cliente inicia a conversa pelo WhatsApp e escolhe (ou é roteado para) a skill de cartão de crédito.
2. A identidade é validada por CPF.
3. O cliente pergunta pelo limite disponível e/ou pelo valor da fatura atual.
4. A plataforma consulta limite e fatura. Atualmente, a resposta vem do `core-bancario-mock`; na arquitetura-alvo, deve vir das APIs reais do domínio de cartões.
5. Caso o cliente faça uma pergunta fora desse escopo (ex.: renegociação), a plataforma sinaliza o desvio e reapresenta o menu de skills.

---

## Capacidades de Inteligência Artificial

### Agente Autônomo

Responsável por conduzir a jornada de renegociação, interpretar mensagens, decidir próximos passos e acionar ferramentas corporativas autorizadas. O agente não calcula nem inventa valores financeiros e não é fonte de verdade do produto.

### RAG (Retrieval Augmented Generation)

Utilizado para responder perguntas com base em informações corporativas confiáveis.

### Base de Conhecimento

Contém:

- FAQ.
- Produtos.
- Políticas.
- Procedimentos.
- Regras de negócio.

### MCP (Model Context Protocol)

Permite que os agentes executem ações em sistemas corporativos por meio de ferramentas padronizadas e governadas.

Exemplos:

- Consultar cliente.
- Consultar contratos.
- Consultar débitos.
- Validar elegibilidade.
- Simular propostas.
- Confirmar acordos.
- Gerar documentos.
- Consultar limite do cartão de crédito.
- Consultar fatura do cartão de crédito.

---

## Requisitos Não Funcionais

### Segurança

- Autenticação e autorização.
- Criptografia em trânsito e em repouso.
- Integrações seguras entre sistemas.

### Privacidade e LGPD

- Proteção de dados pessoais.
- Minimização de dados.
- Auditoria de acessos e operações.

### Escalabilidade

- Escalabilidade horizontal.
- Serviços stateless sempre que possível.

### Disponibilidade

- Alta disponibilidade.
- Tolerância a falhas.

### Observabilidade

- Logs centralizados.
- Métricas operacionais.
- Distributed Tracing.

### Auditoria

- Rastreabilidade completa das conversas.
- Rastreabilidade das decisões da IA.
- Registro das execuções de ferramentas e integrações.

### Performance

- Baixa latência para interações conversacionais.
- Respostas adequadas para jornadas síncronas.

### Governança de Custos

- Monitoramento de consumo de modelos.
- Controle de tokens.
- FinOps para IA Generativa.