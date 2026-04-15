"""
test_sinapsis_bridge.py — Tests del bridge opcional con Sinapsis.

Valida:
- Detecta cuando Sinapsis está presente.
- Degrada silenciosamente cuando no lo está.
- Honra opt-out desde operator-config.
- Lee instincts y los ordena por occurrences.
- Render no crashea con datos vacíos.
- Tolera formatos variantes del schema de Sinapsis.
"""
import json
import sys
from pathlib import Path

import pytest

# Añadir integrations al path para poder importar el bridge
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "integrations"))

from sinapsis_bridge import SinapsisBridge  # noqa: E402


# --------------------------------------------------------------------
# Fixtures para simular un Sinapsis fake
# --------------------------------------------------------------------
@pytest.fixture
def fake_sinapsis(tmp_path):
    """Crea una carpeta con estructura mínima que parezca Sinapsis."""
    root = tmp_path / "fake-sinapsis"
    root.mkdir()

    # Marcador: SKILL.md con versión
    (root / "SKILL.md").write_text(
        "---\nname: test-sinapsis\nversion: 4.9.0-test\n---\n# Sinapsis Fake\n",
        encoding="utf-8",
    )

    # Instincts index con formato {"instincts": [...]}
    (root / "_instincts-index.json").write_text(
        json.dumps({
            "version": "1.0",
            "instincts": [
                {
                    "id": "i001",
                    "rule": "Cuando Supabase, siempre RLS",
                    "confidence": "permanent",
                    "occurrences": 42,
                    "scope": "global",
                },
                {
                    "id": "i002",
                    "rule": "Nunca commitees .env",
                    "confidence": "confirmed",
                    "occurrences": 10,
                    "scope": "global",
                },
                {
                    "id": "i003",
                    "rule": "Instinct borrador, no debería aparecer",
                    "confidence": "draft",
                    "occurrences": 2,
                },
                {
                    "id": "i004",
                    "rule": "Project-specific",
                    "confidence": "confirmed",
                    "occurrences": 5,
                    "scope": "project:foo",
                },
            ],
        }),
        encoding="utf-8",
    )

    return root


