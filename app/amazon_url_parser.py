from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse, urlunparse


AMAZON_DOMAINS = {
    "amazon.com",
    "amazon.ca",
    "amazon.co.uk",
    "amazon.de",
    "amazon.fr",
    "amazon.it",
    "amazon.es",
    "amazon.co.jp",
    "amazon.com.au",
}

ASIN_PATTERN = re.compile(r"\b(B0[A-Z0-9]{8}|B00[A-Z0-9]{7}|[A-Z0-9]{10})\b", re.I)


def _clean_host(hostname: str | None) -> str:
    host = (hostname or "").lower().strip()
    return host[4:] if host.startswith("www.") else host


def _domain_from_host(host: str) -> str:
    for domain in sorted(AMAZON_DOMAINS, key=len, reverse=True):
        if host == domain or host.endswith(f".{domain}"):
            return domain
    if "amazon." in host:
        return host.split("amazon.", 1)[-1].join(["amazon.", ""])
    return "amazon.com"


def _normalize_url(parsed, asin: str | None, amazon_domain: str | None) -> str:
    if not asin or not amazon_domain:
        return ""
    return urlunparse((parsed.scheme or "https", f"www.{amazon_domain}", f"/dp/{asin}", "", "", ""))


def parse_amazon_url(value: str) -> dict[str, object]:
    original = (value or "").strip()
    warnings: list[str] = []
    if not original:
        return {"originalUrl": original, "isAmazonUrl": False, "warnings": ["empty input"]}

    candidate = original if re.match(r"https?://", original, re.I) else f"https://{original}"
    parsed = urlparse(candidate)
    host = _clean_host(parsed.hostname)
    is_amazon = "amazon." in host or host in AMAZON_DOMAINS
    asin = ""

    path_patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
        r"/([A-Z0-9]{10})(?:[/?]|$)",
    ]
    for pattern in path_patterns:
        match = re.search(pattern, parsed.path, flags=re.I)
        if match:
            asin = match.group(1).upper()
            break

    query = parse_qs(parsed.query)
    if not asin:
        for key in ("asin", "ASIN"):
            if query.get(key):
                asin = str(query[key][0]).upper()
                break

    if not asin:
        match = ASIN_PATTERN.search(original)
        if match:
            asin = match.group(1).upper()
            warnings.append("ASIN parsed by fallback regex.")

    amazon_domain = _domain_from_host(host) if is_amazon else None
    normalized = _normalize_url(parsed, asin or None, amazon_domain)
    if not is_amazon and asin:
        warnings.append("Input is not an Amazon URL; ASIN was parsed from text.")
    if is_amazon and not asin:
        warnings.append("Amazon URL detected but ASIN was not found.")

    return {
        "originalUrl": original,
        "normalizedUrl": normalized or None,
        "asin": asin or None,
        "domain": host or None,
        "amazonDomain": amazon_domain,
        "isAmazonUrl": bool(is_amazon),
        "warnings": warnings,
    }
