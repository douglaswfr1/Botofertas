"""
Bot Caçador de Ofertas - Mercado Livre → Telegram
Versão: 3.1 (Corrigido - sem official_store)
"""

import requests
import time
import os
import json
import logging
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURAÇÕES — preencha com seus dados
# ─────────────────────────────────────────────
ACCESS_TOKEN_MELI = os.getenv("MELI_TOKEN",      "SEU_TOKEN_MELI_AQUI")
TOKEN_TELEGRAM    = os.getenv("TELEGRAM_TOKEN",  "SEU_TOKEN_TELEGRAM_AQUI")
CHAT_ID_CANAL     = os.getenv("TELEGRAM_CHAT",   "@seu_canal_aqui")
MEU_ID_AFILIADO   = os.getenv("MELI_AFFILIATE",  "SEU_ID_AFILIADO_AQUI")

DESCONTO_MINIMO = 5    # % mínimo de desconto para postar
INTERVALO_LOOP  = 3600  # segundos entre varreduras (1 hora)

# ─────────────────────────────────────────────
#  BUSCAS POR PALAVRA-CHAVE
# ─────────────────────────────────────────────
BUSCAS = [
    ("📱 Celulares",       "samsung galaxy"),
    ("📱 Celulares",       "motorola edge"),
    ("📱 Celulares",       "xiaomi redmi"),
    ("💇 Cabelo & Beleza", "shampoo loreal"),
    ("💇 Cabelo & Beleza", "shampoo wella"),
    ("💇 Cabelo & Beleza", "condicionador tresemme"),
    ("💇 Cabelo & Beleza", "kit cabelo salon line"),
    ("👕 Roupas",          "camiseta hering"),
    ("👕 Roupas",          "conjunto moletom"),
    ("📚 Livros",          "livro bestseller"),
    ("📚 Livros",          "livro autoajuda"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

ARQUIVO_HISTORICO = "ofertas_postadas.json"

def carregar_historico() -> set:
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r") as f:
            return set(json.load(f))
    return set()

def salvar_historico(ids: set):
    with open(ARQUIVO_HISTORICO, "w") as f:
        json.dump(list(ids), f)

def get_headers() -> dict:
    return {"Authorization": f"Bearer {ACCESS_TOKEN_MELI}"}

def buscar_ofertas(termo: str, categoria: str) -> list:
    # Sem official_store — funciona com qualquer token de desenvolvedor
    url = (
        f"https://api.mercadolibre.com/sites/MLB/search"
        f"?q={requests.utils.quote(termo)}"
        f"&sort=relevance"
        f"&limit=50"
    )
    ofertas = []
    try:
        r = requests.get(url, headers=get_headers(), timeout=15)

        if r.status_code == 401:
            log.error("Token inválido ou expirado! Atualize MELI_TOKEN no Railway.")
            return []
        if r.status_code != 200:
            log.warning(f"Erro {r.status_code} buscando '{termo}': {r.text[:200]}")
            return []

        produtos = r.json().get("results", [])
        log.info(f"  '{termo}': {len(produtos)} produto(s) encontrado(s)")

        for item in produtos:
            preco_atual    = item.get("price")
            preco_original = item.get("original_price")

            if not preco_original or not preco_atual:
                continue
            if preco_atual >= preco_original:
                continue

            desconto = ((preco_original - preco_atual) / preco_original) * 100
            if desconto < DESCONTO_MINIMO:
                continue

            item_id   = item.get("id", "")
            permalink = item.get("permalink", "")
            thumbnail = item.get("thumbnail", "").replace("I.jpg", "O.jpg")

            if MEU_ID_AFILIADO and MEU_ID_AFILIADO != "SEU_ID_AFILIADO_AQUI":
                link = (
                    f"https://mercadolivre.com/sec/afiliados"
                    f"?rec_source=affiliate&affiliation_id={MEU_ID_AFILIADO}"
                    f"&item_id={item_id}"
                )
            else:
                link = permalink

            ofertas.append({
                "id":             item_id,
                "titulo":         item.get("title", ""),
                "preco_atual":    preco_atual,
                "preco_original": preco_original,
                "desconto":       desconto,
                "link":           link,
                "thumbnail":      thumbnail,
                "categoria":      categoria,
            })

    except requests.exceptions.Timeout:
        log.error(f"Timeout buscando '{termo}'")
    except Exception as e:
        log.error(f"Erro ao buscar '{termo}': {e}")

    return ofertas

def formatar_mensagem(o: dict) -> str:
    return (
        f"{o['categoria']}\n\n"
        f"🛒 *{o['titulo']}*\n\n"
        f"❌ De: ~R$ {o['preco_original']:,.2f}~\n"
        f"✅ Por: *R$ {o['preco_atual']:,.2f}*\n"
        f"🔥 *{o['desconto']:.0f}% OFF!*\n\n"
        f"👉 [COMPRAR AGORA]({o['link']})"
    )

def enviar_telegram(oferta: dict) -> bool:
    mensagem = formatar_mensagem(oferta)

    if oferta.get("thumbnail"):
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto",
            json={"chat_id": CHAT_ID_CANAL, "photo": oferta["thumbnail"],
                  "caption": mensagem, "parse_mode": "Markdown"},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log.warning(f"Foto falhou ({r.status_code}), enviando texto...")

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage",
        json={"chat_id": CHAT_ID_CANAL, "text": mensagem,
              "parse_mode": "Markdown", "disable_web_page_preview": False},
        timeout=10,
    )
    if r.status_code != 200:
        log.error(f"Falha Telegram: {r.status_code} — {r.text}")
        return False
    return True

def rodar_varredura(historico: set) -> set:
    total = 0
    for categoria, termo in BUSCAS:
        log.info(f"🔎 Buscando: '{termo}'...")
        ofertas = buscar_ofertas(termo, categoria)
        novas   = [o for o in ofertas if o["id"] not in historico]
        log.info(f"  ✅ {len(novas)} nova(s) com >= {DESCONTO_MINIMO}% OFF")

        for oferta in novas:
            if enviar_telegram(oferta):
                historico.add(oferta["id"])
                total += 1
                log.info(f"  📣 Postado: {oferta['titulo'][:60]}...")
                time.sleep(4)

        time.sleep(2)

    salvar_historico(historico)
    log.info(f"\n✅ Varredura concluída — {total} nova(s) oferta(s) postada(s).")
    return historico

def main():
    log.info("=" * 52)
    log.info("  BOT CAÇADOR DE OFERTAS v3.1 — INICIANDO")
    log.info(f"  Canal:           {CHAT_ID_CANAL}")
    log.info(f"  Desconto mínimo: {DESCONTO_MINIMO}%")
    log.info(f"  Intervalo:       {INTERVALO_LOOP // 60} minutos")
    log.info(f"  Buscas ativas:   {len(BUSCAS)}")
    log.info("=" * 52)

    historico = carregar_historico()
    log.info(f"Histórico: {len(historico)} item(s) já postado(s).\n")

    while True:
        try:
            log.info(f"🕐 [{datetime.now().strftime('%H:%M:%S')}] Iniciando varredura...")
            historico = rodar_varredura(historico)
        except Exception as e:
            log.error(f"Erro no loop: {e}")

        log.info(f"💤 Aguardando {INTERVALO_LOOP // 60} min...\n")
        time.sleep(INTERVALO_LOOP)

if __name__ == "__main__":
    main()
