# tests/unit/test_coordinate_manager.py
from core.utils.coordinate_manager import get_location_name, validate_coordinates, get_city_name

def test_coordinate_manager():
    print("🧪 Тест: coordinate_manager")
    
    # === 1. Валидация ===
    print("\n🔍 Тест 1: Валидация координат")
    assert validate_coordinates(55.75, 37.62) == True
    assert validate_coordinates(99.0, 37.62) == False
    print("✅ Валидация: OK")

    # === 2. Получение названия ===
    print("\n🔍 Тест 2: Получение названия места")
    name = get_location_name(55.75, 37.62)
    print(f"🌍 Название: {name}")
    assert "Москва" in name or "Moscow" in name or "point" in name.lower()
    print("✅ Название: OK")

    # === 3. Получение города ===
    print("\n🔍 Тест 3: Получение города")
    city = get_city_name(55.75, 37.62)
    print(f"🏙️  Город: {city}")
    assert city != "Неизвестный город"
    print("✅ Город: OK")

    print("\n✅ Все тесты coordinate_manager пройдены!")

if __name__ == "__main__":
    test_coordinate_manager()