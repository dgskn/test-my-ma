import asyncio
import requests
import os
import random
import time
import sys

# --- НАСТРОЙКИ ---

# Загружаем URL и куки из переменных окружения
LABORATORY_API_URL = os.getenv("LABORATORY_API_URL")
TARGET_ORIGIN = os.getenv("TARGET_ORIGIN")
ACCOUNTS = [
    {"name": "Аккаунт 2", "cookie": os.getenv("ACCOUNT_2_COOKIE")},
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

# Список трав для варки по кругу
HERBS_TO_BREW = ["MidnightHenbane", "SerpentRoot", "SylvannaFlytrap"]

# --- ОСНОВНАЯ ЛОГИКА ---

def run_brewing_logic_for_account(account_name, account_cookie, herb_to_brew):
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
        
        response = session.post(LABORATORY_API_URL, json=payload)
        response.raise_for_status()
        request_id += 1
        return response.json()

    try:
        # --- Шаг 1: Получаем статус лаборатории ---
        print(f"-> [{account_name}] 1. Получаем статус лаборатории...")
        status_data = send_request("Status")
        lab_status = status_data.get('result', [{}])[0]
        
        brewing_result = lab_status.get("brewing_result")
        is_ready = lab_status.get("ready", False)

        # --- Шаг 2: Принимаем решение ---
        
        # Если что-то есть в котле и оно готово
        if brewing_result and is_ready:
            print(f"-> [{account_name}] 2. Эликсир готов. Собираем...")
            send_request("CollectElixir")
            print(f"   - Эликсир собран.")
            # После сбора котел точно пуст, можно варить
            should_brew = True
        # Если котел изначально пуст
        elif brewing_result is None:
            print(f"-> [{account_name}] 2. Котел пуст. Можно начинать варку.")
            should_brew = True
        # Если что-то варится, но еще не готово
        else:
            print(f"-> [{account_name}] 2. Эликсир еще в процессе варки. Пропускаем.")
            should_brew = False
            
        # --- Шаг 3: Начинаем новую варку ---
        if should_brew:
            print(f"-> [{account_name}] 3. Начинаем варку эликсира из '{herb_to_brew}'...")
            
            # Кладем траву в котел
            send_request("PutHerbInCaldron", {"kind": herb_to_brew, "amount": 1})
            print(f"   - Трава '{herb_to_brew}' помещена в котел.")
            
            # Начинаем варку
            final_status = send_request("StartBrewing")
            print(f"   - Варка запущена.")

            # Финальная проверка
            if final_status.get('result', [{}])[0].get('brewing_since'):
                print(f"-> ✅ [{account_name}] Успех! Новый эликсир успешно запущен в производство.")
            else:
                 print(f"-> ❌ [{account_name}] ОШИБКА! Не удалось запустить новую варку.")
        
    except Exception as e:
        print(f"!!! [{account_name}] Произошла непредвиденная ошибка: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ---

async def main():
    print(f"\n{'=' * 50}\n--- ЗАПУСК СКРИПТА ВАРКИ ЭЛИКСИРОВ ---\n{'=' * 50}")
    
    # Получаем аргумент из командной строки (0 - это имя скрипта, 1 - первый аргумент)
    if len(sys.argv) < 2:
        print("!!! КРИТИЧЕСКАЯ ОШИБКА: Не передан аргумент с номером травы. Завершение работы.")
        return
        
    try:
        # Превращаем '1', '2' или '3' в индекс списка 0, 1 или 2
        herb_index = int(sys.argv[1]) - 1 
        if not (0 <= herb_index < len(HERBS_TO_BREW)):
            raise ValueError
        herb_to_brew = HERBS_TO_BREW[herb_index]
        print(f"--- Целевая трава для варки в этом запуске: '{herb_to_brew}' ---")
    except (ValueError, IndexError):
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Передан неверный аргумент '{sys.argv[1]}'. Должен быть 1, 2 или 3.")
        return

    active_accounts = [acc for acc in ACCOUNTS if acc.get("cookie")]

    for i, account in enumerate(active_accounts):
        print(f"\n--- НАЧАТА РАБОТА С АККАУНТОМ: {account['name']} ({i+1}/{len(active_accounts)}) ---")
        await asyncio.to_thread(run_brewing_logic_for_account, account['name'], account['cookie'], herb_to_brew)
        
        if i < len(active_accounts) - 1:
            pause_duration = random.randint(2, 5)
            print(f"--- Пауза {pause_duration} секунд перед следующим аккаунтом... ---")
            await asyncio.sleep(pause_duration)
    
    print(f"\n\n--- ВСЕ АККАУНТЫ ОБРАБОТАНЫ. ЗАВЕРШЕНИЕ РАБОТЫ. ---\n{'=' * 50}")

if __name__ == "__main__":
    asyncio.run(main())
