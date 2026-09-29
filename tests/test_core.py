import unittest

from time_zone_database import (
    TimeZoneDatabase,
    TimeZone,
    get_time_zone,
    all_time_zones,
    search_time_zones,
)


class TestTimeZoneRecord(unittest.TestCase):
    def test_properties_return_construction_values(self):
        tz = TimeZone("Europe/London", ("GB",), "London, United Kingdom")
        self.assertEqual(tz.identifier, "Europe/London")
        self.assertEqual(tz.country_codes, ("GB",))
        self.assertEqual(tz.label, "London, United Kingdom")

    def test_country_codes_is_a_tuple_not_a_list(self):
        tz = TimeZone("UTC", [], "Coordinated Universal Time")
        self.assertIsInstance(tz.country_codes, tuple)
        self.assertEqual(tz.country_codes, ())

    def test_immutable_setattr_raises(self):
        tz = TimeZone("UTC", (), "Coordinated Universal Time")
        with self.assertRaises(AttributeError):
            tz.identifier = "x"

    def test_immutable_new_attribute_raises(self):
        # A typo should not silently create a new slot.
        tz = TimeZone("UTC", (), "Coordinated Universal Time")
        with self.assertRaises(AttributeError):
            tz.identifer = "x"

    def test_immutable_delattr_raises(self):
        tz = TimeZone("UTC", (), "Coordinated Universal Time")
        with self.assertRaises(AttributeError):
            del tz.identifier

    def test_equality_compares_all_fields(self):
        a = TimeZone("Europe/London", ("GB",), "London, United Kingdom")
        b = TimeZone("Europe/London", ("GB",), "London, United Kingdom")
        c = TimeZone("Europe/London", ("GB",), "Different label")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_equality_returns_notimplemented_for_other_types(self):
        tz = TimeZone("UTC", (), "Coordinated Universal Time")
        self.assertNotEqual(tz, "UTC")
        self.assertNotEqual(tz, 42)

    def test_hashable_and_usable_in_set(self):
        a = TimeZone("UTC", (), "Coordinated Universal Time")
        b = TimeZone("UTC", (), "Coordinated Universal Time")
        self.assertEqual(len({a, b}), 1)

    def test_repr_contains_identifier(self):
        tz = TimeZone("Europe/London", ("GB",), "London, United Kingdom")
        self.assertIn("Europe/London", repr(tz))


