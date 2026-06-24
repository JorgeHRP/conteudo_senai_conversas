# SENAI CRM — Painel de Atendimentos do Agente IA

Dashboard web em Flask para monitorar os leads captados pelo agente IA SDR do SENAI Goiás.
O agente opera via WhatsApp (Lara) e registra conversas no Supabase; este painel é a interface de visualização para o operador humano.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12 + Flask 3.x |
| Banco de dados | Supabase (PostgreSQL) |
| Frontend | HTML/CSS/JS vanilla — design glassmorphism Apple |
| Gráficos | Chart.js 4.x (CDN) |

---

## Estrutura do projeto

```
senai_conversas/
├── .env                    ← credenciais (não sobe no git)
├── app.py                  ← Flask — rotas, lógica, integração Supabase
├── requirements.txt
├── templates/
│   ├── base.html           ← layout base com navegação
│   ├── login.html          ← tela de login com banner e logo SENAI
│   ├── dashboard.html      ← aba analytics (KPIs + gráficos)
│   └── atendimentos.html   ← aba de leads com modal de conversa
└── static/
    ├── css/style.css       ← design system glass Apple completo
    ├── js/main.js          ← filtros de tabela + modal de chat
    └── img/
        ├── capa.png        ← banner retangular (usado no login)
        └── perfil.png      ← logo circular SENAI (usado na nav e login)
```

---

## Tabelas no Supabase

### `conteudo_senai_usuario`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | int | PK |
| `created_at` | timestamp | data de entrada do lead |
| `telefone` | text | número WhatsApp (chave de ligação com conversas) |
| `nomewpp` | text | nome do WhatsApp |
| `status` | int/text | classificação do lead (ver abaixo) |
| `follow_up` | bool | se o lead já recebeu contato humano |

### `conteudo_senai_conversas`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | int | PK |
| `session_id` | text | telefone do lead (FK para `conteudo_senai_usuario.telefone`) |
| `message` | json | objeto com `type` ("human"/"ai") e `content` (texto) |

> **Atenção:** o Supabase pode retornar `status` como string (`"1"`) mesmo que a coluna seja int. O `app.py` já faz `int(raw)` para normalizar.

---

## Enum de status

| Valor | Label | Badge |
|-------|-------|-------|
| `1` | Lead Novo | azul |
| `2` | Interesse | verde |
| `3` | Sem Interesse | vermelho |
| `null` | Pendente | cinza |

O agente IA deve gravar `1`, `2` ou `3` na coluna `status` ao final da conversa.
O campo `follow_up` é atualizado manualmente (ou pelo agente) para `true` quando o humano já entrou em contato.

---

## Variáveis de ambiente (`.env`)

```env
SECRET_KEY=...          # chave Flask para sessão
LOGIN_USER=admin        # usuário do painel
LOGIN_PASSWORD=...      # senha do painel
SUPABASE_URL=...        # URL do projeto Supabase
SUPABASE_KEY=...        # service_role key do Supabase
```

---

## Como rodar

```bash
pip install -r requirements.txt
python app.py
# Acessa: http://127.0.0.1:5000
```

---

## Rotas

| Rota | Descrição |
|------|-----------|
| `GET /` | Redireciona para login ou dashboard |
| `GET/POST /login` | Autenticação por usuário/senha do `.env` |
| `GET /logout` | Encerra sessão |
| `GET /dashboard` | Aba analytics — KPIs + gráficos Chart.js |
| `GET /atendimentos` | Tabela de leads com busca e filtros |
| `GET /api/conversation/<telefone>` | JSON com mensagens da conversa (usado pelo modal) |

---

## Comportamento do modal de conversa

- Clique em qualquer linha da tabela de atendimentos
- Abre um sheet iOS deslizante com o histórico de chat
- Mensagens humanas: bolha azul (direita)
- Mensagens do agente IA: bolha cinza (esquerda)
- Respostas da IA que chegam como JSON `{"output":{"mensagem":"..."}}` são automaticamente extraídas para mostrar só o texto

---

## Observações para próximas sessões

- O design segue a paleta Apple: `#0071e3` (azul), `#34c759` (verde), `#ff3b30` (vermelho), fundo `#07090f`
- Não há banco de dados local — tudo lido em tempo real do Supabase a cada request
- Não há paginação implementada — se o volume de leads crescer muito, adicionar `.range()` nas queries do Supabase
- O filtro da tabela de atendimentos é client-side (JS puro), sem query extra ao backend
