"""
test_sinapsis_memory_bridge.py — v2.2 bridge Sinapsis → Claude memory_20250818

Valida que `SinapsisBridge.to_memory_tool_entries()` produce entradas con el
shape exacto que espera la memory tool (`command: "create"`, path POSIX,
content no vacío) y respeta:
- opt-in (vacío si el bridge no está disponible)
- limit + scope
- deduplicación de paths
- slug seguro (sin chars inválidos para el path)
- truncado razonable del content
"""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "integrations"))

from sinapsis_bridge import SinapsisBridge  # noqa: E402


# --------------------------------------------------------------------
# Fixture: Sinapsis falso con instincts suficientes para cubrir cases
# --------------------------------------------------------------------
@pytest.fixture
def sinapsis_for_memory(tmp_path):
    root = tmp_path / "sin"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: test\nversion: 4.9.0-test\n---\n",
        encoding="utf-8",
    )
    (root / "_instincts-index.json").write_text(
        json.dumps({
            "instincts": [
                {
                    "id": "i001",
                    "title": "Supabase siempre RLS",
                    "rule": "Cuando uses Supabase, activar RLS en todas las tablas públicas.",
                    "confidence": "permanent",
                    "occurrences": 42,
                    "scope": "global",
                    "domain": ["backend", "supabase"],
                },
                {
                    "id": "i002",
                    "rule": "Nunca commitees .env ni credenciales.",
                    "confidence": "confirmed",
                    "occurrences": 10,
                    "scope": "global",
                },
                {
                    "id": "i003",
                    "rule": "Borrador, ignorar.",
                    "confidence": "draft",
                    "occurrences": 1,
                },
                # IDs conflictivos para probar dedup / slugify
                {
                    "id": "weird id/with\\slashes:and*stars",
                    "rule": "Regla con id problemático.",
                    "confidence": "confirmed",
                    "occurrences": 3,
                    "scope": "project:demo",
                },
                {
                    "id": "same-id",
                    "rule": "Primera con same-id.",
                    "confidence": "confirmed",
                    "occurrences": 2,
                    "scope": "global",
                },
                {
                    "id": "same-id",
                    "rule": "Segunda con same-id — dedup esperado.",
                    "confidence": "confirmed",
                    "occurrences": 2,
                    "scope": "global",
                },
            ]
        }),
        encoding="utf-8",
    )
    return root


# --------------------------------------------------------------------
# Contratos básicos
# --------------------------------------------------------------------
class TestMemoryToolShape:
    def test_returns_empty_list_when_unavailable(self):
        bridge = SinapsisBridge(available=False, reason_unavailable="test")
        assert bridge.to_memory_tool_entries() == []

    def test_returns_empty_when_no_active_instincts(self, tmp_path):
        root = tmp_path / "sin"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        (root / "_instincts-index.json").write_text(
            json.dumps({"instincts": []}), encoding="utf-8"
        )
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        assert bridge.available
        assert bridge.to_memory_tool_entries() == []

    def test_every_entry_has_memory_tool_shape(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries()
        assert entries, "expected at least one entry"
        for entry in entries:
            # command siempre 'create' en esta v2.2 (solo write)
            assert entry["command"] == "create"
            # paths son POSIX, empiezan por /memories/
            assert entry["path"].startswith("/memories/")
            assert "\\" not in entry["path"], "paths must be POSIX"
            assert entry["path"].endswith(".md")
            # content no vacío + empieza con un H1
            assert entry["content"].startswith("# "), entry["content"][:40]
            assert entry["content"].strip(), "content must not be empty"


# --------------------------------------------------------------------
# Slugify / dedup
# --------------------------------------------------------------------
class TestSlugAndDedup:
    def test_id_with_unsafe_chars_gets_slugified(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries()
        offending = [
            e for e in entries
            if any(bad in e["path"] for bad in ("/with", "\\", ":and", "*stars"))
        ]
        assert not offending, f"unsafe chars leaked into paths: {offending}"
        # Y existe una entrada para ese instinct con un slug saneado.
        assert any(
            "project-demo" in e["path"] and "weird" in e["path"] for e in entries
        ), entries

    def test_duplicate_ids_are_deduped(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries()
        paths = [e["path"] for e in entries]
        assert len(paths) == len(set(paths)), f"duplicates found: {paths}"
        # Aún así, ambos same-id deberían estar presentes bajo nombres distintos.
        same_id_paths = [p for p in paths if "same-id" in p]
        assert len(same_id_paths) >= 2


# --------------------------------------------------------------------
# Filtros limit / scope
# --------------------------------------------------------------------
class TestFilters:
    def test_limit_is_honoured(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        assert len(bridge.to_memory_tool_entries(limit=2)) == 2

    def test_scope_filter(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        only_global = bridge.to_memory_tool_entries(scope="global")
        for e in only_global:
            # El path contiene el scope tras /memories/<scope>/
            after_prefix = e["path"][len("/memories/") :]
            scope_in_path = after_prefix.split("/", 1)[0]
            assert scope_in_path == "global", e["path"]

    def test_skips_draft_instincts(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries()
        assert not any("Borrador" in e["content"] for e in entries)


# --------------------------------------------------------------------
# Metadata en el content
# --------------------------------------------------------------------
class TestContentBody:
    def test_content_includes_rule(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries()
        supabase_entry = next(
            (e for e in entries if "Supabase" in e["content"]), None
        )
        assert supabase_entry is not None
        assert "RLS" in supabase_entry["content"]
        # Metadata incluye version de Sinapsis y scope
        assert "4.9.0-test" in supabase_entry["content"]
        assert "scope: global" in supabase_entry["content"]

    def test_content_is_reasonably_bounded(self, tmp_path):
        root = tmp_path / "sin"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        huge = "x" * 5000
        (root / "_instincts-index.json").write_text(
            json.dumps({
                "instincts": [{
                    "id": "big",
                    "rule": huge,
                    "confidence": "confirmed",
                    "occurrences": 1,
                }]
            }),
            encoding="utf-8",
        )
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        entries = bridge.to_memory_tool_entries()
        assert len(entries) == 1
        # Cota generosa (~1 KB) pero < payload original.
        assert len(entries[0]["content"]) < 2000, len(entries[0]["content"])


# --------------------------------------------------------------------
# base_path configurable
# --------------------------------------------------------------------
class TestCustomBasePath:
    def test_custom_base_path(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries(base_path="/memories/cognito")
        for e in entries:
            assert e["path"].startswith("/memories/cognito/"), e["path"]

    def test_trailing_slash_on_base_path_is_normalised(self, sinapsis_for_memory):
        bridge = SinapsisBridge.detect(explicit_path=str(sinapsis_for_memory))
        entries = bridge.to_memory_tool_entries(base_path="/memories/cognito/")
        for e in entries:
            assert not e["path"].startswith("/memories/cognito//"), e["path"]
