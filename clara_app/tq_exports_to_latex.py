#!/usr/bin/env python3
"""
tq_exports_to_latex.py
----------------------
Convert one or more C‑LARA text‑questionnaire export ZIPs (created by
`tq_export_csv(..., kind="all")`) into LaTeX tables you can \\input in the paper.

Supports:
  • Whole‑book summary tables (book × question means + overall + #raters)
  • Page‑level summary tables (book × question means aggregated across pages,
    plus pages_rated and (if present) n_raters)

Usage:
  python tq_exports_to_latex.py path/to/exports_dir_or_zip [... more paths ...] \
         --out tex_tables --sort avg --book --page

Notes:
  • You can pass a directory (it will scan for *.zip) and/or specific *.zip files.
  • Output .tex files are written to --out (created if needed).
  • Each ZIP produces up to two files: <base>_book.tex and <base>_page.tex.
  • A tiny index file tables_index.tex is created with \\input lines for convenience.
"""

import argparse, io, re, sys, zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

import os.path

import pprint

trace = True
#trace = False

# -------------------------- helpers ---------------------

def absolute_file_name(pathname):
    pathname = os.path.abspath(os.path.expandvars(pathname))
        
    ## Replace backslashes with forward slashes
    return pathname.replace('\\', '/')

def escape_tex(s: str) -> str:
    if s is None:
        return ""
    # conservative escaping
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

def find_q_mean_cols(df: pd.DataFrame) -> List[str]:
    """
    Return question-mean columns in order: ['q1_mean','q2_mean',...].
    Works even if there are gaps: it sorts by embedded integer.
    """
    qcols = [c for c in df.columns if re.fullmatch(r"q\d+_mean", c)]
    qcols.sort(key=lambda c: int(re.findall(r'\d+', c)[0]))
    return qcols

def read_csv_from_zip(zf: zipfile.ZipFile, name_like: str) -> Optional[pd.DataFrame]:
    """
    Return first CSV whose name contains name_like (case-insensitive).
    """
    name_like_lower = name_like.lower()
    for zi in zf.infolist():
        if zi.filename.lower().endswith('.csv') and name_like_lower in zi.filename.lower():
            with zf.open(zi.filename) as fp:
                return pd.read_csv(fp)
    return None

def read_csv_from_zip_by_parts(zf: zipfile.ZipFile, *parts: str) -> Optional[pd.DataFrame]:
    """
    Find the first CSV inside `zf` whose lowercased path contains *all* `parts`.
    Example: parts ('book','matrix') -> matches 'tq_7_book_matrix.csv'.
    Returns a DataFrame or None if not found.
    """
    parts = tuple(p.lower() for p in parts)
    for name in zf.namelist():
        low = name.lower()
        if low.endswith(".csv") and all(p in low for p in parts):
            with zf.open(name) as f:
                return pd.read_csv(f)
    return None


def load_exports(path: Path) -> List[Tuple[str, Optional[pd.DataFrame], Optional[pd.DataFrame]]]:
    """
    For a path that is a directory or a single zip, return a list of tuples:
      (base_name, df_book, df_page)
    where base_name is a safe stem for output file names.

    df_book   := book-level matrix (rows = books, cols = Q1.. + avg)
    df_page   := page-level matrix (rows = books, cols = Q1.. + pages rated)
    """
    if trace: print(f'--- Calling load_exports on {path}')
    results: List[Tuple[str, Optional[pd.DataFrame], Optional[pd.DataFrame]]] = []

    if path.is_dir():
        zips = sorted(p for p in path.glob("*.zip"))
    elif path.is_file() and path.suffix.lower() == ".zip":
        zips = [path]
    else:
        raise SystemExit(f"Path is neither a directory of zips nor a .zip file: {path}")

    if not zips:
        print(f"[warn] No .zip files found in {path}", file=sys.stderr)
        return results

    for z in zips:
        base = z.stem  # file name without .zip
        with zipfile.ZipFile(z, "r") as zf:
            # Prefer the new names:
            df_book = read_csv_from_zip_by_parts(zf, "book", "matrix")
            df_page = read_csv_from_zip_by_parts(zf, "page", "matrix")

            # Fallbacks (older naming in some branches)
            if df_book is None:
                df_book = (read_csv_from_zip_by_parts(zf, "summary", "book")
                           or read_csv_from_zip_by_parts(zf, "book", "summary")
                           or read_csv_from_zip_by_parts(zf, "book"))
            if df_page is None:
                df_page = (read_csv_from_zip_by_parts(zf, "summary", "page")
                           or read_csv_from_zip_by_parts(zf, "page", "summary")
                           or read_csv_from_zip_by_parts(zf, "page"))

        if df_book is None and df_page is None:
            print(f"[warn] No usable CSVs found in {z.name}", file=sys.stderr)

        results.append((base, df_book, df_page))

    if trace:
        kinds = [(b, df_b is not None, df_p is not None) for (b, df_b, df_p) in results]
        print(f'--- load_exports: found (base, has_book, has_page) = {kinds}')
        pprint.pprint(results)
    return results


