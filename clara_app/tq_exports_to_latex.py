#!/usr/bin/env python3
"""
tq_exports_to_latex.py — robust column autodetection

Converts one or more C-LARA text-questionnaire export ZIPs (created by
`tq_export_csv(..., kind="all")`) into LaTeX tables you can \input.

Usage:
  python tq_exports_to_latex.py path/or/zip [...more...] --out tex_tables
Options:
  --book   only whole-book tables
  --page   only page-level tables
  --sort {avg,alpha}  (default avg)
"""

import argparse, io, re, sys, zipfile, os, pprint
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

trace = True
# trace = False

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

def read_csv_from_zip_by_parts(zf: zipfile.ZipFile, *parts: str) -> Optional[pd.DataFrame]:
    parts = tuple(p.lower() for p in parts)
    for name in zf.namelist():
        low = name.lower()
        if low.endswith(".csv") and all(p in low for p in parts):
            with zf.open(name) as f:
                return pd.read_csv(f)
    return None

def load_exports(path: Path) -> List[Tuple[str, Optional[pd.DataFrame], Optional[pd.DataFrame]]]:
    """Return [(base_name, df_book_matrix, df_page_matrix), ...]."""
    if trace: print(f'--- Calling load_exports on {path}')
    results = []

    if path.is_dir():
        zips = sorted(p for p in path.glob("*.zip"))
    elif path.is_file() and path.suffix.lower() == ".zip":
        zips = [path]
    else:
        raise SystemExit(f"Path is neither a directory of zips nor a .zip: {path}")

    if not zips:
        print(f"[warn] No .zip files found in {path}", file=sys.stderr)
        return results

    for z in zips:
        base = z.stem
        with zipfile.ZipFile(z, "r") as zf:
            # Preferred names produced by current exporter:
            df_book = read_csv_from_zip_by_parts(zf, "book", "matrix")
            df_page = read_csv_from_zip_by_parts(zf, "page", "matrix")
            # Fallbacks:
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

# ---------- column autodetection ----------

_Q_MEAN_PATS = [
    re.compile(r"^q(\d+)_mean$", re.I),   # q1_mean, q2_mean, ...
    re.compile(r"^Q(\d+)$"),              # Q1, Q2, ...
]
def detect_q_cols(df: pd.DataFrame) -> List[str]:
    # collect all columns matching any pattern, with their numeric index
    found = []
    for col in df.columns:
        for pat in _Q_MEAN_PATS:
            m = pat.fullmatch(str(col))
            if m:
                found.append( (int(m.group(1)), col) )
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

def detect_raters_col(df: pd.DataFrame) -> Optional[str]:
    for name in ["n_raters", "n_eval", "raters", "n_evaluators"]:
        if name in df.columns:
            return name
    return None

# ---------- sorting ----------

def sort_rows(df: pd.DataFrame, qcols: List[str], avg_col: Optional[str], mode: str = "avg") -> pd.DataFrame:
    df = df.copy()
    if mode == "alpha":
        if "book_title" in df.columns:
            return df.sort_values(by="book_title", key=lambda s: s.str.lower())
        return df
    # default: by average descending
    if avg_col and avg_col in df.columns:
        key = pd.to_numeric(df[avg_col], errors="coerce")
    else:
        key = df[qcols].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)
    return df.iloc[key.sort_values(ascending=False).index]

# ---------- rendering ----------

def make_title(title: str) -> str:
    """Return \emph{Title} with proper LaTeX escaping (no hyperlink)."""
    return r"\emph{" + escape_tex(title or "") + r"}"

