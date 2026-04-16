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

FORMES DISPONIBLES — choisis UNE seule valeur parmi cette liste exacte, en te basant sur les standards optiques :
- Ronde : monture parfaitement circulaire ou quasi-circulaire, hauteur ≈ largeur
- Ovale : ellipse douce, plus large que haute, bords arrondis sans angles
- Rectangulaire : forme droite, nettement plus large que haute, angles nets ou légèrement arrondis
- Pantos : bas arrondi, haut plat ou légèrement droit (forme en "D" inversé), style vintage
- Papillon : monture évasée vers le haut et l'extérieur (cat-eye), coins supérieurs relevés
- Aviateur : forme goutte d'eau, plus grande en bas qu'en haut, style pilote
- Hexagonale : six côtés géométriques visibles
- Masque : verre bouclier unique couvrant les deux yeux, style sport/shield
- Oversize : monture extrêmement grande dépassant largement le visage (nettement plus grande que la norme)
- Large : monture généreuse, sensiblement plus large que la moyenne sans être oversize

RÈGLE couleur : n'utilise JAMAIS le mot "Havane". Utilise "Écaille" ou "Écaille Havane" selon la nuance.

Retourne UNIQUEMENT un JSON valide avec ces clés (pas de markdown, pas d'explication) :
{
  "forme": "une valeur parmi : Ronde | Ovale | Rectangulaire | Pantos | Papillon | Aviateur | Hexagonale | Masque | Oversize | Large",
  "couleur_motif": "ex: Écaille, Écaille Havane, noir mat, transparent cristal, métal doré, bicolore noir/or",
  "matiere_apparente": "acétate | métal | mixte acétate-métal | autre",
  "type_verres": "solaire | optique",
  "teinte_verres": "description si solaire (ex: dégradé brun, miroité bleu, fumé), sinon null",
  "genre_cible": "femme | homme | mixte",
  "style": "2-4 mots, ex: tendance Miu-miu, rétro 70s, minimaliste, streetwear, classique intemporel",
  "visages_adaptes": "liste des formes de visage qui conviennent, ex: ovale, rond, carré",
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
