# Part 13 — Encoding and Decoding

## 13.1 The Encoding/Decoding Model

```
Python str (code points) ←→ Python bytes (raw bytes)

str.encode(encoding) → bytes    (code points → bytes)
bytes.decode(encoding) → str    (bytes → code points)

                    encode('utf-8')
    "café"  ─────────────────────────→  b'caf\xc3\xa9'
    (str)   ←─────────────────────────  (bytes)
                    decode('utf-8')
```

Internally, this goes through CPython's **codec registry** — a system that maps encoding names to encoder/decoder functions.

---

## 13.2 The Codec Registry

```c
// Python/codecs.c
// At startup, CPython registers built-in codecs:
//   "utf-8", "utf-16", "ascii", "latin-1", "utf-32", etc.

// Registry lookup:
PyObject *_PyCodec_Lookup(const char *encoding)
{
    // 1. Normalize encoding name: "UTF-8" → "utf_8", "Latin1" → "latin_1"
    // 2. Look up in registry dict
    // 3. If not found: try calling registered search functions
    // 4. Return codec info tuple: (encoder, decoder, stream_reader, stream_writer)
}
```

### Fast Paths for Common Encodings:

```c
// encode() dispatcher (simplified):
PyObject *PyUnicode_AsEncodedString(PyObject *unicode, const char *encoding, ...)
{
    // FAST PATH: known C-implemented codecs
    if (encoding == NULL || strcmp(encoding, "utf-8") == 0)
        return _PyUnicode_AsUTF8String(unicode, errors);
    if (strcmp(encoding, "latin-1") == 0 || strcmp(encoding, "iso-8859-1") == 0)
        return _PyUnicode_AsLatin1String(unicode, errors);
    if (strcmp(encoding, "ascii") == 0)
        return _PyUnicode_AsASCIIString(unicode, errors);
    
    // SLOW PATH: general codec registry
    return codec_encode(encoding, unicode, errors);
}
```

The fast paths avoid Python-level function calls entirely — pure C implementation.

---

## 13.3 UTF-8 Encoding Implementation

```c
static PyObject *
_PyUnicode_AsUTF8String(PyObject *unicode, const char *errors)
{
    // FAST PATH: ASCII string IS valid UTF-8!
    if (PyUnicode_IS_ASCII(unicode)) {
        // Just create a bytes object wrapping the same data:
        return PyBytes_FromStringAndSize(
            PyUnicode_DATA(unicode),
            PyUnicode_GET_LENGTH(unicode));
        // O(n) memcpy, no character-by-character conversion!
    }
    
    // Check UTF-8 cache:
    if (PyUnicode_UTF8(unicode)) {
        // Already cached — just wrap existing bytes:
        return PyBytes_FromStringAndSize(
            PyUnicode_UTF8(unicode),
            PyUnicode_UTF8_LENGTH(unicode));
    }
    
    // General path: encode character by character
    int kind = PyUnicode_KIND(unicode);
    void *data = PyUnicode_DATA(unicode);
    Py_ssize_t len = PyUnicode_GET_LENGTH(unicode);
    
    // Allocate max possible size (4 bytes per char worst case):
    char *buffer = PyMem_Malloc(len * 4);
    Py_ssize_t pos = 0;
    
    for (Py_ssize_t i = 0; i < len; i++) {
        Py_UCS4 ch = PyUnicode_READ(kind, data, i);
        if (ch < 0x80) {
            buffer[pos++] = (char)ch;
        } else if (ch < 0x800) {
            buffer[pos++] = 0xC0 | (ch >> 6);
            buffer[pos++] = 0x80 | (ch & 0x3F);
        } else if (ch < 0x10000) {
            buffer[pos++] = 0xE0 | (ch >> 12);
            buffer[pos++] = 0x80 | ((ch >> 6) & 0x3F);
            buffer[pos++] = 0x80 | (ch & 0x3F);
        } else {
            buffer[pos++] = 0xF0 | (ch >> 18);
            buffer[pos++] = 0x80 | ((ch >> 12) & 0x3F);
            buffer[pos++] = 0x80 | ((ch >> 6) & 0x3F);
            buffer[pos++] = 0x80 | (ch & 0x3F);
        }
    }
    
    // Cache the UTF-8 result in the string object:
    // (for non-ASCII compact strings)
    cache_utf8(unicode, buffer, pos);
    
    return PyBytes_FromStringAndSize(buffer, pos);
}
```

---

## 13.4 Error Handlers

```python
# Error handling modes for encode/decode:
"strict"   # Default: raise UnicodeEncodeError/UnicodeDecodeError
"ignore"   # Skip unencodable/undecodable characters
"replace"  # Replace with '?' (encode) or U+FFFD (decode)
"xmlcharrefreplace"  # Encode as &#NNN; XML entity
"backslashreplace"   # Encode as \\uNNNN or \\UNNNNNNNN
"namereplace"        # Encode as \\N{UNICODE NAME}
"surrogateescape"    # Use surrogate code points for undecodable bytes (PEP 383)
"surrogatepass"      # Allow encoding/decoding surrogate code points
```

```python
"café".encode('ascii', errors='strict')       # UnicodeEncodeError!
"café".encode('ascii', errors='ignore')       # b'caf'
"café".encode('ascii', errors='replace')      # b'caf?'
"café".encode('ascii', errors='xmlcharrefreplace')  # b'caf&#233;'
"café".encode('ascii', errors='backslashreplace')   # b'caf\\xe9'
"café".encode('ascii', errors='namereplace')        # b'caf\\N{LATIN SMALL LETTER E WITH ACUTE}'
```

---

## 13.5 The `surrogateescape` Handler (PEP 383)

For handling file paths with invalid encoding on Unix:

```python
# Unix filenames are bytes — may not be valid UTF-8:
import os
filename = b'\xff\xfe.txt'  # Invalid UTF-8 bytes!

# Python must represent this as str (os.listdir returns str):
name = filename.decode('utf-8', errors='surrogateescape')
# name = '\udcff\udcfe.txt'
# Invalid bytes 0xFF, 0xFE mapped to surrogates U+DCFF, U+DCFE

# Round-trip back to bytes:
name.encode('utf-8', errors='surrogateescape')
# b'\xff\xfe.txt'  ← original bytes recovered!
```

---

## 13.6 Interview Questions — Part 13

**Q1**: Why is encoding an ASCII string to UTF-8 nearly free?
**A**: ASCII IS valid UTF-8. CPython just memcpy's the data into a bytes object — no character-by-character conversion needed. O(n) memcpy vs O(n) with per-char branching.

**Q2**: What is the UTF-8 cache and when is it populated?
**A**: Non-ASCII strings have `utf8`/`utf8_length` fields in PyCompactUnicodeObject. They're NULL initially, populated on first encode('utf-8') or C API UTF-8 request. Cached permanently for the string's lifetime.

**Q3**: What does `surrogateescape` error handler do?
**A**: Maps bytes > 127 that can't be decoded to surrogate code points (U+DC80-U+DCFF). Allows lossless round-trip: decode with surrogateescape, then encode with surrogateescape recovers the original bytes. Used for filesystem paths.

**Q4**: What happens when you encode a UCS-4 string to UTF-8?
**A**: Each code point is converted to its UTF-8 byte sequence (1-4 bytes). Characters > U+FFFF produce 4 UTF-8 bytes. The result bytes object is typically SMALLER than the internal 4-byte-per-char representation.
