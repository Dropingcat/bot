# -*- coding: utf-8 -*-
"""
Модель прогноза физиологического состояния и рисков.

Реализует:
1. Загрузку данных из БД (пользовательские + метео)
2. Обучение scikit-learn модели для настройки коэффициентов (response_coeffs) под пользователя
3. Прогноз: персональный (на основе его данных) и общий (по умолчанию)
4. Выдачу рисков (гипертоник, гипотоник, вегетативная система и т.д.)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

from core.db.local_db_meteo import get_user_health_log, get_user_health_stats
from core.db.local_db_weather import get_cached_weather
from scripts.meteo._processes.front_analyzer import detect_fronts, extract_front_geometry

logger = logging.getLogger("health_predictor")

# === ПАРАМЕТРЫ МОДЕЛИ ===
DAYS_BACK = 30  # использовать данные за N дней для калибровки
PREDICT_DAYS = 7  # прогноз на 7 дней

# === ИМПЕРИЧЕСКАЯ МОДЕЛЬ (из v5.1) ===
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
GAMMA = 0.01 / 365.0
SIGMA_S = 0.01

def get_response_coeffs_from_p(p):
    """
    Возвращает коэффициенты реакции на метео-факторы, настроенные под пользователя.
    """
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

    # Индивидуальная настройка (как в v5.1)
    R['ad_dp'] = R['ad_dp'] * (1 + w_c * 0.5)
    R['pulse_dp'] = R['pulse_dp'] * (1 + w_s * 0.5)
    R['spo2_p_abs'] = R['spo2_p_abs'] * (1 + w_d * 0.8)
    R['arousal_front'] = R['arousal_front'] * (1 + w_n * 0.7)
    R['arousal_shear'] = R['arousal_shear'] * (1 + w_s * 0.6)
    R['sns_cape'] = R['sns_cape'] * (1 + w_n * 0.5)

    # Коррекция под уровень АД
    if p[0] > 140:
        R['ad_dp'] = abs(R['ad_dp']) * 1.8
    elif p[0] < 90:
        R['ad_dp'] = -abs(R['ad_dp']) * 1.5

    return R

def align_s_with_p(p_current, s_current, MU, iterations=5):
    """
    Согласование s и p (из v5.1).
    """
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

def evolve_s(s_current, stress_index, phys_dev, days_elapsed, age_normalized):
    """
    Эволюция типа s (из v5.1).
    """
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

class HealthPredictor:
    def __init__(self):
        # Модель для настройки коэффициентов
        self.coeff_model = Ridge(alpha=1.0)  # регуляризация для стабильности
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.is_fitted = False

    def load_user_data(self, user_id: int, lat: float, lon: float) -> pd.DataFrame:
        """
        Загружает данные пользователя и соответствующие метео-данные.
        """
        logger.info(f"🔍 Загрузка данных для user {user_id}...")

        # Получаем данные самочувствия
        start_date = (datetime.now() - timedelta(days=DAYS_BACK)).isoformat()
        end_date = datetime.now().isoformat()
        health_logs = get_user_health_log(user_id, start_date, end_date)

        if not health_logs:
            logger.warning(f"❌ Нет данных самочувствия для user {user_id}")
            return pd.DataFrame()

        df = pd.DataFrame(health_logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Загружаем метео-данные
        meteo_data_list = []
        for _, row in df.iterrows():
            ts = row['timestamp'].isoformat()
            meteo = get_cached_weather(lat, lon, row['timestamp'], source="open_meteo")
            if meteo:
                meteo_data_list.append({
                    'timestamp': row['timestamp'],
                    'msl_hPa': meteo.get('pressure_msl', [0])[0] if 'pressure_msl' in meteo else 0,
                    't_c': meteo.get('temperature', [0])[0] if 'temperature' in meteo else 0,
                    'rh': meteo.get('relative_humidity', [0])[0] if 'relative_humidity' in meteo else 0,
                    'wind_speed': meteo.get('wind_speed', [0])[0] if 'wind_speed' in meteo else 0,
                    'cape': meteo.get('cape', [0])[0] if 'cape' in meteo else 0,
                    'shortwave_radiation': meteo.get('shortwave_radiation', [0])[0] if 'shortwave_radiation' in meteo else 0,
                    'N_turb': meteo.get('N_turb', [0])[0] if 'N_turb' in meteo else 0,
                    'max_front_grad': meteo.get('max_front_grad', [0])[0] if 'max_front_grad' in meteo else 0,
                    'max_wind_shear': meteo.get('max_wind_shear', [0])[0] if 'max_wind_shear' in meteo else 0,
                })
            else:
                meteo_data_list.append({
                    'timestamp': row['timestamp'],
                    'msl_hPa': np.nan,
                    't_c': np.nan,
                    'rh': np.nan,
                    'wind_speed': np.nan,
                    'cape': np.nan,
                    'shortwave_radiation': np.nan,
                    'N_turb': np.nan,
                    'max_front_grad': np.nan,
                    'max_wind_shear': np.nan,
                })

        meteo_df = pd.DataFrame(meteo_data_list)
        meteo_df['dP_dt'] = meteo_df['msl_hPa'].diff().fillna(0)
        meteo_df['dT_dt'] = meteo_df['t_c'].diff().fillna(0)

        # === РАСЧЁТ ФРОНТОВ (если есть данные) ===
        from scripts.meteo._processes.front_analyzer import detect_fronts, extract_front_geometry
        for i, row in meteo_df.iterrows():
            # Пример: используем давление и температуру для расчёта фронта
            # В реальности: нужно передавать сетку данных (не только точку)
            # Пока используем заглушку
            meteo_df.at[i, 'max_front_grad'] = meteo_df.at[i, 'max_front_grad'] or 0.0

        # Объединяем
        df = df.merge(meteo_df, on='timestamp', how='inner')

        logger.info(f"✅ Загружено {len(df)} записей для user {user_id}")
        return df
    def prepare_coeff_tuning_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Подготавливает X (метео-факторы) и y (реакции пользователя: delta_AD, delta_pulse...) для обучения coeff_model.
        """
        # X: метео-факторы
        X_cols = ['dP_dt', 'dT_dt', 'wind_speed', 'cape', 'shortwave_radiation', 'N_turb', 'max_front_grad', 'max_wind_shear']
        X = df[X_cols].fillna(0).values  # (N, 8)

        # y: реакции (изменения) физиологических параметров
        # delta_AD = AD(t) - AD(t-1), и т.д.
        df['delta_ad'] = df['systolic'].diff().fillna(0)
        df['delta_pulse'] = df['heart_rate'].diff().fillna(0)
        df['delta_spo2'] = df['spo2'].diff().fillna(0)

        y_cols = ['delta_ad', 'delta_pulse', 'delta_spo2']
        y = df[y_cols].values  # (N, 3)

        # Масштабируем
        X_scaled = self.scaler_X.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(y)

        return X_scaled, y_scaled

    def tune_response_coeffs_for_user(self, user_id, lat, lon):
        df = self.load_user_data(user_id, lat, lon)
        if df.empty:
            logger.warning(f"❌ Нет данных для настройки коэффициентов user {user_id}")
            return None

        X, y = self.prepare_coeff_tuning_data(df)

        if len(X) < 10:
            logger.warning(f"❌ Мало данных ({len(X)}) для настройки коэффициентов")
            return None

        try:
            # Логируем первые строки X и y
            logger.info(f"📊 Первые 5 строк X: {X[:5]}")
            logger.info(f"📊 Первые 5 строк y: {y[:5]}")

            self.coeff_model.fit(X, y)
            self.is_fitted = True
            logger.info(f"✅ Модель настройки коэффициентов обучена для user {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обучения coeff_model: {e}")
            return None
    def predict_response_coeffs(self, meteo_forecast_df: pd.DataFrame) -> Dict:
        """
        Предсказывает коэффициенты (response_coeffs) для будущих метео-условий.
        """
        if not self.is_fitted:
            logger.warning("⚠️ coeff_model не обучена, используем средние коэффициенты")
            return get_response_coeffs_from_p(MU[:, 0])

        # Подготавливаем X для прогноза
        X_cols = ['dP_dt', 'dT_dt', 'wind_speed', 'cape', 'shortwave_radiation', 'N_turb', 'max_front_grad', 'max_wind_shear']
        X = meteo_forecast_df[X_cols].fillna(0).values  # (168, 8)
        X_scaled = self.scaler_X.transform(X)

        # Предсказываем реакции (y_pred_scaled) -> (168, 3)
        y_pred_scaled = self.coeff_model.predict(X_scaled)
        # y_pred = self.scaler_y.inverse_transform(y_pred_scaled)  # (168, 3) - реальные дельты

        # --- УСЛОЖНЕНИЕ: как из y_pred получить новые R? ---
        # Это **напрямую невозможно**, т.к. R влияет на динамику, а не на мгновенные реакции.
        # Поэтому: используем **усреднённые** R, **настроенные** на **среднюю чувствительность** пользователя.

        # Извлекаем средние реакции
        avg_delta_ad = y_pred_scaled[:, 0].mean()
        avg_delta_pulse = y_pred_scaled[:, 1].mean()
        avg_delta_spo2 = y_pred_scaled[:, 2].mean()

        # Используем эти средние для коррекции R_BASE
        R = get_response_coeffs_from_p(MU[:, 0])  # начальные коэффициенты (здоровый)

        # Пример: если avg_delta_ad > 0, пользователь чувствителен к давлению -> увеличиваем R['ad_dp']
        R['ad_dp'] *= (1 + avg_delta_ad * 0.1)  # гипотетический коэффициент
        R['pulse_dp'] *= (1 + avg_delta_pulse * 0.05)
        R['spo2_p_abs'] *= (1 + avg_delta_spo2 * 0.05)

        logger.info(f"✅ Коэффициенты скорректированы: ad_dp={R['ad_dp']:.3f}, pulse_dp={R['pulse_dp']:.3f}")
        return R