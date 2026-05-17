# 🤖 Bot Caçador de Ofertas — Guia de Configuração

## O que você vai precisar (você já tem os 3 primeiros ✅)

| Item | Status | Onde pegar |
|---|---|---|
| Token do Telegram | ✅ Você já tem | @BotFather no Telegram |
| Token do Mercado Livre | ✅ Você já tem | developers.mercadolibre.com.br |
| Afiliado do ML | ✅ Você já tem | Painel de afiliados do ML |
| Conta no Railway | ⬜ Criar agora | railway.app |
| Conta no GitHub | ⬜ Criar agora (gratuito) | github.com |

---

## PASSO 1 — Preencha suas credenciais no bot.py

Abra o arquivo `bot.py` e substitua os valores entre aspas nas linhas 14–21:

```python
ACCESS_TOKEN_MELI  = os.getenv("MELI_TOKEN",     "SEU_TOKEN_MELI_AQUI")
CLIENT_ID_MELI     = os.getenv("MELI_CLIENT_ID", "SEU_CLIENT_ID_AQUI")
CLIENT_SECRET_MELI = os.getenv("MELI_SECRET",    "SEU_CLIENT_SECRET_AQUI")
REFRESH_TOKEN_MELI = os.getenv("MELI_REFRESH",   "SEU_REFRESH_TOKEN_AQUI")
TOKEN_TELEGRAM     = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_TELEGRAM_AQUI")
CHAT_ID_CANAL      = os.getenv("TELEGRAM_CHAT",  "@seu_canal_aqui")
MEU_ID_AFILIADO    = os.getenv("MELI_AFFILIATE", "SEU_ID_AFILIADO_AQUI")
```

### Onde achar cada dado:

**Tokens do Mercado Livre:**
1. Acesse: https://developers.mercadolibre.com.br/devcenter
2. Clique em "Minhas Aplicações" → selecione seu app
3. Você verá: `App ID` (= CLIENT_ID), `Secret Key` (= CLIENT_SECRET)
4. Para o `Access Token` e `Refresh Token`: vá na aba "Credenciais"

**ID de Afiliado:**
1. Acesse o painel de afiliados do ML
2. Procure por "meu ID de afiliado" ou "tracking ID"
3. Ele aparece nos links gerados pelo painel (ex: `?affiliation_id=XXXXX`)

**Canal do Telegram:**
- Crie um canal público no Telegram
- O nome do canal (ex: `@minhasofertasml`) vai no campo `CHAT_ID_CANAL`
- Adicione seu bot como **Administrador** do canal

---

## PASSO 2 — Personalize as marcas (opcional)

No arquivo `bot.py`, na seção `MARCAS_ALVO`, você pode trocar os nicknames
pelas lojas que quiser monitorar.

**Como descobrir o nickname exato de uma loja:**
1. Acesse a loja no Mercado Livre
2. Clique no nome do vendedor
3. Na URL da loja você verá: `mercadolivre.com.br/perfil/NICKNAME`
4. Copie esse NICKNAME e cole na lista

**Exemplos de lojas populares para cada categoria:**
- Celulares: `SAMSUNG_BRASIL`, `XIAOMI_BRASIL`, `MOTOROLA_MOTOROLA`
- Cabelo: `LOREALPARIS_BRASIL`, `WELLA_BRASIL`
- Roupas: `HERING_OFICIAL`, `CEA_LOJAOFICIAL`
- Livros: `INTRINSECA_LIVROS`, `LIVRARIASARAIVA`

---

## PASSO 3 — Subir para o GitHub

1. Crie uma conta em https://github.com (se não tiver)
2. Crie um repositório **privado** (importante: privado para proteger seus tokens)
3. Suba os 3 arquivos:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`

**Via interface web do GitHub (sem precisar de Git):**
- Clique em "Add file" → "Upload files" → arraste os 3 arquivos → "Commit"

---

## PASSO 4 — Subir para o Railway (nuvem gratuita)

1. Acesse https://railway.app e crie uma conta (pode usar o GitHub para login)
2. Clique em **"New Project"** → **"Deploy from GitHub repo"**
3. Selecione o repositório que você criou
4. O Railway detecta o `Procfile` automaticamente

### Configurar as variáveis de ambiente (MUITO IMPORTANTE):
Em vez de deixar os tokens no código, coloque-os nas variáveis do Railway:

1. No seu projeto no Railway, clique em **"Variables"**
2. Adicione cada variável:

| Nome da variável | Valor |
|---|---|
| `MELI_TOKEN` | seu access token do ML |
| `MELI_CLIENT_ID` | seu client ID do ML |
| `MELI_SECRET` | seu client secret do ML |
| `MELI_REFRESH` | seu refresh token do ML |
| `TELEGRAM_TOKEN` | seu token do BotFather |
| `TELEGRAM_CHAT` | @seu_canal |
| `MELI_AFFILIATE` | seu ID de afiliado |

3. Clique em **"Deploy"** — o bot começa a rodar!

---

## PASSO 5 — Testar se está funcionando

Depois de fazer o deploy, clique em **"Logs"** no Railway.
Você deve ver algo assim:

```
==================================================
  BOT CAÇADOR DE OFERTAS — INICIANDO
  Canal: @seu_canal
  Desconto mínimo: 15%
  Intervalo: 60 minutos
==================================================
Histórico carregado: 0 item(s) já postado(s).

🕐 [10:30:00] Iniciando nova varredura...
🔎 Buscando seller_id de SAMSUNG_BRASIL...
  ✅ SAMSUNG_BRASIL → seller_id=123456
  📦 3 oferta(s) com ≥15% de desconto
  📣 Postado: Samsung Galaxy A54 5G 128GB...
```

---

## ⚙️ Personalizações rápidas

**Mudar o desconto mínimo** (linha 30 do bot.py):
```python
DESCONTO_MINIMO = 20  # só posta se tiver 20% ou mais de desconto
```

**Mudar a frequência de varredura** (linha 33 do bot.py):
```python
INTERVALO_LOOP = 1800  # verifica a cada 30 minutos
```

---

## ❓ Dúvidas frequentes

**O bot não encontrou nenhuma loja:**
→ Os nicknames podem estar diferentes. Use a dica do Passo 2 para confirmar.

**Token expirado:**
→ O bot renova automaticamente usando o Refresh Token. Confira se preencheu o `MELI_REFRESH` corretamente.

**Mensagem não chegou no Telegram:**
→ Confirme que adicionou o bot como Administrador do canal.

**Quer adicionar WhatsApp também:**
→ A opção mais fácil e gratuita é a Evolution API (self-hosted) ou a Z-API (paga, ~R$30/mês).
