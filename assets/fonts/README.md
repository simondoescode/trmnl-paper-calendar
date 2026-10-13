# Embedded Manrope

`manrope-latin.woff2` is the Google Fonts v20 Latin variable subset of Manrope, supporting weights 400–800. It is used unchanged, under the [SIL Open Font License](OFL-Manrope.txt).

Source: https://fonts.gstatic.com/s/manrope/v20/xn7gYHE41ni1AdIRggexSg.woff2

SHA-256: `a30ddcd349703aff7464c34bef3fffdff405ee50c113440d7c8693c02d210972`

The font is 24,836 bytes; base64 adds approximately 33 KB to the production template. Latin letters, common punctuation and currency characters use Manrope. Other scripts and unsupported symbols fall back to Inter, Arial or the system sans-serif font.

`scripts/embed_manrope.py` embeds both the font and its full copyright/licence in `src/full.liquid`. This keeps the plugin ZIP self-contained without requiring Terminus to serve additional font assets. Regenerate after a deliberate asset update:

```sh
docker compose run --rm --no-deps --volume .:/plugin --workdir /plugin preview python scripts/embed_manrope.py
```

Run the native browser test and inspect/update screenshot baselines afterwards. The browser check asserts that the actual Manrope font face loaded, not merely that CSS names it. Local native rendering is verified; loading the exported template in a live Terminus instance remains to be verified.
