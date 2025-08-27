##from bs4 import BeautifulSoup
##import re, html as pyhtml
##
##def _pick_parser():
##    for p in ("lxml", "html5lib", "html.parser"):
##        try:
##            # Cheap probe: bs4 will raise if parser not available
##            BeautifulSoup("<div></div>", p)
##            return p
##        except Exception:
##            continue
##    return "html.parser"
##
##_PARSER = _pick_parser()
##
##def html_to_text(html: str, ruby_format: str = "paren", max_blank_lines: int = 1, bullets: bool = True) -> str:
##    soup = BeautifulSoup(html or "", _PARSER)
##
##    for tag in soup(["script", "style", "noscript"]):
##        tag.decompose()
##
##    # Expand <ruby>…<rt>…</rt></ruby>
##    for ruby in soup.find_all("ruby"):
##        bases = [rb.get_text(" ", strip=True) for rb in ruby.find_all("rb")] or []
##        readings = [rt.get_text(" ", strip=True) for rt in ruby.find_all("rt")] or []
##        base = " ".join(bases).strip() or ruby.get_text(" ", strip=True)
##        reading = " ".join(readings).strip()
##        if base and reading:
##            replacement = (
##                f"{base} ({reading})" if ruby_format == "paren"
##                else f"{base} [{reading}]" if ruby_format == "brackets"
##                else f"{base} /{reading}/"
##            )
##        else:
##            replacement = base or reading
##        ruby.replace_with(replacement)
##
##    for br in soup.find_all(["br", "hr"]):
##        br.replace_with("\n")
##
##    # Bullet lists
##    if bullets:
##        for li in soup.find_all("li"):
##            text = li.get_text(" ", strip=True)
##            li.clear()
##            li.append(soup.new_string(f"• {text}"))
##            li.insert_after(soup.new_string("\n"))
##
##    # Simple table readability
##    for tr in soup.find_all("tr"):
##        tr.insert_after(soup.new_string("\n"))
##    for td in soup.find_all(["td", "th"]):
##        td.insert_after(soup.new_string("\t"))
##
##    text = soup.get_text(separator="\n")
##    text = pyhtml.unescape(text)
##    text = re.sub(r"\r\n?|\u2028|\u2029", "\n", text)
##    text = re.sub(r"[ \t]+\n", "\n", text)
##    text = re.sub(r"[ \t]{2,}", " ", text)
##    text = re.sub(r"\n{2,}", "\n" * max_blank_lines, text).strip()
##    return text

# text_utils.py
from bs4 import BeautifulSoup
import re, html as pyhtml

def _pick_parser():
    for p in ("lxml", "html5lib", "html.parser"):
        try:
            BeautifulSoup("<div></div>", p)
            return p
        except Exception:
            continue
    return "html.parser"

_PARSER = _pick_parser()

_NO_SPACE_BEFORE = set(list(".,;:!?%)]}…»)”’"))  # attach to previous
_NO_SPACE_AFTER  = set(list("([{«“‘$"))          # attach to next
_CONTRACTIONS    = {"'s","’s","'re","’re","'ve","’ve","'ll","’ll","n't","n’t","'d","’d"}

def _join_tokens(tokens: list[str]) -> str:
    out = []
    prev = ""
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        low = tok.lower()

        if not out:
            out.append(tok)
        elif low in _CONTRACTIONS or tok in _NO_SPACE_BEFORE or tok.startswith("'") or tok.startswith("’"):
            # attach to previous token
            out[-1] = out[-1] + tok
        elif prev in _NO_SPACE_AFTER or prev in {"$", "£", "€"}:
            # no leading space (e.g., after opening paren/quote or currency)
            out.append(tok)
        elif tok in {"-", "–", "—"}:
            # surround dashes with spaces if not already
            if out[-1].endswith((" ", "—", "–", "-")):
                out.append(tok)
            else:
                out.append(" " + tok)
        else:
            out.append(" " + tok)
        prev = tok

    text = "".join(out)

    # Light normalisation
    text = re.sub(r"\s+([?!;,.:])", r"\1", text)          # no space before punctuation
    text = re.sub(r"(\() +", r"\1", text)                 # no space after (
    text = re.sub(r" +(\))", r"\1", text)                 # no space before )
    text = re.sub(r"\s+([’”»])", r"\1", text)             # no space before closing quotes
    text = re.sub(r"([«“‘])\s+", r"\1", text)             # no space after opening quotes
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

def html_to_text(
    html: str,
    *,
    scope_selector: str = "#main-text-pane",   # restrict to the story body
    ruby_format: str = "paren",                # "paren" | "brackets" | "slash"
    segment_separator: str = "\n",             # join segments with newline
) -> str:
    soup = BeautifulSoup(html or "", _PARSER)

    # Prefer scoping to the main text; fallback to full document
    scope = soup.select_one(scope_selector) or soup

    # Drop non-content/UI elements inside scope
    for sel in [
        "header", "footer", "nav", ".nav-bar",
        "button", "audio", "source", "iframe",
        ".concordance-pane-wrapper", "#concordance-pane", ".concordance-iframe",
        ".speaker-icon", ".translation-icon",
        "script", "style", "noscript", "link", "meta"
    ]:
        for el in scope.select(sel):
            el.decompose()

    # Expand <ruby> base + reading
    for ruby in scope.find_all("ruby"):
        bases = [rb.get_text(" ", strip=True) for rb in ruby.find_all("rb")] or []
        readings = [rt.get_text(" ", strip=True) for rt in ruby.find_all("rt")] or []
        base = " ".join(bases).strip() or ruby.get_text(" ", strip=True)
        reading = " ".join(readings).strip()
        if base and reading:
            replacement = (
                f"{base} ({reading})" if ruby_format == "paren"
                else f"{base} [{reading}]" if ruby_format == "brackets"
                else f"{base} /{reading}/"
            )
        else:
            replacement = base or reading
        ruby.replace_with(replacement)

    # Prefer a token-aware path if we have C-LARA word spans
    segments = scope.select(".segment")
    if segments:
        seg_texts = []
        for seg in segments:
            words = [w.get_text("", strip=True) for w in seg.select(".word")]
            if words:
                seg_texts.append(_join_tokens(words))
        if seg_texts:
            text = segment_separator.join(seg_texts)
        else:
            # Fallback: no .word children (e.g., header-only segment)
            text = scope.get_text(separator="\n")
    else:
        # Generic fallback
        # Convert line-breakish tags before extraction
        for br in scope.find_all(["br", "hr"]):
            br.replace_with("\n")
        text = scope.get_text(separator="\n")

    # Final tidy-up
    text = pyhtml.unescape(text)
    text = re.sub(r"\r\n?|\u2028|\u2029", "\n", text)     # normalise newlines
    text = re.sub(r"[ \t]+\n", "\n", text)                # trim line-end spaces
    text = re.sub(r"\n{3,}", "\n\n", text).strip()        # cap blank-lines at 1
    return text

