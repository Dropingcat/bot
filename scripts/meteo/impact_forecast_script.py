# -*- coding: utf-8 -*-
"""
Скрипт прогноза влияния погоды на здоровье.

Использует:
- Метеоданные (из GFS Seamless + Open-Meteo)
- Турбулентность (из GFS Seamless)
- Империческую модель (из v5.1)
- Настройку коэффициентов через scikit-learn

Выводит:
- EVENT_TYPE:task_result
- RESULT_TYPE:report
- MESSAGE: краткий отчёт
- FILE_PATH: график
"""

import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from core.utils.script_logger import get_script_logger
from core.db.local_db_meteo import get_user_health_stats
from scripts.meteo._processes.health_predictor import HealthPredictor

# === ИМПОРТ ИЗ ФАЙЛА МОДЕЛИ (вставим сюда функции из v5.1) ===
# --- 1. АТТРАКТОРЫ ТИПОВ ---
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

# --- 2. МАТРИЦЫ ВЛИЯНИЯ ---
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

# --- 3. КОЭФФИЦИЕНТЫ ЭВОЛЮЦИИ ---
ALPHA = 0.4
BETA = 0.6
GAMMA = 0.01 / 365.0
SIGMA_S = 0.01

# --- 4. ФУНКЦИИ МОДЕЛИ ---
def get_average_profile():
    p_avg = MU[:, 0].copy()  # здоровый
    s_avg = np.zeros(N_TYPES)
    s_avg[0] = 1.0  # 100% здоровый
    return p_avg, s_avg

def get_response_coeffs_from_p(p):
    R_BASE = {
        'ad_dp': -0.8,
        'pulse_dp': 0.05,
        'pulse_dt': 0.05,
        'spo2_dp': -0.01,
        'sns_dp': 0.5,
        'sns_dt': 0.05,
        'sns_wind': 0.1,
        'sns_cape': 0.001,
        'sns_turb': 0.3,
        'pulse_syn_t_p': 0.01,
        'pulse_low_wind_high_rh': 0.02,
        'mood_heat': 0.05,
        'spo2_p_abs': -0.001,
        'spo2_rh_abs': -0.0005,
        'mood_sun': 0.3,
        'mood_arousal_int': 0.3,
        'arousal_front': 0.6,
        'arousal_shear': 0.4,
        'arousal_mood_int': 0.5,
        'pulse_wind_gust': 0.02
    }
    w_n, w_d, w_c, w_s, w_age = p[3:8]
    R = R_BASE.copy()

    R['ad_dp'] = R['ad_dp'] * (1 + w_c * 0.5)
    R['pulse_dp'] = R['pulse_dp'] * (1 + w_s * 0.5) * 10  # ✅ Увеличиваем в 10 раз
    R['pulse_dt'] = R['pulse_dt'] * (1 + w_s * 0.5) * 10  # ✅ Увеличиваем в 10 раз
    R['spo2_p_abs'] = R['spo2_p_abs'] * (1 + w_d * 0.8) * 0.1  # ✅ Уменьшаем в 10 раз
    R['spo2_rh_abs'] = R['spo2_rh_abs'] * 0.1  # ✅ Уменьшаем в 10 раз
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

        # === ИСПРАВЛЕНО: используем относительные значения для SpO2 ===
        base_pressure = 1013.0
        base_rh = 70.0
        delta_pressure = df_meteo['msl_hPa'].iloc[i] - base_pressure
        delta_rh = df_meteo['rh'].iloc[i] - base_rh
        spo2_effect = R['spo2_p_abs'] * delta_pressure + R['spo2_rh_abs'] * delta_rh
        # Ограничиваем эффект
        spo2_effect = np.clip(spo2_effect, -1.0, 1.0)

        saturation_factor = 1.0 - (spo2_pred[i-1] - 80) / 20.0
        saturation_factor = max(0.1, saturation_factor)
        spo2_pred[i] = 0.95 * spo2_pred[i-1] + 0.05 * (spo2_pred[i-1] + spo2_effect * saturation_factor)
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
        'ad_pred': ad_pred,
        'pulse_pred': pulse_pred,
        'spo2_pred': spo2_pred,
        'sns_index': sns_index,
        'mood': mood,
        'arousal': arousal,
    }, {}, {
        'ad_max': ad_pred.max(),
        'ad_min': ad_pred.min(),
        'pulse_max': pulse_pred.max(),
        'pulse_min': pulse_pred.min(),
        'spo2_max': spo2_pred.max(),
        'spo2_min': spo2_pred.min(),
        'sns_max': sns_index.max(),
        'mood_max': mood.max(),
        'mood_min': mood.min(),
        'arousal_max': arousal.max(),
        'arousal_min': arousal.min(),
    }

