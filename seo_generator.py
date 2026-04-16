"""
Génère description HTML + balises meta SEO au format Le Petit Lunetier.
Retourne un dict : { description_html, meta_title, meta_description }
Deux modèles : Solaires / Monture Optique
"""
import os
import json
from anthropic import Anthropic

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


# ── Modèle de référence Solaire ──────────────────────────────────────────────
TEMPLATE_SOLAIRE = """
<h2>Design Rétro 90s : L'Élégance de la Forme Ovale</h2>
<p>Le modèle <strong>Dahlia Écaille</strong> incarne l'esthétique minimaliste des années 90. Sa monture fine en acétate havane et sa silhouette ovale ont été conçues pour équilibrer les traits des visages carrés, rectangulaires ou ovales. Ce design mixte offre une allure vintage affirmée tout en restant discret.</p>
<h3>Protection Solaire Catégorie 3 et Confort Visuel</h3>
<p>Équipée de verres solaires de catégorie 3 (protection 100% anti-UV), cette paire assure une vision nette grâce à sa teinte brun uniforme. Les verres sont entièrement <strong>adaptables à la vue</strong> par nos opticiens partenaires. Il suffit de transmettre l'ordonnance après validation de la commande pour bénéficier d'un équipement personnalisé.</p>
<h3>Expertise Optique et Finitions Artisanales</h3>
<ul>
<li><strong>Atelier Parisien :</strong> Chaque paire est minutieusement vérifiée par des opticiens de métier (ajustement des plaquettes, serrage des branches).</li>
<li><strong>Qualité Certifiée :</strong> Monture en acétate haut de gamme, testée selon la Norme EN ISO 12312-1-2013.</li>
<li><strong>Accessoires Inclus :</strong> Livraison avec un <a href="/collections/etuis">étui de protection</a> et une microfibre de nettoyage.</li>
</ul>

Meta title : Lunettes de Soleil Ovales Rétro 90s - Dahlia Écaille | Protection UV400
Meta description : Découvrez la Dahlia Écaille, monture solaire ovale au style vintage 90s. Verres catégorie 3 adaptables à la vue. Qualité optique vérifiée en atelier à Paris.
"""

# ── Modèle de référence Monture Optique ──────────────────────────────────────
TEMPLATE_OPTIQUE = """
<h2>Silhouette Carrée et Design Féminin</h2>
<p>La monture <strong>Annie.J Écaille</strong> se distingue par sa forme carrée audacieuse, idéale pour structurer les visages ovales ou apporter du caractère aux visages ronds. Son coloris écaille intemporel s'adapte à tous les styles, du plus classique au plus contemporain.</p>
<h3>Protection Anti-Lumière Bleue et Matériaux Sains</h3>
<p>Ce modèle est équipé par défaut de <strong>verres anti-lumière bleue sans correction</strong>, essentiels pour protéger les yeux de la fatigue liée aux écrans. La structure métallique est rigoureusement garantie sans nickel ni plomb, assurant un port confortable et hypoallergénique au quotidien.</p>
<h3>Service Optique Sur-Mesure</h3>
<p>Les verres de la Annie.J sont totalement adaptables à la correction visuelle. Le choix des options de verres correcteurs s'effectue directement lors de l'ajout au panier. En tant qu'opticiens, nous assurons un montage précis dans notre atelier parisien, incluant le nettoyage et l'ajustage des branches avant chaque envoi.</p>
<ul>
<li><strong>Inclus :</strong> Étui à lunettes dédié et chiffonnette microfibre.</li>
<li><strong>Conformité :</strong> Produit homologué selon la Norme européenne EN ISO 12312-1-2013.</li>
<li><strong>Style :</strong> Compatible avec l'ensemble de nos <a href="/collections/chaines-lunettes">chaînes de lunettes</a>.</li>
</ul>

Meta title : Lunettes Anti-Lumière Bleue Annie.J Écaille - Monture Carrée Femme
Meta description : Protégez vos yeux avec style grâce à la Annie.J Écaille. Monture carrée en métal sans nickel avec verres anti-lumière bleue. Adaptable à la vue en atelier.
"""

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT_SOLAIRE = """Tu rédiges le contenu SEO d'une fiche produit pour lepetitlunetier.com — type : Lunettes Solaires.

RÈGLES STRICTES :
- Respecte EXACTEMENT la structure HTML du modèle (h2, h3, p, ul/li, strong, a).
- Les liens <a href="/collections/etuis"> et <a href="/collections/chaines-lunettes"> doivent apparaître.
- La section h3 "Expertise Optique..." et son ul/li restent quasi identiques au modèle.
- Adapte uniquement le h2, le premier paragraphe (p), et la teinte des verres.
- Le h2 doit être accrocheur et SEO (style/époque/forme en mots-clés).
- Tutoiement INTERDIT dans la description HTML (texte institutionnel).
- Retourne UNIQUEMENT un JSON valide, sans markdown ni explication :
{{
  "description_html": "...",
  "meta_title": "...",
  "meta_description": "..."
}}

Contraintes meta :
- meta_title : 50-60 caractères, format "Lunettes [type] [forme] [style] - [Nom] | [bénéfice]"
- meta_description : 140-160 caractères, inclut le nom du modèle, la forme, un bénéfice clé.

Modèle de référence (Dahlia Écaille) :
{template}

Produit à décrire :
- Nom : {name}
- Attributs visuels : {attrs}
"""

PROMPT_OPTIQUE = """Tu rédiges le contenu SEO d'une fiche produit pour lepetitlunetier.com — type : Monture Optique.

RÈGLES STRICTES :
- Respecte EXACTEMENT la structure HTML du modèle (h2, h3, p, ul/li, strong, a).
- Le lien <a href="/collections/chaines-lunettes"> doit apparaître.
- La section h3 "Service Optique Sur-Mesure" et son ul/li restent quasi identiques au modèle.
- Adapte le h2, le premier paragraphe, et la section anti-lumière bleue selon les attributs.
- Le h2 doit être accrocheur et SEO (forme/style/matière en mots-clés).
- Tutoiement INTERDIT dans la description HTML.
- Retourne UNIQUEMENT un JSON valide, sans markdown ni explication :
{{
  "description_html": "...",
  "meta_title": "...",
  "meta_description": "..."
}}

Contraintes meta :
- meta_title : 50-60 caractères, format "Lunettes [style] [Nom] - Monture [forme] [genre]"
- meta_description : 140-160 caractères, inclut le nom, la forme, le bénéfice principal.

Modèle de référence (Annie.J Écaille) :
{template}

Produit à décrire :
- Nom : {name}
- Attributs visuels : {attrs}
"""


def generate_description(product_name: str, attrs: dict, product_type: str = "Solaires") -> dict:
    """
    Génère description HTML + meta SEO.
    Retourne : { "description_html": str, "meta_title": str, "meta_description": str }
    """
    is_optique = "optique" in product_type.lower()
    prompt = (PROMPT_OPTIQUE if is_optique else PROMPT_SOLAIRE).format(
        template=TEMPLATE_OPTIQUE if is_optique else TEMPLATE_SOLAIRE,
        name=product_name,
        attrs=json.dumps(attrs, ensure_ascii=False),
    )

    msg = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    # Nettoie les fences markdown éventuelles
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()

    result = json.loads(text)

    # Garantit les 3 clés
    return {
        "description_html": result.get("description_html", ""),
        "meta_title": result.get("meta_title", ""),
        "meta_description": result.get("meta_description", ""),
    }
