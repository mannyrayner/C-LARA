#!/usr/bin/env python3
"""
tq_exports_to_latex.py — Combined appendix tables

Reads C-LARA text-questionnaire export ZIPs (created by tq_export_csv(..., kind="all"))
and emits one longtable per (experiment, language) that merges Teacher + Student and
page-level + whole-book results.

Key features:
- Auto-detect Q columns (Q1, q1_mean, ...).
- For each ZIP: combine page and book matrices per title; book Qs are renumbered to follow page Qs.
- Title cleanup: drop parenthetical model/gloss info; append "(N pages)" if known.
- Group into a single longtable per (exp, language) with Teacher and Student sections.
- Sort rows within each section by Avg (desc).

Usage:
  python tq_exports_to_latex.py path/or/*.zip --out tex_tables
Options:
  --sort {avg,alpha}  sort by average (default) or alphabetically by title.
  --label-prefix STR  label prefix (default "tab:")
  --caption-prefix STR caption prefix.
"""

import argparse, io, os, re, sys, zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

import pprint

trace = True
#trace = False

# ---------- small helpers ----------

def absolute_file_name(pathname):
    pathname = os.path.abspath(os.path.expandvars(pathname))
    return pathname.replace("\\", "/")

def escape_tex(s: str) -> str:
    if s is None: return ""
    return (s.replace('\\', r'\\')
             .replace('&', r'\&')
             .replace('%', r'\%')
             .replace('$', r'\$')
             .replace('#', r'\#')
             .replace('_', r'\_')
             .replace('{', r'\{')
             .replace('}', r'\}')
             .replace('~', r'\textasciitilde{}')
             .replace('^', r'\textasciicircum{}'))

def strip_parenthetical(title: str) -> str:
    # kept for backward-compat if you still call it elsewhere
    return re.sub(r"\s*\([^()]*\)\s*$", "", title or "").strip()