def compute_stress_index(meteo_df):
    norm_dP_dt = np.clip(abs(meteo_df['dP_dt']).mean() / 1.0, 0, 1)
    norm_dT_dt = np.clip(abs(meteo_df['dT_dt']).mean() / 5.0, 0, 1)
    norm_front = np.clip(meteo_df['max_front_grad'].mean() / 10.0, 0, 1)
    norm_shear = np.clip(meteo_df['max_wind_shear'].mean() / 40.0, 0, 1)
    norm_turb = np.clip(meteo_df['N_turb'].mean() / 4.0, 0, 1)
    norm_rad = np.clip(meteo_df['shortwave_radiation'].mean() / 200.0, 0, 1)
    norm_dRH_dt = np.clip(abs(meteo_df['rh'].diff().fillna(0).mean()) / 20.0, 0, 1)

    stress_vector = [
        norm_dP_dt,
        norm_dT_dt,
        norm_front,
        norm_shear,
        norm_turb,
        norm_rad,
        norm_dRH_dt
    ]
    weights = np.array([0.2, 0.1, 0.25, 0.2, 0.05, 0.1, 0.1])
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
    ds_phys = BETA * phys_dev * np.dot(W_PHYS, s_current)
    ds_age = GAMMA * age_normalized * 0.1
    ds_healthy = -0.05 * phys_dev
    if phys_dev < 0.05:
        ds_healthy += 0.01

    noise = np.random.normal(0, SIGMA_S, N_TYPES)

    ds += ds_met + ds_phys
    ds[4] += ds_age
    ds[0] += ds_healthy
    ds += noise

    ds = np.nan_to_num(ds, nan=0.0, posinf=0.0, neginf=0.0)

    s_new = s_current + 0.1 * ds  # === ИНЕРЦИЯ ===
    s_new = np.clip(s_new, 0, 1)
    s_new_sum = np.sum(s_new)
    if s_new_sum == 0:
        return s_current
    s_new = s_new / s_new_sum
    return s_new

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
            return s_current
        s = np.clip(s, 0, 1)
        s_sum = np.sum(s)
        if s_sum == 0:
            return s_current
        s = s / s_sum
    return s

