import asyncio
import requests
import os
from datetime import datetime, timezone, timedelta
import random

# --- НАСТРОЙКИ ---

# Загружаем URL и куки из переменных окружения
GARDEN_API_URL = os.getenv("GARDEN_API_URL")
TARGET_ORIGIN = os.getenv("TARGET_ORIGIN")
ACCOUNTS = [
    {"name": "Аккаунт 1", "cookie": os.getenv("ACCOUNT_1_COOKIE")},
    #{"name": "Аккаунт 2", "cookie": os.getenv("ACCOUNT_2_COOKIE")},
    {"name": "Аккаунт 3", "cookie": os.getenv("ACCOUNT_3_COOKIE")},
    {"name": "Аккаунт 4", "cookie": os.getenv("ACCOUNT_4_COOKIE")},
    {"name": "Аккаунт 5", "cookie": os.getenv("ACCOUNT_5_COOKIE")},
    {"name": "Аккаунт 6", "cookie": os.getenv("ACCOUNT_6_COOKIE")},
    {"name": "Аккаунт 7", "cookie": os.getenv("ACCOUNT_7_COOKIE")},
    {"name": "Аккаунт 8", "cookie": os.getenv("ACCOUNT_8_COOKIE")},
    {"name": "Аккаунт 9", "cookie": os.getenv("ACCOUNT_9_COOKIE")},
    {"name": "Аккаунт 10", "cookie": os.getenv("ACCOUNT_10_COOKIE")},
    {"name": "Аккаунт 11", "cookie": os.getenv("ACCOUNT_11_COOKIE")},
]

# Травы, которые будем сажать (индекс соответствует номеру грядки)
HERBS_TO_PLANT = ["MidnightHenbane", "SerpentRoot", "SylvannaFlytrap"]
GROWTH_DURATION_HOURS = 8

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def parse_time(time_str):
    """Обрезает и парсит строку времени, устойчиво к ошибкам."""
    try:
        # Обрезаем до 6 знаков после точки для совместимости
        if '.' in time_str:
            parts = time_str.split('.')
            parts[1] = parts[1][:6]
            time_str = '.'.join(parts)
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None

# --- ОСНОВНАЯ ЛОГИКА ---

def run_garden_logic_for_account(account_name, account_cookie):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Origin": TARGET_ORIGIN,
        "Cookie": account_cookie,
        "Content-Type": "application/json"
    })
    
    request_id = 2001
    
    def send_request(method, params=None):
        nonlocal request_id
        payload = {"id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        
        response = session.post(GARDEN_API_URL, json=payload)
        response.raise_for_status()
        request_id += 1
        return response.json()

    try:
        # --- Шаг 1: Инициализация и статус ---
        print(f"-> [{account_name}] 1. Получаем статус сада...")
        status_data = send_request("Status")
        beds = status_data.get('result', [{}])[0].get('beds', [])
        
        if not beds:
            print(f"!!! [{account_name}] Ошибка: не удалось получить данные о грядках. Пропускаем аккаунт.")
            return

        # --- Шаг 2: Логика ожидания ---
        planted_beds = [bed for bed in beds if bed is not None]
        
        if planted_beds:
            harvest_times = [parse_time(bed[1]) + timedelta(hours=GROWTH_DURATION_HOURS) for bed in planted_beds]
            latest_harvest_time = max(t for t in harvest_times if t is not None)
            now_utc = datetime.now(timezone.utc)

            wait_seconds = (latest_harvest_time - now_utc).total_seconds()
            
            if wait_seconds > 0:
                print(f"-> [{account_name}] 2. Сад еще не созрел. Ожидаем {int(wait_seconds // 60)} мин {int(wait_seconds % 60)} сек...")
                time.sleep(wait_seconds)
            else:
                print(f"-> [{account_name}] 2. Сад созрел. Начинаем сбор.")
        else:
             print(f"-> [{account_name}] 2. Сад пуст. Переходим к посадке.")

        # --- Шаг 3: Цикл сбора ---
        # Получаем свежий статус, чтобы убедиться, что всё созрело
        current_status_data = send_request("Status")
        beds_to_check = current_status_data.get('result', [{}])[0].get('beds', [])
        
        beds_to_collect = [i for i, bed in enumerate(beds_to_check) if bed is not None]

        if beds_to_collect:
            print(f"-> [{account_name}] 3. Собираем урожай с грядок: {beds_to_collect}...")
            for bed_index in beds_to_collect:
                print(f"   - Собираем грядку #{bed_index}...")
                send_request("CollectHerb", bed_index)
                send_request("Status") # Имитируем запрос статуса после каждого действия
                time.sleep(random.uniform(0.3, 0.5))

        # --- Шаг 4: Цикл посадки ---
        final_status_before_plant = send_request("Status")
        beds_to_plant = [i for i, bed in enumerate(final_status_before_plant.get('result', [{}])[0].get('beds', [])) if bed is None]

        if beds_to_plant:
            print(f"-> [{account_name}] 4. Сажаем новые растения на грядки: {beds_to_plant}...")
            last_status = None
            for bed_index in beds_to_plant:
                herb_to_plant = HERBS_TO_PLANT[bed_index]
                print(f"   - Сажаем '{herb_to_plant}' на грядку #{bed_index}...")
                params = {"herb": herb_to_plant}
                # API требует параметр "bed" только для 2-й и 3-й грядки
                if bed_index > 0:
                    params["bed"] = bed_index
                send_request("PlantHerb", params)
                last_status = send_request("Status") # Сохраняем последний статус
                time.sleep(random.uniform(0.3, 0.5))
            
            # --- Шаг 5: Финальная проверка ---
            if last_status:
                final_beds = last_status.get('result', [{}])[0].get('beds', [])
                if all(bed is not None for bed in final_beds):
                    print(f"-> ✅ [{account_name}] 5. Успех! Все грядки успешно собраны и засажены.")
                else:
                    print(f"-> ❌ [{account_name}] 5. КРИТИЧЕСКАЯ ОШИБКА! Не все грядки были засажены. Требуется проверка.")
            else: # Если ничего не сажали, проверяем, что всё собрано
                if not beds_to_collect:
                    print(f"-> ✅ [{account_name}] 5. Успех! Сад уже был пуст и ничего не требовалось делать.")
                else:
                    print(f"-> ❌ [{account_name}] 5. ОШИБКА! Что-то пошло не так после сбора.")

    except Exception as e:
        print(f"!!! [{account_name}] Произошла непредвиденная ошибка: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ---

async def main():
    print(f"\n{'=' * 50}\n--- ЗАПУСК СКРИПТА СБОРА УРОЖАЯ ---\n{'=' * 50}")
    
    active_accounts = [acc for acc in ACCOUNTS if acc.get("cookie")]

    for i, account in enumerate(active_accounts):
        print(f"\n--- НАЧАТА РАБОТА С АККАУНТОМ: {account['name']} ({i+1}/{len(active_accounts)}) ---")
        # Запускаем блокирующую логику в отдельном потоке
        await asyncio.to_thread(run_garden_logic_for_account, account['name'], account['cookie'])
        
        if i < len(active_accounts) - 1:
            pause_duration = random.randint(20, 60)
            print(f"--- Пауза {pause_duration} секунд перед следующим аккаунтом... ---")
            await asyncio.sleep(pause_duration)
    
    print(f"\n\n--- ВСЕ АККАУНТЫ ОБРАБОТАНЫ. ЗАВЕРШЕНИЕ РАБОТЫ. ---\n{'=' * 50}")

if __name__ == "__main__":
    asyncio.run(main())