def clean_title_core(title: str) -> str:
    """
    Remove ALL parenthetical chunks anywhere in the title and any trailing ', vN'.
    Collapse whitespace. Example:
      'Foo (gpt-image-1, gpt-5), v2 (Chinese glosses)' -> 'Foo'
    """
    s = re.sub(r"\([^)]*\)", "", title or "")
    s = re.sub(r",?\s*v\d+\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def read_csv_from_zip_by_parts(zf: zipfile.ZipFile, *parts: str) -> Optional[pd.DataFrame]:
    parts = tuple(p.lower() for p in parts)
    for name in zf.namelist():
        low = name.lower()
        if low.endswith(".csv") and all(p in low for p in parts):
            with zf.open(name) as f:
                return pd.read_csv(f)
    return None

# ---------- base parsing & grouping ----------

def parse_base_name(base: str) -> tuple[str, str, str]:
    """
    Parse 'exp_1_teacher_chinese' -> ('1','teacher','chinese').
    Works with missing language: 'exp_2_teacher' -> ('2','teacher','NA').
    Returns (exp, audience, language).
    """
    b = base.lower()
    m = re.match(r"^exp[_-]?([^_]+)_([^_]+)(?:_([^_]+))?$", b)
    if m:
        exp, audience, lang = m.group(1), m.group(2), (m.group(3) or "NA")
        if trace: print(f'parse_base_name({base}) = ({exp}, {audience}, {lang})')
        return exp, audience, lang
    if trace: print(f'parse_base_name({base}) = ("X", "unknown", "NA")')
    return ("X", "unknown", "NA")

# ---------- column autodetection ----------

_Q_MEAN_PATS = [
    re.compile(r"^q(\d+)_mean$", re.I),  # q1_mean, ...
    re.compile(r"^Q(\d+)$"),             # Q1, ...
]
def detect_q_cols(df: pd.DataFrame) -> List[str]:
    found = []
    for col in df.columns:
        for pat in _Q_MEAN_PATS:
            m = pat.fullmatch(str(col))
            if m:
                found.append((int(m.group(1)), col))
                break
    found.sort(key=lambda t: t[0])
    return [c for _, c in found]

def detect_avg_col(df: pd.DataFrame) -> Optional[str]:
    for name in ["overall_mean", "Avg", "avg", "Average", "mean"]:
        if name in df.columns:
            return name
    return None

def detect_pages_col(df: pd.DataFrame) -> Optional[str]:
    for name in ["pages_rated", "Pages", "pages", "n_pages"]:
        if name in df.columns:
            return name
    return None

def to_numeric_inplace(df: pd.DataFrame, cols: List[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

# ---------- reading exports ----------

def load_exports(paths: List[Path]) -> List[Tuple[str, str, str, pd.DataFrame, pd.DataFrame]]:
    """
    Return list of (exp, audience, lang, df_book_matrix, df_page_matrix) for each zip.
    """
    if trace: print(f'--- call load_exports on {paths}')
    results = []
    zips: List[Path] = []
    for p in paths:
        if p.is_dir():
            zips.extend(sorted(p.glob("*.zip")))
        elif p.is_file() and p.suffix.lower() == ".zip":
            zips.append(p)
        else:
            print(f"[warn] skipping {p}: not a dir or .zip", file=sys.stderr)

    if not zips:
        raise SystemExit("No .zip files found.")

    for z in zips:
        base = z.stem
        exp, audience, lang = parse_base_name(base)
        with zipfile.ZipFile(z, "r") as zf:
            df_book = read_csv_from_zip_by_parts(zf, "book", "matrix")
            df_page = read_csv_from_zip_by_parts(zf, "page", "matrix")
            # fallbacks, just in case
            if df_book is None:
                df_book = (read_csv_from_zip_by_parts(zf, "summary", "book")
                           or read_csv_from_zip_by_parts(zf, "book"))
            if df_page is None:
                df_page = (read_csv_from_zip_by_parts(zf, "summary", "page")
                           or read_csv_from_zip_by_parts(zf, "page"))
        if df_book is None and df_page is None:
            print(f"[warn] {z.name}: no usable CSVs.", file=sys.stderr)
            continue
        results.append((exp, audience, lang, df_book, df_page))
    if trace:
        print(f'--- load_exports: results')
        pprint.pprint(results)
    return results

# ---------- combine page + book per ZIP ----------

def combine_page_book(df_book: Optional[pd.DataFrame],
                      df_page: Optional[pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str,int]]:
    """
    Produce a unified per-zip DataFrame with columns:
      book_title, (Q1..Qn), Avg, pages
    where book Qs are renumbered to follow page Qs.
    Also returns a {title -> pages} map (if page info available).
    """
    # Normalize minimal columns
    def _norm(df: pd.DataFrame) -> pd.DataFrame:
        if "book_title" not in df.columns:
            # try common alias
            for cand in ["title", "book"]:
                if cand in df.columns:
                    df = df.rename(columns={cand: "book_title"})
                    break
        return df.copy()

    pages_map: Dict[str, int] = {}
    out_rows: Dict[str, Dict[str, float]] = {}

    # page part
    page_qcols: List[str] = []
    if df_page is not None and not df_page.empty:
        dfp = _norm(df_page)
        page_qcols = detect_q_cols(dfp)
        to_numeric_inplace(dfp, page_qcols)
        pcol = detect_pages_col(dfp)
        if pcol:
            for _, r in dfp.iterrows():
                title = r.get("book_title", "")
                if pd.notna(r.get(pcol)):
                    pages_map[title] = int(r[pcol])

        for _, r in dfp.iterrows():
            title = r.get("book_title", "")
            row = out_rows.setdefault(title, {})
            for i, qc in enumerate(page_qcols, start=1):
                v = r.get(qc)
                if pd.notna(v):
                    row[f"Q{i}"] = float(v)

    # book part
    if df_book is not None and not df_book.empty:
        dfb = _norm(df_book)
        book_qcols = detect_q_cols(dfb)
        to_numeric_inplace(dfb, book_qcols)
        offset = len(page_qcols)  # renumber starts after page Qs
        for _, r in dfb.iterrows():
            title = r.get("book_title", "")
            row = out_rows.setdefault(title, {})
            for j, qc in enumerate(book_qcols, start=1):
                v = r.get(qc)
                if pd.notna(v):
                    row[f"Q{offset + j}"] = float(v)

    # build combined dataframe
    titles = sorted(out_rows.keys(), key=lambda s: s.lower())
    max_q = 0
    for vals in out_rows.values():
        for k in vals.keys():
            if k.startswith("Q"):
                try:
                    max_q = max(max_q, int(k[1:]))
                except ValueError:
                    pass

    cols = ["book_title"] + [f"Q{i}" for i in range(1, max_q+1)] + ["Avg", "pages"]
    data = []
    for t in titles:
        row = {"book_title": t}
        qvals = []
        for i in range(1, max_q+1):
            v = out_rows[t].get(f"Q{i}")
            row[f"Q{i}"] = v if v is not None else None
            if v is not None:
                qvals.append(v)
        row["Avg"] = sum(qvals)/len(qvals) if qvals else None
        row["pages"] = pages_map.get(t)
        data.append(row)

    return pd.DataFrame(data, columns=cols), pages_map

# ---------- rendering ----------

def sort_rows(df: pd.DataFrame, qcols: List[str], avg_col: str, mode: str = "avg") -> pd.DataFrame:
    if mode == "alpha":
        return df.sort_values(by="book_title", key=lambda s: s.str.lower())
    # default: by Avg descending
    key = pd.to_numeric(df[avg_col], errors="coerce")
    return df.iloc[key.sort_values(ascending=False).index]

def render_group_longtable(exp: str,
                           lang: str,
                           audience_to_df: Dict[str, pd.DataFrame],
                           caption_prefix: str,
                           label_prefix: str,
                           sort_mode: str = "avg") -> Optional[str]:
    """
    Build one longtable for a (exp, lang), with Teacher + Student sections (if present).
    Columns are the superset of available Qs across both audiences.
    Each section prints its own Q-header row (only its present Qs are labeled).
    """
    if not audience_to_df:
        return None

    # Determine superset of Q columns + collect a normalised {title -> pages} map
    all_qnums = set()
    pages_by_title: Dict[str, int] = {}
    for df in audience_to_df.values():
        if df is None or df.empty:
            continue
        for c in df.columns:
            m = re.fullmatch(r"Q(\d+)", c)
            if m:
                all_qnums.add(int(m.group(1)))
        if "pages" in df.columns:
            for _, r in df.iterrows():
                tcore = clean_title_core(str(r.get("book_title", "")))
                p = r.get("pages")
                if pd.notna(p):
                    pages_by_title[tcore] = int(p)

    if not all_qnums:
        return None

    qmax  = max(all_qnums)
    qcols = [f"Q{i}" for i in range(1, qmax + 1)]

    # Longtable skeleton (generic head only for page breaks)
    col_spec = "@{}l" + "r" * len(qcols) + "r@{}"  # Title + Qs + Avg
    head = r"\textbf{Title} & " + " & ".join(qcols) + r" & \textbf{Avg.}\\"

    lines = []
    lines.append(r"\begin{longtable}{" + col_spec + "}")
    lines.append(r"\toprule")
    # No generic header on the first page:
    lines.append(r"\endfirsthead")
    # From page 2 onwards, show the generic header:
    lines.append(r"\toprule")
    lines.append(head)
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\bottomrule")
    lines.append(r"\endfoot")

    def _emit_section(name: str, df: pd.DataFrame):
        if df is None or df.empty:
            return

        # Ensure all needed cols exist
        for c in qcols + ["Avg", "book_title", "pages"]:
            if c not in df.columns:
                df[c] = None

        # Recompute Avg robustly over visible Q columns
        df2 = df.copy()
        df2["Avg"] = df2[qcols].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)
        df2 = sort_rows(df2, qcols, "Avg", mode=sort_mode)

        # Section label
        lines.append(r"\multicolumn{" + str(1 + len(qcols) + 1) + r"}{l}{\textit{" + escape_tex(name) + r"}}\\")

        # Section-specific header: label only those Qs that actually have data
        present = [c for c in qcols if df2[c].notna().any()]
        section_header = " & ".join([c if c in present else "" for c in qcols])
        lines.append(r"\textbf{Title} & " + section_header + r" & \textbf{Avg.}\\")
        lines.append(r"\midrule")

        # Rows
        for _, r in df2.iterrows():
            title_core = clean_title_core(str(r["book_title"]))
            pages_val  = r.get("pages")
            if (pd.isna(pages_val) or pages_val is None) and title_core in pages_by_title:
                pages_val = pages_by_title[title_core]

            title_tex = r"\emph{" + escape_tex(title_core) + (" (%d pages)" % pages_val if pages_val else "") + "}"
            cells = [title_tex]
            for c in qcols:
                v = r.get(c)
                cells.append(f"{float(v):.2f}" if pd.notna(v) else r"")
            avg = r.get("Avg")
            cells.append(f"{float(avg):.2f}" if pd.notna(avg) else r"")
            lines.append(" & ".join(cells) + r"\\")

        lines.append(r"\addlinespace")

    # Emit sections in a stable order
    aud_keys = {k.lower(): k for k in audience_to_df.keys()}
    if "teacher" in aud_keys:
        _emit_section("Teacher", audience_to_df[aud_keys["teacher"]])
    if "student" in aud_keys:
        _emit_section("Student", audience_to_df[aud_keys["student"]])

    # Caption/label
    cap = f"{caption_prefix}Experiment {exp}"
    if lang and lang != "NA":
        cap += f" — {lang.title()}"
    label = f"{label_prefix}exp_{exp}_{lang}_combined"
    lines.append(r"\caption{" + escape_tex(cap) + r"}")
    lines.append(r"\label{" + escape_tex(label) + r"}")
    lines.append(r"\end{longtable}")
    return "\n".join(lines) + "\n"

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="ZIP(s) or directory with ZIPs")
    ap.add_argument("--out", default="tex_tables", help="Output dir for .tex")
    ap.add_argument("--sort", choices=["avg","alpha"], default="avg")
    ap.add_argument("--caption-prefix", default="", help="Caption prefix")
    ap.add_argument("--label-prefix", default="tab:", help="Label prefix")
    args = ap.parse_args()

    in_paths = [Path(absolute_file_name(p)) for p in args.paths]
    exports = load_exports(in_paths)

    # 1) Combine page+book per ZIP
    combined: List[Tuple[str,str,str,str,pd.DataFrame,Dict[str,int]]] = []
    # (exp, audience, lang, basekey, df_combined, pages_map)
    for (exp, audience, lang, df_book, df_page) in exports:
        df_comb, pmap = combine_page_book(df_book, df_page)
        basekey = f"exp_{exp}_{audience}_{lang}"
        combined.append((exp, audience, lang, basekey, df_comb, pmap))

    # 2) Group by (exp, lang); merge Teacher/Student into one longtable
    groups: Dict[Tuple[str,str], Dict[str,pd.DataFrame]] = {}
    for exp, audience, lang, _, dfc, _ in combined:
        key = (exp, lang)
        groups.setdefault(key, {})
        groups[key][audience] = dfc

    out_dir = Path(absolute_file_name(args.out))
    out_dir.mkdir(parents=True, exist_ok=True)
    index_lines = []

    for (exp, lang), aud_map in sorted(groups.items(), key=lambda t: (t[0][0], t[0][1])):
        tex = render_group_longtable(exp, lang, aud_map, args.caption_prefix, args.label_prefix, args.sort)
        if not tex:
            continue
        outfile = out_dir / f"exp_{exp}_{lang}_combined.tex"
        outfile.write_text(tex, encoding="utf-8")
        index_lines.append(r"\input{" + str(outfile) + "}")
        print(f"[ok] wrote {outfile}")

    if index_lines:
        idx = out_dir / "tables_index.tex"
        idx.write_text("% Auto-generated list of combined tables\n" + "\n".join(index_lines) + "\n", encoding="utf-8")
        print(f"[ok] wrote {idx}")

if __name__ == "__main__":
    main()
