#!/usr/bin/env python3
"""
Turns your Berghan font file into a small base64 text you can store as a GitHub secret.

    pip install fonttools
    python scripts/prepare_font.py path/to/Berghan.otf

It keeps only the characters the profile needs (Latin letters, digits, punctuation),
writes Berghan-subset.b64.txt next to where you run it, and prints its size.
GitHub secrets can hold up to 48 KB, so the file must be smaller than that.
Do NOT commit the font or the .b64.txt file (both are git-ignored).
"""
import base64
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

if len(sys.argv) != 2:
    sys.exit("usage: python scripts/prepare_font.py path/to/Berghan.otf")

unicodes = list(range(0x20, 0x7F)) + [0x2018, 0x2019, 0x201C, 0x201D, 0x2013, 0x2014, 0x2026, 0x00B7, 0xA0]
font = TTFont(sys.argv[1])
opts = subset.Options()
opts.layout_features = []
opts.notdef_outline = True
opts.name_IDs = [1, 2]
s = subset.Subsetter(opts)
s.populate(unicodes=unicodes)
s.subset(font)
font.flavor = None
font.save("Berghan-subset.font")
data = open("Berghan-subset.font", "rb").read()
b64 = base64.b64encode(data).decode()
open("Berghan-subset.b64.txt", "w").write(b64)
print(f"subset font: {len(data):,} bytes, base64 text: {len(b64):,} characters")
print("OK to use as a secret (limit 48,000)." if len(b64) < 48000 else "Too big for a GitHub secret.")
