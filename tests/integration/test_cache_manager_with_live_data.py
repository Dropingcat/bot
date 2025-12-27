# -*- coding: utf-8 -*-
"""
Тест: обе функции генерации карт — PNG и HTML.
"""

from core.utils.api_client import APIClient
from core.utils.map_generators import (
    generate_static_pressure_map_png,
    generate_interactive_pressure_map_html
)


def test_both_pressure_maps():
    print("🧪 Тест: обе карты давления — PNG и HTML")
    client = APIClient()

    # === Генерация сетки ===
    center_lat, center_lon = 55.75, 37.62
    step, size = 0.25, 5
    lats_base = [center_lat + (i - size // 2) * step for i in range(size)]
    lons_base = [center_lon + (j - size // 2) * step for j in range(size)]

    lats_full, lons_full, pressures = [], [], []
    for lat in lats_base:
        for lon in lons_base:
            lats_full.append(lat)
            lons_full.append(lon)
            data = client.get_weather_data(lat, lon, days=1)
            p = data["hourly"]["pressure_msl"][0] if data else 1013.25
            pressures.append(p)

    print(f"📊 Собрано точек: {len(pressures)}")

    # === Тест 1: Статичная PNG-карта ===
    print("\n🖼️  Генерация PNG-карты...")
    png_path = generate_static_pressure_map_png(
        lats=lats_full,
        lons=lons_full,
        pressures=pressures,
        output_path="отчет/test_pressure_map.png",
        contour_interval=1.0,
        dpi=100
    )

    # === Тест 2: Интерактивная HTML-карта ===
    print("\n🌐 Генерация HTML-карты...")
    html_path = generate_interactive_pressure_map_html(
        lats=lats_full,
        lons=lons_full,
        pressures=pressures,
        title="Интерактивная карта давления",
        contour_interval=1.0,
        output_prefix="test_pressure_map"
    )

    print(f"\n✅ Обе карты готовы:")
    print(f"   PNG: {png_path}")
    print(f"   HTML: {html_path}")


if __name__ == "__main__":
    test_both_pressure_maps()