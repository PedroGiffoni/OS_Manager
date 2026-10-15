"""Generate the Vercel proxy using the real backend URL; no secrets are written."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


def configuration(backend_url):
    origin = backend_url.rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "*" in origin
        or origin != origin.strip()
        or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Informe somente a origem HTTPS pública do backend, sem /api.")
    return {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "framework": "vite",
        "buildCommand": "npm run build",
        "outputDirectory": "dist",
        "headers": [
            {
                "source": "/api/:path*",
                "headers": [
                    {"key": "Cache-Control", "value": "no-store"},
                    {"key": "x-vercel-enable-rewrite-caching", "value": "0"},
                ],
            }
        ],
        "rewrites": [
            {"source": "/api/:path*", "destination": origin + "/api/:path*"},
            {"source": "/((?!api(?:/|$)).*)", "destination": "/index.html"},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "frontend" / "vercel.json",
    )
    args = parser.parse_args()
    try:
        result = configuration(args.backend_url)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Configuração Vercel gravada em " + str(args.output))


if __name__ == "__main__":
    main()
