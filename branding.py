"""Branding / white-label — carrega a configuracao de marca do Supabase,
mantem um cache curto em memoria e processa (comprime) as imagens enviadas
pela tela de admin antes de subir para o Storage.

Tabela `branding` (1 linha, id=1) + bucket publico `branding` no Storage.
"""

import io
import os
import time
from datetime import datetime, timezone

from PIL import Image
from supabase import create_client

_sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

BUCKET = "branding"
CACHE_TTL = 30           # segundos
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Limites de processamento por tipo de imagem (lado maior, em px)
_IMG_RULES = {
    "logo":   {"max": 512,  "fmt": "WEBP", "quality": 82, "ext": "webp", "mime": "image/webp"},
    "banner": {"max": 1600, "fmt": "WEBP", "quality": 80, "ext": "webp", "mime": "image/webp"},
    "favicon": {"max": 180, "fmt": "PNG",  "quality": None, "ext": "png", "mime": "image/png"},
}

# Valores atuais dos templates — usados como fallback quando o campo esta vazio.
DEFAULTS = {
    "site_title": "Educon FGV — Dashboard",
    "brand_name": "Educon FGV — Dashboard",
    "login_subtitle": "Painel de Atendimentos — Agente IA",
    "tab_labels": {
        "dashboard": "Dashboard",
        "atendimentos": "Atendimentos",
        "agentes": "Criador de Agentes",
    },
    "pages": {
        "dashboard.title": "Dashboard",
        "dashboard.subtitle": "Visão geral dos atendimentos do agente IA SDR",
        "atendimentos.title": "Atendimentos",
        "atendimentos.subtitle": "Clique em um lead para visualizar a conversa com o agente IA",
        "agentes.title": "Criador de Agentes",
        "agentes.subtitle": "Configure agentes de IA para atendimento via WhatsApp — dados de demonstração",
    },
    "colors": {
        "blue": "#0071e3",
        "green": "#34c759",
        "red": "#ff3b30",
        "bg": "#07090f",
    },
}

_cache = {"data": None, "ts": 0.0}


# --------------------------------------------------------------------------- #
# Leitura / cache
# --------------------------------------------------------------------------- #
def _hex_to_rgb(value):
    v = str(value).lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _css_vars(colors):
    """Gera um bloco <style> que sobrescreve as variaveis CSS do design system."""
    out = [":root{"]
    for key, var in (("blue", "--blue"), ("green", "--green"), ("red", "--red")):
        hexv = colors.get(key)
        if not hexv:
            continue
        out.append(f"{var}:{hexv};")
        try:
            r, g, b = _hex_to_rgb(hexv)
            out.append(f"{var}-a:rgba({r},{g},{b},0.18);")
        except Exception:
            pass
    out.append("}")
    css = "".join(out)
    if colors.get("bg"):
        css += f"html,body{{background:{colors['bg']} !important;}}"
    return css


def _resolve(raw):
    raw = raw or {}
    b = {
        "site_title": raw.get("site_title") or DEFAULTS["site_title"],
        "brand_name": raw.get("brand_name") or DEFAULTS["brand_name"],
        "login_subtitle": raw.get("login_subtitle") or DEFAULTS["login_subtitle"],
        "tab_labels": {**DEFAULTS["tab_labels"], **(raw.get("tab_labels") or {})},
        # overrides (editor JSON avancado) tem prioridade sobre pages
        "pages": {
            **DEFAULTS["pages"],
            **(raw.get("pages") or {}),
            **(raw.get("overrides") or {}),
        },
        "colors": {**DEFAULTS["colors"], **(raw.get("colors") or {})},
        "favicon_url": raw.get("favicon_url") or None,
        "logo_url": raw.get("logo_url") or None,
        "banner_url": raw.get("banner_url") or None,
        "overrides": raw.get("overrides") or {},
        "updated_at": raw.get("updated_at"),
    }
    b["css_vars"] = _css_vars(b["colors"])
    return b


def get_branding(force=False):
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"] < CACHE_TTL):
        return _cache["data"]
    try:
        rows = _sb.table("branding").select("*").eq("id", 1).execute().data
        raw = rows[0] if rows else {}
    except Exception:
        # Falha de rede: devolve o ultimo valor bom, ou cai nos defaults.
        if _cache["data"]:
            return _cache["data"]
        raw = {}
    data = _resolve(raw)
    _cache["data"] = data
    _cache["ts"] = now
    return data


def invalidate_cache():
    _cache["data"] = None
    _cache["ts"] = 0.0


# --------------------------------------------------------------------------- #
# Upload de imagens (com compressao)
# --------------------------------------------------------------------------- #
def _is_svg(data, filename):
    if filename and filename.lower().endswith(".svg"):
        return True
    head = data[:400].lstrip().lower()
    return head.startswith(b"<?xml") or head.startswith(b"<svg")


def process_image(data, kind, filename=""):
    """Valida e comprime a imagem. Retorna (bytes, ext, mime).

    kind: 'logo' | 'banner' | 'favicon'
    Levanta ValueError com mensagem amigavel se algo estiver errado.
    """
    if kind not in _IMG_RULES:
        raise ValueError(f"Tipo de imagem desconhecido: {kind}")
    if not data:
        raise ValueError("Arquivo vazio.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Arquivo muito grande ({len(data) // 1024} KB). Limite: "
            f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB."
        )

    rule = _IMG_RULES[kind]

    # SVG (so favicon/logo): sobe como esta, apenas com limite de tamanho.
    if _is_svg(data, filename):
        if len(data) > 512 * 1024:
            raise ValueError("SVG acima de 512 KB. Otimize o arquivo antes.")
        return data, "svg", "image/svg+xml"

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()                       # valida integridade
        img = Image.open(io.BytesIO(data))  # reabre (verify inutiliza o obj)
    except Exception:
        raise ValueError("Arquivo nao e uma imagem valida.")

    # normaliza modo de cor
    if rule["fmt"] == "PNG":
        img = img.convert("RGBA")
    else:
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    # redimensiona mantendo proporcao se exceder o lado maximo
    img.thumbnail((rule["max"], rule["max"]), Image.LANCZOS)

    # favicon: centraliza num quadrado (padding transparente) para nao distorcer
    if kind == "favicon":
        side = max(img.size)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        img = canvas

    buf = io.BytesIO()
    save_kwargs = {"format": rule["fmt"]}
    if rule["quality"] is not None:
        save_kwargs.update(quality=rule["quality"], method=6)
    else:
        save_kwargs.update(optimize=True)
    img.save(buf, **save_kwargs)
    return buf.getvalue(), rule["ext"], rule["mime"]


def upload_asset(data, kind, filename=""):
    """Processa e envia a imagem para o Storage. Retorna a URL publica
    (com cache-buster). `kind` vira o nome do arquivo no bucket."""
    payload, ext, mime = process_image(data, kind, filename)
    path = f"{kind}.{ext}"
    _sb.storage.from_(BUCKET).upload(
        path,
        payload,
        {"content-type": mime, "upsert": "true", "cache-control": "3600"},
    )
    url = _sb.storage.from_(BUCKET).get_public_url(path).split("?")[0]
    return f"{url}?v={int(time.time())}"


def save_branding(update):
    """Persiste as mudancas na linha id=1 e invalida o cache.

    Escreve exatamente as chaves recebidas. Campo escalar com valor None
    volta a NULL (ou seja, passa a usar o default do template)."""
    update = dict(update)
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    _sb.table("branding").update(update).eq("id", 1).execute()
    invalidate_cache()
