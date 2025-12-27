# -*- coding: utf-8 -*-
"""
Генератор HTML-карт через Scattermapbox (Heatmap + Contour + Points).
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from core.utils.cache_manager import save_html

def generate_pressure_map_html(
    lats: list,
    lons: list,
    pressures: list,
    title: str = "Карта давления (Scattermapbox)",
    map_style: str = "carto-positron",
    pressure_colormap: str = "Viridis",
    pressure_opacity: float = 0.6,
    contour_color: str = "white",
    contour_width: int = 2,
    contour_interval: float = 2.0,
    contour_opacity: float = 1.0,
    point_color: str = "red",
    point_size: int = 8,
    point_opacity: float = 0.8,
    output_prefix: str = "pressure_map_scatter"
) -> str:
    """
    Генерирует HTML-карту давления через Scattermapbox (Heatmap + Contour + Points).
    """
    if len(lats) != len(lons) or len(lats) != len(pressures):
        raise ValueError("Длины lats, lons и pressures должны совпадать")

    df = pd.DataFrame({"lat": lats, "lon": lons, "pressure": pressures})

    # === ИНТЕРПОЛЯЦИЯ ===
    print("🔄 Интерполируем давление...")
    grid_lat = np.linspace(min(lats), max(lats), 100)
    grid_lon = np.linspace(min(lons), max(lons), 100)
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)

    points = df[["lat", "lon"]].values
    values = df["pressure"].values
    grid_pressure = griddata(
        points, values, (grid_lat_mesh, grid_lon_mesh),
        method="cubic",
        fill_value=np.nan
    )

    print(f"✅ Интерполяция завершена. Min: {np.nanmin(grid_pressure):.2f}, Max: {np.nanmax(grid_pressure):.2f}")

    # === ИЗВЛЕЧЕНИЕ ИЗОЛИНИЙ ЧЕРЕЗ MATPLOTLIB ===
    print("🔍 Извлекаем изолинии...")
    import matplotlib.pyplot as plt2
    cs = plt2.contour(grid_lon_mesh, grid_lat_mesh, grid_pressure, levels=np.arange(
        np.nanmin(grid_pressure), np.nanmax(grid_pressure), contour_interval
    ))
    plt2.close()

    # === ПОДГОТОВКА ДАННЫХ ДЛЯ SCATTERMAPBOX ===
    fig = go.Figure()

    # === СЛОЙ 1: ГРАДИЕНТ (через точки с цветом) ===
    # Преобразуем сетку в список точек для Heatmap-эффекта
    lat_flat = grid_lat_mesh.flatten()
    lon_flat = grid_lon_mesh.flatten()
    pressure_flat = grid_pressure.flatten()

    # Убираем NaN
    mask = ~np.isnan(pressure_flat)
    lat_clean = lat_flat[mask]
    lon_clean = lon_flat[mask]
    pressure_clean = pressure_flat[mask]

    fig.add_trace(go.Scattermapbox(
        lat=lat_clean,
        lon=lon_clean,
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=3,  # мелкие точки для градиента
            color=pressure_clean,
            colorscale=pressure_colormap,
            showscale=True,
            colorbar=dict(title="гПа"),
            opacity=pressure_opacity
        ),
        name="Давление (градиент)",
        hovertemplate="<b>Давление</b>: %{marker.color:.2f} гПа<br>" +
                      "Широта: %{lat:.2f}<br>" +
                      "Долгота: %{lon:.2f}<extra></extra>"
    ))

    # === СЛОЙ 2: ИЗОЛИНИИ (из matplotlib) ===
    for i, collection in enumerate(cs.collections):
        for path in collection.get_paths():
            vertices = path.vertices  # (N, 2) -> (lon, lat)
            if len(vertices) > 1:
                fig.add_trace(go.Scattermapbox(
                    lat=vertices[:, 1],  # lat
                    lon=vertices[:, 0],  # lon
                    mode='lines',
                    line=dict(
                        width=contour_width,
                        color=contour_color,
                        opacity=contour_opacity
                    ),
                    name=f"Изолиния {i}",
                    hoverinfo='skip',  # не показываем подсказки для линий
                    showlegend=False
                ))

    # === СЛОЙ 3: ТОЧКИ ИЗМЕРЕНИЙ ===
    fig.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode='markers+text',
        text=df["pressure"].round(1),
        textposition="top center",
        marker=dict(
            size=point_size,
            color=point_color,
            opacity=point_opacity
        ),
        name="Измерения",
        hovertemplate="<b>Точка</b><br>" +
                      "Давление: %{text} гПа<br>" +
                      "Широта: %{lat:.2f}<br>" +
                      "Долгота: %{lon:.2f}<extra></extra>"
    ))

    # === НАСТРОЙКА КАРТЫ ===
    fig.update_layout(
        title=title,
        mapbox=dict(
            style=map_style,
            center=dict(lat=np.mean(lats), lon=np.mean(lons)),
            zoom=8
        ),
        width=900,
        height=700,
        hovermode='closest'
    )

    # === СОХРАНЕНИЕ ===
    html_path = save_html(fig.to_html(), prefix=output_prefix)
    print(f"✅ Карта давления (HTML) сохранена: {html_path}")
    return html_path