def render_book_table(df: pd.DataFrame, caption: str, label: str, sort_mode: str = "avg") -> str:
    if df is None or df.empty:
        return "% (no whole-book data)\n"

    qcols   = detect_q_cols(df)
    avg_col = detect_avg_col(df)
    raters_col = detect_raters_col(df)

    df2 = df.copy()
    # numeric coercion
    for c in qcols + ([avg_col] if avg_col else []):
        if c and c in df2.columns:
            df2[c] = pd.to_numeric(df2[c], errors="coerce")

    df2 = sort_rows(df2, qcols, avg_col, mode=sort_mode)

    header_q = " & ".join([re.sub(r"^q(\d+)_mean$", r"Q\1", c) for c in qcols])
    cols_extra = 1 + (1 if raters_col else 0)  # Avg + optional #raters
    lines = []
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{@{}l" + "r" * (len(qcols) + cols_extra) + r"@{}}")
    lines.append(r"\toprule")
    head = r"\textbf{Title}"
    if header_q:
        head += " & " + header_q
    head += r" & \textbf{Avg.}"
    if raters_col:
        head += r" & \textbf{\#raters}"
    head += r"\\"
    lines.append(head)
    lines.append(r"\midrule")

    for _, row in df2.iterrows():
        title = make_title(row.get("book_title", ""))
        qvals = []
        for c in qcols:
            v = row.get(c)
            qvals.append(f"{v:.2f}" if pd.notna(v) else r"--")
        avg_v = row.get(avg_col) if avg_col else pd.Series(qvals, dtype="float").mean()
        avg_s = f"{float(avg_v):.2f}" if pd.notna(avg_v) else r"--"
        cells = [title]
        if qvals: cells += qvals
        cells.append(avg_s)
        if raters_col:
            rv = row.get(raters_col)
            cells.append(str(int(rv)) if pd.notna(rv) else "0")
        lines.append(" & ".join(cells) + r"\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if caption: lines.append(r"\caption{" + escape_tex(caption) + r"}")
    if label:   lines.append(r"\label{" + escape_tex(label) + r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"

def render_page_table(df: pd.DataFrame, caption: str, label: str, sort_mode: str = "avg") -> str:
    if df is None or df.empty:
        return "% (no page-level data)\n"

    qcols      = detect_q_cols(df)
    pages_col  = detect_pages_col(df)
    raters_col = detect_raters_col(df)
    avg_col    = detect_avg_col(df)  # some exports include Avg here too

    df2 = df.copy()
    for c in qcols + ([avg_col] if avg_col else []):
        if c and c in df2.columns:
            df2[c] = pd.to_numeric(df2[c], errors="coerce")

    if not avg_col:
        df2["row_avg"] = df2[qcols].mean(axis=1, skipna=True)
        avg_col = "row_avg"

    df2 = sort_rows(df2, qcols, avg_col, mode=sort_mode)

    header_q = " & ".join([re.sub(r"^q(\d+)_mean$", r"Q\1", c) for c in qcols])
    cols_extra = 2 + (1 if raters_col else 0)  # Avg + Pages + optional #raters
    lines = []
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{@{}l" + "r" * (len(qcols) + cols_extra) + r"@{}}")
    lines.append(r"\toprule")
    head = r"\textbf{Title}"
    if header_q:
        head += " & " + header_q
    head += r" & \textbf{Avg.} & \textbf{Pages}"
    if raters_col:
        head += r" & \textbf{\#raters}"
    head += r"\\"
    lines.append(head)
    lines.append(r"\midrule")

    for _, row in df2.iterrows():
        title = make_title(row.get("book_title", ""))
        qvals = []
        for c in qcols:
            v = row.get(c)
            qvals.append(f"{v:.2f}" if pd.notna(v) else r"--")
        avg_v = row.get(avg_col)
        avg_s = f"{float(avg_v):.2f}" if pd.notna(avg_v) else r"--"
        pages = int(row.get(pages_col)) if (pages_col and pd.notna(row.get(pages_col))) else 0

        cells = [title]
        if qvals: cells += qvals
        cells += [avg_s, str(pages)]
        if raters_col:
            rv = row.get(raters_col)
            cells.append(str(int(rv)) if pd.notna(rv) else "0")
        lines.append(" & ".join(cells) + r"\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if caption: lines.append(r"\caption{" + escape_tex(caption) + r"}")
    if label:   lines.append(r"\label{" + escape_tex(label) + r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="ZIP(s) or a directory with ZIPs")
    ap.add_argument("--out", default="tex_tables", help="Output dir for .tex")
    ap.add_argument("--sort", choices=["avg","alpha"], default="avg")
    ap.add_argument("--book", action="store_true", help="Only whole-book tables")
    ap.add_argument("--page", action="store_true", help="Only page-level tables")
    ap.add_argument("--caption-prefix", default="", help="Caption prefix")
    ap.add_argument("--label-prefix", default="tab:", help="Label prefix")
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
                tex = render_book_table(
                    df_book,
                    caption=f"{args.caption_prefix}Whole-book questionnaire summary ({safe_base})",
                    label=f"{args.label_prefix}{safe_base}_book",
                    sort_mode=args.sort,
                )
                out_file = out_dir / f"{safe_base}_book.tex"
                out_file.write_text(tex, encoding="utf-8")
                index_lines.append(r"\input{" + str(out_file) + "}")
                print(f"[ok] wrote {out_file}")

            if want_page and df_page is not None and not df_page.empty:
                tex = render_page_table(
                    df_page,
                    caption=f"{args.caption_prefix}Page-level questionnaire summary ({safe_base})",
                    label=f"{args.label_prefix}{safe_base}_page",
                    sort_mode=args.sort,
                )
                out_file = out_dir / f"{safe_base}_page.tex"
                out_file.write_text(tex, encoding="utf-8")
                index_lines.append(r"\input{" + str(out_file) + "}")
                print(f"[ok] wrote {out_file}")

    if index_lines:
        idx = out_dir / "tables_index.tex"
        idx.write_text("% Auto-generated list of tables\n" + "\n".join(index_lines) + "\n", encoding="utf-8")
        print(f"[ok] wrote {idx}")

if __name__ == "__main__":
    main()
