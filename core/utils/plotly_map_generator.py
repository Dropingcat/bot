# -*- coding: utf-8 -*-
"""
Генераторы карт давления: статичная (PNG) и интерактивная (HTML).
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import contextily as ctx
import plotly.graph_objects as go
from scipy.interpolate import griddata as gd
from core.utils.cache_manager import save_html


# === ФУНКЦИЯ 1: СТАТИЧНАЯ КАРТА (PNG) ===
def generate_static_pressure_map_png(
    lats: list,
    lons: list,
    pressures: list,
    title: str = "Карта давления (MSLP)",
    output_path: str = "pressure_map_osm.png",
    colormap: str = "viridis",
    contour_interval: float = 1.0,
    point_color: str = "red",
    point_size: int = 50,
    dpi: int = 200
) -> str:
    """Генерирует PNG-карту с OSM-подложкой."""
    if len(lats) != len(lons) or len(lats) != len(pressures):
        raise ValueError("Длины lats, lons и pressures должны совпадать")

    df = pd.DataFrame({"lat": lats, "lon": lons, "pressure": pressures})
    print("🔄 Интерполируем давление (PNG)...")
    grid_lat = np.linspace(min(lats), max(lats), 80)
    grid_lon = np.linspace(min(lons), max(lons), 80)
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)

    points = df[["lat", "lon"]].values
    values = df["pressure"].values
    grid_pressure = griddata(
        points, values, (grid_lat_mesh, grid_lon_mesh),
        method="cubic", fill_value=np.nan
    )

    p_min = np.nanmin(grid_pressure)
    p_max = np.nanmax(grid_pressure)
    if np.isnan(p_min) or np.isnan(p_max):
        raise ValueError("Интерполяция не удалась")

    levels = np.arange(
        np.floor(p_min / contour_interval) * contour_interval,
        np.ceil(p_max / contour_interval) * contour_interval + contour_interval,
        contour_interval
    )

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.contourf(grid_lon, grid_lat, grid_pressure, levels=30, cmap=colormap, alpha=0.65)
    cs = ax.contour(grid_lon, grid_lat, grid_pressure, levels=levels, colors='white', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=9, fmt='%.1f', colors='white')
    ax.scatter(lons, lats, c=pressures, cmap=colormap, s=point_size, edgecolor='black', zorder=10)

    try:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.OpenStreetMap.Mapnik)
    except Exception as e:
        print(f"⚠️ OSM недоступен: {e}")
        ax.set_facecolor('#f0f0f0')

    ax.set_xlabel("Долгота (°E)")
    ax.set_ylabel("Широта (°N)")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02).set_label("Давление (гПа)")

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"✅ PNG сохранён: {output_path}")
    return output_path


# === ФУНКЦИЯ 2: ИНТЕРАКТИВНАЯ КАРТА (HTML) ===
def generate_interactive_pressure_map_html(
    lats: list,
    lons: list,
    pressures: list,
    title: str = "Карта давления (интерактивная)",
    contour_interval: float = 2.0,
    colormap: str = "Viridis",
    output_prefix: str = "pressure_map"
) -> str:
    """Генерирует интерактивную HTML-карту через Plotly (в x/y координатах)."""
    if len(lats) != len(lons) or len(lats) != len(pressures):
        raise ValueError("Длины lats, lons и pressures должны совпадать")

    df = pd.DataFrame({"lat": lats, "lon": lons, "pressure": pressures})
    print("🔄 Интерполируем давление (HTML)...")

    grid_lat = np.linspace(min(lats), max(lats), 100)
    grid_lon = np.linspace(min(lons), max(lons), 100)
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)

    points = df[["lat", "lon"]].values
    values = df["pressure"].values
    grid_pressure = gd(points, values, (grid_lat_mesh, grid_lon_mesh), method="cubic", fill_value=np.nan)

    p_min = np.nanmin(grid_pressure)
    p_max = np.nanmax(grid_pressure)

    # Извлекаем изолинии
    import matplotlib.pyplot as plt2
    cs = plt2.contour(grid_lon_mesh, grid_lat_mesh, grid_pressure, levels=np.arange(p_min, p_max, contour_interval))
    plt2.close()

    contour_lines = []
    for collection in cs.allsegs:
        for path in collection:
            if len(path) > 1:
                contour_lines.append(path)

    fig = go.Figure()

    # Градиент
    fig.add_trace(go.Heatmap(
        z=grid_pressure, x=grid_lon, y=grid_lat,
        colorscale=colormap, zmin=p_min, zmax=p_max,
        opacity=0.7, showscale=True, colorbar=dict(title="гПа")
    ))

    # Изолинии (упрощённо — можно улучшить)
    for line in contour_lines[:10]:  # ограничим для производительности
        fig.add_trace(go.Contour(
            z=grid_pressure, x=grid_lon, y=grid_lat,
            contours=dict(start=p_min, end=p_max, size=contour_interval, showlabels=True),
            showscale=False, line=dict(width=1.5, color="white"),
            opacity=0.9, hoverinfo='skip', showlegend=False
        ))
        break  # NOTE: в реальности нужно рисовать все, но это упрощённый пример

    # Точки
    fig.add_trace(go.Scatter(
        x=lons, y=lats, mode='markers+text',
        text=[f"{p:.1f}" for p in pressures],
        textposition="top center",
        marker=dict(size=8, color='red', opacity=0.8),
        hovertemplate="Давление: %{text} гПа<br>Широта: %{y:.2f}<br>Долгота: %{x:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Долгота (°E)",
        yaxis_title="Широта (°N)",
        width=900, height=700
    )

    html_path = save_html(fig.to_html(), prefix=output_prefix)
    print(f"✅ HTML сохранён: {html_path}")
    return html_path