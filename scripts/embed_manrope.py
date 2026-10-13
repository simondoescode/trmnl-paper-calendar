"""Refresh the self-contained Manrope font block from checked-in assets."""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "full.liquid"
BEGIN = "{% comment %}BEGIN EMBEDDED MANROPE"
END = "/* END EMBEDDED MANROPE */"


def embed():
    font = (ROOT / "assets/fonts/manrope-latin.woff2").read_bytes()
    if font[:4] != b"wOF2" or len(font) > 100_000:
        raise SystemExit("Expected a small Manrope WOFF2 font")
    licence = "\n".join(line.rstrip() for line in (ROOT / "assets/fonts/OFL-Manrope.txt").read_text(encoding="utf-8").splitlines()).strip()
    encoded = base64.b64encode(font).decode("ascii")
    block = (f"{BEGIN}\n{licence}\nEND MANROPE LICENCE{{% endcomment %}}\n"
             "<style>\n/* BEGIN EMBEDDED MANROPE */\n"
             "@font-face {font-family:Manrope;font-style:normal;font-weight:400 800;"
             "font-display:block;"
             f"src:url(data:font/woff2;base64,{encoded}) format('woff2');"
             "unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;}\n"
             f"{END}\n</style>\n")
    markup = TEMPLATE.read_text(encoding="utf-8")
    if BEGIN in markup:
        start = markup.index(BEGIN)
        finish = markup.index("</style>", markup.index(END, start)) + len("</style>\n")
        markup = markup[:start] + block + markup[finish:]
    else:
        markup = markup.replace("<style>", block + "\n<style>", 1)
    TEMPLATE.write_text(markup, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    embed()
