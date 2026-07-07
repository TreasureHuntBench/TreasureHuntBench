"""Deterministic encoding codecs used by encoded-message levels.

Every codec is a pure, reversible function pair. A level instruction always
names the codec and its parameters explicitly; the agent never has to guess.
"""

import base64 as _b64
import string
from typing import List

_UPPER = string.ascii_uppercase

_MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}
_MORSE_REV = {v: k for k, v in _MORSE.items()}


def base64_encode(text: str) -> str:
    return _b64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode(text: str) -> str:
    return _b64.b64decode(text.encode("ascii")).decode("utf-8")


def hex_encode(text: str) -> str:
    return text.encode("utf-8").hex().upper()


def hex_decode(text: str) -> str:
    return bytes.fromhex(text).decode("utf-8")


def caesar_encode(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch.isalpha():
            alpha = _UPPER if ch.isupper() else string.ascii_lowercase
            out.append(alpha[(alpha.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


def caesar_decode(text: str, shift: int) -> str:
    return caesar_encode(text, -shift)


def vigenere_encode(text: str, key: str) -> str:
    out, ki = [], 0
    key = key.upper()
    for ch in text:
        if ch.isalpha():
            shift = _UPPER.index(key[ki % len(key)])
            alpha = _UPPER if ch.isupper() else string.ascii_lowercase
            out.append(alpha[(alpha.index(ch) + shift) % 26])
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def vigenere_decode(text: str, key: str) -> str:
    out, ki = [], 0
    key = key.upper()
    for ch in text:
        if ch.isalpha():
            shift = _UPPER.index(key[ki % len(key)])
            alpha = _UPPER if ch.isupper() else string.ascii_lowercase
            out.append(alpha[(alpha.index(ch) - shift) % 26])
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def morse_encode(text: str) -> str:
    words = text.upper().split(" ")
    return " / ".join(" ".join(_MORSE[c] for c in w if c in _MORSE)
                      for w in words)


def morse_decode(text: str) -> str:
    words = text.strip().split(" / ")
    return " ".join("".join(_MORSE_REV[sym] for sym in w.split(" ") if sym)
                    for w in words)


def acrostic_encode(message: str, filler_titles: List[str]) -> List[str]:
    """Build titles whose first characters spell ``message``.

    ``filler_titles`` supplies the rest of each title (must be >= len(message)).
    """
    if len(filler_titles) < len(message):
        raise ValueError("not enough filler titles")
    out = []
    for ch, filler in zip(message, filler_titles):
        out.append(ch + filler)
    return out


def acrostic_decode(titles: List[str]) -> str:
    return "".join(t[0] for t in titles if t)


CODECS = {
    "base64": (base64_encode, base64_decode),
    "hex": (hex_encode, hex_decode),
}