def predict_7day_health_state(p_current, s_current, meteo_forecast, df_turb, days=7, response_coeffs=None):
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
        raise ValueError(f"Метеоданные содержат только {len(meteo_forecast)} часов, требуется {days * 24}")
    if len(df_turb) < days * 24:
        raise ValueError(f"Данные турбулентности содержат только {len(df_turb)} часов, требуется {days * 24}")

    # === НАЧАЛЬНОЕ СОСТОЯНИЕ ===
    last_ad_end = p[0]
    last_pulse_end = p[1]
    last_spo2_end = p[2]

    for day in range(days):
        print(f"🔍 Прогноз: день {day+1}/{days}")
        start_idx = day * 24
        end_idx = (day + 1) * 24
        meteo_df = meteo_forecast.iloc[start_idx:end_idx].copy()
        turb_df = df_turb.iloc[start_idx:end_idx].copy()

        meteo_df = meteo_df.set_index('time')
        turb_df = turb_df.set_index('time')
        
        # === УБИРАЕМ N_turb ИЗ meteo_df ===
        meteo_df = meteo_df.drop(columns=['N_turb'], errors='ignore')
        
        # === ОБЪЕДИНЯЕМ ===
        combined_df = meteo_df.join(turb_df, how='left', rsuffix='_turb')
        meteo_df = combined_df.reset_index()

        meteo_df['dP_dt'] = meteo_df['msl_hPa'].diff().fillna(0)
        meteo_df['dT_dt'] = meteo_df['t_c'].diff().fillna(0)
        base_radiation = 20.0
        meteo_df['d_rad_pct'] = (meteo_df['shortwave_radiation'] - base_radiation) / base_radiation * 100

        # === ЗАПУСКАЕМ МОДЕЛЬ ПО ЧАСАМ ===
        R = response_coeffs  # ✅ Передаём извне

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

        output = tensor_model_fixed_with_climate_norms(
            meteo_df,
            user_profile,
            R,
            start_values=start_values
        )
        main_output = output[0]

        # === ОБНОВЛЯЕМ ПОСЛЕДНИЕ ЗНАЧЕНИЯ ===
        last_ad_end = main_output['ad_pred'][-1]
        last_pulse_end = main_output['pulse_pred'][-1]
        last_spo2_end = main_output['spo2_pred'][-1]

        # === ДОБАВЛЯЕМ В ИСТОРИЮ ===
        sns_hourly_history.extend(main_output['sns_index'])
        mood_hourly_history.extend(main_output['mood'])
        arousal_hourly_history.extend(main_output['arousal'])

        # === ВЫЧИСЛЯЕМ ФИЗИОЛОГИЧЕСКОЕ ОТКЛОНЕНИЕ ПО ЧАСАМ ===
        ad_traj = main_output['ad_pred']
        pulse_traj = main_output['pulse_pred']
        spo2_traj = main_output['spo2_pred']

        expected_ad = np.dot(s_current, MU[0])
        expected_pulse = np.dot(s_current, MU[1])
        expected_spo2 = np.dot(s_current, MU[2])

        dev_ad = np.sqrt(np.mean((ad_traj - expected_ad)**2)) / 20.0
        dev_pulse = np.sqrt(np.mean((pulse_traj - expected_pulse)**2)) / 25.0
        dev_spo2 = np.sqrt(np.mean((spo2_traj - expected_spo2)**2)) / 3.0

        weights = np.array([0.4, 0.3, 0.3])
        phys_dev = np.dot([dev_ad, dev_pulse, dev_spo2], weights)

        # === ОБНОВЛЯЕМ ТИПЫ (s_current) КАЖДЫЙ ЧАС ===
        for i in range(len(main_output['ad_pred'])):
            ad_traj_i = main_output['ad_pred'][i]
            pulse_traj_i = main_output['pulse_pred'][i]
            spo2_traj_i = main_output['spo2_pred'][i]

            # Вычисляем отклонение от ожидаемых значений (на основе s_current)
            expected_ad_i = np.dot(s_current, MU[0])
            expected_pulse_i = np.dot(s_current, MU[1])
            expected_spo2_i = np.dot(s_current, MU[2])

            # === ИСПРАВЛЕНО: используем абсолютное значение ===
            dev_ad_i = abs(ad_traj_i - expected_ad_i) / 20.0
            dev_pulse_i = abs(pulse_traj_i - expected_pulse_i) / 25.0
            dev_spo2_i = abs(spo2_traj_i - expected_spo2_i) / 3.0

            weights = np.array([0.4, 0.3, 0.3])
            phys_dev_i = np.dot([dev_ad_i, dev_pulse_i, dev_spo2_i], weights)
            phys_dev_hourly_history.append(phys_dev_i)

            # Вычисляем индекс стресса по текущему часу
            stress_index = compute_stress_index_for_hour(meteo_df.iloc[i:i+1])
            stress_hourly_history.append(stress_index)

            # Обновляем типы (s_current) каждый час
            s = evolve_s(s, stress_index, phys_dev_i, day, age_normalized)
            s_current = s

            s_hourly_history.append(s.copy())

        # === ОБНОВЛЯЕМ ПАРАМЕТРЫ (p) ===
        p = np.dot(MU, s_current)
        p_age_effect = np.dot(W_AGE, s_current) * GAMMA * day
        p += p_age_effect
        sigma_p = np.array([10, 10, 1, 0.1, 0.1, 0.1, 0.1, 0.05])
        p += np.random.normal(0, sigma_p)
        p[0] = np.clip(p[0], 70, 200)
        p[1] = np.clip(p[1], 30, 200)
        p[2] = np.clip(p[2], 85, 100)
        p[3:8] = np.clip(p[3:8], 0, 1)

        # === ДОБАВЛЯЕМ В ИСТОРИЮ ===
        p_hourly_day = np.column_stack([
            main_output['ad_pred'],
            main_output['pulse_pred'],
            main_output['spo2_pred'],
            np.full(24, p[3]),
            np.full(24, p[4]),
            np.full(24, p[5]),
            np.full(24, p[6]),
            np.full(24, p[7]),
        ])
        p_hourly_history.extend(p_hourly_day.tolist())

    total_hours = days * 24 + 1
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
def compute_stress_index_for_hour(meteo_df_hour):
    """
    Вычисляет индекс стресса для одного часа.
    """
    norm_dP_dt = np.clip(abs(meteo_df_hour['dP_dt'].iloc[0]) / 1.0, 0, 1)
    norm_dT_dt = np.clip(abs(meteo_df_hour['dT_dt'].iloc[0]) / 5.0, 0, 1)
    norm_front = np.clip(meteo_df_hour['max_front_grad'].iloc[0] / 10.0, 0, 1)
    norm_shear = np.clip(meteo_df_hour['max_wind_shear'].iloc[0] / 40.0, 0, 1)
    norm_turb = np.clip(meteo_df_hour['N_turb'].iloc[0] / 4.0, 0, 1)
    norm_rad = np.clip(meteo_df_hour['shortwave_radiation'].iloc[0] / 200.0, 0, 1)
    norm_dRH_dt = np.clip(abs(meteo_df_hour['rh'].diff().fillna(0).iloc[0]) / 20.0, 0, 1)

    stress_vector = [
        norm_dP_dt,
        norm_dT_dt,
        norm_front,
        norm_shear,
        norm_turb,
        norm_rad,
        norm_dRH_dt
    ]
    weights = np.array([0.2, 0.1, 0.25, 0.2, 0.05, 0.1, 0.1])
    stress_index = np.dot(stress_vector, weights)
    return np.clip(stress_index, 0, 1)

