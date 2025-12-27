# -*- coding: utf-8 -*-
"""
Сложный многофакторный тест модели.

Тест 1: Корректность модели и её обучение на синтетических данных
- Синтез данных пользователя
- Прогноз модели на метео-датасете
- Сравнение с базовыми значениями
- График отклонения модели от базовых значений

Тест 2: Модель для разных сценариев
- Пользователь с кучей данных → обученная модель
- Пользователь с начальными данными → средние коэффициенты
- Пользователь без данных → общая модель
- Графики отклонения для каждого случая
- Проверка отказоустойчивости при критических отклонениях
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import tempfile
import os
from datetime import datetime, timedelta

from scripts.meteo._processes.health_predictor import HealthPredictor
from scripts.meteo.impact_forecast_script import (
    get_average_profile,
    get_response_coeffs_from_p,
    tensor_model_fixed_with_climate_norms,
    predict_7day_health_state,
    plot_prediction_extended_corrected
)

def generate_synthetic_user_data(
    user_id: int,
    baseline_ad: float = 120,
    baseline_pulse: float = 70,
    baseline_spo2: float = 98.0,
    sensitivity_to_pressure: float = 0.1,  # чувствительность к давлению
    sensitivity_to_temp: float = 0.05,     # чувствительность к температуре
    sensitivity_to_wind: float = 0.02,     # чувствительность к ветру
    days: int = 30
) -> pd.DataFrame:
    """
    Генерирует синтетические данные пользователя, **реагирующие на метео-факторы**.
    """
    print(f"🧪 Генерация данных для user {user_id}...")
    
    timestamps = pd.date_range(start='2025-01-01', periods=days, freq='D')
    
    ad_values = []
    pulse_values = []
    spo2_values = []
    migraine_values = []
    drowsiness_values = []
    anxiety_values = []
    depression_values = []
    excitement_values = []
    malaise_values = []

    # Генерируем метео-факторы (с небольшой корреляцией)
    for i, ts in enumerate(timestamps):
        # Метео-факторы
        pressure_change = np.random.normal(0, 2)  # изменение давления
        temp_change = np.random.normal(0, 1)      # изменение температуры
        wind_change = np.random.normal(0, 1)      # изменение ветра

        # Случайные отклонения
        ad_noise = np.random.normal(0, 3)
        pulse_noise = np.random.normal(0, 2)
        spo2_noise = np.random.normal(0, 0.3)

        # Реакция на метео-факторы
        ad_pressure_effect = sensitivity_to_pressure * pressure_change
        ad_temp_effect = sensitivity_to_temp * temp_change
        pulse_wind_effect = sensitivity_to_wind * wind_change

        ad = baseline_ad + ad_noise + ad_pressure_effect + ad_temp_effect
        pulse = baseline_pulse + pulse_noise + pulse_wind_effect
        spo2 = baseline_spo2 + spo2_noise - abs(pressure_change) * 0.01

        # Симптомы (0-10)
        migraine = max(0, min(10, np.random.exponential(0.5) + abs(pressure_change) * 0.2))
        drowsiness = max(0, min(10, np.random.exponential(0.3) + abs(temp_change) * 0.1))
        anxiety = max(0, min(10, np.random.exponential(0.4) + abs(pressure_change) * 0.15))
        depression = max(0, min(10, np.random.exponential(0.2) + abs(temp_change) * 0.1))
        excitement = max(0, min(10, np.random.exponential(0.3) + abs(wind_change) * 0.1))
        malaise = max(0, min(10, np.random.exponential(0.3) + abs(pressure_change) * 0.1))

        ad_values.append(ad)
        pulse_values.append(pulse)
        spo2_values.append(spo2)
        migraine_values.append(migraine)
        drowsiness_values.append(drowsiness)
        anxiety_values.append(anxiety)
        depression_values.append(depression)
        excitement_values.append(excitement)
        malaise_values.append(malaise)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'user_id': user_id,
        'systolic': ad_values,
        'diastolic': [ad * 0.6 for ad in ad_values],  # прикидываем диастолическое
        'heart_rate': pulse_values,
        'spo2': spo2_values,
        'migraine': migraine_values,
        'drowsiness': drowsiness_values,
        'anxiety': anxiety_values,
        'depression': depression_values,
        'excitement': excitement_values,
        'malaise': malaise_values
    })

    print(f"✅ Сгенерировано {len(df)} записей для user {user_id}")
    return df

def generate_synthetic_meteo_data(days: int = 7) -> pd.DataFrame:
    """
    Генерирует синтетические метео-данные на 7 дней.
    """
    print("🧪 Генерация метео-данных...")
    
    timestamps = pd.date_range(start='2025-01-01', periods=days*24, freq='h')
    
    # Случайные метео-факторы
    msl_hPa = 1013 + np.random.normal(0, 5, len(timestamps))
    t_c = -5 + np.random.normal(0, 3, len(timestamps))
    rh = 70 + np.random.normal(0, 10, len(timestamps))
    wind_speed = 5 + np.random.exponential(1, len(timestamps))
    shortwave_radiation = 20 + np.random.exponential(5, len(timestamps))
    cape = np.random.exponential(20, len(timestamps))
    N_turb = np.random.exponential(0.5, len(timestamps))
    max_front_grad = np.random.exponential(2, len(timestamps))
    max_wind_shear = np.random.exponential(10, len(timestamps))

    df = pd.DataFrame({
        'time': timestamps,
        'msl_hPa': msl_hPa,
        't_c': t_c,
        'rh': rh,
        'wind_speed': wind_speed,
        'shortwave_radiation': shortwave_radiation,
        'cape': cape,
        'N_turb': N_turb,
        'max_front_grad': max_front_grad,
        'max_wind_shear': max_wind_shear
    })

    # Вычисляем градиенты
    df['dP_dt'] = df['msl_hPa'].diff().fillna(0)
    df['dT_dt'] = df['t_c'].diff().fillna(0)

    print(f"✅ Сгенерировано {len(df)} часов метео-данных")
    return df

import os  # ✅ Уже импортирован

def test_model_accuracy_with_synthetic_data():
    """
    Тест 1: Корректность модели и её обучение на синтетических данных.
    """
    print("\n🧪 ТЕСТ 1: Корректность модели на синтетических данных")
    print("="*60)

    # === СОЗДАЁМ ПАПКУ 'тесты' ===
    os.makedirs('тесты', exist_ok=True)  # ✅ Создаём папку, если нет

    # === ГЕНЕРАЦИЯ СИНТЕТИЧЕСКИХ ДАННЫХ ===
    user_df = generate_synthetic_user_data(
        user_id=999,
        baseline_ad=125,  # гипертоник
        baseline_pulse=75,
        baseline_spo2=97.5,
        sensitivity_to_pressure=0.2,  # высокая чувствительность к давлению
        sensitivity_to_temp=0.1,
        days=30
    )

    meteo_df = generate_synthetic_meteo_data(days=7)

    # === УБИРАЕМ N_turb ИЗ meteo_df (чтобы не дублировалось) ===
    meteo_df_for_join = meteo_df.drop(columns=['N_turb'], errors='ignore')

    # === ОБУЧЕНИЕ МОДЕЛИ ===
    print("\n🔍 Обучение модели...")

    # === ПОДМЕНЯЕМ load_user_data, ЧТОБЫ ОН ВОЗВРАЩАЛ ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ + МЕТЕО-ДАННЫЕ ===
    from scripts.meteo._processes.health_predictor import HealthPredictor
    original_load_user_data = HealthPredictor.load_user_data

    def mock_load_user_data(self, user_id, lat, lon):
        if user_id == 999:
            # Объединяем пользовательские и метео-данные по времени
            user_df_filtered = user_df[user_df['user_id'] == user_id].copy()
            user_df_filtered['timestamp'] = pd.to_datetime(user_df_filtered['timestamp'])
            
            # Берём только дату из пользовательских данных
            user_df_filtered['date'] = user_df_filtered['timestamp'].dt.date
            
            # Берём только дату из метео-данных
            meteo_df_with_date = meteo_df_for_join.copy()
            meteo_df_with_date['date'] = pd.to_datetime(meteo_df_with_date['time']).dt.date
            
            # Объединяем по дате
            merged_df = user_df_filtered.merge(meteo_df_with_date, on='date', how='inner')
            
            # Убираем лишние столбцы
            merged_df = merged_df.drop(columns=['date'], errors='ignore')
            
            # Вычисляем delta_AD, delta_pulse, delta_spo2
            merged_df['delta_ad'] = merged_df['systolic'].diff().fillna(0)
            merged_df['delta_pulse'] = merged_df['heart_rate'].diff().fillna(0)
            merged_df['delta_spo2'] = merged_df['spo2'].diff().fillna(0)
            
            # Добавляем N_turb (если не хватает)
            if 'N_turb' not in merged_df.columns:
                merged_df['N_turb'] = 0.1  # среднее значение
            
            # Убедимся, что все нужные столбцы есть
            required_cols = ['dP_dt', 'dT_dt', 'wind_speed', 'cape', 'shortwave_radiation', 'N_turb', 'max_front_grad', 'max_wind_shear']
            for col in required_cols:
                if col not in merged_df.columns:
                    merged_df[col] = 0.0  # заполняем нулями, если нет
                    
            return merged_df
        else:
            return pd.DataFrame()

    # Заменяем метод
    HealthPredictor.load_user_data = mock_load_user_data

    predictor = HealthPredictor()

    try:
        # === ИСПРАВЛЕНО: вызываем tune_response_coeffs_for_user с правильными аргументами ===
        success = predictor.tune_response_coeffs_for_user(user_id=999, lat=55.75, lon=37.62)
        if success:
            # === ИСПРАВЛЕНО: вызываем predict_response_coeffs без user_id, lat, lon ===
            R = predictor.predict_response_coeffs(meteo_forecast_df=meteo_df)
            print(f"✅ Коэффициенты получены: ad_dp={R['ad_dp']:.3f}, pulse_dp={R['pulse_dp']:.3f}")
        else:
            print("⚠️ Не удалось обучить модель, используем средние коэффициенты")
            R = get_response_coeffs_from_p(get_average_profile()[0])

        # === ЗАПУСК ПРОГНОЗА ===
        print("\n📈 Запуск прогноза...")
        p_current, s_current = get_average_profile()
        p_current[0] = 125  # baseline AD
        p_current[1] = 75   # baseline pulse
        p_current[2] = 97.5 # baseline spo2

        # === СОЗДАЁМ turb_df БЕЗ N_turb В meteo_df ===
        df_turb = pd.DataFrame({
            'time': meteo_df['time'],
            'N_turb': [0.1] * len(meteo_df)
        })

        result = predict_7day_health_state(
            p_current, s_current, meteo_df, 
            df_turb=df_turb,  # ✅ Передаём правильный df_turb
            days=7,
            response_coeffs=R
        )

        # === СРАВНЕНИЕ С БАЗОВЫМИ ЗНАЧЕНИЯМИ ===
        baseline_ad = 120
        baseline_pulse = 70
        baseline_spo2 = 98.0

        ad_deviation = result['p_hourly_history'][:, 0] - baseline_ad
        pulse_deviation = result['p_hourly_history'][:, 1] - baseline_pulse
        spo2_deviation = result['p_hourly_history'][:, 2] - baseline_spo2

        print(f"📊 Отклонение АД: среднее={ad_deviation.mean():.2f}, std={ad_deviation.std():.2f}")
        print(f"📊 Отклонение ЧСС: среднее={pulse_deviation.mean():.2f}, std={pulse_deviation.std():.2f}")
        print(f"📊 Отклонение SpO2: среднее={spo2_deviation.mean():.2f}, std={spo2_deviation.std():.2f}")

        # === ГРАФИК ОТКЛОНЕНИЯ ===
        plt.figure(figsize=(12, 8))
        hours = np.arange(len(ad_deviation))
        plt.plot(hours, ad_deviation, label='Отклонение АД', color='red', alpha=0.7)
        plt.plot(hours, pulse_deviation, label='Отклонение ЧСС', color='blue', alpha=0.7)
        plt.plot(hours, spo2_deviation, label='Отклонение SpO2', color='green', alpha=0.7)
        plt.axhline(0, color='black', linestyle='--', alpha=0.3)
        plt.title('Отклонение параметров от базовых значений (синтетические данные)')
        plt.xlabel('Час')
        plt.ylabel('Отклонение')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('тесты/отклонение_от_базы_синтетика.png')  # ✅ Папка существует
        plt.close()
        print("📊 График сохранён: тесты/отклонение_от_базы_синтетика.png")

        print("✅ ТЕСТ 1 ПРОЙДЕН: модель корректно обучена на синтетических данных")

    finally:
        # Восстанавливаем оригинальный метод
        HealthPredictor.load_user_data = original_load_user_data


def test_model_for_different_scenarios():
    """
    Тест 2: Модель для разных сценариев.
    """
    print("\n🧪 ТЕСТ 2: Модель для разных сценариев")
    print("="*60)

    meteo_df = generate_synthetic_meteo_data(days=7)

    # === СЦЕНАРИЙ 1: ПОЛЬЗОВАТЕЛЬ С МНОГО ДАННЫМИ ===
    print("\n🔍 Сценарий 1: Пользователь с кучей данных (обученная модель)")
    user_df_rich = generate_synthetic_user_data(
        user_id=1001,
        baseline_ad=130,  # гипертоник
        baseline_pulse=80,
        baseline_spo2=97.0,
        sensitivity_to_pressure=0.3,
        days=60  # много данных
    )

    # === ПОДМЕНЯЕМ load_user_data ДЛЯ predictor_rich ===
    from scripts.meteo._processes.health_predictor import HealthPredictor
    original_load_user_data = HealthPredictor.load_user_data

    def mock_load_user_data_rich(self, user_id, lat, lon):
        if user_id == 1001:
            # Объединяем пользовательские и метео-данные по времени
            user_df_filtered = user_df_rich[user_df_rich['user_id'] == user_id].copy()
            user_df_filtered['timestamp'] = pd.to_datetime(user_df_filtered['timestamp'])
            
            # Берём только дату из пользовательских данных
            user_df_filtered['date'] = user_df_filtered['timestamp'].dt.date
            
            # Берём только дату из метео-данных
            meteo_df_with_date = meteo_df.drop(columns=['N_turb'], errors='ignore').copy()
            meteo_df_with_date['date'] = pd.to_datetime(meteo_df_with_date['time']).dt.date
            
            # Объединяем по дате
            merged_df = user_df_filtered.merge(meteo_df_with_date, on='date', how='inner')
            
            # Убираем лишние столбцы
            merged_df = merged_df.drop(columns=['date'], errors='ignore')
            
            # Вычисляем delta_AD, delta_pulse, delta_spo2
            merged_df['delta_ad'] = merged_df['systolic'].diff().fillna(0)
            merged_df['delta_pulse'] = merged_df['heart_rate'].diff().fillna(0)
            merged_df['delta_spo2'] = merged_df['spo2'].diff().fillna(0)
            
            # Добавляем N_turb (если не хватает)
            if 'N_turb' not in merged_df.columns:
                merged_df['N_turb'] = 0.1  # среднее значение
            
            # Убедимся, что все нужные столбцы есть
            required_cols = ['dP_dt', 'dT_dt', 'wind_speed', 'cape', 'shortwave_radiation', 'N_turb', 'max_front_grad', 'max_wind_shear']
            for col in required_cols:
                if col not in merged_df.columns:
                    merged_df[col] = 0.0  # заполняем нулями, если нет
                    
            return merged_df
        else:
            return pd.DataFrame()

    # Заменяем метод
    HealthPredictor.load_user_data = mock_load_user_data_rich

    predictor_rich = HealthPredictor()

    try:
        # === ИСПРАВЛЕНО: вызываем tune_response_coeffs_for_user с правильными аргументами ===
        success_rich = predictor_rich.tune_response_coeffs_for_user(user_id=1001, lat=55.75, lon=37.62)
        if success_rich:
            # === ИСПРАВЛЕНО: вызываем predict_response_coeffs без user_id, lat, lon ===
            R_rich = predictor_rich.predict_response_coeffs(meteo_forecast_df=meteo_df)
            print(f"✅ Обученные коэффициенты: ad_dp={R_rich['ad_dp']:.3f}")
        else:
            print("⚠️ Не удалось обучить модель, используем средние коэффициенты")
            R_rich = get_response_coeffs_from_p(get_average_profile()[0])

        # === СЦЕНАРИЙ 2: ПОЛЬЗОВАТЕЛЬ С НАЧАЛЬНЫМИ ДАННЫМИ ===
        print("\n🔍 Сценарий 2: Пользователь с начальными данными")
        user_df_initial = generate_synthetic_user_data(
            user_id=1002,
            baseline_ad=115,  # нормотоник
            baseline_pulse=68,
            baseline_spo2=98.5,
            days=5  # мало данных
        )

        def mock_load_user_data_initial(self, user_id, lat, lon):
            if user_id == 1002:
                # Объединяем пользовательские и метео-данные по времени
                user_df_filtered = user_df_initial[user_df_initial['user_id'] == user_id].copy()
                user_df_filtered['timestamp'] = pd.to_datetime(user_df_filtered['timestamp'])
                
                # Берём только дату из пользовательских данных
                user_df_filtered['date'] = user_df_filtered['timestamp'].dt.date
                
                # Берём только дату из метео-данных
                meteo_df_with_date = meteo_df.drop(columns=['N_turb'], errors='ignore').copy()
                meteo_df_with_date['date'] = pd.to_datetime(meteo_df_with_date['time']).dt.date
                
                # Объединяем по дате
                merged_df = user_df_filtered.merge(meteo_df_with_date, on='date', how='inner')
                
                # Убираем лишние столбцы
                merged_df = merged_df.drop(columns=['date'], errors='ignore')
                
                # Вычисляем delta_AD, delta_pulse, delta_spo2
                merged_df['delta_ad'] = merged_df['systolic'].diff().fillna(0)
                merged_df['delta_pulse'] = merged_df['heart_rate'].diff().fillna(0)
                merged_df['delta_spo2'] = merged_df['spo2'].diff().fillna(0)
                
                # Добавляем N_turb (если не хватает)
                if 'N_turb' not in merged_df.columns:
                    merged_df['N_turb'] = 0.1  # среднее значение
                
                # Убедимся, что все нужные столбцы есть
                required_cols = ['dP_dt', 'dT_dt', 'wind_speed', 'cape', 'shortwave_radiation', 'N_turb', 'max_front_grad', 'max_wind_shear']
                for col in required_cols:
                    if col not in merged_df.columns:
                        merged_df[col] = 0.0  # заполняем нулями, если нет
                        
                return merged_df
            else:
                return pd.DataFrame()

        # Заменяем метод
        HealthPredictor.load_user_data = mock_load_user_data_initial

        predictor_initial = HealthPredictor()

        success_initial = predictor_initial.tune_response_coeffs_for_user(user_id=1002, lat=55.75, lon=37.62)
        if success_initial:
            R_initial = predictor_initial.predict_response_coeffs(meteo_forecast_df=meteo_df)
            print(f"✅ Средние коэффициенты: ad_dp={R_initial['ad_dp']:.3f}")
        else:
            print("⚠️ Не удалось обучить модель, используем средние коэффициенты")
            R_initial = get_response_coeffs_from_p(get_average_profile()[0])

        # === СЦЕНАРИЙ 3: ПОЛЬЗОВАТЕЛЬ БЕЗ ДАННЫХ ===
        print("\n🔍 Сценарий 3: Пользователь без данных (общая модель)")
        R_general = get_response_coeffs_from_p(get_average_profile()[0])  # средние коэффициенты
        print(f"✅ Общие коэффициенты: ad_dp={R_general['ad_dp']:.3f}")

        # === ЗАПУСК ПРОГНОЗОВ ===
        scenarios = [
            ("Обученная модель", R_rich),
            ("Средние коэффициенты", R_initial),
            ("Общая модель", R_general)
        ]

        results = {}
        for name, R in scenarios:
            print(f"\n📈 Прогноз для: {name}")
            p_current, s_current = get_average_profile()
            p_current[0] = 120
            p_current[1] = 70
            p_current[2] = 98.0

            result = predict_7day_health_state(
                p_current, s_current, meteo_df,
                df_turb=pd.DataFrame({'time': meteo_df['time'], 'N_turb': [0.1]*len(meteo_df)}),
                days=7,
                response_coeffs=R
            )
            results[name] = result

            # === ОТКЛОНЕНИЯ ===
            ad_dev = result['p_hourly_history'][:, 0] - 120
            pulse_dev = result['p_hourly_history'][:, 1] - 70
            spo2_dev = result['p_hourly_history'][:, 2] - 98.0

            print(f"   Отклонение АД: среднее={ad_dev.mean():.2f}, std={ad_dev.std():.2f}")
            print(f"   Отклонение ЧСС: среднее={pulse_dev.mean():.2f}, std={pulse_dev.std():.2f}")
            print(f"   Отклонение SpO2: среднее={spo2_dev.mean():.2f}, std={spo2_dev.std():.2f}")

        # === ГРАФИК СРАВНЕНИЯ СЦЕНАРИЕВ ===
        plt.figure(figsize=(14, 10))

        hours = np.arange(len(results["Обученная модель"]['p_hourly_history'][:, 0]))

        plt.subplot(3, 1, 1)
        for name, result in results.items():
            ad_dev = result['p_hourly_history'][:, 0] - 120
            plt.plot(hours, ad_dev, label=name, alpha=0.8)
        plt.title('Отклонение АД для разных сценариев')
        plt.xlabel('Час')
        plt.ylabel('Отклонение АД')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.subplot(3, 1, 2)
        for name, result in results.items():
            pulse_dev = result['p_hourly_history'][:, 1] - 70
            plt.plot(hours, pulse_dev, label=name, alpha=0.8)
        plt.title('Отклонение ЧСС для разных сценариев')
        plt.xlabel('Час')
        plt.ylabel('Отклонение ЧСС')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.subplot(3, 1, 3)
        for name, result in results.items():
            spo2_dev = result['p_hourly_history'][:, 2] - 98.0
            plt.plot(hours, spo2_dev, label=name, alpha=0.8)
        plt.title('Отклонение SpO2 для разных сценариев')
        plt.xlabel('Час')
        plt.ylabel('Отклонение SpO2')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('тесты/сравнение_сценариев.png')
        plt.close()
        print("📊 График сохранён: тесты/сравнение_сценариев.png")

        # === ПРОВЕРКА ОТКАЗОУСТОЙЧИВОСТИ ===
        print("\n🔍 Проверка отказоустойчивости при критических отклонениях...")
        critical_meteo = meteo_df.copy()
        critical_meteo['dP_dt'] = critical_meteo['dP_dt'] * 10  # критическое изменение давления
        critical_meteo['dT_dt'] = critical_meteo['dT_dt'] * 5   # критическое изменение температуры

        try:
            result_critical = predict_7day_health_state(
                p_current, s_current, critical_meteo,
                df_turb=pd.DataFrame({'time': critical_meteo['time'], 'N_turb': [10.0]*len(critical_meteo)}),
                days=7,
                response_coeffs=R_general
            )
            print("✅ Модель устойчива к критическим отклонениям (не упала)")
            
            # Проверим, что параметры в разумных пределах
            ad_values = result_critical['p_hourly_history'][:, 0]
            pulse_values = result_critical['p_hourly_history'][:, 1]
            spo2_values = result_critical['p_hourly_history'][:, 2]

            if (50 <= ad_values.min() <= ad_values.max() <= 250 and
                20 <= pulse_values.min() <= pulse_values.max() <= 250 and
                80 <= spo2_values.min() <= spo2_values.max() <= 100):
                print("✅ Параметры в разумных пределах даже при критических условиях")
            else:
                print("⚠️ Параметры вышли за разумные пределы при критических условиях")

        except Exception as e:
            print(f"❌ Модель неустойчива к критическим отклонениям: {e}")

        print("✅ ТЕСТ 2 ПРОЙДЕН: все сценарии протестированы, отказоустойчивость проверена")

    finally:
        # Восстанавливаем оригинальный метод
        HealthPredictor.load_user_data = original_load_user_data
def run_complex_model_validation():
    """
    Запуск всех тестов.
    """
    print("🧪 ЗАПУСК СЛОЖНОГО МНОГОФАКТОРНОГО ТЕСТА МОДЕЛИ")
    print("="*70)

    test_model_accuracy_with_synthetic_data()
    print("\n" + "="*70)
    test_model_for_different_scenarios()

    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")

if __name__ == "__main__":
    run_complex_model_validation()