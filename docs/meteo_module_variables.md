# Модуль метео-анализа (`scripts/meteo/`) — переменные и функции

## Таблицы в `local_db_meteo.db`

### 1. `user_profiles`
| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | INTEGER | ID пользователя |
| `health_category` | TEXT | `'hypertensive', 'hypotensive', 'sensitive', 'normal'` |
| `age` | INTEGER | Возраст |
| `weight` | REAL | Вес |
| `height` | REAL | Рост |
| `baseline_systolic` | REAL | Базовое систолическое АД |
| `baseline_diastolic` | REAL | Базовое диастолическое АД |
| `baseline_heart_rate` | REAL | Базовый пульс |
| `baseline_spo2` | REAL | Базовый СаО2 |
| `baseline_symptoms` | TEXT | JSON: `{"migraine": 0, "drowsiness": 0, ...}` |

### 2. `user_health_log`
| Поле | Тип | Описание |
|------|-----|----------|
| `log_id` | INTEGER | ID записи |
| `user_id` | INTEGER | ID пользователя |
| `timestamp` | DATETIME | Время измерения |
| `systolic` | REAL | Систолическое АД |
| `diastolic` | REAL | Диастолическое АД |
| `heart_rate` | INTEGER | Пульс |
| `spo2` | REAL | Насыщение кислородом |
| `migraine` | INTEGER | Мигрень (0-10) |
| `drowsiness` | INTEGER | Сонливость (0-10) |
| `anxiety` | INTEGER | Тревожность (0-10) |
| `depression` | INTEGER | Подавленность (0-10) |
| `excitement` | INTEGER | Возбуждение (0-10) |
| `malaise` | INTEGER | Недомогание (0-10) |
| `comment` | TEXT | Комментарий |

### 3. `front_analysis`
| Поле | Тип | Описание |
|------|-----|----------|
| `analysis_id` | INTEGER | ID анализа |
| `lat`, `lon` | REAL | Координаты |
| `timestamp` | DATETIME | Время анализа |
| `pressure_gradient` | REAL | Градиент давления |
| `temperature_gradient` | REAL | Градиент температуры |
| `wind_oscillation` | REAL | Колебания ветра |
| `baric_anomaly` | REAL | Барическая аномалия |
| `front_distance_km` | REAL | Расстояние до фронта |
| `front_direction` | TEXT | Направление фронта |
| `front_type` | TEXT | `'warm', 'cold', 'occluded', 'stationary'` |
| `data_json` | TEXT | Все данные в JSON |

### 4. `health_impact_prediction`
| Поле | Тип | Описание |
|------|-----|----------|
| `prediction_id` | INTEGER | ID прогноза |
| `user_id` | INTEGER | ID пользователя |
| `timestamp` | DATETIME | Время прогноза |
| `risk_level` | TEXT | `'low', 'medium', 'high', 'critical'` |
| `risk_category` | TEXT | `'hypertensive', 'hypotensive', 'cardio', 'oxygen', 'psycho'` |
| `risk_comment` | TEXT | Комментарий |
| `risk_score` | REAL | Оценка риска (0.0 - 1.0) |
| `forecast_json` | TEXT | Детализированный прогноз |

---

## Функции

### `save_user_profile(user_id, profile_data)`
Сохраняет профиль пользователя.

### `get_user_profile(user_id)`
Получает профиль пользователя.

### `save_user_health_log(...)`
Сохраняет запись в журнал самочувствия.

### `get_user_health_log(user_id, start_date, end_date)`
Получает журнал за период.

### `get_user_health_stats(user_id)`
Получает средние значения самочувствия.

### `save_front_analysis(lat, lon, timestamp, analysis_data)`
Сохраняет анализ фронтов.

### `get_recent_front_analysis(lat, lon, hours_back)`
Получает анализ фронтов за N часов.

### `save_health_impact_prediction(user_id, timestamp, prediction_data)`
Сохраняет прогноз влияния.

### `get_user_health_predictions(user_id, start_date, end_date)`
Получает прогнозы за период.