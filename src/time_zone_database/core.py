"""Core implementation of the offline IANA time zone database.

Design decisions
----------------

1. **Static data, not a parser.** The IANA tzdata distribution is a set of text
   files plus compiled zone1970.tab. Bundling a parser would mean shipping a
   partial, always-out-of-date implementation. Instead we ship a curated list
   of the zones that Python's standard library actually exposes via
   ``zoneinfo.available_timezones()``, plus the metadata that is stable and
   useful offline: the ISO 3166-1 alpha-2 country code(s) each zone belongs to
   and a human-readable label.

2. **Country codes, not names.** We store ISO 3166-1 alpha-2 codes because
   they are stable, short, and unambiguous. Resolving them to display names is
   a presentation concern and belongs in the caller. This keeps the library
   free of locale and political questions about country naming.

3. **No clock.** Nothing here reads the wall clock. UTC offsets are not
   provided because they depend on the date of observation (DST, historical
   changes). Providing a single offset would be misleading; providing a
   date-dependent offset calculator would be a different library. We
   deliberately do not try.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple


# A representative subset of the IANA Time Zone Database.
#
# This is not every identifier zoneinfo has ever published — it is the set
# that is both (a) present in Python's ``zoneinfo.available_timezones()`` on
# a stock CPython install and (b) carries a stable country association in
# zone1970.tab. We include the principal zones for each region plus the
# common aliases callers actually look up by name.
#
# Each entry: (identifier, country_codes, label)
#   - identifier: the exact IANA string, e.g. "Europe/London".
#   - country_codes: tuple of ISO 3166-1 alpha-2 codes. Some zones (e.g.
#     "America/Indiana/Indianapolis") are sub-national but still belong to
#     exactly one country; others like "Europe/London" cover GB and are
#     also the de-facto zone for the Isle of Man (IM) and Guernsey (GG).
#   - label: a short, stable, English description. This is NOT localized.
_TIME_ZONES: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("Africa/Abidjan", ("CI",), "Abidjan, Côte d'Ivoire"),
    ("Africa/Accra", ("GH",), "Accra, Ghana"),
    ("Africa/Addis_Ababa", ("ET",), "Addis Ababa, Ethiopia"),
    ("Africa/Algiers", ("DZ",), "Algiers, Algeria"),
    ("Africa/Cairo", ("EG",), "Cairo, Egypt"),
    ("Africa/Casablanca", ("MA",), "Casablanca, Morocco"),
    ("Africa/Johannesburg", ("ZA",), "Johannesburg, South Africa"),
    ("Africa/Lagos", ("NG",), "Lagos, Nigeria"),
    ("Africa/Nairobi", ("KE",), "Nairobi, Kenya"),
    ("Africa/Tunis", ("TN",), "Tunis, Tunisia"),
    ("America/Anchorage", ("US",), "Anchorage, Alaska, United States"),
    ("America/Argentina/Buenos_Aires", ("AR",), "Buenos Aires, Argentina"),
    ("America/Chicago", ("US",), "Chicago, United States"),
    ("America/Denver", ("US",), "Denver, United States"),
    ("America/Halifax", ("CA",), "Halifax, Canada"),
    ("America/Indiana/Indianapolis", ("US",), "Indianapolis, Indiana, United States"),
    ("America/Los_Angeles", ("US",), "Los Angeles, United States"),
    ("America/Mexico_City", ("MX",), "Mexico City, Mexico"),
    ("America/New_York", ("US",), "New York, United States"),
    ("America/Phoenix", ("US",), "Phoenix, Arizona, United States"),
    ("America/Sao_Paulo", ("BR",), "São Paulo, Brazil"),
    ("America/Toronto", ("CA",), "Toronto, Canada"),
    ("America/Vancouver", ("CA",), "Vancouver, Canada"),
    ("Asia/Bangkok", ("TH",), "Bangkok, Thailand"),
    ("Asia/Dubai", ("AE",), "Dubai, United Arab Emirates"),
    ("Asia/Hong_Kong", ("HK",), "Hong Kong"),
    ("Asia/Jerusalem", ("IL",), "Jerusalem, Israel"),
    ("Asia/Karachi", ("PK",), "Karachi, Pakistan"),
    ("Asia/Kolkata", ("IN",), "Kolkata, India"),
    ("Asia/Seoul", ("KR",), "Seoul, South Korea"),
    ("Asia/Shanghai", ("CN",), "Shanghai, China"),
    ("Asia/Singapore", ("SG",), "Singapore"),
    ("Asia/Tokyo", ("JP",), "Tokyo, Japan"),
    ("Australia/Adelaide", ("AU",), "Adelaide, Australia"),
    ("Australia/Brisbane", ("AU",), "Brisbane, Australia"),
    ("Australia/Melbourne", ("AU",), "Melbourne, Australia"),
    ("Australia/Perth", ("AU",), "Perth, Australia"),
    ("Australia/Sydney", ("AU",), "Sydney, Australia"),
    ("Europe/Amsterdam", ("NL",), "Amsterdam, Netherlands"),
    ("Europe/Berlin", ("DE",), "Berlin, Germany"),
    ("Europe/Brussels", ("BE",), "Brussels, Belgium"),
    ("Europe/Dublin", ("IE",), "Dublin, Ireland"),
    ("Europe/Helsinki", ("FI",), "Helsinki, Finland"),
    ("Europe/Istanbul", ("TR",), "Istanbul, Türkiye"),
    ("Europe/Lisbon", ("PT",), "Lisbon, Portugal"),
    ("Europe/London", ("GB",), "London, United Kingdom"),
    ("Europe/Madrid", ("ES",), "Madrid, Spain"),
    ("Europe/Moscow", ("RU",), "Moscow, Russia"),
    ("Europe/Oslo", ("NO",), "Oslo, Norway"),
    ("Europe/Paris", ("FR",), "Paris, France"),
    ("Europe/Rome", ("IT",), "Rome, Italy"),
    ("Europe/Stockholm", ("SE",), "Stockholm, Sweden"),
    ("Europe/Warsaw", ("PL",), "Warsaw, Poland"),
    ("Europe/Zurich", ("CH",), "Zurich, Switzerland"),
    ("Pacific/Auckland", ("NZ",), "Auckland, New Zealand"),
    ("Pacific/Honolulu", ("US",), "Honolulu, Hawaii, United States"),
    ("Pacific/Tahiti", ("PF",), "Tahiti, French Polynesia"),
    ("UTC", (), "Coordinated Universal Time"),
)


class TimeZone:
    """An immutable IANA time zone record.

    Instances are created by the library; callers should not construct them
    directly because the library is the source of truth for which identifiers
    exist. We enforce immutability by overriding ``__setattr__`` so that a
    typo like ``tz.identfier = "x"`` raises instead of silently creating a
    new attribute.
    """

    __slots__ = ("_identifier", "_country_codes", "_label")

    def __init__(
        self,
        identifier: str,
        country_codes: Sequence[str],
        label: str,
    ) -> None:
        object.__setattr__(self, "_identifier", identifier)
        object.__setattr__(self, "_country_codes", tuple(country_codes))
        object.__setattr__(self, "_label", label)

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def country_codes(self) -> Tuple[str, ...]:
        return self._country_codes

    @property
    def label(self) -> str:
        return self._label

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"TimeZone is immutable; cannot set attribute {name!r}"
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"TimeZone is immutable; cannot delete attribute {name!r}"
        )

    def __repr__(self) -> str:
        return f"TimeZone(identifier={self._identifier!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeZone):
            return NotImplemented
        return (
            self._identifier == other._identifier
            and self._country_codes == other._country_codes
            and self._label == other._label
        )

    def __hash__(self) -> int:
        return hash((self._identifier, self._country_codes, self._label))


class TimeZoneDatabase:
    """Offline, read-only lookup over a bundled set of IANA time zones.

    The database is built once at construction and never mutated. Lookups are
    O(1) for identifier fetches and O(n) for searches, which is fine because
    n is on the order of 60.
    """

    def __init__(self) -> None:
        self._by_identifier: Dict[str, TimeZone] = {}
        for identifier, country_codes, label in _TIME_ZONES:
            # If the source table ever gains a duplicate, we want to know at
            # import time, not silently return the last one from a dict.
            if identifier in self._by_identifier:
                raise ValueError(f"Duplicate time zone identifier in source data: {identifier}")
            self._by_identifier[identifier] = TimeZone(identifier, country_codes, label)

    def get(self, identifier: str) -> Optional[TimeZone]:
        """Return the ``TimeZone`` for *identifier*, or ``None`` if unknown.

        Lookup is case-sensitive and exact. IANA identifiers are case-sensitive
        in practice (``America/Indiana/Indianapolis`` is not
        ``america/indiana/indianapolis``), so we do not normalize. Callers who
        want case-insensitive lookup should lowercase both sides themselves;
        we will not guess.
        """
        if not isinstance(identifier, str):
            raise TypeError(
                f"identifier must be str, got {type(identifier).__name__}"
            )
        return self._by_identifier.get(identifier)

    def all(self) -> List[TimeZone]:
        """Return every known ``TimeZone``, sorted by identifier.

        A fresh list is returned each call so callers can safely mutate it
        without affecting the database's internal state.
        """
        return [self._by_identifier[k] for k in sorted(self._by_identifier)]

    def search(
        self,
        *,
        country_code: Optional[str] = None,
        label_contains: Optional[str] = None,
    ) -> List[TimeZone]:
        """Return zones matching *all* given filters, sorted by identifier.

        - ``country_code``: an ISO 3166-1 alpha-2 code. Matched case-sensitively
          and exactly against the zone's country codes. We do not uppercase
          for you because that would hide a typo like ``"us"`` when you meant
          ``"US"``; better to return nothing and let the caller notice.
        - ``label_contains``: a substring matched case-insensitively against
          the human-readable label. Case-insensitive here because labels are
          prose, not identifiers.

        Passing no filters returns every zone, same as ``all()``.
        """
        if country_code is not None and not isinstance(country_code, str):
            raise TypeError(
                f"country_code must be str or None, got {type(country_code).__name__}"
            )
        if label_contains is not None and not isinstance(label_contains, str):
            raise TypeError(
                f"label_contains must be str or None, got {type(label_contains).__name__}"
            )

        label_needle = label_contains.lower() if label_contains is not None else None

        results: List[TimeZone] = []
        for identifier in sorted(self._by_identifier):
            tz = self._by_identifier[identifier]
            if country_code is not None and country_code not in tz.country_codes:
                continue
            if label_needle is not None and label_needle not in tz.label.lower():
                continue
            results.append(tz)
        return results


# Module-level convenience singletons. The database is immutable and cheap to
# build (a dict of ~60 entries), so a shared instance is safe. These exist so
# callers can do ``from time_zone_database import get_time_zone`` without
# instantiating anything, which is the common case for a quick lookup.
_DEFAULT_DB = TimeZoneDatabase()


def get_time_zone(identifier: str) -> Optional[TimeZone]:
    """Look up a time zone by IANA identifier using a shared database."""
    return _DEFAULT_DB.get(identifier)


def all_time_zones() -> List[TimeZone]:
    """Return every known time zone using a shared database."""
    return _DEFAULT_DB.all()


def search_time_zones(
    *,
    country_code: Optional[str] = None,
    label_contains: Optional[str] = None,
) -> List[TimeZone]:
    """Search time zones using a shared database. See ``TimeZoneDatabase.search``."""
    return _DEFAULT_DB.search(country_code=country_code, label_contains=label_contains)
