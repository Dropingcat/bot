# -*- coding: utf-8 -*-
"""
Обработка и интерполяция данных.

Поддерживает:
- 1D: временные ряды (температура, давление, влажность)
- 2D: сетки (давление по координатам, температура на карте)
- 3D+: тензоры (физиологическое состояние, модели)
- Фильтрация, нормализация, агрегация
- Интеграция с pandas, numpy, scipy
"""

import numpy as np
import pandas as pd
from scipy import interpolate
import logging
from typing import List, Dict, Union, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("data_processor")

# === 1D: ВРЕМЕННЫЕ РЯДЫ ===
def interpolate_timeseries(
    timestamps: List[str],
    values: List[float],
    target_timestamps: List[str],
    method: str = 'linear'
) -> List[float]:
    """
    Интерполяция одномерного временного ряда.

    Args:
        timestamps (list): Временные метки (ISO формат)
        values (list): Значения (температура, давление и т.д.)
        target_timestamps (list): Целевые временные метки
        method (str): Метод ('linear', 'cubic', 'quadratic', 'time')

    Returns:
        list: Интерполированные значения
    """
    if len(timestamps) < 2 or len(values) < 2:
        logger.error("❌ Недостаточно данных для интерполяции")
        return [np.nan] * len(target_timestamps)

    ts_numeric = pd.to_datetime(timestamps).astype(int) // 10**9
    target_ts_numeric = pd.to_datetime(target_timestamps).astype(int) // 10**9

    f = interpolate.interp1d(ts_numeric, values, kind=method, fill_value='extrapolate')
    interpolated = f(target_ts_numeric)
    logger.info(f"📈 1D интерполяция: {len(timestamps)} → {len(target_timestamps)} точек")
    return interpolated.tolist()

def resample_timeseries(
    timestamps: List[str],
    values: List[float],
    new_freq: str = '1h'
) -> Tuple[List[str], List[float]]:
    """
    Ресэмплирование временного ряда.

    Args:
        timestamps (list): Временные метки
        values (list): Значения
        new_freq (str): Частота ('1h', '30min', '1d', etc.)

    Returns:
        tuple: (новые_временные_метки, интерполированные_значения)
    """
    df = pd.DataFrame({'value': values}, index=pd.to_datetime(timestamps))
    resampled = df.resample(new_freq).mean()
    resampled = resampled.interpolate(method='time').ffill().bfill()
    new_times = resampled.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
    new_values = resampled['value'].tolist()
    logger.info(f"📅 Ресэмплирование: {len(timestamps)} → {len(new_times)} точек")
    return new_times, new_values

# === 2D: СЕТКИ (напр. давление на карте) ===
def interpolate_2d_grid(
    x_orig: List[float],
    y_orig: List[float],
    z_values: List[List[float]],  # shape: (len(y_orig), len(x_orig))
    x_target: List[float],
    y_target: List[float],
    method: str = 'linear'
) -> List[List[float]]:
    """
    2D интерполяция (например, давление по сетке координат).

    Args:
        x_orig (list): Исходные X
        y_orig (list): Исходные Y
        z_values (list[list]): Матрица Z-значений (y, x) -> z
        x_target (list): Целевые X
        y_target (list): Целевые Y
        method (str): Метод ('linear', 'cubic', 'nearest')

    Returns:
        list[list]: Интерполированная матрица Z
    """
    x_orig = np.array(x_orig)
    y_orig = np.array(y_orig)
    z_values = np.array(z_values)

    X_orig, Y_orig = np.meshgrid(x_orig, y_orig, indexing='ij')
    points = np.column_stack((X_orig.ravel(), Y_orig.ravel()))
    values = z_values.ravel()

    X_target, Y_target = np.meshgrid(x_target, y_target, indexing='ij')
    target_points = np.column_stack((X_target.ravel(), Y_target.ravel()))

    interpolated = interpolate.griddata(points, values, target_points, method=method, fill_value=np.nan)
    result = interpolated.reshape(X_target.shape)

    logger.info(f"🗺️  2D интерполяция: {X_orig.shape} → {X_target.shape}")
    return result.tolist()

def interpolate_2d_to_points(
    x_orig: List[float],
    y_orig: List[float],
    z_values: List[List[float]],
    target_points: List[Tuple[float, float]],
    method: str = 'linear'
) -> List[float]:
    """
    Интерполяция 2D сетки в конкретные точки (например, давление в 5 точках).

    Args:
        x_orig (list): Исходные X
        y_orig (list): Исходные Y
        z_values (list[list]): Матрица Z-значений
        target_points (list): [(x1, y1), (x2, y2), ...]
        method (str): Метод ('linear', 'cubic', 'nearest')

    Returns:
        list: Интерполированные значения для точек
    """
    x_orig = np.array(x_orig)
    y_orig = np.array(y_orig)
    z_values = np.array(z_values)

    X_orig, Y_orig = np.meshgrid(x_orig, y_orig, indexing='ij')
    points = np.column_stack((X_orig.ravel(), Y_orig.ravel()))
    values = z_values.ravel()

    target_x, target_y = zip(*target_points)
    target_points_arr = np.column_stack((target_x, target_y))

    interpolated = interpolate.griddata(points, values, target_points_arr, method=method, fill_value=np.nan)
    logger.info(f"📍 2D → точки: {len(target_points)} точек")
    return interpolated.tolist()

