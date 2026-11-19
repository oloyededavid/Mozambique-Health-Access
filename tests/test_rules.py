"""Facility inclusion rules."""
import pytest


@pytest.mark.parametrize("amenity,healthcare,expected", [
    ("hospital", None, "hospital"), ("clinic", None, "facility"), ("doctors", "doctor", "facility"),
    ("health_post", None, "facility"), ("pharmacy", None, "pharmacy"), ("dentist", "dentist", None),
    (None, "hospital", "hospital"), (None, "centre", "facility"), (None, "pharmacy", "pharmacy"), (None, None, None),
    ("clinic", "hospital", "facility"),     # amenity is read first
    (" Hospital ", None, "hospital"),
])
def test_osm_class(access, amenity, healthcare, expected):
    assert access.osm_class(amenity, healthcare) == expected


def test_maina_hospitals(access):
    assert access.maina_is_hospital("Hospital Rural")
    assert access.maina_is_hospital("Hospital Distrital")
    assert not access.maina_is_hospital("Centro de Saúde Rural II")
    assert not access.maina_is_hospital(None)


@pytest.mark.parametrize("status,all_,func,fully", [
    ("Fully Functioning", True, True, True), ("Partially Functioning", True, True, False),
    ("Non-Functioning", True, False, False), (None, True, True, False),
])
def test_herams_rules(access, status, all_, func, fully):
    assert access.herams_keep(status, "all") is all_
    assert access.herams_keep(status, "functioning") is func
    assert access.herams_keep(status, "fully") is fully
    with pytest.raises(ValueError):
        access.herams_keep(status, "other")


def test_text_cleaning(access):
    assert access.fix_mojibake("SaÃºde") == "Saúde"
    assert access.norm_text("  CS  Saúde-Nahadje ") == "cs saude nahadje"
    assert access.norm_text("Zambézia") == access.norm_text("Zambezia")
    assert access.quarter_key("2024 - Q2") == 20242 and access.quarter_key("2023 - Q4") < access.quarter_key("2024 - Q1")
    assert access.quarter_key(None) == -1
