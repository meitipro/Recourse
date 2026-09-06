"""
Stage 1 of the linter: deterministic, free, and first.

Three checks that need no model and cost nothing, so a promise that cannot pass
them never spends money. Each returns the specific check it failed, because
"not judgeable" without a reason is the kind of answer this project exists to
refuse.

The categories come from the deployed gate's own wording: judgeable means a
count, a bound, a named field or a freshness limit; not judgeable means only a
quality, such as accurate, high quality or reliable. Stage 1 is a cheap
approximation of that sentence. Stage 2 asks the sentence itself.
"""

from __future__ import annotations

import re
from typing import NamedTuple

MIN_LENGTH = 20
MAX_LENGTH = 500


class Check(NamedTuple):
    ok: bool
    failed_check: str | None
    reason: str


#: Words that describe a quality and nothing checkable. A promise made only of
#: these (plus stopwords) is the textbook unjudgeable promise.
QUALITY_WORDS = {
    "accurate", "fast", "quick", "reliable", "high", "quality", "good", "best",
    "great", "excellent", "precise", "correct", "timely", "robust", "secure",
    "comprehensive", "complete", "up-to-date", "real-time", "realtime", "fresh",
    "latest", "trusted", "trustworthy", "verified", "premium", "professional",
    "consistent", "stable", "efficient", "optimal", "superior", "top", "clean",
    "rich", "detailed", "relevant", "useful", "helpful", "responsive", "smooth",
    "solid", "strong", "powerful", "advanced", "modern", "smart", "intelligent",
}

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with", "is", "are",
    "be", "very", "always", "all", "any", "our", "your", "we", "you", "it",
    "this", "that", "on", "at", "by", "as", "from", "will", "can",
}

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
    "million", "dozen", "half", "single",
}

UNITS = {
    "second", "seconds", "sec", "secs", "s", "minute", "minutes", "min", "mins",
    "hour", "hours", "hr", "hrs", "day", "days", "week", "weeks", "month",
    "months", "year", "years", "ms", "millisecond", "milliseconds", "byte",
    "bytes", "kb", "mb", "gb", "kilobyte", "kilobytes", "megabyte", "megabytes",
    "percent", "%", "item", "items", "result", "results", "row", "rows",
    "entry", "entries", "record", "records", "character", "characters", "char",
    "chars", "token", "tokens", "word", "words", "page", "pages", "venue",
    "venues", "source", "sources", "exchange", "exchanges", "decimal", "decimals",
    "digit", "digits", "point", "points", "usd", "eur", "gbp", "gen", "eth", "btc",
}

#: Phrases that bound a quantity or a time, whichever number sits beside them.
BOUND_PHRASES = (
    "at least", "at most", "no more than", "no fewer than", "no older than",
    "not older than", "within", "under", "over", "older than", "newer than",
    "in the last", "in the past", "since", "before", "after", "up to",
    "maximum", "minimum", "max", "min", "exactly", "every", "each", "per",
    "less than", "more than", "fewer than", "greater than", "between",
)

#: Concrete fields and outcomes a response can be held to. "The full text of
#: the requested document, or an explicit not found" has no number in it and is
#: still judgeable, because both halves name something a reader can check for.
FIELD_WORDS = {
    "text", "title", "url", "urls", "link", "links", "id", "ids", "price",
    "prices", "timestamp", "timestamps", "status", "field", "fields", "error",
    "body", "document", "documents", "list", "json", "key", "keys", "value",
    "values", "code", "header", "headers", "name", "names", "date", "dates",
    "time", "amount", "total", "count", "sum", "hash", "signature", "address",
    "pair", "pairs", "symbol", "symbols", "ticker", "tickers", "quote", "quotes",
    "filing", "filings", "summary", "abstract", "transcript", "image", "images",
    "file", "files", "schema", "format", "language", "currency", "unit",
    "explicit", "not found", "404", "200", "empty", "null", "none", "boolean",
    "true", "false", "sorted", "ascending", "descending", "unique", "deduplicated",
    "match", "matches", "matching", "requested", "exact", "verbatim", "full",
}

WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def has_number(text: str, tokens: list[str]) -> bool:
    if re.search(r"\d", text):
        return True
    return any(token in NUMBER_WORDS for token in tokens)


def has_unit(tokens: list[str]) -> bool:
    """
    A unit with a number beside it: "five seconds", "ten items", "24 hours".

    A bare unit is not a measurement. "High quality results" has results in it
    and measures nothing, and the first version of this let it through on
    exactly that word.
    """
    for index, token in enumerate(tokens):
        if token not in UNITS or index == 0:
            continue
        before = tokens[index - 1]
        if before in NUMBER_WORDS or re.fullmatch(r"\d+(\.\d+)?%?", before):
            return True
    return False


def has_bound(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BOUND_PHRASES)


DETERMINERS = {
    "the", "a", "an", "each", "every", "its", "their", "your", "this", "that",
    "any", "all", "per", "one", "no", "same", "exact", "requested", "matching",
}


def has_field(text: str, tokens: list[str]) -> bool:
    """
    A named field is one that is referred to, not one that floats: "the full
    text", "a title", "an explicit not found". A determiner up to two words
    before the field word is the tell. "Great prices, always" has a field word
    and names nothing, and the first version of this passed it.
    """
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("not found", "http 200", "http 404", "or an error")):
        return True
    for index, token in enumerate(tokens):
        if token not in FIELD_WORDS:
            continue
        window = tokens[max(0, index - 3) : index]
        if any(word in DETERMINERS for word in window):
            return True
    return False


def has_named_source(text: str) -> bool:
    """
    A proper noun that is not the first word of a sentence, or a domain.

    "Binance, Coinbase and Kraken" is a checkable list of venues. The first word
    of a sentence is excluded because every sentence starts with a capital.
    """
    if re.search(r"\b[a-z0-9-]+\.(com|io|org|net|gov|xyz|ai)\b", text.lower()):
        return True
    sentences = re.split(r"[.!?]\s+", text.strip())
    for sentence in sentences:
        parts = sentence.split()
        for part in parts[1:]:
            cleaned = part.strip(",;:()\"'")
            if len(cleaned) > 1 and cleaned[0].isupper() and cleaned[1:].islower():
                if cleaned.lower() not in STOPWORDS:
                    return True
    return False


def precheck(promise: str) -> Check:
    """
    The three deterministic checks, in the order they are cheapest to explain.

    Length first, because a promise outside the bounds cannot be stored on
    chain anyway. Adjective-only second, because it is the clearest failure
    and names itself. Measurable term last, because it is the one a nearly
    good promise fails, and the reason tells the seller what to add.
    """
    text = promise.strip()
    if len(text) < MIN_LENGTH:
        return Check(False, "length", f"Too short to hold a checkable claim: {len(text)} characters, minimum {MIN_LENGTH}.")
    if len(text) > MAX_LENGTH:
        return Check(False, "length", f"Longer than the contract stores: {len(text)} characters, maximum {MAX_LENGTH}.")

    tokens = words(text)
    content = [token for token in tokens if token not in STOPWORDS]
    if content and all(token in QUALITY_WORDS for token in content):
        return Check(
            False,
            "adjectives only",
            "Every word describes a quality and none names a thing to check. "
            "A judge given this can only invent a standard the seller never agreed to.",
        )

    if not (
        has_number(text, tokens)
        or has_unit(tokens)
        or has_bound(text)
        or has_field(text, tokens)
        or has_named_source(text)
    ):
        return Check(
            False,
            "no measurable term",
            "Nothing here is measurable: no number, unit, time bound, count, "
            "named field or named source. Say what arrives and how fresh, "
            "not how good.",
        )

    return Check(True, None, "Passes the deterministic checks; judgeability is the next question.")
