"""
Bot Caçador de Ofertas - Pelando.com.br → Telegram
Versão: 4.0 (Fonte: Pelando RSS)
"""

import requests
import time
import os
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURAÇÕES
# ─────────────────────────────────────────────
TOKEN_TELEGRAM  = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_TELEGRAM_AQUI")
CHAT_ID_CANAL   = os.getenv("TELEGRAM_CHAT",  "@seu_canal_aqui")
MEU_ID_AFILIADO = os.getenv("MELI_AFFILIATE", "SEU_ID_AFILIADO_AQUI")

INTERVALO_LOOP = 1800  # 30 minutos

# Palavras-chave para filtrar as ofertas do Pelando
PALAVRAS_CHAVE = [
    "samsung", "motorola", "xiaomi", "iphone", "celular", "smartphone",
    "shampoo", "cabelo", "loreal", "wella", "condicionador", "tresemme",
    "camiseta", "roupa", "calcado", "tenis", "moletom",
    "livro", "kindle",
]

# Feeds RSS públicos do Pelando por categoria
FEEDS = [
    ("📱 Celulares",       "https://www.pelando.com.br/feed/categoria/eletronicos"),
    ("💇 Cabelo & Beleza", "https://www.pelando.com.br/feed/categoria/beleza"),
    ("👕 Roupas",          "https://www.pelando.com.br/feed/categoria/moda"),
    ("📚 Livros",          "https://www.pelando.com.br/feed/categoria/livros"),
    ("🔥 Geral",           "https://www.pelando.com.br/feed"),
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
    texto_lower = texto.lower()
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

def gerar_link_afiliado(link_original: str) -> str:
    """Se o link for do ML, adiciona o ID de afiliado."""
    if MEU_ID_AFILIADO == "SEU_ID_AFILIADO_AQUI":
        return link_original
    if "mercadolivre.com.br" in link_original or "mercadolibre.com" in link_original:
        sep = "&" if "?" in link_original else "?"
        return f"{link_original}{sep}affiliation_id={MEU_ID_AFILIADO}"
    return link_original

def buscar_feed(url: str, categoria: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OfertasBot/1.0)"}
    ofertas = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            log.warning(f"Erro {r.status_code} no feed: {url}")
            return []

        root = ET.fromstring(r.content)
        channel = root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")
        log.info(f"  {categoria}: {len(items)} item(s) no feed")

        for item in items:
            titulo = item.findtext("title", "")
            link   = item.findtext("link", "")
            desc   = item.findtext("description", "")
            guid   = item.findtext("guid", link)

            texto_completo = f"{titulo} {desc}"

            if not contem_palavra_chave(texto_completo):
                continue

            link_final = gerar_link_afiliado(link)

            ofertas.append({
                "id":        guid,
                "titulo":    titulo,
                "descricao": desc[:200].strip(),
                "link":      link_final,
                "categoria": categoria,
            })

    except ET.ParseError as e:
        log.error(f"Erro ao parsear RSS de {url}: {e}")
    except requests.exceptions.Timeout:
        log.error(f"Timeout no feed: {url}")
    except Exception as e:
        log.error(f"Erro no feed {url}: {e}")

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
    mensagem = formatar_mensagem(oferta)
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage",
        json={
            "chat_id":                  CHAT_ID_CANAL,
            "text":                     mensagem,
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
    total = 0
    for categoria, url_feed in FEEDS:
        log.info(f"🔎 Lendo feed: {categoria}...")
        ofertas = buscar_feed(url_feed, categoria)
        novas   = [o for o in ofertas if o["id"] not in historico]
        log.info(f"  ✅ {len(novas)} nova(s) oferta(s) relevante(s)")

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
    log.info("  BOT CAÇADOR DE OFERTAS v4.0 — INICIANDO")
    log.info(f"  Canal:     {CHAT_ID_CANAL}")
    log.info(f"  Fonte:     Pelando.com.br (RSS)")
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
