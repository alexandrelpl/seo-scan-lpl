"""Analyse d'image packshot lunettes via Claude Vision."""
import os
import json
import base64
import requests
from anthropic import Anthropic

_client: Anthropic | None = None

# Choisis le packshot fond blanc le plus représentatif
# (on prend la première image par défaut, mais tu peux améliorer
# cette heuristique en regardant le nom de fichier / alt)
def pick_packshot(images: list[dict]) -> str | None:
    if not images:
        return None
    # Priorité : images dont alt ou src contient "packshot", "front", "white"
    for img in images:
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if any(k in src or k in alt for k in ("packshot", "front", "fond", "white")):
            return img["src"]
    return images[0]["src"]


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


ANALYSIS_PROMPT = """Tu analyses un packshot de lunettes sur fond blanc pour un opticien français.

Retourne UNIQUEMENT un JSON valide avec ces clés (pas de markdown, pas d'explication) :
{
  "forme": "ovale | ronde | carrée | rectangulaire | papillon | aviateur | hexagonale | pantos | autre",
  "couleur_motif": "description courte, ex: écaille brune, noir mat, transparent cristal, métal doré, bicolore noir/or",
  "matiere_apparente": "acétate | métal | mixte acétate-métal | autre",
  "type_verres": "solaire | optique",
  "teinte_verres": "description si solaire (ex: dégradé brun, miroité bleu, fumé), sinon null",
  "genre_cible": "femme | homme | mixte",
  "style": "2-4 mots, ex: tendance Miu-miu, rétro 70s, minimaliste, streetwear, classique intemporel, oversize",
  "visages_adaptes": "liste de formes de visage qui conviennent, ex: ovale, rond, carré",
  "details_notables": "1 phrase courte sur un détail visuel (ex: branches dorées fines, plaquettes métal, charnières apparentes)"
}"""


def analyze_image(image_url: str) -> dict:
    """Analyse le packshot et renvoie un dict d'attributs."""
    r = requests.get(image_url, timeout=30)
    r.raise_for_status()
    media_type = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
    if media_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        media_type = "image/jpeg"
    b64 = base64.standard_b64encode(r.content).decode("utf-8")

    msg = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": ANALYSIS_PROMPT},
                ],
            }
        ],
    )
    text = msg.content[0].text.strip()
    # Sécurité : strip fences éventuelles
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
