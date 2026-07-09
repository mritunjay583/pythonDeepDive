# Part 3 — Grapheme Clusters and Normalization

## 3.1 The Grapheme Problem

A **grapheme cluster** is what a human perceives as a single "character." It may consist of multiple Unicode code points:

```python
# Single code point graphemes (simple):
"A"   # U+0041 → 1 code point, 1 grapheme ✓
"é"   # U+00E9 → 1 code point, 1 grapheme ✓ (precomposed)

# Multi-code-point graphemes:
"é"   # U+0065 U+0301 → 2 code points, 1 grapheme! (e + combining acute)
"क्ष"   # U+0915 U+094D U+0937 → 3 code points, 1 grapheme (Devanagari)
"🇯🇵"  # U+1F1EF U+1F1F5 → 2 code points, 1 grapheme (flag)
"👨‍👩‍👧‍👦" # 7 code points (4 people + 3 ZWJ), 1 grapheme

# Python sees CODE POINTS, not graphemes:
len("é")              # 1 (precomposed U+00E9)
len("e\u0301")        # 2 (decomposed: e + combining acute)
# Both LOOK identical on screen!
```

---

## 3.2 Combining Characters

Unicode defines **combining characters** — code points that visually attach to the preceding base character:

```
Category Mn (Mark, Nonspacing): combining accents, diacritics
  U+0301: COMBINING ACUTE ACCENT (´)
  U+0302: COMBINING CIRCUMFLEX ACCENT (^)
  U+0303: COMBINING TILDE (~)
  U+0327: COMBINING CEDILLA (¸)
  U+0308: COMBINING DIAERESIS (¨)

Example constructions:
  'e' + U+0301 → 'é' (e with acute)
  'n' + U+0303 → 'ñ' (n with tilde)
  'u' + U+0308 → 'ü' (u with diaeresis)
  'a' + U+0301 + U+0308 → 'ä́' (a with acute AND diaeresis — stacks!)
```

### The Canonical Equivalence Problem

```python
s1 = "\u00E9"        # U+00E9: LATIN SMALL LETTER E WITH ACUTE (precomposed)
s2 = "e\u0301"       # U+0065 + U+0301: e + COMBINING ACUTE (decomposed)

s1 == s2             # FALSE! Different code point sequences!
len(s1)              # 1
len(s2)              # 2

# But they LOOK identical and represent the SAME logical character!
# This is where normalization becomes critical.
```

---

## 3.3 Unicode Normalization Forms

Unicode defines 4 normalization forms to handle equivalence:

### NFC (Canonical Decomposition + Canonical Composition)
```
Strategy: Compose characters whenever possible (use precomposed forms)
"e\u0301" → NFC → "\u00E9" (compose to precomposed é)
"A\u030A" → NFC → "\u00C5" (compose to precomposed Å)

This is what Python's unicodedata.normalize('NFC', s) does.
NFC is the RECOMMENDED form for storage and comparison.
```

### NFD (Canonical Decomposition)
```
Strategy: Decompose everything to base + combining characters
"\u00E9" → NFD → "e\u0301" (decompose é to e + combining acute)
"\u00C5" → NFD → "A\u030A" (decompose Å to A + combining ring)

Used by: macOS file systems (HFS+ stores filenames in NFD!)
```

### NFKC (Compatibility Decomposition + Canonical Composition)
```
Strategy: NFC + resolve compatibility equivalences
"ﬁ" (U+FB01, fi ligature) → NFKC → "fi" (two separate chars)
"①" (U+2460, circled 1) → NFKC → "1"
"Ω" (U+2126, Ohm sign) → NFKC → "Ω" (U+03A9, Greek capital omega)

More aggressive — loses some distinctions. Used for search/comparison.
```

### NFKD (Compatibility Decomposition)
```
Strategy: NFD + resolve compatibility equivalences
Most aggressive decomposition.
```

### Python's normalize():
```python
import unicodedata

s1 = "\u00E9"           # precomposed é
s2 = "e\u0301"          # decomposed e + combining acute

# Normalize to same form for comparison:
unicodedata.normalize('NFC', s1) == unicodedata.normalize('NFC', s2)  # True!
unicodedata.normalize('NFD', s1) == unicodedata.normalize('NFD', s2)  # True!

# For identifier comparison, Python uses NFKC internally:
# PEP 3131: identifiers are normalized to NFKC
```

---

## 3.4 Why Python Doesn't Auto-Normalize

CPython stores strings **exactly as created** — no automatic normalization:

```python
s = "e\u0301"
len(s)  # 2 — CPython stores both code points as-is
# It does NOT auto-normalize to NFC (which would give len=1)
```

Reasons:
1. **Performance**: Normalizing every string on creation is expensive
2. **Fidelity**: Some applications need to preserve the exact code point sequence
3. **Round-trip**: Encoding then decoding must return the exact same bytes
4. **Explicitness**: Python's design philosophy — explicit normalization via `unicodedata.normalize()`

---

## 3.5 Grapheme Clusters in Practice

### Python's `str` operates on code points:
```python
s = "👨‍👩‍👧‍👦"   # Family emoji
len(s)        # 7 (code points)
s[0]          # '👨' (just the man emoji)
list(s)       # ['👨', '\u200d', '👩', '\u200d', '👧', '\u200d', '👦']
```

### For grapheme-aware operations, use third-party libraries:
```python
# pip install grapheme
import grapheme
s = "👨‍👩‍👧‍👦"
grapheme.length(s)  # 1 (one grapheme cluster)
list(grapheme.graphemes(s))  # ['👨\u200d👩\u200d👧\u200d👦']
```

### The regex module (not re) has grapheme support:
```python
import regex  # pip install regex
s = "Hëllo 👨‍👩‍👧‍👦 World"
graphemes = regex.findall(r'\X', s)  # \X matches one grapheme cluster
len(graphemes)  # 14 (H, ë, l, l, o, ' ', 👨‍👩‍👧‍👦, ' ', W, o, r, l, d)
```

---

## 3.6 Impact on String Operations

```python
# Reversing a string with combining characters:
s = "café"  # If 'é' is decomposed: "cafe\u0301"
s[::-1]     # "\u0301efac" — the combining accent detaches! Visually broken!

# Safe reversal requires grapheme awareness:
import grapheme
"".join(reversed(list(grapheme.graphemes(s))))

# Case conversion and normalization:
"ß".upper()       # "SS" (German sharp s → len changes from 1 to 2!)
"ﬁ".upper()       # "FI" (fi ligature → len changes from 1 to 2!)
```

---

## 3.7 Interview Questions — Part 3

**Q1**: What is a grapheme cluster?
**A**: What a human perceives as a single "character." May consist of one or more Unicode code points. Python's str operates on code points, not graphemes — len() counts code points.

**Q2**: Why does `"café" == "cafe\u0301"` return False?
**A**: Different code point sequences. "café" uses precomposed é (U+00E9), while "cafe\u0301" uses e + combining acute. Normalize both to NFC or NFD before comparing.

**Q3**: What normalization form should you use for string comparison?
**A**: NFC (Canonical Decomposition + Composition) for most purposes. NFKC for search (also resolves compatibility equivalences). Python identifiers use NFKC.

**Q4**: Why doesn't CPython auto-normalize strings?
**A**: Performance cost, fidelity preservation (exact code point sequence matters for some use cases), and Python's explicit design philosophy.

**Q5**: What can go wrong when reversing a string with combining characters?
**A**: The combining character (e.g., U+0301 acute accent) ends up before a different base character or at the start of the string, visually "detaching" from its intended base. Grapheme-aware reversal is needed.