# === 3D+: ТЕНЗОРЫ (физиологическое состояние) ===
def interpolate_tensor(
    tensor: np.ndarray,
    target_shape: Tuple[int, ...],
    method: str = 'linear'
) -> np.ndarray:
    """
    Интерполяция многомерного тензора (например, физиологическое состояние).

    Args:
        tensor (np.ndarray): Входной тензор
        target_shape (tuple): Целевая форма
        method (str): Метод ('linear', 'cubic', 'nearest')

    Returns:
        np.ndarray: Интерполированный тензор
    """
    if tensor.ndim == 1:
        # 1D case
        old_indices = np.linspace(0, 1, tensor.size)
        new_indices = np.linspace(0, 1, target_shape[0])
        f = interpolate.interp1d(old_indices, tensor, kind=method, fill_value='extrapolate')
        return f(new_indices)

    elif tensor.ndim == 2:
        # 2D case
        old_x = np.linspace(0, 1, tensor.shape[1])
        old_y = np.linspace(0, 1, tensor.shape[0])
        new_x = np.linspace(0, 1, target_shape[1])
        new_y = np.linspace(0, 1, target_shape[0])
        f = interpolate.RectBivariateSpline(old_y, old_x, tensor, kx=1, ky=1)
        return f(new_y, new_x)

    else:
        logger.warning(f"⚠️  Интерполяция для {tensor.ndim}D тензора не реализована")
        return tensor

# === ФИЛЬТРАЦИЯ ===
def moving_average_filter(values: List[float], window_size: int = 3) -> List[float]:
    """
    Скользящее среднее (для фильтрации шума).
    """
    if len(values) < window_size:
        logger.warning("❌ Размер данных меньше окна фильтрации")
        return values

    arr = np.array(values, dtype=float)
    padded = np.pad(arr, (window_size//2, window_size//2), mode='edge')
    kernel = np.ones(window_size) / window_size
    filtered = np.convolve(padded, kernel, mode='valid')
    logger.debug(f"📊 Скользящее среднее: window={window_size}, {len(values)} → {len(filtered)}")
    return filtered.tolist()

def median_filter(values: List[float], window_size: int = 3) -> List[float]:
    """
    Медианный фильтр (для удаления выбросов).
    """
    from scipy.signal import medfilt
    if window_size % 2 == 0:
        window_size += 1
    filtered = medfilt(values, kernel_size=window_size)
    logger.debug(f"📊 Медианный фильтр: window={window_size}, {len(values)} → {len(filtered)}")
    return filtered.tolist()

# === НОРМАЛИЗАЦИЯ ===
def normalize_min_max(values: List[float], min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
    """
    Нормализация значений в заданный диапазон (min-max scaling).
    """
    arr = np.array(values)
    arr_min = np.nanmin(arr)
    arr_max = np.nanmax(arr)
    if arr_max == arr_min:
        return [min_val] * len(values)
    normalized = (arr - arr_min) / (arr_max - arr_min)
    scaled = normalized * (max_val - min_val) + min_val
    logger.debug(f"📊 MinMax нормализация: {len(values)} значений")
    return scaled.tolist()

def normalize_z_score(values: List[float]) -> List[float]:
    """
    Z-нормализация (среднее 0, std 1).
    """
    arr = np.array(values)
    mean = np.nanmean(arr)
    std = np.nanstd(arr)
    if std == 0:
        return [0.0] * len(values)
    z_scores = (arr - mean) / std
    logger.debug(f"📊 Z-нормализация: {len(values)} значений")
    return z_scores.tolist()

# === АГРЕГАЦИЯ ===
def aggregate_by_time(
    df: pd.DataFrame,
    freq: str = '1h',
    agg_func: str = 'mean'
) -> pd.DataFrame:
    """
    Агрегация данных по времени (например, усреднение за час).
    """
    grouped = df.resample(freq).agg(agg_func)
    logger.info(f"📊 Агрегация по времени: {freq}, {agg_func}")
    return grouped

# === УДОБНЫЕ ФУНКЦИИ ===
def process_weather_timeseries(
    timestamps: List[str],
    temperatures: List[float],
    pressures: List[float],
    target_freq: str = '1h'
) -> Dict[str, List]:
    """
    Обработка временного ряда погоды: интерполяция, фильтрация, агрегация.
    """
    new_times_temp, temp_interp = resample_timeseries(timestamps, temperatures, target_freq)
    _, press_interp = resample_timeseries(timestamps, pressures, target_freq)

    temp_filtered = moving_average_filter(temp_interp, window_size=3)
    press_filtered = moving_average_filter(press_interp, window_size=3)

    return {
        "timestamps": new_times_temp,
        "temperature": temp_filtered,
        "pressure": press_filtered
    }

def process_2d_weather_map(
    lats: List[float],
    lons: List[float],
    pressure_grid: List[List[float]],
    target_lats: List[float],
    target_lons: List[float]
) -> List[List[float]]:
    """
    Обработка 2D-сетки (например, давление на карте).
    """
    return interpolate_2d_grid(
        x_orig=lats,
        y_orig=lons,
        z_values=pressure_grid,
        x_target=target_lats,
        y_target=target_lons,
        method='linear'
    )