def sort_rows(df: pd.DataFrame, qcols: List[str], mode: str = "avg") -> pd.DataFrame:
    """Sort by avg (desc) or alpha of title. Adds/uses 'Avg' column if needed."""
    df = df.copy()
    if mode == "alpha":
        return df.sort_values(by="book_title", key=lambda s: s.str.lower())

    # Default: sort by overall_mean (or computed mean of qcols) descending
    if "overall_mean" in df.columns:
        key = df["overall_mean"]
    else:
        # compute across qcols (skip NaNs)
        key = df[qcols].mean(axis=1, skipna=True)
    return df.iloc[key.sort_values(ascending=False).index]

def make_href(title: str, url: str) -> str:
    if pd.isna(url) or not url or not isinstance(url, str):
        return escape_tex(title)
    return r"\href{" + url + "}{" + r"\emph{" + escape_tex(title) + r"}}"

def render_book_table(df: pd.DataFrame, caption: str, label: str) -> str:
    """
    Render whole-book table: Title | Q1..Qk | Avg | n_eval
    """
    if df is None or df.empty:
        return "% (no whole-book data)\n"

    qcols = find_q_mean_cols(df)
    df2 = df.copy()

    # ensure numeric for formatting
    for c in qcols + ["overall_mean"]:
        if c in df2.columns:
            df2[c] = pd.to_numeric(df2[c], errors="coerce")

    df2 = sort_rows(df2, qcols, mode="avg")

    header_q = " & ".join([c.replace("q", "Q").replace("_mean", "") for c in qcols])
    lines = []
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{@{}l" + "r" * (len(qcols) + 2) + r"@{}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Title} & " + header_q + r" & \textbf{Avg.} & \textbf{\#raters}\\")
    lines.append(r"\midrule")

    for _, row in df2.iterrows():
        title = make_href(row.get("book_title",""), row.get("book_url",""))
        qvals = []
        for c in qcols:
            v = row.get(c)
            qvals.append(f"{v:.2f}" if pd.notna(v) else r"--")
        avg = row.get("overall_mean")
        avg_s = f"{avg:.2f}" if pd.notna(avg) else r"--"
        n_eval = int(row.get("n_eval")) if pd.notna(row.get("n_eval")) else 0
        lines.append(title + " & " + " & ".join(qvals) + f" & {avg_s} & {n_eval}" + r"\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if caption:
        lines.append(r"\caption{" + escape_tex(caption) + r"}")
    if label:
        lines.append(r"\label{" + escape_tex(label) + r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"

def render_page_table(df: pd.DataFrame, caption: str, label: str) -> str:
    """
    Render page-level table: Title | Q1..Qk | Avg | Pages | (optional) #raters
    Expects columns: book_title, book_url, pages_rated (int), qN_mean...
    Optionally uses n_raters if present.
    """
    if df is None or df.empty:
        return "% (no page-level data)\n"

    qcols = find_q_mean_cols(df)
    df2 = df.copy()

    for c in qcols:
        df2[c] = pd.to_numeric(df2[c], errors="coerce")

    # compute row avg across qcols
    df2["row_avg"] = df2[qcols].mean(axis=1, skipna=True)

    df2 = sort_rows(df2, qcols, mode="avg")

    has_n_raters = "n_raters" in df2.columns
    header_q = " & ".join([c.replace("q", "Q").replace("_mean", "") for c in qcols])

    # build col spec
    extra_cols = 2 + (1 if has_n_raters else 0)  # Avg + Pages + maybe #raters
    lines = []
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{@{}l" + "r" * (len(qcols) + extra_cols) + r"@{}}")
    lines.append(r"\toprule")
    head = r"\textbf{Title} & " + header_q + r" & \textbf{Avg.} & \textbf{Pages}"
    if has_n_raters:
        head += r" & \textbf{\#raters}"
    head += r"\\"
    lines.append(head)
    lines.append(r"\midrule")

    for _, row in df2.iterrows():
        title = make_href(row.get("book_title",""), row.get("book_url",""))
        qvals = []
        for c in qcols:
            v = row.get(c)
            qvals.append(f"{v:.2f}" if pd.notna(v) else r"--")
        avg_s = f"{row['row_avg']:.2f}" if pd.notna(row["row_avg"]) else r"--"
        pages = int(row.get("pages_rated")) if pd.notna(row.get("pages_rated")) else 0
        cells = [title] + qvals + [avg_s, str(pages)]
        if has_n_raters:
            nr = int(row.get("n_raters")) if pd.notna(row.get("n_raters")) else 0
            cells.append(str(nr))
        lines.append(" & ".join(cells) + r"\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if caption:
        lines.append(r"\caption{" + escape_tex(caption) + r"}")
    if label:
        lines.append(r"\label{" + escape_tex(label) + r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"

# -------------------------- main --------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="ZIP file(s) or a directory containing ZIPs")
    ap.add_argument("--out", default="tex_tables", help="Output directory for .tex files")
    ap.add_argument("--sort", choices=["avg", "alpha"], default="avg", help="Row ordering")
    ap.add_argument("--book", action="store_true", help="Generate whole-book tables")
    ap.add_argument("--page", action="store_true", help="Generate page-level tables")
    ap.add_argument("--caption-prefix", default="", help="Prefix for captions")
    ap.add_argument("--label-prefix", default="tab:", help="Prefix for LaTeX labels")
    args = ap.parse_args()

    want_book = args.book or (not args.book and not args.page)
    want_page = args.page or (not args.book and not args.page)

    out_dir = Path(absolute_file_name(args.out))
    out_dir.mkdir(parents=True, exist_ok=True)

    index_lines = []
    for p in args.paths:
        for base, df_book, df_page in load_exports(Path(absolute_file_name(p))):
            safe_base = re.sub(r"[^A-Za-z0-9_.-]+", "_", base)

            if want_book and df_book is not None and not df_book.empty:
                tex = render_book_table(df_book, caption=f"{args.caption_prefix}Whole‑book questionnaire summary ({safe_base})",
                                        label=f"{args.label_prefix}{safe_base}_book")
                out_file = out_dir / f"{safe_base}_book.tex"
                out_file.write_text(tex, encoding="utf-8")
                index_lines.append(r"\input{" + str(out_file) + "}")
                print(f"[ok] wrote {out_file}")

            if want_page and df_page is not None and not df_page.empty:
                tex = render_page_table(df_page, caption=f"{args.caption_prefix}Page‑level questionnaire summary ({safe_base})",
                                        label=f"{args.label_prefix}{safe_base}_page")
                out_file = out_dir / f"{safe_base}_page.tex"
                out_file.write_text(tex, encoding="utf-8")
                index_lines.append(r"\input{" + str(out_file) + "}")
                print(f"[ok] wrote {out_file}")

    # write a minimal index .tex to include all generated tables
    if index_lines:
        idx = out_dir / "tables_index.tex"
        idx.write_text("% Auto-generated list of tables\n" + "\n".join(index_lines) + "\n", encoding="utf-8")
        print(f"[ok] wrote {idx}")

if __name__ == "__main__":
    main()
