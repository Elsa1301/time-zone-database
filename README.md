# time_zone_database

Offline access to a curated set of IANA time zone identifiers with ISO 3166-1
alpha-2 country codes and English labels. No network, no system tzdata files,
no third-party packages.

## Usage

```python
from time_zone_database import (
    TimeZoneDatabase,
    TimeZone,
    get_time_zone,
    all_time_zones,
    search_time_zones,
)

# Quick lookups via module-level helpers.
tz = get_time_zone("Europe/London")
print(tz.identifier)      # "Europe/London"
print(tz.country_codes)   # ("GB",)
print(tz.label)           # "London, United Kingdom"

# Or hold your own instance.
db = TimeZoneDatabase()
us_zones = db.search(country_code="US")
for z in us_zones:
    print(z.identifier, z.label)
```

## Why this exists

The problem: you need a stable list of time zone identifiers and their
country associations in an environment with no network and no guarantee that
system `tzdata` is installed or current. `zoneinfo.available_timezones()`
reflects whatever the host happens to have, which varies across containers and
operating systems and is empty on a minimal Windows install.

The trade-off: this library ships a **static, curated** list of roughly 60
zones rather than the full ~400 IANA publishes. We include the principal zone
for each country plus common sub-national zones (US has six, Australia has
five, Canada has three). If you need every identifier IANA has ever defined,
this is the wrong library and you should bundle `tzdata` directly.

## Edges you will hit

- **No UTC offsets.** A zone's offset depends on the date of observation (DST,
  historical changes). We do not provide offsets because a single number would
  be wrong half the year for most zones. Use `datetime.timezone.utc` or
  `zoneinfo.ZoneInfo` for date-aware conversion.

- **Lookup is case-sensitive.** `get_time_zone("europe/london")` returns
  `None`. IANA identifiers are case-sensitive in practice; we do not normalize.

- **Country code search is case-sensitive.** `search(country_code="us")`
  returns nothing. Codes are ISO 3166-1 alpha-2, uppercase. We do not uppercase
  for you because that would hide a typo.

- **Labels are English-only prose.** They are not localized and not
  guaranteed stable across versions. Use the identifier as the canonical key;
  treat the label as display text only.

- **`UTC` has no country codes.** Its `country_codes` tuple is empty.

## Exports

- `TimeZoneDatabase` — the database class. Methods: `get(identifier)`,
  `all()`, `search(country_code=None, label_contains=None)`.
- `TimeZone` — immutable record. Properties: `identifier`, `country_codes`,
  `label`.
- `get_time_zone(identifier)` — module-level lookup, returns `TimeZone | None`.
- `all_time_zones()` — module-level list, sorted by identifier.
- `search_time_zones(country_code=None, label_contains=None)` — module-level
  search.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

