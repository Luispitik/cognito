"""
Cognito — Sinapsis Bridge
==========================

Módulo opcional que conecta Cognito con Sinapsis (si está instalado).

Filosofía:
- **Opt-in por auto-detect**: si Sinapsis existe, se integra; si no, no pasa nada.
- **Zero crash**: si Sinapsis se rompe, Cognito sigue funcionando en modo standalone.
- **Sin acoplamiento duro**: Cognito no importa ningún módulo de Sinapsis.
  Lee su estado desde el filesystem (archivos JSON públicos).

Uso desde los hooks:
    from cognito.integrations.sinapsis_bridge import SinapsisBridge
    bridge = SinapsisBridge.detect()
    if bridge.available:
        instincts = bridge.get_active_instincts(limit=10)
        skills = bridge.get_catalog()
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Paths candidatos donde podría vivir Sinapsis.
# Se prueban en orden; el primero existente gana.
# Genéricos primero, luego fallback a instalaciones personalizadas (operator profile).
_CANDIDATE_ROOTS = [
    "~/.claude/skills/sinapsis",
    "~/.claude/skills/norteia-continuous-learning",  # Sinapsis v4.3+ packaged as a global skill
    "~/.sinapsis",
    "~/sinapsis",
    "~/.claude/skills/sinapsis-learning",
]


@dataclass
class SinapsisBridge:
    """
    Puente opcional a Sinapsis. Usa solo lectura de filesystem.

    Si `available == False`, todos los métodos retornan estructuras vacías.
    """

    root: Path | None = None
    available: bool = False
    version: str | None = None
    reason_unavailable: str = ""

    # Subpaths típicos de Sinapsis (tolerantes a variantes)
    _instincts_index_candidates: tuple[str, ...] = field(
        default_factory=lambda: (
            "_instincts-index.json",
            "instincts/_index.json",
            "data/instincts-index.json",
        )
    )
    _passive_rules_candidates: tuple[str, ...] = field(
        default_factory=lambda: (
            "_passive-rules.json",
            "passive-rules.json",
        )
    )
    _catalog_candidates: tuple[str, ...] = field(
        default_factory=lambda: (
            "_catalog.json",
            "skills/_catalog.json",
            "../../_catalog.json",  # ~/.claude/skills/_catalog.json relative
        )
    )

    # ------------------------------------------------------------------ #
    # Construcción / detección
    # ------------------------------------------------------------------ #

    @classmethod
    def detect(
        cls,
        explicit_path: str | None = None,
        operator_config: dict | None = None,
    ) -> "SinapsisBridge":
        """
        Intenta localizar Sinapsis. Orden de prioridad:
          1. `explicit_path` si se pasa.
          2. `operator_config["integrations"]["sinapsis"]["path"]` si existe.
          3. Variable de entorno `SINAPSIS_DIR`.
          4. Lista de rutas candidatas.

        Siempre retorna una instancia, incluso si no detecta (available=False).
        """
        # opt-out explícito del operador: se respeta incluso con explicit_path
        if operator_config:
            sin_cfg = operator_config.get("integrations", {}).get("sinapsis", {})
            if isinstance(sin_cfg, dict) and sin_cfg.get("installed") is False:
                return cls(
                    available=False,
                    reason_unavailable="Deshabilitado en _operator-config.json",
                )

        # Si hay explicit_path, es fuente de verdad: solo se prueba ese.
        # No caer a candidates automáticos (los tests confían en este contrato).
        if explicit_path:
            candidates = [explicit_path]
        else:
            candidates = []
            if operator_config:
                sin_cfg = operator_config.get("integrations", {}).get("sinapsis", {})
                if isinstance(sin_cfg, dict):
                    custom_path = sin_cfg.get("path")
                    if custom_path:
                        candidates.append(custom_path)
            env_path = os.environ.get("SINAPSIS_DIR")
            if env_path:
                candidates.append(env_path)
            candidates.extend(_CANDIDATE_ROOTS)

        for cand in candidates:
            expanded = Path(os.path.expanduser(cand)).resolve()
            if not expanded.exists() or not expanded.is_dir():
                continue
            if cls._looks_like_sinapsis(expanded):
                version = cls._read_version(expanded)
                return cls(root=expanded, available=True, version=version)

        reason = (
            f"Path explícito no válido: {explicit_path}"
            if explicit_path
            else "Sinapsis no encontrado en rutas conocidas"
        )
        return cls(available=False, reason_unavailable=reason)

    @staticmethod
    def _looks_like_sinapsis(path: Path) -> bool:
        """
        Heurística: contiene al menos uno de estos signos típicos de Sinapsis.
        """
        markers = [
            "_instincts-index.json",
            "instincts",
            "_passive-rules.json",
            "SKILL.md",
        ]
        for marker in markers:
            if (path / marker).exists():
                return True
        return False

    @staticmethod
    def _read_version(path: Path) -> str | None:
        """
        Intenta extraer la versión de Sinapsis (si existe VERSION o skill.md).
        """
        version_file = path / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text(encoding="utf-8").strip()
            except OSError:
                pass

        skill_md = path / "SKILL.md"
        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8")
                for line in content.splitlines()[:20]:
                    if line.lower().startswith("version:"):
                        return line.split(":", 1)[1].strip()
            except OSError:
                pass
        return None

    # ------------------------------------------------------------------ #
    # Lecturas de Sinapsis
    # ------------------------------------------------------------------ #

    def _read_first_existing(self, candidates: tuple[str, ...]) -> Any:
        """Retorna el contenido JSON del primer candidato que exista."""
        if not self.available or self.root is None:
            return None
        for rel in candidates:
            full = (self.root / rel).resolve()
            if full.exists():
                try:
                    with open(full, encoding="utf-8") as f:
                        return json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue
        return None

    def get_active_instincts(self, limit: int = 20, scope: str | None = None) -> list[dict]:
        """
        Devuelve los instincts activos (confirmed + permanent) ordenados por
        ocurrencias descendente. Si scope se especifica, filtra (global, project, etc).
        """
        if not self.available:
            return []

        data = self._read_first_existing(tuple(self._instincts_index_candidates))
        if data is None:
            return []

        instincts_raw: list[dict] = []
        if isinstance(data, dict):
            # Formatos típicos: {"instincts": [...]} o {"items": [...]}
            if isinstance(data.get("instincts"), list):
                instincts_raw = data["instincts"]
            elif isinstance(data.get("items"), list):
                instincts_raw = data["items"]
            else:
                # Podría ser {"id1": {...}, "id2": {...}}
                if all(isinstance(v, dict) for v in data.values()):
                    instincts_raw = list(data.values())
        elif isinstance(data, list):
            instincts_raw = data

        # Filtrar: confidence ∈ {confirmed, permanent}, scope si aplica
        filtered: list[dict] = []
        for inst in instincts_raw:
            if not isinstance(inst, dict):
                continue
            conf = (inst.get("confidence") or inst.get("status") or "").lower()
            if conf and conf in ("draft", "quarantine"):
                continue
            if scope and (inst.get("scope") or "global") != scope:
                continue
            filtered.append(inst)

        # Ordenar por occurrences desc
        filtered.sort(key=lambda i: i.get("occurrences", 0), reverse=True)
        return filtered[:limit]

    def get_catalog(self) -> list[dict]:
        """Devuelve el catálogo de skills (si existe). Lista vacía si no."""
        if not self.available:
            return []
        data = self._read_first_existing(tuple(self._catalog_candidates))
        if data is None:
            return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if isinstance(data.get("skills"), list):
                return data["skills"]
            if isinstance(data.get("entries"), list):
                return data["entries"]
            if all(isinstance(v, dict) for v in data.values()):
                return list(data.values())
        return []

    def get_passive_rules(self) -> list[dict]:
        """Devuelve las passive rules de Sinapsis (si existen)."""
        if not self.available:
            return []
        data = self._read_first_existing(tuple(self._passive_rules_candidates))
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("rules", "items", "passiveRules"):
                if isinstance(data.get(key), list):
                    return data[key]
        return []

    # ------------------------------------------------------------------ #
    # Formateo para inyección al contexto
    # ------------------------------------------------------------------ #

    def render_injection(self, limit: int = 10) -> str:
        """
        Produce un bloque markdown para inyectar en systemMessage cuando
        Cognito quiere que Claude sea consciente de los instincts de Sinapsis.
        Si no hay bridge disponible, retorna cadena vacía.
        """
        if not self.available:
            return ""

        instincts = self.get_active_instincts(limit=limit)
        if not instincts:
            return ""

        lines: list[str] = [
            "\n---",
            "## Sinapsis — Instincts activos (desde bridge)",
            "",
            "_Reglas aprendidas por Sinapsis que aplican a este contexto. "
            "No las anules sin razón; si entran en conflicto con la decisión del operador, señálalo._",
            "",
        ]
        for inst in instincts:
            rule = inst.get("rule") or inst.get("body") or inst.get("description", "")
            if not rule:
                continue
            scope = inst.get("scope") or "global"
            occ = inst.get("occurrences", 0)
            lines.append(f"- **{scope}** ({occ}×): {rule.strip()[:300]}")

        version_note = f" (Sinapsis v{self.version})" if self.version else ""
        lines.append(f"\n_Fuente: Sinapsis bridge{version_note}._\n")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # v2.2 — Export a Claude `memory_20250818` tool entries (opt-in)
    # ------------------------------------------------------------------ #

    # Caracteres inválidos para nombres de fichero en Windows + POSIX combinados.
    # Mantener conservador: sustituimos todo lo que no sea [A-Za-z0-9_.-] por '-'.
    _MEMORY_SAFE_ID_RE = None  # set lazily to avoid top-level re import cost

    @staticmethod
    def _slugify_memory_id(raw: str) -> str:
        import re

        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-.")
        # Evita nombres vacíos o sólo separadores.
        return cleaned or "instinct"

    def to_memory_tool_entries(
        self,
        limit: int = 20,
        scope: str | None = None,
        base_path: str = "/memories",
    ) -> list[dict]:
        """
        Map active Sinapsis instincts to Claude `memory_20250818` tool entries.

        Each entry is a `create` command shaped like:
            {
              "command": "create",
              "path": "/memories/{scope}/{safe_id}.md",
              "content": "<markdown body>"
            }

        Notes
        -----
        * **Opt-in.** This method produces values only; it does not call the
          tool handler. Callers are responsible for wiring the output into
          whatever memory-tool adapter they run against Claude.
        * Paths are always POSIX-style (forward slashes) because they address
          logical memory slots, not on-disk files.
        * Duplicate IDs within the same scope are deduplicated by appending
          `-2`, `-3`, ... so every `path` is unique in the returned list.
        * Content is truncated to ~1 KB per entry to keep the memory corpus
          small; the original instinct payload stays in Sinapsis.
        """
        if not self.available:
            return []

        instincts = self.get_active_instincts(limit=limit, scope=scope)
        if not instincts:
            return []

        entries: list[dict] = []
        seen_paths: dict[str, int] = {}

        for inst in instincts:
            if not isinstance(inst, dict):
                continue

            rule = (
                inst.get("rule")
                or inst.get("body")
                or inst.get("description")
                or ""
            ).strip()
            if not rule:
                continue

            inst_scope = (inst.get("scope") or "global").strip() or "global"
            safe_scope = self._slugify_memory_id(inst_scope)
            raw_id = (
                inst.get("id")
                or inst.get("instinct_id")
                or inst.get("slug")
                or rule[:40]
            )
            safe_id = self._slugify_memory_id(str(raw_id))

            path = f"{base_path.rstrip('/')}/{safe_scope}/{safe_id}.md"
            if path in seen_paths:
                seen_paths[path] += 1
                path = (
                    f"{base_path.rstrip('/')}/{safe_scope}/"
                    f"{safe_id}-{seen_paths[path]}.md"
                )
            else:
                seen_paths[path] = 1

            title = inst.get("title") or inst.get("name") or safe_id
            confidence = (inst.get("confidence") or inst.get("status") or "").strip()
            occurrences = inst.get("occurrences")
            domain = inst.get("domain") or inst.get("tags")

            lines = [f"# {title}", "", rule[:900]]
            meta: list[str] = []
            if confidence:
                meta.append(f"confidence: {confidence}")
            if occurrences is not None:
                meta.append(f"occurrences: {occurrences}")
            if domain:
                if isinstance(domain, (list, tuple)):
                    meta.append(f"domain: {', '.join(str(d) for d in domain)}")
                else:
                    meta.append(f"domain: {domain}")
            meta.append(f"scope: {inst_scope}")
            if self.version:
                meta.append(f"sinapsis: v{self.version}")

            if meta:
                lines.append("")
                lines.append("_" + " · ".join(meta) + "_")

            entries.append(
                {
                    "command": "create",
                    "path": path,
                    "content": "\n".join(lines),
                }
            )

        return entries

    def status_dict(self) -> dict:
        """Resumen en dict para /cognition-status."""
        if not self.available:
            return {
                "available": False,
                "reason": self.reason_unavailable,
            }
        return {
            "available": True,
            "root": str(self.root),
            "version": self.version,
            "instincts_count": len(self.get_active_instincts(limit=9999)),
            "skills_count": len(self.get_catalog()),
            "passive_rules_count": len(self.get_passive_rules()),
        }


# -------------------------------------------------------------------- #
# CLI (útil para tests y /cognition-status)
# -------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cognito → Sinapsis bridge probe")
    parser.add_argument("--path", help="Ruta explícita a Sinapsis (override)")
    parser.add_argument("--inject", action="store_true", help="Imprimir bloque de inyección")
    parser.add_argument("--status", action="store_true", help="Imprimir status JSON")
    args = parser.parse_args()

    bridge = SinapsisBridge.detect(explicit_path=args.path)

    if args.inject:
        print(bridge.render_injection())
    elif args.status or not any([args.inject]):
        print(json.dumps(bridge.status_dict(), indent=2, ensure_ascii=False))
