"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Модель прогноза физиологического состояния.
НЕ вызывает другие модели напрямую.
Получает всё из кэша.
"""

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.stats import dirichlet
import warnings
import logging

from core.db.local_db_meteo import get_cached_meteo_impact
from core.db.local_db_weather import get_cached_weather
from core.db.local_db_atmosphere import get_cached_atmosphere_data
from core.db.local_db_agro import get_cached_agro_forecast
from core.utils.api_client import OpenMeteoClient  # или твой fetcher

logger = logging.getLogger("health_predictor")

# === 1. АТТРАКТОРЫ ТИПОВ (центры в 8-мерном пространстве параметров) ===
MU = np.array([
    [120, 155, 90, 125, 135],
    [70, 85, 60, 80, 75],
    [98, 97, 97, 95, 96],
    [0.4, 0.3, 0.5, 0.7, 0.3],
    [0.2, 0.3, 0.4, 0.8, 0.5],
    [0.1, 0.9, 0.0, 0.1, 0.7],
    [0.5, 0.5, 0.4, 0.9, 0.6],
    [0.3, 0.5, 0.2, 0.4, 0.7]
])
TYPE_NAMES = ['healthy', 'hypertension', 'hypotension', 'anxiety_disorder', 'elderly']
N_TYPES = len(TYPE_NAMES)
N_PARAMS = MU.shape[0]
DAYS = 7  # Прогноз на 7 дней

# === 2. МАТРИЦЫ ВЛИЯНИЯ ===
W_METEO = np.array([
    [ 0.0,   -0.1,   -0.1,   -0.1,    0.0 ],
    [-0.1,    0.8,   -0.1,   -0.1,    0.1 ],
    [-0.1,   -0.1,    0.7,   -0.1,    0.0 ],
    [-0.1,   -0.1,   -0.1,    0.9,    0.0 ],
    [ 0.0,    0.0,    0.0,    0.0,    0.8 ],
])
W_PHYS = np.array([
    [ 0.0,   -0.2,   -0.1,   -0.2,    0.0 ],
    [-0.2,    0.9,   -0.1,   -0.1,    0.2 ],
    [-0.1,   -0.1,    0.8,   -0.1,    0.1 ],
    [-0.2,   -0.1,   -0.1,    0.8,    0.1 ],
    [ 0.0,    0.1,    0.1,    0.1,    0.7 ],
])
W_AGE = np.array([
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
    [-0.02,  -0.01,  -0.01,  -0.01,   0.05],
])

# === 3. КОЭФФИЦИЕНТЫ ЭВОЛЮЦИИ ===
ALPHA = 0.4
BETA = 0.6
GAMMA = 0.01 / 365.0  # новое: 0.01 за год
SIGMA_S = 0.01

# === 4. ФУНКЦИИ МОДЕЛИ (как в v5.1) ===
def get_average_profile():
    p_avg = MU[:, 0].copy()  # здоровый
    s_avg = np.zeros(N_TYPES)
    s_avg[0] = 1.0  # 100% здоровый
    return p_avg, s_avg

def get_real_weather_data(lat, lon, hours=168):
    """Запрос поверхностных данных от Open-Meteo (ECMWF IFS) через api_client."""
    # Вместо прямого вызова requests — используем api_client
    client = OpenMeteoClient()
    df = client.get_hourly_forecast(lat, lon, hours=hours)
    # Добавляем расчёты градиентов и т.д. как в оригинальном коде
    df['dP_dt'] = df['msl_hPa'].diff().fillna(0)
    df['dT_dt'] = df['t_c'].diff().fillna(0)
    df['d_rad_pct'] = (df['shortwave_radiation'] - 20.0) / 20.0 * 100
    df['max_front_grad'] = abs(df['dP_dt']).rolling(window=4, min_periods=1).mean()
    df['max_wind_shear'] = df['wind_speed'].diff().rolling(window=4, min_periods=1).max().fillna(0)
    return df

def fetch_gfs_turbulence_data(lat, lon, hours=168):
    """Запрос данных GFS Seamless для расчёта турбулентности через api_client."""
    client = OpenMeteoClient()
    df = client.get_gfs_data(lat, lon, hours=hours)
    # Вычисления турбулентности как в оригинале
    # ...
    N_turb = np.full(len(df), 0.1)  # заглушка
    df['N_turb'] = N_turb
    return df

def compute_stress_index(meteo_df):
    # --- Нормировки ---
    norm_dP_dt = np.clip(abs(meteo_df['dP_dt']).mean() / 1.0, 0, 1)
    norm_dT_dt = np.clip(abs(meteo_df['dT_dt']).mean() / 5.0, 0, 1)
    norm_front = np.clip(meteo_df['max_front_grad'].mean() / 10.0, 0, 1)
    norm_shear = np.clip(meteo_df['max_wind_shear'].mean() / 40.0, 0, 1)
    norm_turb = np.clip(meteo_df['N_turb'].mean() / 4.0, 0, 1)
    norm_rad = np.clip(meteo_df['shortwave_radiation'].mean() / 200.0, 0, 1)
    norm_dRH_dt = np.clip(abs(meteo_df['rh'].diff().fillna(0).mean()) / 20.0, 0, 1)

    weights = np.array([0.2, 0.1, 0.25, 0.2, 0.05, 0.1, 0.1])
    stress_vector = [
        norm_dP_dt,
        norm_dT_dt,
        norm_front,
        norm_shear,
        norm_turb,
        norm_rad,
        norm_dRH_dt
    ]
    stress_index = np.dot(stress_vector, weights)
    return np.clip(stress_index, 0, 1)

def compute_physiological_deviation(ad_traj, pulse_traj, spo2_traj, s_current):
    expected_ad = np.dot(s_current, MU[0])
    expected_pulse = np.dot(s_current, MU[1])
    expected_spo2 = np.dot(s_current, MU[2])
    dev_ad = np.sqrt(np.mean((ad_traj - expected_ad)**2)) / 20.0
    dev_pulse = np.sqrt(np.mean((pulse_traj - expected_pulse)**2)) / 25.0
    dev_spo2 = np.sqrt(np.mean((spo2_traj - expected_spo2)**2)) / 3.0
    weights = np.array([0.4, 0.3, 0.3])
    phys_dev = np.dot([dev_ad, dev_pulse, dev_spo2], weights)
    return np.clip(phys_dev, 0, 1)

def evolve_s(s_current, stress_index, phys_dev, days_elapsed, age_normalized):
    ds = np.zeros(N_TYPES)
    ds_met = ALPHA * stress_index * np.dot(W_METEO, s_current)
    ds += ds_met
    ds_phys = BETA * phys_dev * np.dot(W_PHYS, s_current)
    ds += ds_phys
    ds_age = GAMMA * age_normalized * 0.1
    ds[4] += ds_age
    ds_healthy = -0.05 * phys_dev
    if phys_dev < 0.05:
        ds_healthy += 0.01
    ds[0] += ds_healthy
    noise = np.random.normal(0, SIGMA_S, N_TYPES)
    ds += noise

    if np.any(np.isnan(ds)) or np.any(np.isinf(ds)):
        logger.error("NaN/Inf в evolve_s")
        ds = np.nan_to_num(ds, nan=0.0, posinf=0.0, neginf=0.0)

    s_new = s_current + ds
    s_new = np.clip(s_new, 0, 1)
    s_new_sum = np.sum(s_new)
    if s_new_sum == 0:
        return s_current
    s_new = s_new / s_new_sum
    return s_new

def get_response_coeffs_from_p(p):
    R_BASE = {
        'ad_dp': -0.8, 'pulse_dp': 0.05, 'pulse_dt': 0.05, 'spo2_dp': -0.01,
        'sns_dp': 0.5, 'sns_dt': 0.05, 'sns_wind': 0.1, 'sns_cape': 0.001,
        'sns_turb': 0.3, 'pulse_syn_t_p': 0.01, 'pulse_low_wind_high_rh': 0.02,
        'mood_heat': 0.05, 'spo2_p_abs': -0.001, 'spo2_rh_abs': -0.0005,
        'mood_sun': 0.3, 'mood_arousal_int': 0.3, 'arousal_front': 0.6,
        'arousal_shear': 0.4, 'arousal_mood_int': 0.5, 'pulse_wind_gust': 0.02
    }
    w_n, w_d, w_c, w_s, w_age = p[3:8]
    R = R_BASE.copy()
    R['ad_dp'] = R['ad_dp'] * (1 + w_c * 0.5)
    R['pulse_dp'] = R['pulse_dp'] * (1 + w_s * 0.5)
    R['spo2_p_abs'] = R['spo2_p_abs'] * (1 + w_d * 0.8)
    R['arousal_front'] = R['arousal_front'] * (1 + w_n * 0.7)
    R['arousal_shear'] = R['arousal_shear'] * (1 + w_s * 0.6)
    R['sns_cape'] = R['sns_cape'] * (1 + w_n * 0.5)
    if p[0] > 140:
        R['ad_dp'] = abs(R['ad_dp']) * 1.8
    elif p[0] < 90:
        R['ad_dp'] = -abs(R['ad_dp']) * 1.5
    return R

def tensor_model_fixed_with_climate_norms(df_meteo, user_profile, response_coeffs, start_values=None):
    R = response_coeffs
    baseline_ad = user_profile['baseline_ad']
    baseline_pulse = user_profile['baseline_pulse']
    baseline_spo2 = user_profile['baseline_spo2']

    ad_pred = np.full(len(df_meteo), baseline_ad)
    pulse_pred = np.full(len(df_meteo), baseline_pulse)
    spo2_pred = np.full(len(df_meteo), baseline_spo2)

    if start_values is not None:
        ad_pred[0] = start_values.get('ad_start', baseline_ad)
        pulse_pred[0] = start_values.get('pulse_start', baseline_pulse)
        spo2_pred[0] = start_values.get('spo2_start', baseline_spo2)

    sns_index = np.zeros(len(df_meteo))
    mood = np.zeros(len(df_meteo))
    arousal = np.zeros(len(df_meteo))

    for i in range(1, len(df_meteo)):
        dt = 1
        delta_ad = R['ad_dp'] * df_meteo['dP_dt'].iloc[i]
        ad_pred[i] = ad_pred[i-1] + delta_ad

        dP_dt_smooth = df_meteo['dP_dt'].rolling(window=3, center=True, min_periods=1).mean().iloc[i]
        dT_dt_smooth = df_meteo['dT_dt'].rolling(window=3, center=True, min_periods=1).mean().iloc[i]
        d_wind = df_meteo['wind_speed'].diff().fillna(0).iloc[i]
        wind_gust_term = R['pulse_wind_gust'] * abs(d_wind)
        delta_pulse_base = R['pulse_dp'] * dP_dt_smooth + R['pulse_dt'] * dT_dt_smooth
        syn_term = R['pulse_syn_t_p'] * max(0, 1000 - df_meteo['msl_hPa'].iloc[i]) * max(0, df_meteo['t_c'].iloc[i] - 10)
        stagnation_term = R['pulse_low_wind_high_rh'] * max(0, 2 - df_meteo['wind_speed'].iloc[i]) * max(0, df_meteo['rh'].iloc[i] - 80)
        delta_pulse = delta_pulse_base + syn_term + stagnation_term + wind_gust_term
        pulse_pred[i] = 0.90 * pulse_pred[i-1] + 0.10 * (pulse_pred[i-1] + delta_pulse)

        spo2_effect = R['spo2_p_abs'] * df_meteo['msl_hPa'].iloc[i] + R['spo2_rh_abs'] * df_meteo['rh'].iloc[i]
        saturation_factor = 1.0 - (spo2_pred[i-1] - 80) / 20.0
        saturation_factor = max(0.1, saturation_factor)
        spo2_pred[i] = spo2_pred[i-1] + spo2_effect * saturation_factor
        spo2_pred[i] = np.clip(spo2_pred[i], 80, 100)

        sns_base = R['sns_dp'] * abs(df_meteo['dP_dt'].iloc[i])
        sns_dt = R['sns_dt'] * abs(df_meteo['dT_dt'].iloc[i])
        sns_wind = R['sns_wind'] * df_meteo['wind_speed'].iloc[i]
        sns_rad = R['sns_cape'] * df_meteo['shortwave_radiation'].iloc[i] / 100.0
        sns_turb = R['sns_turb'] * df_meteo['N_turb'].iloc[i]
        sns_index[i] = sns_base + sns_dt + sns_wind + sns_rad + sns_turb

        d_mood = R['mood_sun'] * max(0, -df_meteo['shortwave_radiation'].iloc[i]) + R['mood_arousal_int'] * np.tanh(arousal[i-1])
        mood[i] = mood[i-1] + d_mood * dt
        mood[i] = np.clip(mood[i], -10, 10)

        d_arousal = (
            R['arousal_front'] * max(0, df_meteo['max_front_grad'].iloc[i] - 3) +
            R['arousal_shear'] * max(0, df_meteo['max_wind_shear'].iloc[i] - 10) +
            R['arousal_mood_int'] * np.tanh(-mood[i-1])
        )
        arousal[i] = arousal[i-1] + d_arousal * dt
        arousal[i] = np.clip(arousal[i], -10, 10)

    ad_pred = np.clip(ad_pred, 50, 250)
    pulse_pred = np.clip(pulse_pred, 20, 250)
    spo2_pred = np.clip(spo2_pred, 80, 100)

    return {
        'ad_pred': ad_pred, 'pulse_pred': pulse_pred, 'spo2_pred': spo2_pred,
        'sns_index': sns_index, 'mood': mood, 'arousal': arousal,
    }, {}, {
        'ad_max': ad_pred.max(), 'ad_min': ad_pred.min(),
        'pulse_max': pulse_pred.max(), 'pulse_min': pulse_pred.min(),
        'spo2_max': spo2_pred.max(), 'spo2_min': spo2_pred.min(),
        'sns_max': sns_index.max(), 'mood_max': mood.max(), 'mood_min': mood.min(),
        'arousal_max': arousal.max(), 'arousal_min': arousal.min(),
    }

def align_s_with_p(p_current, s_current, MU, iterations=5):
    s = s_current.copy()
    p_target = p_current.copy()
    indices_to_match = [0, 1, 2]
    for iter_num in range(iterations):
        p_current_calc = np.dot(MU, s)
        diff = p_target[indices_to_match] - p_current_calc[indices_to_match]
        grad = MU[indices_to_match].T
        s_delta = 0.01 * grad @ diff
        s += s_delta
        if np.any(np.isnan(s)) or np.any(np.isinf(s)):
            logger.error("NaN/Inf в align_s_with_p")
            return s_current
        s = np.clip(s, 0, 1)
        s_sum = np.sum(s)
        if s_sum == 0:
            return s_current
        s = s / s_sum
    return s

def predict_7day_health_state(p_current, s_current, meteo_forecast, df_turb, days=7):
    p = p_current.copy()
    s = s_current.copy()
    age_normalized = p[7]

    p_hourly_history = [p.copy()]
    s_hourly_history = [s.copy()]
    stress_hourly_history = [0.0]
    phys_dev_hourly_history = [0.0]
    sns_hourly_history = [0.0]
    mood_hourly_history = [0.0]
    arousal_hourly_history = [0.0]

    if len(meteo_forecast) < days * 24:
        raise ValueError(f"Метеоданные: {len(meteo_forecast)}, требуется {days * 24}")
    if len(df_turb) < days * 24:
        raise ValueError(f"Турбулентность: {len(df_turb)}, требуется {days * 24}")

    last_ad_end = p[0]
    last_pulse_end = p[1]
    last_spo2_end = p[2]

    for day in range(days):
        logger.info(f"День {day+1}/{days}")
        start_idx = day * 24
        end_idx = (day + 1) * 24
        meteo_df = meteo_forecast.iloc[start_idx:end_idx].copy()
        turb_df = df_turb.iloc[start_idx:end_idx].copy()

        meteo_df = meteo_df.set_index('time')
        turb_df = turb_df.set_index('time')
        combined_df = meteo_df.join(turb_df, how='left')
        meteo_df = combined_df.reset_index()

        meteo_df['dP_dt'] = meteo_df['msl_hPa'].diff().fillna(0)
        meteo_df['dT_dt'] = meteo_df['t_c'].diff().fillna(0)
        base_radiation = 20.0
        meteo_df['d_rad_pct'] = (meteo_df['shortwave_radiation'] - base_radiation) / base_radiation * 100
        stress_index = compute_stress_index(meteo_df)
        R = get_response_coeffs_from_p(p)

        user_profile = {
            'baseline_ad': p[0],
            'baseline_pulse': p[1],
            'baseline_spo2': p[2],
        }
        start_values = {
            'ad_start': last_ad_end,
            'pulse_start': last_pulse_end,
            'spo2_start': last_spo2_end,
        }
        output, _, stats = tensor_model_fixed_with_climate_norms(
            meteo_df, user_profile, R, start_values=start_values
        )

        last_ad_end = output['ad_pred'][-1]
        last_pulse_end = output['pulse_pred'][-1]
        last_spo2_end = output['spo2_pred'][-1]

        sns_hourly_history.extend(output['sns_index'])
        mood_hourly_history.extend(output['mood'])
        arousal_hourly_history.extend(output['arousal'])

        phys_dev = compute_physiological_deviation(
            output['ad_pred'], output['pulse_pred'], output['spo2_pred'], s
        )

        s = evolve_s(s, stress_index, phys_dev, day, age_normalized)
        p = np.dot(MU, s)
        p_age_effect = np.dot(W_AGE, s) * GAMMA * day
        p += p_age_effect
        sigma_p = np.array([10, 10, 1, 0.1, 0.1, 0.1, 0.1, 0.05])
        p += np.random.normal(0, sigma_p)
        p[0] = np.clip(p[0], 70, 200)
        p[1] = np.clip(p[1], 30, 200)
        p[2] = np.clip(p[2], 85, 100)
        p[3:8] = np.clip(p[3:8], 0, 1)

        p_hourly_day = np.column_stack([
            output['ad_pred'], output['pulse_pred'], output['spo2_pred'],
            np.full(24, p[3]), np.full(24, p[4]), np.full(24, p[5]),
            np.full(24, p[6]), np.full(24, p[7]),
        ])
        p_hourly_history.extend(p_hourly_day.tolist())
        s_hourly_history.extend([s.copy()] * 24)
        stress_hourly_history.extend([stress_index] * 24)
        phys_dev_hourly_history.extend([phys_dev] * 24)

    total_hours = days * 24 + 1
    assert len(p_hourly_history) == total_hours

    return {
        'p_hourly_history': np.array(p_hourly_history),
        's_hourly_history': np.array(s_hourly_history),
        'stress_hourly_history': np.array(stress_hourly_history),
        'phys_dev_hourly_history': np.array(phys_dev_hourly_history),
        'sns_hourly': np.array(sns_hourly_history),
        'mood_hourly': np.array(mood_hourly_history),
        'arousal_hourly': np.array(arousal_hourly_history),
        'meteo_hourly': meteo_forecast,
        'p_history': np.array([p_hourly_history[i * 24] for i in range(days + 1)]),
        's_history': np.array([s_hourly_history[i * 24] for i in range(days + 1)]),
        'stress_history': np.array([stress_hourly_history[i * 24] for i in range(1, days + 1)]),
        'phys_dev_history': np.array([phys_dev_hourly_history[i * 24] for i in range(1, days + 1)]),
    }

def plot_prediction_extended_corrected(result, filename="data/health_prediction.png"):
    s_hist = result['s_history']
    p_hist = result['p_history']
    stress_hist = result['stress_history']
    phys_dev_hist = result['phys_dev_history']
    days_for_p_s = np.arange(len(s_hist))
    days_for_metrics = np.arange(1, len(s_hist))

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('Прогноз физиологического состояния на 7 дней', fontsize=16)

    for i, t in enumerate(TYPE_NAMES):
        axes[0, 0].plot(days_for_p_s, s_hist[:, i], label=t, marker='o', linewidth=1.5)
    axes[0, 0].set_title('Распределение типов $s(t)$')
    axes[0, 0].set_xlabel('День')
    axes[0, 0].set_ylabel('Вероятность')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(days_for_p_s, p_hist[:, 0], label='baseline_ad', color='red', marker='o', linewidth=1.5)
    axes[0, 1].set_title('Прогноз АД (baseline_ad)')
    axes[0, 1].set_xlabel('День')
    axes[0, 1].set_ylabel('мм рт.ст.')
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(days_for_p_s, p_hist[:, 1], label='baseline_pulse', color='blue', marker='o', linewidth=1.5)
    axes[1, 0].set_title('Прогноз ЧСС (baseline_pulse)')
    axes[1, 0].set_xlabel('День')
    axes[1, 0].set_ylabel('уд/мин')
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(days_for_p_s, s_hist[:, 1], label='s_hypertension', color='orange', marker='o', linewidth=1.5)
    axes[1, 1].set_title('Вероятность гипертонии')
    axes[1, 1].set_xlabel('День')
    axes[1, 1].set_ylabel('Вероятность')
    axes[1, 1].grid(True, alpha=0.3)

    axes[2, 0].plot(days_for_metrics, stress_hist, label='Индекс стресса', color='purple', marker='o', linewidth=1.5)
    axes[2, 0].set_title('Индекс метео-стресса')
    axes[2, 0].set_xlabel('День')
    axes[2, 0].set_ylabel('Стресс')
    axes[2, 0].grid(True, alpha=0.3)

    axes[2, 1].plot(days_for_metrics, phys_dev_hist, label='Физиологическое отклонение', color='green', marker='o', linewidth=1.5)
    axes[2, 1].set_title('Физиологическое отклонение')
    axes[2, 1].set_xlabel('День')
    axes[2, 1].set_ylabel('Отклонение')
    axes[2, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    logger.info("📊 Основной график сохранён: %s", filename)

# --- ФУНКЦИИ ЗАГЛУШКИ ---
def plot_all_debug_charts_corrected(result, filename="data/debug_all_params.png"):
    logger.info("📊 Отладочный график сохранён: %s", filename)

def plot_hourly_dynamics(result, filename="data/hourly_dynamics.png"):
    logger.info("📊 График почасовой динамики сохранён: %s", filename)

def plot_meteo_vs_physics(result, filename="data/meteo_vs_physics.png"):
    logger.info("📊 График метео vs физиология сохранён: %s", filename)

def plot_gradients_and_intermediates(result, filename="data/gradients.png"):
    logger.info("📊 График градиентов сохранён: %s", filename)

async def run_health_predictor(user_id: int, lat: float, lon: float, start_date: datetime, end_date: datetime, profile: Dict):
    """
    Запускает модель физиологического прогноза, используя только кэшированные данные.
    """
    logger.info("🚀 Запуск health_predictor для %s", user_id)

    # 1. Получаем метео-данные из кэша
    meteo_data = get_cached_weather(lat, lon, start_date, user_id)
    if not meteo_data:
        logger.warning("❌ Нет метео-данных в кэше для %s. Запрашиваем API...", user_id)
        meteo_forecast = get_real_weather_data(lat, lon, hours=DAYS * 24)
    else:
        logger.info("✅ Метео-данные загружены из кэша")
        # В продакшене: конвертируй кэшированные данные в pd.DataFrame
        meteo_forecast = pd.DataFrame(meteo_data)  # <-- НУЖНО РЕАЛИЗОВАТЬ КОНВЕРТАЦИЮ

    # 2. Получаем турбулентность из кэша
    turb_data = get_cached_meteo_impact(lat, lon, start_date, "turbulence", user_id)
    if not turb_data:
        logger.warning("❌ Нет данных турбулентности в кэше для %s. Запрашиваем API...", user_id)
        df_turb = fetch_gfs_turbulence_data(lat, lon, hours=DAYS * 24)
    else:
        logger.info("✅ Данные турбулентности загружены из кэша")
        df_turb = pd.DataFrame(turb_data)  # <-- НУЖНО РЕАЛИЗОВАТЬ КОНВЕРТАЦИЮ

    # 3. Инициализируем начальное состояние
    p_current, s_current = get_average_profile()
    p_current[0] = profile.get("baseline_ad", p_current[0])
    p_current[1] = profile.get("baseline_pulse", p_current[1])
    p_current[2] = profile.get("baseline_spo2", p_current[2])
    age = profile.get("age", 30)
    age_normalized = (age - 20) / 65
    p_current[7] = age_normalized
    s_current = align_s_with_p(p_current, s_current, MU)

    # 4. Запускаем прогноз
    result = predict_7day_health_state(p_current, s_current, meteo_forecast, df_turb, days=DAYS)

    # 5. Сохраняем графики
    plot_prediction_extended_corrected(result)
    plot_all_debug_charts_corrected(result)
    plot_hourly_dynamics(result)
    plot_meteo_vs_physics(result)
    plot_gradients_and_intermediates(result)

    # 6. Возвращаем результат
    return {
        "status": "success",
        "graph_path": "data/health_prediction.png",
        "data": result
    }