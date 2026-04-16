"""Client Shopify Admin API — fetch produits + update body_html."""
import os
import requests
from typing import List, Dict, Optional

API_VERSION = "2024-10"


def _base_url() -> str:
    shop = os.environ["SHOPIFY_SHOP"]
    return f"https://{shop}.myshopify.com/admin/api/{API_VERSION}"


def _headers() -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": os.environ["SHOPIFY_ACCESS_TOKEN"],
        "Content-Type": "application/json",
    }


PRODUCT_TYPES = ["Solaires", "Monture Optique"]


def _fetch_by_type(product_type: str) -> List[Dict]:
    """Récupère les produits d'un type donné (paginés)."""
    url = f"{_base_url()}/products.json"
    params = {
        "limit": 250,
        "product_type": product_type,
        "fields": "id,title,handle,body_html,product_type,tags,vendor,variants,images,status",
    }
    products: List[Dict] = []
    while url:
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        products.extend(r.json().get("products", []))
        link = r.headers.get("Link", "")
        next_url: Optional[str] = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
        url = next_url
        params = None
    return products


def fetch_all_products() -> List[Dict]:
    """Récupère tous les produits Solaires + Monture Optique."""
    products: List[Dict] = []
    seen_ids: set = set()
    for ptype in PRODUCT_TYPES:
        for p in _fetch_by_type(ptype):
            if p["id"] not in seen_ids:
                products.append(p)
                seen_ids.add(p["id"])
    return products


def update_product_description(product_id: int, new_html: str) -> Dict:
    """Met à jour uniquement la description (body_html) via REST — fallback."""
    url = f"{_base_url()}/products/{product_id}.json"
    payload = {"product": {"id": product_id, "body_html": new_html}}
    r = requests.put(url, headers=_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["product"]


def update_product_full(
    product_id: int,
    description_html: str,
    meta_title: str,
    meta_description: str,
) -> Dict:
    """
    Met à jour description HTML + meta title + meta description
    en une seule requête GraphQL productUpdate.
    """
    shop = os.environ["SHOPIFY_SHOP"]
    url = f"https://{shop}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id title }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "id": f"gid://shopify/Product/{product_id}",
            "descriptionHtml": description_html,
            "metafields": [
                {
                    "namespace": "global",
                    "key": "title_tag",
                    "value": meta_title,
                    "type": "single_line_text_field",
                },
                {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": meta_description,
                    "type": "single_line_text_field",
                },
            ],
        }
    }

    r = requests.post(
        url,
        headers=_headers(),
        json={"query": mutation, "variables": variables},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    user_errors = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if user_errors:
        raise ValueError(f"Shopify GraphQL errors: {user_errors}")

    return data


def product_public_url(handle: str) -> str:
    # Domaine public (pas le myshopify) — adapte si tu changes de domaine
    return f"https://lepetitlunetier.com/products/{handle}"
