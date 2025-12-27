# tests/unit/test_cache_manager.py
import matplotlib.pyplot as plt
from core.utils.cache_manager import save_plot, save_json, get_recent_files

def test_cache_manager():
    print("🧪 Тест: cache_manager")
    
    # === 1. Сохранение графика ===
    print("\n🔍 Тест 1: Сохранение matplotlib-графика")
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 2])
    path = save_plot(fig, prefix="test_plot")
    print(f"✅ График сохранён: {path}")

    # === 2. Сохранение JSON ===
    print("\n🔍 Тест 2: Сохранение JSON")
    data = {"temperature": [1, 2, 3], "humidity": [40, 50, 60]}
    json_path = save_json(data, prefix="test_data")
    print(f"✅ JSON сохранён: {json_path}")

    # === 3. Получение последних файлов ===
    print("\n🔍 Тест 3: Получение последних файлов")
    recent_png = get_recent_files(ext="png", limit=5)
    recent_json = get_recent_files(ext="json", limit=5)
    print(f"🖼️  PNG файлы: {recent_png}")
    print(f"📄 JSON файлы: {recent_json}")

    print("\n✅ Все тесты cache_manager пройдены!")

if __name__ == "__main__":
    test_cache_manager()