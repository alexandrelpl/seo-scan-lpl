"""
Script one-shot pour capturer le token OAuth Shopify.
Gère le flow complet en 2 étapes :
  1. GET /        → redirige vers la page d'autorisation Shopify
  2. GET /callback → échange le code contre le token et l'écrit dans .env
Usage: python get_token.py
"""
import os
import secrets
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("SHOPIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SHOP          = "test-store20.myshopify.com"
SCOPES        = "read_products,write_products"
PORT          = 3333
REDIRECT_URI  = f"http://localhost:{PORT}/callback"
ENV_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

captured_token = [None]
_state = secrets.token_hex(16)


def exchange_code_for_token(code: str) -> str | None:
    r = requests.post(
        f"https://{SHOP}/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("access_token")


def write_token_to_env(token: str):
    lines = []
    found = False
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                if line.startswith("SHOPIFY_ACCESS_TOKEN="):
                    lines.append(f"SHOPIFY_ACCESS_TOKEN={token}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"SHOPIFY_ACCESS_TOKEN={token}\n")
    with open(ENV_FILE, "w") as f:
        f.writelines(lines)
    print(f"\n  Token ecrit dans .env : {token[:14]}...")


class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # --- Etape 1 : Shopify redirige vers application_url ---
        if parsed.path == "/":
            shop = params.get("shop", [SHOP])[0]
            auth_params = urlencode({
                "client_id": CLIENT_ID,
                "scope": SCOPES,
                "redirect_uri": REDIRECT_URI,
                "state": _state,
            })
            auth_url = f"https://{shop}/admin/oauth/authorize?{auth_params}"
            print(f"  Etape 1 : redirection vers OAuth Shopify...")
            self.send_response(302)
            self.send_header("Location", auth_url)
            self.end_headers()

        # --- Etape 2 : Shopify renvoie le code ici ---
        elif parsed.path == "/callback":
            code = params.get("code", [None])[0]
            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Erreur : pas de code dans le callback.")
                return

            print("  Etape 2 : code recu, echange contre un token...")
            try:
                token = exchange_code_for_token(code)
            except Exception as e:
                print(f"  Erreur echange : {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Erreur lors de l'echange du code.")
                return

            if token:
                captured_token[0] = token
                write_token_to_env(token)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    b"<h2>Token capture avec succes !</h2>"
                    b"<p>Ferme cet onglet et retourne dans ton terminal.</p>"
                )
                print("\n  Token capture et sauvegarde dans .env")
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Token vide dans la reponse Shopify.")

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"""
+------------------------------------------------------+
|  Capture du token OAuth Shopify                      |
|  Serveur local sur http://localhost:{PORT}              |
|                                                      |
|  -> Va dans Dev Dashboard > Distribution             |
|  -> Copie et ouvre le lien d'installation            |
|  -> Accepte les permissions sur test-store20         |
|  -> Le token sera capture automatiquement            |
+------------------------------------------------------+
""")
    server = HTTPServer(("localhost", PORT), OAuthHandler)
    while not captured_token[0]:
        server.handle_request()
    server.server_close()
    print("\n  Termine. Lance maintenant : streamlit run app.py\n")
