#!/usr/bin/env python3
"""
Remove unused imports from a single Python file using LibCST.

"""
import libcst as cst
from libcst import RemovalSentinel, MetadataWrapper
from libcst.metadata import PositionProvider              # no heavy deps

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

    # -------------------------------------------------------------- #
    def leave_Import(self, original, updated):
        kept = [
            item for item in updated.names
            if (item.asname.name.value if item.asname else item.name.value) in self.used
        ]
        return updated.with_changes(names=kept) if kept else RemovalSentinel.REMOVE

    def leave_ImportFrom(self, original, updated):
        if updated.names is None or updated.names[0].name.value == "*":
            return updated                                  # keep star-import
        kept = []
        for item in updated.names:
            local = item.asname.name.value if item.asname else item.name.value
            if local in self.used:
                kept.append(item)
        return updated.with_changes(names=kept) if kept else RemovalSentinel.REMOVE


# ------------------------------------------------------------------ #
def trim_imports_from_file(src_file: str, dst_file: str) -> None:
    code = read_txt_file(src_file)
    wrapper = MetadataWrapper(cst.parse_module(code))       # wrap tree
    cleaned = wrapper.visit(ImportCleaner())                # transform
    write_txt_file(cleaned.code, dst_file)
    print(f"✓ cleaned imports in {dst_file} from {src_file}")
