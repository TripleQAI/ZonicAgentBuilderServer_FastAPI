"""One-off: transcribe the Django node registry into JSON resources.

Reads ``agentBuilder/services/node_registry.py`` from the source project
**read-only** and writes ``app/resources/node_types/*.json`` plus
``app/resources/fragments/*.json`` into this repository.

Doing the transcription mechanically instead of by hand is what makes the
"deep-equal to the source registry" exit criterion (MIGRATION_PLAN.md, P2)
achievable rather than aspirational: the shared section and option objects are
detected by *identity*, so a fragment reference is emitted exactly where the
Python code reused the same object.

    python scripts/gen_registry_resources.py --source PATH [--check]

``--check`` regenerates into a temporary directory and diffs, so CI can prove
the committed resources still match the source. Each node type's ``icon``,
``color`` and ``sortOrder`` have since been restyled by hand to match the
Strands Visual Builder, so ``--check`` reports those three keys as drift.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
RESOURCES = REPO / "app" / "resources"

#: Python module-level name -> fragment id. Matched by object identity.
FRAGMENTS: dict[str, str] = {
    "_VAR_UPDATES": "section.variable_updates",
    "_OUTPUT_STRUCT": "section.output_structure",
    "_OUTPUT_SCHEMA": "section.output_schema",
    "_MODELS": "options.models",
    "_STATE_OPS": "options.state_ops",
    "_MAPPING_TYPES": "options.mapping_types",
    "_SCHEMA_TYPES": "options.schema_types",
}


def load_source_module(path: Path) -> Any:
    """Import the registry module from an absolute path without touching sys.path."""
    if not path.exists():
        raise SystemExit(f"source registry not found: {path}")
    spec = importlib.util.spec_from_file_location("_source_node_registry", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_identity_index(module: Any) -> dict[int, str]:
    index: dict[int, str] = {}
    for attr, fragment_id in FRAGMENTS.items():
        obj = getattr(module, attr, None)
        if obj is None:
            print(f"  warning: {attr} not found in the source module", file=sys.stderr)
            continue
        index[id(obj)] = fragment_id
    return index


def externalise(
    node: Any, index: dict[int, str], used: set[str], *, root: bool = False
) -> Any:
    """Replace every reused shared object with a {"$ref": "<fragment id>"} marker."""
    if not root and id(node) in index:
        fragment_id = index[id(node)]
        used.add(fragment_id)
        return {"$ref": fragment_id}
    if isinstance(node, dict):
        return {k: externalise(v, index, used) for k, v in node.items()}
    if isinstance(node, list):
        return [externalise(v, index, used) for v in node]
    return node


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def generate(source: Path, out_root: Path) -> tuple[int, int]:
    module = load_source_module(source)
    registry = getattr(module, "NODE_REGISTRY", None)
    if not isinstance(registry, dict):
        raise SystemExit("NODE_REGISTRY not found or not a dict")

    index = build_identity_index(module)
    used: set[str] = set()

    node_docs = {
        node_type: externalise(definition, index, used, root=True)
        for node_type, definition in registry.items()
    }

    # Only fragments the registry actually references are emitted. The source
    # module also defines _STATE_OPS, _MAPPING_TYPES, _SCHEMA_TYPES and
    # _OUTPUT_SCHEMA, which no node type uses — dead constants that are not
    # carried over (MIGRATION_PLAN.md §3.5 disposition: drop).
    unused = sorted(set(FRAGMENTS.values()) - used)
    if unused:
        print(f"  note: {len(unused)} unreferenced source constant(s) skipped: "
              f"{', '.join(unused)}")

    for fragment_id in sorted(used):
        attr = next(a for a, f in FRAGMENTS.items() if f == fragment_id)
        # root=True so a fragment does not turn into a reference to itself.
        write_json(out_root / "fragments" / f"{fragment_id}.json",
                   externalise(getattr(module, attr), index, set(), root=True))

    for node_type, doc in node_docs.items():
        write_json(out_root / "node_types" / f"{node_type}.json", doc)

    return len(used), len(registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="the source project's agentBuilder/services/node_registry.py")
    parser.add_argument("--out", type=Path, default=RESOURCES)
    parser.add_argument("--check", action="store_true",
                        help="regenerate into a temp dir and diff against the committed files")
    args = parser.parse_args()

    if args.check:
        import filecmp
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            generate(args.source, tmp_root)
            differences: list[str] = []
            for generated in sorted(tmp_root.rglob("*.json")):
                rel = generated.relative_to(tmp_root)
                committed = args.out / rel
                if not committed.exists():
                    differences.append(f"missing: {rel}")
                elif not filecmp.cmp(generated, committed, shallow=False):
                    differences.append(f"differs: {rel}")
            if differences:
                print("registry resources are out of date:", file=sys.stderr)
                for line in differences:
                    print(f"  {line}", file=sys.stderr)
                return 1
            print("registry resources match the source registry")
            return 0

    fragments, node_types = generate(args.source, args.out)
    print(f"wrote {fragments} fragments and {node_types} node types to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
