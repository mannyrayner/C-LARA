#!/usr/bin/env python3
"""
Remove unused imports from a single Python file using LibCST.

"""
import libcst as cst
from libcst import RemovalSentinel, MaybeSentinel, MetadataWrapper
from libcst.metadata import PositionProvider              # no heavy deps
from typing import List, Tuple

# ------------------------------------------------------------- helpers
def _dedupe(aliases: List[cst.ImportAlias]) -> List[cst.ImportAlias]:
    seen = set()
    out: List[cst.ImportAlias] = []
    for alias in aliases:
        key = (
            alias.name.value,
            alias.asname.name.value if alias.asname else None,
        )
        if key not in seen:
            seen.add(key)
            out.append(alias)
    return out


def _strip_trailing_comma(aliases: List[cst.ImportAlias]) -> List[cst.ImportAlias]:
    if aliases:
        aliases[-1] = aliases[-1].with_changes(comma=MaybeSentinel.DEFAULT)
    return aliases


# ------------------------------------------------------------------ #
class _NameCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    # ------------- skip import statements entirely ---------------- #
    def visit_Import(self, node: cst.Import) -> bool:
        return False            # don't traverse inside

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        return False            # don't traverse inside

    # ------------- gather identifiers used elsewhere -------------- #
    def visit_Name(self, node: cst.Name) -> None:
        self.names.add(node.value)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        base = node
        while isinstance(base, cst.Attribute):
            base = base.value
        if isinstance(base, cst.Name):
            self.names.add(base.value)


class ImportCleaner(cst.CSTTransformer):
    """Remove unused 'import' / 'from … import …' lines."""
    METADATA_DEPENDENCIES = (PositionProvider,)           # any lightweight one

    # -------------------------------------------------------------- #
    def visit_Module(self, node):
        # collect identifiers once, store in self.used
        collector = _NameCollector()
        node.visit(collector)
        self.used = collector.names
        self.seen_src = set()                       # final-rendered imports
        self._mod_helper = cst.Module(body=[])      # for code_for_node

    # ------------------------------------------------------------------ helpers
    def _finalise(self, original, updated, aliases):
        """Return updated node or REMOVE, while filtering duplicates."""
        if not aliases:                               # nothing left
            return RemovalSentinel.REMOVE

        updated = updated.with_changes(names=aliases)
        src = self._mod_helper.code_for_node(updated)
        if src in self.seen_src:
            return RemovalSentinel.REMOVE
        self.seen_src.add(src)
        return updated

    # -------------------------------------------------------------- #
    def leave_Import(self, original, updated):
        aliases = [
            a for a in updated.names
            if (a.asname.name.value if a.asname else a.name.value) in self.used
        ]
        aliases = _strip_trailing_comma(_dedupe(aliases))
        return self._finalise(original, updated, aliases)

    def leave_ImportFrom(self, original, updated):
        if updated.names is None or updated.names[0].name.value == "*":
            return updated                                          # keep  *
        aliases = []
        for a in updated.names:
            local = a.asname.name.value if a.asname else a.name.value
            if local in self.used:
                aliases.append(a)
        aliases = _strip_trailing_comma(_dedupe(aliases))
        return self._finalise(original, updated, aliases)

# ------------------------------------------------------------------ #
def trim_imports_from_file(src_file: str, dst_file: str) -> None:
    code = read_txt_file(src_file)
    wrapper = MetadataWrapper(cst.parse_module(code))       # wrap tree
    cleaned = wrapper.visit(ImportCleaner())                # transform
    write_txt_file(cleaned.code, dst_file)
    print(f"✓ cleaned imports in {dst_file} from {src_file}")
