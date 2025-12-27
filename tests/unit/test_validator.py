# -*- coding: utf-8 -*-
"""
Тесты для core/utils/validator.py
"""
from core.utils.validator import validate_coordinates, validate_user_id, validate_telegram_location


def test_validate_coordinates():
    assert validate_coordinates(55.75, 37.62) == True
    assert validate_coordinates("55.75", "37.62") == True
    assert validate_coordinates(91, 0) == False
    assert validate_coordinates(0, 181) == False
    assert validate_coordinates("invalid", 0) == False
    print("✅ test_validate_coordinates passed")


def test_validate_user_id():
    assert validate_user_id(123) == True
    assert validate_user_id("456") == True
    assert validate_user_id(0) == False
    assert validate_user_id(-1) == False
    assert validate_user_id("abc") == False
    print("✅ test_validate_user_id passed")


def test_validate_telegram_location():
    assert validate_telegram_location({"latitude": 55.75, "longitude": 37.62}) == True
    assert validate_telegram_location({"latitude": 91, "longitude": 0}) == False
    assert validate_telegram_location({"latitude": 55.75}) == False
    assert validate_telegram_location("invalid") == False
    print("✅ test_validate_telegram_location passed")


if __name__ == "__main__":
    test_validate_coordinates()
    test_validate_user_id()
    test_validate_telegram_location()