class TestTimeZoneDatabaseGet(unittest.TestCase):
    def setUp(self):
        self.db = TimeZoneDatabase()

    def test_known_identifier_returns_record(self):
        tz = self.db.get("Europe/London")
        self.assertIsNotNone(tz)
        self.assertEqual(tz.identifier, "Europe/London")
        self.assertIn("GB", tz.country_codes)

    def test_utc_has_no_country_codes(self):
        tz = self.db.get("UTC")
        self.assertIsNotNone(tz)
        self.assertEqual(tz.country_codes, ())

    def test_unknown_identifier_returns_none(self):
        self.assertIsNone(self.db.get("Mars/Olympus_Mons"))

    def test_lookup_is_case_sensitive(self):
        # IANA identifiers are case-sensitive; we do not normalize.
        self.assertIsNotNone(self.db.get("Europe/London"))
        self.assertIsNone(self.db.get("europe/london"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.db.get(""))

    def test_non_string_identifier_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.db.get(123)
        with self.assertRaises(TypeError):
            self.db.get(None)


class TestTimeZoneDatabaseAll(unittest.TestCase):
    def setUp(self):
        self.db = TimeZoneDatabase()

    def test_all_returns_list_sorted_by_identifier(self):
        zones = self.db.all()
        identifiers = [z.identifier for z in zones]
        self.assertEqual(identifiers, sorted(identifiers))

    def test_all_returns_fresh_list_each_call(self):
        a = self.db.all()
        b = self.db.all()
        self.assertIsNot(a, b)
        a.append("sentinel")
        self.assertNotIn("sentinel", b)

    def test_all_returns_time_zone_instances(self):
        zones = self.db.all()
        for z in zones:
            self.assertIsInstance(z, TimeZone)


class TestTimeZoneDatabaseSearch(unittest.TestCase):
    def setUp(self):
        self.db = TimeZoneDatabase()

    def test_search_by_country_code_us_returns_multiple(self):
        results = self.db.search(country_code="US")
        identifiers = {z.identifier for z in results}
        self.assertIn("America/New_York", identifiers)
        self.assertIn("America/Chicago", identifiers)
        self.assertIn("America/Los_Angeles", identifiers)
        self.assertIn("America/Indiana/Indianapolis", identifiers)
        self.assertIn("Pacific/Honolulu", identifiers)
        # Zones belonging to other countries must not leak in.
        for z in results:
            self.assertIn("US", z.country_codes)

    def test_search_by_country_code_case_sensitive(self):
        # We deliberately do not uppercase; "us" should match nothing.
        results = self.db.search(country_code="us")
        self.assertEqual(results, [])

    def test_search_by_unknown_country_code_returns_empty(self):
        self.assertEqual(self.db.search(country_code="ZZ"), [])

    def test_search_by_label_contains_case_insensitive(self):
        results = self.db.search(label_contains="london")
        identifiers = {z.identifier for z in results}
        self.assertIn("Europe/London", identifiers)

    def test_search_by_label_contains_exact_case(self):
        results = self.db.search(label_contains="London")
        identifiers = {z.identifier for z in results}
        self.assertIn("Europe/London", identifiers)

    def test_search_by_label_contains_no_match_returns_empty(self):
        self.assertEqual(self.db.search(label_contains="Atlantis"), [])

    def test_search_with_no_filters_returns_all(self):
        no_filters = self.db.search()
        all_zones = self.db.all()
        self.assertEqual(no_filters, all_zones)

    def test_search_combines_filters_with_and(self):
        results = self.db.search(country_code="US", label_contains="Anchorage")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].identifier, "America/Anchorage")

    def test_search_combined_filters_where_one_excludes_all_returns_empty(self):
        results = self.db.search(country_code="US", label_contains="Tokyo")
        self.assertEqual(results, [])

    def test_search_non_string_country_code_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.db.search(country_code=123)

    def test_search_non_string_label_contains_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.db.search(label_contains=123)

    def test_search_results_are_sorted_by_identifier(self):
        results = self.db.search(country_code="US")
        identifiers = [z.identifier for z in results]
        self.assertEqual(identifiers, sorted(identifiers))


class TestModuleLevelFunctions(unittest.TestCase):
    def test_get_time_zone_returns_record(self):
        tz = get_time_zone("Asia/Tokyo")
        self.assertIsNotNone(tz)
        self.assertEqual(tz.identifier, "Asia/Tokyo")
        self.assertEqual(tz.country_codes, ("JP",))

    def test_get_time_zone_unknown_returns_none(self):
        self.assertIsNone(get_time_zone("Nonexistent/Zone"))

    def test_all_time_zones_returns_sorted_list(self):
        zones = all_time_zones()
        self.assertGreater(len(zones), 0)
        identifiers = [z.identifier for z in zones]
        self.assertEqual(identifiers, sorted(identifiers))

    def test_search_time_zones_by_country_code(self):
        results = search_time_zones(country_code="JP")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].identifier, "Asia/Tokyo")

    def test_search_time_zones_no_filters(self):
        results = search_time_zones()
        self.assertGreater(len(results), 0)


class TestDataIntegrity(unittest.TestCase):
    def test_no_duplicate_identifiers(self):
        # If the source table has a duplicate, TimeZoneDatabase.__init__
        # raises. Constructing one here is the test.
        db = TimeZoneDatabase()
        seen = set()
        for z in db.all():
            self.assertNotIn(z.identifier, seen)
            seen.add(z.identifier)

    def test_every_identifier_is_non_empty_string(self):
        for z in TimeZoneDatabase().all():
            self.assertIsInstance(z.identifier, str)
            self.assertGreater(len(z.identifier), 0)

    def test_every_country_code_is_uppercase_alpha2(self):
        for z in TimeZoneDatabase().all():
            for cc in z.country_codes:
                self.assertEqual(len(cc), 2)
                self.assertTrue(cc.isalpha())
                self.assertEqual(cc, cc.upper())

    def test_every_label_is_non_empty_string(self):
        for z in TimeZoneDatabase().all():
            self.assertIsInstance(z.label, str)
            self.assertGreater(len(z.label), 0)

    def test_identifier_uses_slash_separator(self):
        # Every non-UTC identifier follows the Area/Location convention.
        for z in TimeZoneDatabase().all():
            if z.identifier == "UTC":
                continue
            self.assertIn("/", z.identifier)


if __name__ == "__main__":
    unittest.main()
