"""Finalize the GitHub App Manifest flow.

docs/install-app/ POSTs a manifest to github.com/settings/apps/new. After the
user clicks "Create GitHub App", GitHub redirects here with ``?code=<temp>``.
The temp code is single-use and has a 1-hour TTL; the App is only finalized
once we POST to ``/app-manifests/{code}/conversions``, which also returns the
private key (the entire point of the flow — keys can't be reissued later
without going to the App settings page).

https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest
"""

from __future__ import annotations

import json
from html import escape
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlparse

from workers import Response, WorkerEntrypoint, fetch


class Default(WorkerEntrypoint):
    async def fetch(self, request) -> Response:
        url = urlparse(request.url)
        if request.method != "GET" or url.path != "/callback":
            return Response("Not found", status=HTTPStatus.NOT_FOUND)

        params = parse_qs(url.query)
        codes = params.get("code")
        if not codes:
            return _error_page(
                "Missing `code` parameter",
                "This page is only reachable as the redirect target of the "
                "GitHub App manifest flow. Start over from the install-app page.",
                HTTPStatus.BAD_REQUEST,
            )

        try:
            app = await _convert_manifest(codes[0])
        except _ConversionError as err:
            return _error_page(
                "Couldn't finalize the App with GitHub",
                str(err),
                HTTPStatus.BAD_GATEWAY,
            )

        return _credentials_page(app)


class _ConversionError(Exception):
    pass


async def _convert_manifest(code: str) -> dict[str, Any]:
    resp = await fetch(
        f"https://api.github.com/app-manifests/{code}/conversions",
        method="POST",
        headers={
            "accept": "application/vnd.github+json",
            "user-agent": "scriv-release-install-app-callback",
            "x-github-api-version": "2022-11-28",
        },
    )
    if resp.status < 200 or resp.status >= 300:
        text = await resp.text()
        raise _ConversionError(
            f"GitHub returned {resp.status}.\n"
            f"The temporary code may have expired (1-hour TTL) or already been used.\n\n"
            f"{text}"
        )
    return await resp.json()


_RESPONSE_HEADERS = {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "no-store",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


def _html_response(html: str, status: int = 200) -> Response:
    return Response(html, status=status, headers=_RESPONSE_HEADERS)


def _error_page(title: str, detail: str, status: int) -> Response:
    body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)} — scriv-release App install</title>
    {_BASE_STYLES}
  </head>
  <body>
    <main>
      <h1>{escape(title)}</h1>
      <pre>{escape(detail)}</pre>
      <p>
        <a href="https://whitphx.github.io/scriv-release/install-app/">Start over</a>
        or
        <a href="https://github.com/whitphx/scriv-release/blob/main/docs/token-setup.md#manual-setup">create the App manually</a>.
      </p>
    </main>
  </body>
</html>"""
    return _html_response(body, status=status)


def _credentials_page(app: dict[str, Any]) -> Response:
    slug = str(app.get("slug", ""))
    app_id = str(app.get("id", ""))
    app_url = str(app.get("html_url", ""))
    pem = str(app.get("pem", ""))
    install_url = f"{app_url}/installations/new"

    pem_js = json.dumps(pem)
    slug_js = json.dumps(slug)

    body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>App created: {escape(slug)}</title>
    {_BASE_STYLES}
  </head>
  <body>
    <main>
      <h1>App created: <a href="{escape(app_url)}" target="_blank" rel="noopener">{escape(slug)}</a></h1>
      <p class="warn"><strong>This page shows the private key once.</strong> Copy or download it now — closing this tab loses it, and you'll need to generate a new key from the App's settings page.</p>

      <h2>1. Install the App on your repo</h2>
      <p>
        <a class="btn" href="{escape(install_url)}" target="_blank" rel="noopener">Install <code>{escape(slug)}</code></a>
      </p>
      <p>Pick the repository (or repositories) you want <code>scriv-release</code> to manage.</p>

      <h2>2. Set the variable and secret in your repo</h2>
      <p>In the target repo: <code>Settings → Secrets and variables → Actions</code>.</p>

      <h3>Repository variable: <code>RELEASE_APP_ID</code></h3>
      <div class="field">
        <input id="app-id" type="text" readonly value="{escape(app_id)}" />
        <button type="button" data-copy="app-id">Copy</button>
      </div>

      <h3>Repository secret: <code>RELEASE_APP_KEY</code></h3>
      <textarea id="pem" readonly rows="12">{escape(pem)}</textarea>
      <p>
        <button type="button" data-copy="pem">Copy</button>
        <button type="button" id="download-pem">Download <code>{escape(slug)}.pem</code></button>
      </p>

      <h2>3. Reference them in <code>.github/workflows/release.yml</code></h2>
      <pre><code>      - uses: whitphx/scriv-release@v0.3.0
        with:
          app-id: ${{{{ vars.RELEASE_APP_ID }}}}
          app-private-key: ${{{{ secrets.RELEASE_APP_KEY }}}}</code></pre>

      <p class="muted">App ID <code>{escape(app_id)}</code> · slug <code>{escape(slug)}</code></p>
    </main>

    <script>
      (() => {{
        const pem = {pem_js};
        const slug = {slug_js};

        document.querySelectorAll("[data-copy]").forEach((btn) => {{
          btn.addEventListener("click", async () => {{
            const target = document.getElementById(btn.dataset.copy);
            try {{
              await navigator.clipboard.writeText(target.value);
            }} catch {{
              target.focus();
              target.select();
              return;
            }}
            const original = btn.textContent;
            btn.textContent = "Copied";
            setTimeout(() => {{ btn.textContent = original; }}, 1500);
          }});
        }});

        document.getElementById("download-pem").addEventListener("click", () => {{
          const blob = new Blob([pem], {{ type: "application/x-pem-file" }});
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = slug + ".private-key.pem";
          a.click();
          URL.revokeObjectURL(url);
        }});
      }})();
    </script>
  </body>
</html>"""
    return _html_response(body)


_BASE_STYLES = """<style>
  :root { color-scheme: light dark; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    max-width: 42rem;
    margin: 2rem auto;
    padding: 0 1rem;
    line-height: 1.55;
  }
  h1 { margin-top: 0; }
  h2 { margin-top: 2rem; }
  h3 { margin: 1.25rem 0 0.5rem; }
  pre, textarea, input[type="text"] {
    background: color-mix(in srgb, currentColor 8%, transparent);
    border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
    padding: 0.5rem 0.75rem;
    border-radius: 0.4rem;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.9rem;
    box-sizing: border-box;
    color: inherit;
  }
  textarea { width: 100%; resize: vertical; }
  input[type="text"] { flex: 1; }
  pre { overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
  button, .btn {
    font-size: 0.95rem;
    padding: 0.45rem 0.95rem;
    border-radius: 0.4rem;
    border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
    background: color-mix(in srgb, currentColor 6%, transparent);
    color: inherit;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    font-family: inherit;
  }
  .btn:hover, button:hover:not(:disabled) {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
  .field { display: flex; gap: 0.5rem; align-items: stretch; }
  .warn {
    padding: 0.75rem 1rem;
    border-radius: 0.4rem;
    background: color-mix(in srgb, orange 25%, transparent);
    border: 1px solid color-mix(in srgb, orange 50%, transparent);
  }
  .muted { color: color-mix(in srgb, currentColor 60%, transparent); font-size: 0.9rem; }
  code {
    background: color-mix(in srgb, currentColor 12%, transparent);
    padding: 0.1em 0.3em;
    border-radius: 0.25em;
  }
  pre code { background: none; padding: 0; }
</style>"""
