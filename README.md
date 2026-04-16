# SEO Scan — Le Petit Lunetier

App locale (puis déployable gratuitement) qui :
1. Récupère tous les produits de la boutique Shopify `lepetitlunetier`
2. Analyse le packshot de chaque paire (forme, couleur, style, type…) via Claude Vision
3. Génère une description SEO au format Le Petit Lunetier
4. Permet de valider / éditer / régénérer en bulk
5. Pousse les descriptions validées directement sur les fiches Shopify

---

## PHASE 1 — Créer la custom app Shopify

1. Connecte-toi à ton admin Shopify → **Settings** → **Apps and sales channels** → **Develop apps**.
2. Si c'est ta première fois : clique **Allow custom app development** puis confirme.
3. Clique **Create an app**, nomme-la `SEO Scan` (toi comme développeur).
4. Onglet **Configuration** → **Admin API integration** → **Configure**.
5. Coche ces scopes et rien d'autre :
   - `read_products`
   - `write_products`
6. Sauvegarde, puis onglet **API credentials** → **Install app**.
7. Copie l'**Admin API access token** (commence par `shpat_…`). Il ne s'affichera qu'une fois — garde-le.

---

## PHASE 2 — Récupérer une clé API Anthropic

1. Va sur https://console.anthropic.com → crée un compte / connecte-toi.
2. **Settings** → **API Keys** → **Create Key**.
3. Crédite ton compte (~10 € suffisent largement pour 250 produits).
4. Copie la clé (`sk-ant-…`).

---

## PHASE 3 — Installer l'environnement sur ton Mac M1

Ouvre Terminal.app et copie-colle ces commandes une par une.

```bash
# 1. Installer Homebrew (si pas déjà fait)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Installer Python 3.11
brew install python@3.11

# 3. Aller dans le dossier du projet
cd "~/Documents/…/SCAN VISUEL SEO"   # adapte au chemin réel

# 4. Créer un environnement virtuel Python
python3.11 -m venv venv

# 5. L'activer
source venv/bin/activate

# 6. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

Tu dois voir `(venv)` en début de ligne dans ton terminal une fois activé.

---

## PHASE 4 — Configurer les clés

1. Duplique `.env.example` et renomme la copie `.env` :
   ```bash
   cp .env.example .env
   ```
2. Ouvre `.env` dans un éditeur (VSCode, TextEdit) et remplis :
   - `SHOPIFY_SHOP=lepetitlunetier` (le handle `.myshopify.com`)
   - `SHOPIFY_ACCESS_TOKEN=shpat_xxx…`
   - `ANTHROPIC_API_KEY=sk-ant-xxx…`

Le fichier `.env` ne sera JAMAIS commité (cf `.gitignore`). C'est ton coffre-fort local.

---

## PHASE 5 — Lancer l'app localement

```bash
source venv/bin/activate    # si pas déjà fait
streamlit run app.py
```

Ton navigateur ouvre `http://localhost:8501`. L'interface contient :
- Barre latérale : bouton **Charger les produits Shopify** (à cliquer en premier), filtres de statut.
- Bouton **🔍 Analyser + générer pour TOUS les 'pending'** : lance l'analyse visuelle + génération SEO en chaîne.
- Bouton **✅ Pousser vers Shopify tous les 'validated'** : push bulk.
- Section détaillée par produit : image, description actuelle, description générée éditable, boutons Régénérer / Enregistrer / Valider / Push.

**Workflow conseillé**
1. Charger les produits → tu auras 150-250 lignes.
2. Lancer l'analyse en bulk (laisse tourner 10-20 min, ~2-5 €).
3. Parcourir produit par produit : relire, éditer si besoin, cliquer **Valider**.
4. Une fois tout validé : **Push bulk**.

L'état est sauvegardé dans `data/state.json` — tu peux fermer l'app et reprendre où tu en étais.

---

## PHASE 6 — Déployer sur Streamlit Cloud (multi-postes, gratuit)

Pour y accéder depuis n'importe quel poste :

1. Crée un compte GitHub si tu n'en as pas.
2. Crée un repo **privé** nommé `seo-scan-lpl`.
3. Dans le terminal :
   ```bash
   cd "SCAN VISUEL SEO"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TON_USER/seo-scan-lpl.git
   git branch -M main
   git push -u origin main
   ```
4. Va sur https://share.streamlit.io → **New app** → sélectionne ton repo, branche `main`, fichier `app.py`.
5. Dans **Advanced settings** → **Secrets**, colle :
   ```toml
   SHOPIFY_SHOP = "lepetitlunetier"
   SHOPIFY_ACCESS_TOKEN = "shpat_xxx"
   ANTHROPIC_API_KEY = "sk-ant-xxx"
   ```
6. Deploy. Tu obtiens une URL `https://xxx.streamlit.app` protégée par ton login Streamlit.

Pour protéger l'accès : dans **Settings → Sharing**, passe en **Private** et invite les emails autorisés.

---

## Coût estimé

- Analyse image (Claude Sonnet 4.5, ~1 image + prompt) : ~0,006 €/produit
- Génération texte (prompt + ~500 tokens sortie) : ~0,004 €/produit
- Total : ~0,01 €/produit → **~2,5 € pour 250 produits** en passe complète.
- Les régénérations individuelles sont du même ordre.

---

## Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| `401 Unauthorized` Shopify | token invalide ou app pas installée | Vérifie `SHOPIFY_ACCESS_TOKEN`, réinstalle l'app |
| `403` sur update produit | scope `write_products` manquant | Édite la custom app, ajoute le scope, réinstalle |
| Images non chargées | URL Shopify signée expirée | Relance **Charger les produits Shopify** |
| JSON parse error dans vision.py | Claude a renvoyé un texte non-JSON | Bouton **Régénérer** sur le produit |
| Rate limit Anthropic | Trop de requêtes/minute | Le `time.sleep(0.2)` suffit en général, sinon augmente-le |

---

## Structure du projet

```
SCAN VISUEL SEO/
├── app.py                # UI Streamlit
├── shopify_client.py     # Fetch + update Shopify
├── vision.py             # Analyse image via Claude Vision
├── seo_generator.py      # Génération description au format LPL
├── requirements.txt      # Dépendances Python
├── .env.example          # Modèle de config
├── .env                  # Tes clés (NON commité)
├── .gitignore
└── data/
    └── state.json        # Etat persisté
```
