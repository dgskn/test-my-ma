import asyncio
import requests
import os
import random
import time

# --- НАСТРОЙКИ ---

# Загружаем URL и куки из переменных окружения
PET_API_URL = os.getenv("PET_API_URL")
QUEST_API_URL = os.getenv("QUEST_API_URL")
TARGET_ORIGIN = os.getenv("TARGET_ORIGIN")
ACCOUNTS = [
    {"name": "Аккаунт 1", "cookie": os.getenv("ACCOUNT_1_COOKIE")},
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

# --- ЛОГИКА ЕЖЕДНЕВНЫХ ЗАДАЧ ---

def run_daily_tasks_for_account(account_name, account_cookie):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Origin": TARGET_ORIGIN,
        "Cookie": account_cookie,
        "Content-Type": "application/json"
    })

    # --- ЧАСТЬ 1: КОРМЛЕНИЕ ПИТОМЦА ---
    try:
        print(f"-> [{account_name}] 1. Проверяем статус питомца...")
        payload_status = {"id": 2002, "method": "Status"}
        response_status = session.post(PET_API_URL, json=payload_status)
        response_status.raise_for_status()
        data_status = response_status.json()
        fed_today = data_status.get('result', [{}])[0].get('fed_today')

        if fed_today is False:
            print(f"-> [{account_name}] Питомец голоден. Кормим...")
            payload_feed = {"id": 2003, "method": "Feed"}
            session.post(PET_API_URL, json=payload_feed).raise_for_status()
            payload_collect = {"id": 2004, "method": "CollectReward"}
            session.post(PET_API_URL, json=payload_collect).raise_for_status()
            print(f"-> ✅ [{account_name}] Питомец покормлен, награда собрана!")
        else:
            print(f"-> ✅ [{account_name}] Питомец уже покормлен сегодня.")
    except Exception as e:
        print(f"!!! [{account_name}] Ошибка в логике питомца: {e}")
    
    print("-" * 20) # Разделитель
    time.sleep(1)

    # --- ЧАСТЬ 2: СБОР НАГРАД ЗА КВЕСТЫ ---
    try:
        print(f"-> [{account_name}] 2. Проверяем статус ежедневных заданий...")
        payload_status = {"id": 2001, "method": "TapperDailiesStatus"}
        response_status = session.post(QUEST_API_URL, json=payload_status)
        response_status.raise_for_status()
        data = response_status.json()

        result = data.get('result', [{}])[0]
        progress = result.get('progress', {})
        claimed = result.get('claimed', [])

        # Словарь с квестами: { 'название_в_API': требуемый_прогресс }
        quests_to_check = {
            "Tap": 3000,
            "TapperPlayGames": 3,
            "TapperWinGames": 1
        }

        for quest_name, required_progress in quests_to_check.items():
            current_progress = progress.get(quest_name, 0)
            
            if current_progress >= required_progress:
                if quest_name not in claimed:
                    print(f"   - Выполнен квест '{quest_name}'. Получаем награду...")
                    payload_claim = {"id": random.randint(2002, 2999), "method": "ClaimTapperDaily", "params": quest_name}
                    session.post(QUEST_API_URL, json=payload_claim).raise_for_status()
                    print(f"   -> ✅ Награда за '{quest_name}' успешно получена!")
                    time.sleep(random.uniform(0.5, 1))
                else:
                    print(f"   - ✅ Награда за '{quest_name}' уже была получена ранее.")
            else:
                 print(f"   - ⏳ Квест '{quest_name}' еще не выполнен ({current_progress}/{required_progress}).")

    except Exception as e:
        print(f"!!! [{account_name}] Ошибка в логике заданий: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ---

async def main():
    print(f"\n{'=' * 50}\n--- ЗАПУСК СКРИПТА ЕЖЕДНЕВНЫХ ЗАДАЧ ---\n{'=' * 50}")
    
    active_accounts = [acc for acc in ACCOUNTS if acc.get("cookie")]

    for i, account in enumerate(active_accounts):
        print(f"\n--- НАЧАТА РАБОТА С АККАУНТОМ: {account['name']} ({i+1}/{len(active_accounts)}) ---")
        await asyncio.to_thread(run_daily_tasks_for_account, account['name'], account['cookie'])
        
        if i < len(active_accounts) - 1:
            pause_duration = random.randint(2, 5)
            print(f"--- Пауза {pause_duration} секунд перед следующим аккаунтом... ---")
            await asyncio.sleep(pause_duration)
    
    print(f"\n\n--- ВСЕ АККАУНТЫ ОБРАБОТАНЫ. ЗАВЕРШЕНИЕ РАБОТЫ. ---\n{'=' * 50}")

if __name__ == "__main__":
    asyncio.run(main())
