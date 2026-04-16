"""Génère la description SEO au format Le Petit Lunetier à partir des attributs."""
import os
from anthropic import Anthropic

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


TEMPLATE_REFERENCE = """La Dolores Écaille et sa forme Ovale convient aux visages ovales ou ronds, ou carrés pour casser avec la forme de visage. C'est un modèle qui conviendra plutôt aux femmes. Avec son style Miu-miu tendance la Dolores Écaille est équipée de verres solaires de catégorie 3 (100% anti-UV). La Dolores s'accorde avec toutes nos chaînes de lunettes et tient dans tous nos étuis à lunettes. Les verres peuvent être adaptés à ta vue. Pour cela, choisis les options de verres de vue que tu veux lors de l'ajout au panier. En fonction des options choisies, la couleur des verres solaires de vue peut varier : clique sur "Détails du modèle" pour en savoir plus. Il te suffira de nous envoyer ton ordonnance ou ta correction par mail une fois la commande validée. Opticiens de métier, nous vérifions minutieusement chaque produit avant l'envoi : les branches sont serrées, les verres nettoyés et les plaquettes ajustées dans notre atelier optique à Paris. Un étui à lunettes et une chiffonnette microfibre sont fournis pour chaque paire de lunettes achetée. Nous designons et fabriquons nous-même toutes nos lunettes et accessoires, pour te garantir une qualité supérieure au meilleur prix. Tous nos produits sont testés et homologués par la Norme EN ISO 12312-1-2013."""


PROMPT = """Tu rédiges une description SEO pour une fiche produit de lunettes sur lepetitlunetier.com.

Règles STRICTES :
- Tu respectes EXACTEMENT la structure et le ton du modèle de référence ci-dessous.
- Le bloc à partir de "Les verres peuvent être adaptés..." jusqu'à la fin (garanties, étui, norme EN ISO) DOIT rester IDENTIQUE au modèle.
- Tu adaptes uniquement les 3 premières phrases selon les attributs du produit.
- Pour un modèle OPTIQUE (non solaire), remplace la phrase sur les verres cat.3 par : "équipée de verres optiques transparents" et adapte le reste.
- Tutoiement systématique.
- Pas de markdown, pas de titres, pas de listes. Texte brut en un seul paragraphe.
- N'invente pas d'informations absentes des attributs.

Modèle de référence (Dolores Écaille) :
{template}

Produit à décrire :
- Nom : {name}
- Attributs visuels : {attrs}

Rédige la description maintenant."""


def generate_description(product_name: str, attrs: dict) -> str:
    msg = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=900,
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    template=TEMPLATE_REFERENCE,
                    name=product_name,
                    attrs=attrs,
                ),
            }
        ],
    )
    return msg.content[0].text.strip()
