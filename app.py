"""Interface Streamlit — scan, génération, validation bulk, push Shopify."""
import os
import json
import time
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import pandas as pd

from shopify_client import fetch_all_products, update_product_description, update_product_full, update_product_forme, product_public_url
from vision import analyze_image, pick_packshot
from seo_generator import generate_description

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"


# ---------- Persistance simple sur disque ----------
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"products": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ---------- UI ----------
st.set_page_config(page_title="SEO Scan - Le Petit Lunetier", layout="wide")
st.title("SEO Scan — Le Petit Lunetier")

state = load_state()

with st.sidebar:
    st.header("Étapes")
    if st.button("1. Charger les produits Shopify", use_container_width=True):
        with st.spinner("Récupération des produits…"):
            products = fetch_all_products()
            for p in products:
                pid = str(p["id"])
                if pid not in state["products"]:
                    state["products"][pid] = {
                        "id": p["id"],
                        "title": p["title"],
                        "handle": p["handle"],
                        "product_type": p.get("product_type", ""),
                        "current_html": p.get("body_html") or "",
                        "image_url": pick_packshot(p.get("images", [])),
                        "attrs": None,
                        "forme": "",
                        "generated": None,
                        "edited": None,
                        "meta_title": None,
                        "meta_description": None,
                        "status": "pending",
                    }
            save_state(state)
        st.success(f"{len(products)} produits chargés.")

    filter_status = st.selectbox(
        "Filtrer par statut",
        ["tous", "pending", "generated", "validated", "pushed", "skipped"],
    )

    filter_no_desc = st.checkbox(
        "Sans description uniquement",
        value=False,
        help="Affiche uniquement les produits dont la description Shopify actuelle est vide",
    )

    filter_no_forme = st.checkbox(
        "Sans filtre forme uniquement",
        value=False,
        help="Affiche uniquement les produits dont le champ 'Filtre forme' est vide dans l'état local",
    )

    # Compteur rapide
    if state["products"]:
        n_no_desc = sum(1 for p in state["products"].values() if not p.get("current_html", "").strip())
        st.caption(f"Sans description : **{n_no_desc}** / {len(state['products'])}")

    st.divider()
    st.caption(f"API key : {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    st.caption(f"Shopify : {'✅' if os.getenv('SHOPIFY_ACCESS_TOKEN') else '❌'}")


if not state["products"]:
    st.info("Clique sur **Charger les produits Shopify** dans la barre latérale pour démarrer.")
    st.stop()

# ---------- Tableau récap ----------
FORMES_VALIDES = ["Ronde", "Ovale", "Rectangulaire", "Pantos", "Papillon",
                  "Aviateur", "Hexagonale", "Masque", "Oversize", "Large"]


def product_matches_filters(p: dict) -> bool:
    if filter_status != "tous" and p["status"] != filter_status:
        return False
    if filter_no_desc and p.get("current_html", "").strip():
        return False
    if filter_no_forme and p.get("forme", "").strip():
        return False
    return True

rows = []
for pid, p in state["products"].items():
    if not product_matches_filters(p):
        continue
    rows.append({
        "ID": pid,
        "Produit": p["title"],
        "Statut": p["status"],
        "Description actuelle": "❌ vide" if not p.get("current_html", "").strip() else "✅ remplie",
        "A une image": "✅" if p["image_url"] else "❌",
    })

st.subheader(f"Produits ({len(rows)})")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Fonction worker (thread-safe) ────────────────────────────────────────────
def _process_one(pid: str, p: dict) -> tuple:
    """Analyse image + génère description. Exécuté en parallèle."""
    try:
        attrs = analyze_image(p["image_url"])
        result = generate_description(p["title"], attrs, p.get("product_type", ""))
        return pid, {
            "attrs": attrs,
            "generated": result["description_html"],
            "edited": result["description_html"],
            "meta_title": result["meta_title"],
            "meta_description": result["meta_description"],
            "forme": attrs.get("forme", "") if not p.get("forme") else p["forme"],
            "status": "generated",
            "error": None,
        }
    except Exception as e:
        return pid, {"error": str(e), "status": "pending"}


# ---------- Actions bulk ----------
MAX_WORKERS = 5  # requêtes Claude en parallèle

st.markdown("### Actions bulk")
col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    if st.button("🔍 Analyser + générer (pending)", use_container_width=True):
        pending = [
            pid for pid, p in state["products"].items()
            if p["status"] == "pending"
            and p["image_url"]
            and (not filter_no_desc or not p.get("current_html", "").strip())
            and (not filter_no_forme or not p.get("forme", "").strip())
        ]
        if not pending:
            st.info("Aucun produit pending à traiter.")
        else:
            progress = st.progress(0.0)
            status_txt = st.empty()
            errors = []
            done = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futures = {ex.submit(_process_one, pid, state["products"][pid]): pid
                           for pid in pending}
                for future in as_completed(futures):
                    pid, res = future.result()
                    done += 1
                    if res.get("error"):
                        errors.append(f"{state['products'][pid]['title']} : {res['error']}")
                    else:
                        state["products"][pid].update(
                            {k: v for k, v in res.items() if k != "error"}
                        )
                    save_state(state)
                    progress.progress(done / len(pending))
                    status_txt.caption(f"{done}/{len(pending)} traités…")
            if errors:
                st.warning("Erreurs : " + " | ".join(errors))
            st.success(f"✅ {done - len(errors)}/{len(pending)} générés.")
            st.rerun()

with col_b:
    n_validated = sum(1 for p in state["products"].values() if p["status"] == "validated")
    if st.button(f"📤 Push descriptions + SEO ({n_validated} validés)", use_container_width=True):
        to_push = [pid for pid, p in state["products"].items() if p["status"] == "validated"]
        progress = st.progress(0.0)
        errors = []
        for i, pid in enumerate(to_push):
            p = state["products"][pid]
            try:
                update_product_full(p["id"], p["edited"],
                                    p.get("meta_title") or "",
                                    p.get("meta_description") or "")
                p["status"] = "pushed"
            except Exception as e:
                errors.append(f"{p['title']} : {e}")
            save_state(state)
            progress.progress((i + 1) / max(len(to_push), 1))
        if errors:
            st.warning("Erreurs : " + " | ".join(errors))
        st.success(f"✅ {len(to_push) - len(errors)} descriptions/SEO mis à jour.")
        st.rerun()

with col_c:
    n_avec_forme = sum(1 for p in state["products"].values() if p.get("forme"))
    if st.button(f"🔺 Push formes ({n_avec_forme} renseignées)", use_container_width=True):
        to_push_forme = [pid for pid, p in state["products"].items() if p.get("forme")]
        progress = st.progress(0.0)
        errors = []
        for i, pid in enumerate(to_push_forme):
            p = state["products"][pid]
            try:
                update_product_forme(p["id"], p["forme"])
            except Exception as e:
                errors.append(f"{p['title']} : {e}")
            progress.progress((i + 1) / max(len(to_push_forme), 1))
        if errors:
            st.warning("Erreurs : " + " | ".join(errors))
        st.success(f"✅ {len(to_push_forme) - len(errors)} formes mises à jour.")

with col_d:
    if st.button("🗑️ Réinitialiser l'état", use_container_width=True):
        state = {"products": {}}
        save_state(state)
        st.rerun()

st.divider()

# ---------- Pagination ----------
PAGE_SIZE = 20
visible_all = [(pid, p) for pid, p in state["products"].items() if product_matches_filters(p)]
n_pages = max(1, (len(visible_all) + PAGE_SIZE - 1) // PAGE_SIZE)

if "page" not in st.session_state:
    st.session_state.page = 0
st.session_state.page = min(st.session_state.page, n_pages - 1)

pc1, pc2, pc3 = st.columns([1, 3, 1])
with pc1:
    if st.button("◀ Précédent") and st.session_state.page > 0:
        st.session_state.page -= 1
with pc2:
    st.caption(f"Page {st.session_state.page + 1} / {n_pages}  —  {len(visible_all)} produits filtrés")
with pc3:
    if st.button("Suivant ▶") and st.session_state.page < n_pages - 1:
        st.session_state.page += 1

start = st.session_state.page * PAGE_SIZE
visible = visible_all[start: start + PAGE_SIZE]

# ---------- Édition produit par produit ----------
for pid, p in visible:
    with st.expander(f"{p['title']} — [{p['status']}]"):
        c1, c2 = st.columns([1, 2])
        with c1:
            if p["image_url"]:
                st.image(p["image_url"], use_container_width=True)
            st.caption(f"[Voir la fiche]({product_public_url(p['handle'])})")
            if p["attrs"]:
                st.json(p["attrs"], expanded=False)

        with c2:
            tab_desc, tab_meta, tab_forme = st.tabs(["📝 Description HTML", "🔍 Meta SEO", "🔺 Filtre Forme"])

            with tab_desc:
                st.markdown("**Actuelle sur Shopify :**")
                st.text_area("current", p["current_html"], height=100, disabled=True,
                             key=f"cur_{pid}", label_visibility="collapsed")
                st.markdown("**Générée (éditable) :**")
                edited = st.text_area(
                    "edited",
                    p.get("edited") or p.get("generated") or "",
                    height=280,
                    key=f"edit_{pid}",
                    label_visibility="collapsed",
                )

            with tab_meta:
                st.markdown("**Meta title** (50-60 car.)")
                meta_title = st.text_input(
                    "meta_title",
                    value=p.get("meta_title") or "",
                    key=f"mt_{pid}",
                    label_visibility="collapsed",
                )
                chars_title = len(meta_title)
                st.caption(f"{chars_title} car. {'✅' if 50 <= chars_title <= 60 else '⚠️ hors cible'}")

                st.markdown("**Meta description** (140-160 car.)")
                meta_desc = st.text_area(
                    "meta_description",
                    value=p.get("meta_description") or "",
                    height=100,
                    key=f"md_{pid}",
                    label_visibility="collapsed",
                )
                chars_desc = len(meta_desc)
                st.caption(f"{chars_desc} car. {'✅' if 140 <= chars_desc <= 160 else '⚠️ hors cible'}")

            with tab_forme:
                st.markdown("**Forme détectée par le scan visuel :**")
                forme_idx = FORMES_VALIDES.index(p.get("forme")) if p.get("forme") in FORMES_VALIDES else 0
                forme_selectee = st.selectbox(
                    "forme",
                    options=FORMES_VALIDES,
                    index=forme_idx,
                    key=f"forme_{pid}",
                    label_visibility="collapsed",
                )
                st.caption("⚠️ Vérifie visuellement que la forme correspond avant de pousser.")
                if st.button("🔺 Push Forme uniquement", key=f"push_forme_{pid}"):
                    try:
                        update_product_forme(p["id"], forme_selectee)
                        p["forme"] = forme_selectee
                        save_state(state)
                        st.success(f"✅ Forme '{forme_selectee}' envoyée sur Shopify")
                    except Exception as e:
                        st.error(str(e))

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("🔄 Régénérer", key=f"regen_{pid}"):
                    with st.spinner("Analyse + génération…"):
                        try:
                            attrs = p["attrs"] or analyze_image(p["image_url"])
                            result = generate_description(p["title"], attrs, p.get("product_type", ""))
                            p["attrs"] = attrs
                            p["generated"] = result["description_html"]
                            p["edited"] = result["description_html"]
                            p["meta_title"] = result["meta_title"]
                            p["meta_description"] = result["meta_description"]
                            if not p.get("forme") and attrs.get("forme"):
                                p["forme"] = attrs["forme"]
                            p["status"] = "generated"
                            save_state(state)
                            st.rerun()
                        except Exception as e:
                            import traceback
                            p["status"] = "pending"
                            save_state(state)
                            st.error(f"Erreur : {e}")
                            st.code(traceback.format_exc())
            with b2:
                if st.button("💾 Enregistrer", key=f"save_{pid}"):
                    p["edited"] = edited
                    p["meta_title"] = meta_title
                    p["meta_description"] = meta_desc
                    save_state(state)
                    st.toast("Modifications enregistrées")
            with b3:
                if st.button("✔️ Valider", key=f"val_{pid}"):
                    p["edited"] = edited
                    p["meta_title"] = meta_title
                    p["meta_description"] = meta_desc
                    p["status"] = "validated"
                    save_state(state)
                    st.rerun()
            with b4:
                if st.button("🚀 Push Shopify", key=f"push_{pid}"):
                    try:
                        update_product_full(
                            p["id"],
                            edited,
                            meta_title,
                            meta_desc,
                        )
                        p["edited"] = edited
                        p["meta_title"] = meta_title
                        p["meta_description"] = meta_desc
                        p["status"] = "pushed"
                        save_state(state)
                        st.success("✅ Mis à jour sur Shopify")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