def plot_prediction_extended_corrected(result, filename="отчеты/прогноз_пользователя.png"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    s_hist = result['s_hourly_history']
    p_hist = result['p_hourly_history']
    stress_hist = result['stress_hourly_history']
    phys_dev_hist = result['phys_dev_hourly_history']
    hours_for_p_s = np.arange(len(s_hist))
    hours_for_metrics = np.arange(len(stress_hist))

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('Прогноз физиологического состояния на 7 дней', fontsize=16)

    for i, t in enumerate(TYPE_NAMES):
        axes[0, 0].plot(hours_for_p_s, s_hist[:, i], label=t, marker='o', linewidth=1.5)
    axes[0, 0].set_title('Распределение типов $s(t)$')
    axes[0, 0].set_xlabel('Час')
    axes[0, 0].set_ylabel('Вероятность')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(hours_for_p_s, p_hist[:, 0], label='baseline_ad', color='red', marker='o', linewidth=1.5)
    axes[0, 1].set_title('Прогноз АД (baseline_ad)')
    axes[0, 1].set_xlabel('Час')
    axes[0, 1].set_ylabel('мм рт.ст.')
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(hours_for_p_s, p_hist[:, 1], label='baseline_pulse', color='blue', marker='o', linewidth=1.5)
    axes[1, 0].set_title('Прогноз ЧСС (baseline_pulse)')
    axes[1, 0].set_xlabel('Час')
    axes[1, 0].set_ylabel('уд/мин')
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(hours_for_p_s, s_hist[:, 1], label='s_hypertension', color='orange', marker='o', linewidth=1.5)
    axes[1, 1].set_title('Вероятность гипертонии')
    axes[1, 1].set_xlabel('Час')
    axes[1, 1].set_ylabel('Вероятность')
    axes[1, 1].grid(True, alpha=0.3)

    axes[2, 0].plot(hours_for_metrics, stress_hist, label='Индекс стресса', color='purple', marker='o', linewidth=1.5)
    axes[2, 0].set_title('Индекс метео-стресса')
    axes[2, 0].set_xlabel('Час')
    axes[2, 0].set_ylabel('Стресс')
    axes[2, 0].grid(True, alpha=0.3)

    axes[2, 1].plot(hours_for_metrics, phys_dev_hist, label='Физиологическое отклонение', color='green', marker='o', linewidth=1.5)
    axes[2, 1].set_title('Физиологическое отклонение')
    axes[2, 1].set_xlabel('Час')
    axes[2, 1].set_ylabel('Отклонение')
    axes[2, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"📊 Основной график сохранён: {filename}")

# === ОСНОВНОЙ СКРИПТ ===
def main():
    task_id = sys.argv[5] if len(sys.argv) > 5 else "unknown_task"
    logger = get_script_logger(task_id=task_id, script_name="impact_forecast_script", args=sys.argv)

    try:
        user_id_str = sys.argv[1]
        user_id = int(user_id_str) if user_id_str != "None" else None
        lat = float(sys.argv[2])
        lon = float(sys.argv[3])
        days = int(sys.argv[4]) if len(sys.argv) > 4 else 7

        logger.info(f"🚀 Прогноз влияния погоды: user_id={user_id}, lat={lat}, lon={lon}, days={days}")

        # === ЗАГРУЗКА МЕТЕО-ДАННЫХ ===
        logger.info("🔄 Загрузка метео-данных...")
        from core.utils.api_client import APIClient
        client = APIClient()
        # В impact_forecast_script.py
        # После загрузки метео-данных
        # === РАСЧЁТ ФРОНТОВ (из front_analyzer) ===
        from scripts.meteo._processes.front_analyzer import detect_fronts, extract_front_geometry

        # Пример: расчёт фронтов (нужно передавать сетку данных)
        # df_meteo — содержит 'msl_hPa', 't_c', 'rh', 'wind_speed', ...
        # lat, lon — координаты

        # Заглушка: если max_front_grad не рассчитан — рассчитываем
        if 'max_front_grad' not in df_meteo.columns or df_meteo['max_front_grad'].isna().all():
            # Пример: использовать detect_fronts
            # front_data = detect_fronts(df_meteo, lat, lon)
            # df_meteo['max_front_grad'] = front_data['max_front_grad']
            df_meteo['max_front_grad'] = abs(df_meteo['dT_dt']).rolling(window=4, min_periods=1).mean()

        # Аналогично для max_wind_shear
        if 'max_wind_shear' not in df_meteo.columns or df_meteo['max_wind_shear'].isna().all():
            df_meteo['wind_850_speed'] = np.sqrt(df_meteo['wind_u_850']**2 + df_meteo['wind_v_850']**2)
            df_meteo['max_wind_shear'] = abs(df_meteo['wind_850_speed'] - df_meteo['wind_speed']).rolling(window=4, min_periods=1).max().fillna(0)
        # === ЗАПРОС ПОВЕРХНОСТНЫХ ДАННЫХ (Open-Meteo) ===
        logger.info("🔄 Загрузка поверхностных данных от Open-Meteo...")
        raw_surface_data = client.get_weather_data(lat=lat, lon=lon, provider="open_meteo", days=days)
        if not raw_surface_data:
            raise RuntimeError("❌ Не удалось получить поверхностные данные")

        hourly_surface = raw_surface_data['hourly']
        df_surface = pd.DataFrame({
            'time': pd.to_datetime(hourly_surface['time']),
            'msl_hPa': pd.Series(hourly_surface['pressure_msl']),
            't_c': pd.Series(hourly_surface['temperature_2m']),
            'rh': pd.Series(hourly_surface['relative_humidity_2m']),
            'wind_speed': pd.Series(hourly_surface['wind_speed_10m']),
            'shortwave_radiation': pd.Series(hourly_surface['shortwave_radiation']),
            'apparent_temperature': pd.Series(hourly_surface.get('apparent_temperature', [0]*len(hourly_surface['time']))),
        })

        # === ЗАПРОС ВЫСОТНЫХ ДАННЫХ (GFS Seamless) ===
        logger.info("🔄 Загрузка высотных данных от GFS Seamless...")
        raw_upper_air_data = client.get_weather_data(lat=lat, lon=lon, provider="gfs", days=days)
        if not raw_upper_air_data:
            raise RuntimeError("❌ Не удалось получить высотные данные")

        hourly_upper = raw_upper_air_data['hourly']
        df_upper = pd.DataFrame({
            'time': pd.to_datetime(hourly_upper['time']),
            'temperature_850': pd.Series(hourly_upper.get('temperature_850hPa', [0]*len(hourly_upper['time']))),
            'temperature_700': pd.Series(hourly_upper.get('temperature_700hPa', [0]*len(hourly_upper['time']))),
            'geopotential_height_850': pd.Series(hourly_upper.get('geopotential_height_850hPa', [0]*len(hourly_upper['time']))),
            'geopotential_height_700': pd.Series(hourly_upper.get('geopotential_height_700hPa', [0]*len(hourly_upper['time']))),
            'wind_u_850': pd.Series(hourly_upper.get('u_component_of_wind_850hPa', [0]*len(hourly_upper['time']))),
            'wind_v_850': pd.Series(hourly_upper.get('v_component_of_wind_850hPa', [0]*len(hourly_upper['time']))),
            'cape': pd.Series(hourly_upper.get('cape', [0]*len(hourly_upper['time']))),
        })

        # === ОБЪЕДИНЕНИЕ ПОВЕРХНОСТНЫХ И ВЫСОТНЫХ ДАННЫХ ===
        df_surface = df_surface.set_index('time')
        df_upper = df_upper.set_index('time')
        combined_df = df_surface.join(df_upper, how='inner')
        df_meteo = df_combined.reset_index()

        # === ВЫЧИСЛЕНИЕ НЕДОСТАЮЩИХ ПАРАМЕТРОВ ===
        df_meteo['dP_dt'] = df_meteo['msl_hPa'].diff().fillna(0)
        df_meteo['dT_dt'] = df_meteo['t_c'].diff().fillna(0)
        df_meteo['max_front_grad'] = abs(df_meteo['dT_dt']).rolling(window=4, min_periods=1).mean()
        df_meteo['wind_850_speed'] = np.sqrt(df_meteo['wind_u_850']**2 + df_meteo['wind_v_850']**2)
        df_meteo['max_wind_shear'] = abs(df_meteo['wind_850_speed'] - df_meteo['wind_speed']).rolling(window=4, min_periods=1).max().fillna(0)
        base_radiation = 20.0
        df_meteo['d_rad_pct'] = (df_meteo['shortwave_radiation'] - base_radiation) / base_radiation * 100

        logger.info(f"📊 Получено {len(df_meteo)} строк метео-данных с вычисленными параметрами")

        # === ЗАГРУЗКА ТУРБУЛЕНТНОСТИ ===
        logger.info("🔄 Загрузка данных турбулентности...")
        df_turb = client.get_gfs_turbulence_data_sync(lat, lon, hours=days * 24)
        if df_turb is None or df_turb.empty:
            logger.warning("⚠️ Данные турбулентности отсутствуют, используем заглушку")
            df_turb = pd.DataFrame({
                'time': pd.date_range(start=datetime.now(), periods=days*24, freq='h'),
                'N_turb': [0.1] * (days * 24)
            })

        # === НАСТРОЙКА ПОЛЬЗОВАТЕЛЯ ===
        if user_id:
            logger.info(f"👤 Загрузка профиля пользователя {user_id}...")
            stats = get_user_health_stats(user_id)
            if stats:
                ad = stats.get('avg_systolic', 120)
                pulse = stats.get('avg_heart_rate', 70)
                spo2 = stats.get('avg_spo2', 98.0)
                age = stats.get('age', 30)
                logger.info(f"📊 Профиль пользователя: AD={ad}, HR={pulse}, SpO2={spo2}, Age={age}")
            else:
                logger.warning("⚠️ Профиль пользователя не найден, используем средние значения")
                ad, pulse, spo2, age = 120, 70, 98.0, 30
        else:
            logger.info("👤 Общий прогноз (без пользователя)")
            ad, pulse, spo2, age = 120, 70, 98.0, 30

        # === ИНИЦИАЛИЗАЦИЯ ПАРАМЕТРОВ ===
        p_current, s_current = get_average_profile()
        age_normalized = (age - 20) / 65
        p_current[7] = age_normalized
        p_current[0] = ad
        p_current[1] = pulse
        p_current[2] = spo2

        s_current = align_s_with_p(p_current, s_current, MU)
        logger.info(f"✅ Начальное состояние: AD={ad}, HR={pulse}, SpO2={spo2}, Age={age}")

        # === НАСТРОЙКА КОЭФФИЦИЕНТОВ (ВСЕГДА ЧЕРЕЗ HealthPredictor) ===
        predictor = HealthPredictor()
        R = predictor.get_response_coeffs(user_id, lat, lon, df_meteo)
        logger.info(f"✅ Коэффициенты получены: ad_dp={R['ad_dp']:.3f}")

        # === ЗАПУСК ПРОГНОЗА ===
        logger.info("📈 Вычисление прогноза...")
        result = predict_7day_health_state(p_current, s_current, df_meteo, df_turb, days=days, response_coeffs=R)

        # === СОХРАНЕНИЕ ГРАФИКОВ ===
        graph_path = f"отчеты/impact_forecast_{user_id}_{int(lat*1000)}_{int(lon*1000)}.png"
        plot_prediction_extended_corrected(result, filename=graph_path)

        # === ОЦЕНКА РИСКОВ ===
        risks = []
        for i in range(len(result['p_hourly_history'])):
            p = result['p_hourly_history'][i]
            timestamp = result['meteo_hourly'].iloc[i]['time'] if i < len(result['meteo_hourly']) else datetime.now()

            risk_entry = {"timestamp": timestamp.isoformat(), "risks": {}}
            if p[0] > 140:
                risk_entry["risks"]["hypertensive"] = f"Высокое АД: {p[0]:.1f}"
            elif p[0] < 90:
                risk_entry["risks"]["hypotensive"] = f"Низкое АД: {p[0]:.1f}"

            if p[1] > 100:
                risk_entry["risks"]["cardio"] = f"Тахикардия: {p[1]:.1f}"
            elif p[1] < 50:
                risk_entry["risks"]["cardio"] = f"Брадикардия: {p[1]:.1f}"

            if p[2] < 95:
                risk_entry["risks"]["oxygen"] = f"Низкий СаО2: {p[2]:.1f}%"

            if result['mood_hourly'][i] < -5:
                risk_entry["risks"]["psycho"] = f"Подавленность: {result['mood_hourly'][i]:.1f}"
            if result['arousal_hourly'][i] > 5:
                risk_entry["risks"]["psycho"] = f"Возбуждение: {result['arousal_hourly'][i]:.1f}"

            risks.append(risk_entry)

        # === ВЫВОД В STDOUT (для process_manager) ===
        summary = f"Прогноз на {days} дней: AD={ad:.1f}, HR={pulse:.1f}, SpO2={spo2:.1f}. Риски: {len([r for r in risks if r['risks']])}."

        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:report")
        print(f"USER_ID:{user_id}")
        print(f"FILE_PATH:{graph_path}")
        print(f"MESSAGE:{summary}")
        print(f"RISKS:{json.dumps(risks[:10], ensure_ascii=False)}")  # первые 10 рисков

        logger.info("✅ Прогноз завершён")

    except Exception as e:
        logger.error(f"❌ Ошибка в скрипте: {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Ошибка: {e}")

if __name__ == "__main__":
    main()