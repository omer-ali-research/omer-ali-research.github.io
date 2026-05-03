#!/usr/bin/env python3
"""Build files/omer_cv.pdf from _data/profile.yml (website + CV single source)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "_data" / "profile.yml"
TEMPLATE_DIR = ROOT / "templates"
OUT_DIR = ROOT / "files"
CV_NAME = "omer_cv.pdf"
DEFAULT_SITE_BASE = "https://omer-ali-research.github.io"


def load_profile() -> dict:
    if not DATA_PATH.is_file():
        print(f"Missing {DATA_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(DATA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def effective_audience(item: dict, section: dict) -> str:
    return item.get("audience") or section.get("audience") or "both"


def absolutize_url(url: str | None, base: str) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = base.rstrip("/")
    path = url if url.startswith("/") else f"/{url}"
    return f"{base}{path}"


def sections_for_cv(profile: dict, site_base: str) -> list[dict]:
    """Sections and items visible on CV (exclude web-only; include cv-only)."""
    out: list[dict] = []
    for sec in profile.get("sections", []):
        sec_aud = sec.get("audience") or "both"
        if sec_aud == "web":
            continue

        items_out = []
        for item in sec.get("entries", []):
            ea = effective_audience(item, sec)
            if ea == "web":
                continue
            row = dict(item)
            if sec.get("kind") == "working_paper" and row.get("url"):
                row["url"] = absolutize_url(row["url"], site_base)
            items_out.append(row)

        # Skip empty sections unless you explicitly want empty headings (don't).
        if not items_out:
            continue

        sec_copy = {**sec, "entries": items_out}
        out.append(sec_copy)
    return out


def render_pdf(html: str, pdf_path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as e:
        print("Install deps: pip install -r scripts/requirements.txt", file=sys.stderr)
        raise e

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(ROOT.as_uri()) + "/").write_pdf(pdf_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CV PDF from _data/profile.yml")
    parser.add_argument(
        "--site-base",
        default=DEFAULT_SITE_BASE,
        help=f"Prefix for relative /files/ links (default: {DEFAULT_SITE_BASE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print HTML path only (skip PDF; needs weasyprint unless dry-run writes HTML)",
    )
    args = parser.parse_args()

    profile = load_profile()
    meta = profile.get("meta", {})

    updated = datetime.now(timezone.utc).strftime("%B %Y")
    sections = sections_for_cv(profile, args.site_base)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("cv_pdf.html.j2")
    html = tpl.render(
        meta=meta,
        sections=sections,
        updated_label=updated,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT_DIR / CV_NAME

    if args.dry_run:
        debug_html = OUT_DIR / "_cv_preview.html"
        debug_html.write_text(html, encoding="utf-8")
        print(f"Wrote {debug_html} (dry-run; PDF not built)")
        return

    render_pdf(html, pdf_path)
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
