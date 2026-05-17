"""
Bot Caçador de Ofertas - Pelando.com.br → Telegram
Versão: 4.2
"""

import requests
import time
import os
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_TELEGRAM_AQUI")
CHAT_ID_CANAL  = os.getenv("TELEGRAM_CHAT",  "@seu_canal_aqui")

INTERVALO_LOOP = 1800  # 30 minutos

PALAVRAS_CHAVE = [
    "samsung", "motorola", "xiaomi", "iphone", "celular", "smartphone",
    "shampoo", "cabelo", "loreal", "wella", "condicionador", "tresemme",
    "salon line", "mascara capilar", "creme",
    "camiseta", "roupa", "calcado", "tenis", "moletom", "vestido",
    "livro", "kindle", "manga",
]

# Só os feeds que funcionaram
FEEDS = [
    ("🔥 Oferta",    "https://www.pelando.com.br/feed"),
    ("🔥 Populares", "https://www.pelando.com.br/feed/popular"),
    ("🔥 Recentes",  "https://www.pelando.com.br/feed/new"),
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

def contem_palavra_chave(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in PALAVRAS_CHAVE)

def categorizar(texto: str) -> str:
    t = texto.lower()
    if any(p in t for p in ["samsung", "motorola", "xiaomi", "iphone", "celular", "smartphone"]):
        return "📱 Celulares & Tech"
    if any(p in t for p in ["shampoo", "cabelo", "loreal", "wella", "condicionador", "tresemme", "salon line"]):
        return "💇 Cabelo & Beleza"
    if any(p in t for p in ["camiseta", "roupa", "calcado", "tenis", "moletom", "vestido"]):
        return "👕 Moda & Roupas"
    if any(p in t for p in ["livro", "kindle", "manga"]):
        return "📚 Livros"
    return "🔥 Oferta"

def buscar_feed(url: str, nome: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OfertasBot/1.0)"}
    ofertas = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            log.warning(f"Erro {r.status_code} no feed {nome}")
            return []

        root    = ET.fromstring(r.content)
        channel = root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")
        log.info(f"  {nome}: {len(items)} oferta(s) no feed")

        for item in items:
            titulo = item.findtext("title", "")
            link   = item.findtext("link", "")
            desc   = item.findtext("description", "")
            guid   = item.findtext("guid", link)

            texto = f"{titulo} {desc}"
            if not contem_palavra_chave(texto):
                continue

            desc_limpa = desc.replace("<p>", "").replace("</p>", "").replace("<br>", "").strip()[:200]
            categoria  = categorizar(texto)

            ofertas.append({
                "id":        guid,
                "titulo":    titulo,
                "descricao": desc_limpa,
                "link":      link,
                "categoria": categoria,
            })

    except ET.ParseError:
        log.error(f"Erro ao ler RSS de {nome}")
    except requests.exceptions.Timeout:
        log.error(f"Timeout no feed {nome}")
    except Exception as e:
        log.error(f"Erro no feed {nome}: {e}")

    return ofertas

def formatar_mensagem(o: dict) -> str:
    desc = f"\n_{o['descricao']}_\n" if o.get("descricao") else ""
    return (
        f"{o['categoria']}\n\n"
        f"🛒 *{o['titulo']}*\n"
        f"{desc}\n"
        f"👉 [VER OFERTA]({o['link']})"
    )

def enviar_telegram(oferta: dict) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage",
        json={
            "chat_id":                  CHAT_ID_CANAL,
            "text":                     formatar_mensagem(oferta),
            "parse_mode":               "Markdown",
            "disable_web_page_preview": False,
        },
        timeout=10,
    )
    if r.status_code != 200:
        log.error(f"Falha Telegram: {r.status_code} — {r.text}")
        return False
    return True

def rodar_varredura(historico: set) -> set:
    total    = 0
    ids_vistos = set()

    for nome, url_feed in FEEDS:
        log.info(f"🔎 Lendo: {nome}...")
        ofertas = buscar_feed(url_feed, nome)

        for oferta in ofertas:
            if oferta["id"] in historico or oferta["id"] in ids_vistos:
                continue
            ids_vistos.add(oferta["id"])

            if enviar_telegram(oferta):
                historico.add(oferta["id"])
                total += 1
                log.info(f"  📣 Postado: {oferta['titulo'][:60]}...")
                time.sleep(4)

        time.sleep(2)

    salvar_historico(historico)
    log.info(f"\n✅ Concluído — {total} nova(s) oferta(s) postada(s).")
    return historico

def main():
    log.info("=" * 52)
    log.info("  BOT DE OFERTAS v4.2 — INICIANDO")
    log.info(f"  Canal:     {CHAT_ID_CANAL}")
    log.info(f"  Fonte:     Pelando.com.br")
    log.info(f"  Intervalo: {INTERVALO_LOOP // 60} minutos")
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