# --------------------------------------------------------------------
# Tests de detección
# --------------------------------------------------------------------
class TestDetection:
    def test_detects_valid_sinapsis(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        assert bridge.available is True
        assert bridge.root == fake_sinapsis.resolve()
        assert bridge.version == "4.9.0-test"

    def test_not_available_when_path_missing(self, tmp_path):
        ghost = tmp_path / "does-not-exist"
        bridge = SinapsisBridge.detect(explicit_path=str(ghost))
        assert bridge.available is False
        assert bridge.reason_unavailable

    def test_not_available_when_path_empty_dir(self, tmp_path):
        empty = tmp_path / "empty-dir"
        empty.mkdir()
        bridge = SinapsisBridge.detect(explicit_path=str(empty))
        assert bridge.available is False

    def test_opt_out_via_operator_config(self, fake_sinapsis):
        """Si operator-config dice installed: false, no detecta aunque exista."""
        op = {"integrations": {"sinapsis": {"installed": False}}}
        bridge = SinapsisBridge.detect(
            explicit_path=str(fake_sinapsis),
            operator_config=op,
        )
        assert bridge.available is False
        assert "Deshabilitado" in bridge.reason_unavailable

    def test_uses_operator_config_path(self, fake_sinapsis):
        """Path desde operator-config es respetado."""
        op = {"integrations": {"sinapsis": {"path": str(fake_sinapsis)}}}
        bridge = SinapsisBridge.detect(operator_config=op)
        assert bridge.available is True


# --------------------------------------------------------------------
# Tests de lectura
# --------------------------------------------------------------------
class TestReadInstincts:
    def test_reads_active_instincts(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        instincts = bridge.get_active_instincts()
        # 3 activos (permanent + confirmed), excluye draft
        assert len(instincts) == 3
        ids = [i["id"] for i in instincts]
        assert "i003" not in ids  # draft excluido

    def test_sorted_by_occurrences_desc(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        instincts = bridge.get_active_instincts()
        occ = [i.get("occurrences", 0) for i in instincts]
        assert occ == sorted(occ, reverse=True)
        assert instincts[0]["id"] == "i001"  # el de 42 ocurrencias

    def test_filter_by_scope(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        globals_ = bridge.get_active_instincts(scope="global")
        assert all(i["scope"] == "global" for i in globals_)

    def test_limit(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        limited = bridge.get_active_instincts(limit=1)
        assert len(limited) == 1
        assert limited[0]["id"] == "i001"  # top por occurrences


# --------------------------------------------------------------------
# Tests de formato alternativo de Sinapsis
# --------------------------------------------------------------------
class TestSchemaVariants:
    def test_flat_list_format(self, tmp_path):
        """Sinapsis puede exponer _instincts-index.json como lista directa."""
        root = tmp_path / "sinapsis"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        (root / "_instincts-index.json").write_text(
            json.dumps([
                {"id": "a", "rule": "r1", "confidence": "confirmed", "occurrences": 1}
            ]),
            encoding="utf-8",
        )
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        assert bridge.available
        assert len(bridge.get_active_instincts()) == 1

    def test_dict_of_dicts_format(self, tmp_path):
        """Sinapsis puede exponer {"id1": {...}, "id2": {...}}."""
        root = tmp_path / "sinapsis"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        (root / "_instincts-index.json").write_text(
            json.dumps({
                "a": {"id": "a", "rule": "r1", "confidence": "confirmed", "occurrences": 3},
                "b": {"id": "b", "rule": "r2", "confidence": "permanent", "occurrences": 7},
            }),
            encoding="utf-8",
        )
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        results = bridge.get_active_instincts()
        assert len(results) == 2
        assert results[0]["id"] == "b"  # más ocurrencias


# --------------------------------------------------------------------
# Tests de robustez
# --------------------------------------------------------------------
class TestResilience:
    def test_corrupt_json_no_crash(self, tmp_path):
        root = tmp_path / "sinapsis"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        (root / "_instincts-index.json").write_text("not json at all", encoding="utf-8")
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        # Bridge puede detectarse aunque index esté corrupto
        assert bridge.available is True
        # ...pero get_active_instincts no rompe
        assert bridge.get_active_instincts() == []

    def test_empty_render_when_unavailable(self):
        bridge = SinapsisBridge(available=False)
        assert bridge.render_injection() == ""

    def test_render_when_no_instincts(self, tmp_path):
        root = tmp_path / "sinapsis"
        root.mkdir()
        (root / "SKILL.md").write_text("name: s\n", encoding="utf-8")
        (root / "_instincts-index.json").write_text(json.dumps({"instincts": []}), encoding="utf-8")
        bridge = SinapsisBridge.detect(explicit_path=str(root))
        assert bridge.render_injection() == ""


# --------------------------------------------------------------------
# Tests de render
# --------------------------------------------------------------------
class TestRenderInjection:
    def test_render_mentions_instinct_rules(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        rendered = bridge.render_injection(limit=5)
        assert "Supabase, siempre RLS" in rendered
        assert "Sinapsis" in rendered
        assert "Instincts activos" in rendered

    def test_render_includes_version(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        rendered = bridge.render_injection()
        assert "4.9.0-test" in rendered

    def test_render_respects_limit(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        rendered = bridge.render_injection(limit=1)
        # Solo un instinct listado
        bullets = [line for line in rendered.split("\n") if line.startswith("- **")]
        assert len(bullets) == 1


# --------------------------------------------------------------------
# Tests de status_dict
# --------------------------------------------------------------------
class TestStatusDict:
    def test_status_when_unavailable(self):
        bridge = SinapsisBridge(available=False, reason_unavailable="Not found")
        status = bridge.status_dict()
        assert status["available"] is False
        assert "reason" in status

    def test_status_when_available(self, fake_sinapsis):
        bridge = SinapsisBridge.detect(explicit_path=str(fake_sinapsis))
        status = bridge.status_dict()
        assert status["available"] is True
        assert status["version"] == "4.9.0-test"
        assert status["instincts_count"] == 3
