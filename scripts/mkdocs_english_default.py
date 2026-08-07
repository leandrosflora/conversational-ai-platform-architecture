"""Build-time adapter for English-first MkDocs publishing.

The repository keeps Portuguese source pages as ``*.md`` and English
translations as ``*.en.md``. mkdocs-static-i18n expects the unsuffixed files
to belong to the default locale, so making English the default directly would
make the Portuguese files collide with the English translations.

This hook copies ``docs/`` to a temporary directory and renames only the
unsuffixed Markdown files to ``*.pt.md`` there. The repository layout remains
unchanged while MkDocs sees explicit ``.pt.md`` and ``.en.md`` variants.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from mkdocs.plugins import event_priority

_SOURCE_DOCS_DIR: Path | None = None
_STAGE_ROOT: Path | None = None
_STAGE_DOCS_DIR: Path | None = None


def _prepare_stage() -> None:
    if _SOURCE_DOCS_DIR is None or _STAGE_DOCS_DIR is None:
        return

    if _STAGE_DOCS_DIR.exists():
        shutil.rmtree(_STAGE_DOCS_DIR)

    shutil.copytree(_SOURCE_DOCS_DIR, _STAGE_DOCS_DIR)

    for page in sorted(_STAGE_DOCS_DIR.rglob("*.md")):
        if page.name.endswith((".en.md", ".pt.md")):
            continue

        localized_page = page.with_name(f"{page.stem}.pt.md")
        if localized_page.exists():
            raise RuntimeError(
                f"Cannot stage {page}: localized file already exists: {localized_page}"
            )
        page.rename(localized_page)


@event_priority(100)
def on_config(config):
    """Point MkDocs to a temporary language-explicit docs tree."""
    global _SOURCE_DOCS_DIR, _STAGE_ROOT, _STAGE_DOCS_DIR

    incoming_docs_dir = Path(config.docs_dir).resolve()

    if _STAGE_ROOT is None:
        _STAGE_ROOT = Path(tempfile.mkdtemp(prefix="mkdocs-english-default-"))
        _STAGE_DOCS_DIR = _STAGE_ROOT / "docs"

    assert _STAGE_DOCS_DIR is not None

    if incoming_docs_dir != _STAGE_DOCS_DIR.resolve():
        _SOURCE_DOCS_DIR = incoming_docs_dir

    config.docs_dir = str(_STAGE_DOCS_DIR)
    return config


@event_priority(100)
def on_pre_build(config) -> None:
    """Refresh staged documentation before every build."""
    _prepare_stage()


def on_page_context(context, page, config, nav):
    """Keep Portuguese edit links pointing to canonical unsuffixed files."""
    if page.edit_url and ".pt.md" in page.edit_url:
        page.edit_url = page.edit_url.replace(".pt.md", ".md")
    return context


def on_shutdown() -> None:
    """Remove the temporary documentation tree."""
    global _SOURCE_DOCS_DIR, _STAGE_ROOT, _STAGE_DOCS_DIR

    if _STAGE_ROOT is not None:
        shutil.rmtree(_STAGE_ROOT, ignore_errors=True)

    _SOURCE_DOCS_DIR = None
    _STAGE_ROOT = None
    _STAGE_DOCS_DIR = None
