"""
Bot Caçador de Ofertas - Mercado Livre → Telegram
Versão: 2.0 (Produção / Nuvem)
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
ACCESS_TOKEN_MELI  = os.getenv("MELI_TOKEN",     "SEU_TOKEN_MELI_AQUI")
CLIENT_ID_MELI     = os.getenv("MELI_CLIENT_ID", "SEU_CLIENT_ID_AQUI")
CLIENT_SECRET_MELI = os.getenv("MELI_SECRET",    "SEU_CLIENT_SECRET_AQUI")
REFRESH_TOKEN_MELI = os.getenv("MELI_REFRESH",   "SEU_REFRESH_TOKEN_AQUI")

TOKEN_TELEGRAM     = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_TELEGRAM_AQUI")
CHAT_ID_CANAL      = os.getenv("TELEGRAM_CHAT",  "@seu_canal_aqui")

# ID de afiliado do Mercado Livre (obtido no painel de afiliados)
MEU_ID_AFILIADO    = os.getenv("MELI_AFFILIATE", "SEU_ID_AFILIADO_AQUI")

# Desconto mínimo para postar (em %)
DESCONTO_MINIMO    = 15

# Intervalo entre cada varredura completa (em segundos)
INTERVALO_LOOP     = 3600  # 1 hora

# Marcas por categoria — o bot busca o seller_id automaticamente
MARCAS_ALVO = {
    "📱 Celulares": [
        "SAMSUNG_BRASIL",
        "XIAOMI_BRASIL",
        "MOTOROLA_MOTOROLA",
    ],
    "💇 Cabelo & Beleza": [
        "LOREALPARIS_BRASIL",
        "NAZCA_COSMETICOS",
        "WELLA_BRASIL",
    ],
    "👕 Roupas": [
        "HERING_OFICIAL",
        "RENNER_LOJAOFICIAL",
        "CEA_LOJAOFICIAL",
    ],
    "📚 Livros": [
        "INTRINSECA_LIVROS",
        "CULTURAOFICIAL",
        "LIVRARIASARAIVA",
    ],
}

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONTROLE DE DUPLICATAS (evita re-postar a mesma oferta)
# ─────────────────────────────────────────────
ARQUIVO_HISTORICO = "ofertas_postadas.json"

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r") as f:
            return set(json.load(f))
    return set()

def salvar_historico(ids: set):
    with open(ARQUIVO_HISTORICO, "w") as f:
        json.dump(list(ids), f)

# ─────────────────────────────────────────────
#  RENOVAÇÃO AUTOMÁTICA DO TOKEN MELI
# ─────────────────────────────────────────────
_token_cache = {"token": ACCESS_TOKEN_MELI, "expira_em": 0}

def renovar_token():
    """Renova o Access Token do Mercado Livre automaticamente."""
    log.info("Renovando token do Mercado Livre...")
    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     CLIENT_ID_MELI,
        "client_secret": CLIENT_SECRET_MELI,
        "refresh_token": REFRESH_TOKEN_MELI,
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            dados = r.json()
            _token_cache["token"]     = dados["access_token"]
            _token_cache["expira_em"] = time.time() + dados.get("expires_in", 21600) - 300
            log.info("Token renovado com sucesso.")
        else:
            log.warning(f"Falha ao renovar token: {r.status_code} — {r.text}")
    except Exception as e:
        log.error(f"Erro na renovação do token: {e}")

def get_headers():
    """Retorna headers com token válido, renovando se necessário."""
    if time.time() >= _token_cache["expira_em"]:
        renovar_token()
    return {"Authorization": f"Bearer {_token_cache['token']}"}

# ─────────────────────────────────────────────
#  MERCADO LIVRE — busca de seller_id e ofertas
# ─────────────────────────────────────────────
def descobrir_seller_id(nickname: str) -> int | None:
    """Descobre o seller_id de uma loja pelo nickname."""
    url = f"https://api.mercadolibre.com/sites/MLB/search?nickname={nickname}&limit=1"
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code == 200:
            dados = r.json()
            seller = dados.get("seller")
            if seller:
                return seller["id"]
    except Exception as e:
        log.error(f"Erro buscando seller_id de {nickname}: {e}")
    return None

def buscar_ofertas_vendedor(seller_id: int, categoria: str, nome_marca: str) -> list[dict]:
    """Busca produtos em promoção de um vendedor específico."""
    url = (
        f"https://api.mercadolibre.com/sites/MLB/search"
        f"?seller_id={seller_id}&sort=price_asc&limit=50"
    )
    ofertas = []
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            log.warning(f"Erro {r.status_code} para seller {seller_id}")
            return []

        produtos = r.json().get("results", [])

        for item in produtos:
            preco_atual    = item.get("price")
            preco_original = item.get("original_price")

            if not preco_original or preco_atual >= preco_original:
                continue

            desconto = ((preco_original - preco_atual) / preco_original) * 100
            if desconto < DESCONTO_MINIMO:
                continue

            item_id = item.get("id")
            link    = item.get("permalink", "")

            # Monta link de afiliado
            link_afiliado = (
                f"https://www.mercadolivre.com.br/afiliados/redirect"
                f"?item_id={item_id}&affiliation_id={MEU_ID_AFILIADO}"
                if MEU_ID_AFILIADO != "SEU_ID_AFILIADO_AQUI"
                else link
            )

            thumbnail = item.get("thumbnail", "").replace("I.jpg", "O.jpg")

            ofertas.append({
                "id":             item_id,
                "titulo":         item.get("title", ""),
                "preco_atual":    preco_atual,
                "preco_original": preco_original,
                "desconto":       desconto,
                "link":           link_afiliado,
                "thumbnail":      thumbnail,
                "categoria":      categoria,
                "marca":          nome_marca,
            })

    except Exception as e:
        log.error(f"Erro ao buscar ofertas do seller {seller_id}: {e}")

    return ofertas

# ─────────────────────────────────────────────
#  TELEGRAM — envio de mensagens
# ─────────────────────────────────────────────
def formatar_mensagem(oferta: dict) -> str:
    return (
        f"{oferta['categoria']}\n\n"
        f"🛒 *{oferta['titulo']}*\n\n"
        f"❌ De: ~R$ {oferta['preco_original']:,.2f}~\n"
        f"✅ Por: *R$ {oferta['preco_atual']:,.2f}*\n"
        f"🔥 *{oferta['desconto']:.0f}% OFF!*\n\n"
        f"👉 [COMPRAR AGORA]({oferta['link']})"
    )

def enviar_telegram(oferta: dict) -> bool:
    """Envia oferta com foto para o canal do Telegram."""
    url_foto = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
    url_texto = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"

    mensagem = formatar_mensagem(oferta)

    # Tenta enviar com foto; se falhar, manda só texto
    if oferta.get("thumbnail"):
        payload = {
            "chat_id":    CHAT_ID_CANAL,
            "photo":      oferta["thumbnail"],
            "caption":    mensagem,
            "parse_mode": "Markdown",
        }
        r = requests.post(url_foto, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        log.warning("Foto falhou, enviando só texto...")

    payload = {
        "chat_id":                  CHAT_ID_CANAL,
        "text":                     mensagem,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": False,
    }
    r = requests.post(url_texto, json=payload, timeout=10)
    return r.status_code == 200

# ─────────────────────────────────────────────
#  LOOP PRINCIPAL
# ─────────────────────────────────────────────
def rodar_varredura(historico: set) -> set:
    """Faz uma varredura completa em todas as marcas e posta as novas ofertas."""
    total_postadas = 0

    for categoria, marcas in MARCAS_ALVO.items():
        for nickname in marcas:
            log.info(f"🔎 Buscando seller_id de {nickname}...")
            seller_id = descobrir_seller_id(nickname)

            if not seller_id:
                log.warning(f"  ⚠️  Loja não encontrada: {nickname}")
                time.sleep(1)
                continue

            log.info(f"  ✅ {nickname} → seller_id={seller_id}")
            ofertas = buscar_ofertas_vendedor(seller_id, categoria, nickname)
            log.info(f"  📦 {len(ofertas)} oferta(s) com ≥{DESCONTO_MINIMO}% de desconto")

            for oferta in ofertas:
                if oferta["id"] in historico:
                    continue  # Já postado antes, pula

                sucesso = enviar_telegram(oferta)
                if sucesso:
                    historico.add(oferta["id"])
                    total_postadas += 1
                    log.info(f"  📣 Postado: {oferta['titulo'][:60]}...")
                    time.sleep(4)  # Pausa entre posts

            time.sleep(2)  # Pausa entre marcas

    salvar_historico(historico)
    log.info(f"\n✅ Varredura concluída — {total_postadas} nova(s) oferta(s) postada(s).")
    return historico


def main():
    log.info("=" * 50)
    log.info("  BOT CAÇADOR DE OFERTAS — INICIANDO")
    log.info(f"  Canal: {CHAT_ID_CANAL}")
    log.info(f"  Desconto mínimo: {DESCONTO_MINIMO}%")
    log.info(f"  Intervalo: {INTERVALO_LOOP // 60} minutos")
    log.info("=" * 50)

    historico = carregar_historico()
    log.info(f"Histórico carregado: {len(historico)} item(s) já postado(s).\n")

    while True:
        try:
            log.info(f"\n🕐 [{datetime.now().strftime('%H:%M:%S')}] Iniciando nova varredura...")
            historico = rodar_varredura(historico)
        except Exception as e:
            log.error(f"Erro inesperado no loop principal: {e}")

        log.info(f"💤 Aguardando {INTERVALO_LOOP // 60} minutos até a próxima varredura...\n")
        time.sleep(INTERVALO_LOOP)


if __name__ == "__main__":
    main()
