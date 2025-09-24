import asyncio
import websockets
import json
import random
import time
import requests
import os
from datetime import datetime, timezone, timedelta

# --- НАСТРОЙКИ (Читаются из переменных окружения) ---

# Загружаем URL из окружения
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")
PET_API_URL = os.getenv("PET_API_URL")
TARGET_ORIGIN = os.getenv("TARGET_ORIGIN") # URL для заголовка Origin

# Загружаем куки аккаунтов из окружения
ACCOUNTS = [
    {"name": "Аккаунт 1", "cookie": os.getenv("ACCOUNT_1_COOKIE")},
   # {"name": "Аккаунт 2", "cookie": os.getenv("ACCOUNT_2_COOKIE")},
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

# --- Проверка всех переменных окружения ---
# Собираем все переменные, которые должны быть установлены
required_vars = {
    "WEBSOCKET_URL": WEBSOCKET_URL,
    "PET_API_URL": PET_API_URL,
    "TARGET_ORIGIN": TARGET_ORIGIN,
}
for i, acc in enumerate(ACCOUNTS):
    required_vars[f"ACCOUNT_{i+1}_COOKIE"] = acc["cookie"]

# Находим те, которые не установлены
missing_vars = [key for key, value in required_vars.items() if value is None]

if missing_vars:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Следующие переменные окружения не установлены: {', '.join(missing_vars)}")
    print("!!! Пожалуйста, задайте их в настройках хостинга. Завершение работы.")
    exit(1)


# --- ЛОГИКА КОРМЛЕНИЯ ПИТОМЦА ---

def _blocking_pet_logic(account_name, account_cookie):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Origin": TARGET_ORIGIN,  # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
            "Cookie": account_cookie,
            "Content-Type": "application/json"
        }
        with requests.Session() as session:
            session.headers.update(headers)

            print(f"-> [{account_name}] Проверяем статус питомца...")
            payload_status = {"id": 2002, "method": "Status"}
            response_status = session.post(PET_API_URL, json=payload_status) # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
            response_status.raise_for_status()
            # ... (остальная логика функции без изменений)
            data_status = response_status.json()

            fed_today = data_status.get('result', [{}])[0].get('fed_today')
            if fed_today is None:
                print(f"!! [{account_name}] Не удалось получить статус 'fed_today'. Пропускаем кормление.")
                return

            if not fed_today:
                print(f"-> [{account_name}] Питомец голоден. Кормим...")
                payload_feed = {"id": 2003, "method": "Feed"}
                session.post(PET_API_URL, json=payload_feed).raise_for_status() # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ

                print(f"-> [{account_name}] Собираем награду...")
                payload_collect = {"id": 2004, "method": "CollectReward"}
                session.post(PET_API_URL, json=payload_collect).raise_for_status() # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
                
                print(f"-> ✅ [{account_name}] Питомец покормлен, награда собрана!")
            else:
                print(f"-> ✅ [{account_name}] Питомец уже покормлен сегодня.")

    except requests.exceptions.HTTPError as http_err:
        print(f"!!! [{account_name}] Ошибка HTTP при работе с API питомца: {http_err.response.status_code}")
    except requests.exceptions.RequestException as req_err:
        print(f"!!! [{account_name}] Ошибка сети при работе с API питомца: {req_err}")
    except Exception as e:
        print(f"!!! [{account_name}] Непредвиденная ошибка в логике питомца: {e}")

# --- SUPERVISOR И КЛИКЕР (здесь тоже нужно заменить URL) ---

async def supervisor_for_account(account):
    # ... (код до заголовков без изменений) ...
    print(f"\n\n{'=' * 50}\n--- НАЧИНАЕМ РАБОТУ С АККАУНТОМ: {account['name']} ---\n{'=' * 50}")
    
    await feed_pet_for_account(account)
    
    print(f"\n--- НАЧАТА СЕССИЯ КЛИКЕРА для {account['name']} ---")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Origin": TARGET_ORIGIN, # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
        "Cookie": account['cookie']
    }
    while True:
        try:
            # <-- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
            async with websockets.connect(WEBSOCKET_URL, extra_headers=headers, ping_interval=15,
                                          ping_timeout=20) as websocket:
                # ... (остальная логика функции без изменений)
                initial_message = await websocket.recv()
                while not initial_message.startswith('{'): initial_message = await websocket.recv()
                initial_state = json.loads(initial_message)

                energy = initial_state.get('result', [{}])[0].get('available_energy', 0)
                refills = initial_state.get('result', [{}])[0].get('remaining_refills', 0)

                if energy < 100 and refills == 0:
                    print(f"--- Кликер для {account['name']} уже отработал (энергии нет, рефиллов нет). ---")
                    return

                result = await asyncio.gather(main_game_loop(websocket, initial_state, account['name']), receiver(websocket))
                if result[0] == "SUCCESS": return

        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            print(f"--- СЕРВЕР РАЗОРВАЛ СОЕДИНЕНИЕ (Код: {e.code}). Переподключаемся через 5 секунд... ---")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"!!! ГЛОБАЛЬНАЯ ОШИБКА: {e}. Повторная попытка через 10 секунд... ---")
            await asyncio.sleep(10)


# --- ОСНОВНАЯ ЧАСТЬ (убедитесь, что у вас есть все функции) ---
# Убедитесь, что здесь находятся все остальные функции:
# feed_pet_for_account, receiver, perform_taps, main_game_loop

async def feed_pet_for_account(account):
    print(f"\n--- НАЧАТА ПРОВЕРКА ПИТОМЦА для {account['name']} ---")
    await asyncio.to_thread(_blocking_pet_logic, account['name'], account['cookie'])
    print(f"--- ПРОВЕРКА ПИТОМЦА для {account['name']} ЗАВЕРШЕНА ---")

shared_state = {'last_ack_id': 0, 'current_energy': 0}

async def receiver(websocket):
    try:
        async for message in websocket:
            if message == "2":
                await websocket.send("3")
            elif message.startswith("P"):
                await websocket.send("PING")
            try:
                data = json.loads(message)
                if data.get('id') is not None: shared_state['last_ack_id'] = data['id']
                result = data.get('result')
                if isinstance(result, list) and len(result) > 0 and result[0].get('type') == 'AlchemyMachine':
                    if 'available_energy' in result[0]: shared_state['current_energy'] = result[0]['available_energy']
            except (json.JSONDecodeError, AttributeError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"!!! ОШИБКА в receiver: {e}")

async def perform_taps(websocket, start_id, taps_to_do, session_name=""):
    print(f"-> {session_name} Начинаем сессию: {taps_to_do} тапов.")
    request_id, taps_made, chunk_size = start_id, 0, 70
    while taps_made < taps_to_do:
        if not websocket.open: return request_id, False
        for _ in range(chunk_size):
            if taps_made >= taps_to_do: break
            await websocket.send(json.dumps({"id": request_id, "method": "Tap"}))
            request_id += 1;
            taps_made += 1
            await asyncio.sleep(0.01)
        print(f"-> {session_name} Отправлено {taps_made}/{taps_to_do} тапов.")
        if taps_made < taps_to_do: await asyncio.sleep(random.uniform(0.1, 0.3))
    return request_id, True

async def main_game_loop(websocket, initial_state, account_name):
    request_id = 3
    current_refills = initial_state.get('result', [{}])[0].get('remaining_refills', 0)
    shared_state['current_energy'] = initial_state.get('result', [{}])[0].get('available_energy', 0)
    if initial_state.get('result', [{}])[0].get('available_offline_income') is not None:
        print("-> Логика: найден оффлайн-доход. Отправляем клейм...")
        await websocket.send(json.dumps({"id": request_id, "method": "ClaimOfflineIncome"}))
        request_id += 1;
        await asyncio.sleep(2)
        shared_state['current_energy'] = 10500
    while True:
        taps_to_do = 535 if shared_state['current_energy'] >= 10500 else (shared_state['current_energy'] // 20) - 5
        print(
            f"\n--- Новая сессия: Энергии ~{shared_state['current_energy']}, Рефиллов {current_refills}. Планируем основную серию: {taps_to_do} тапов ---")
        if taps_to_do > 10:
            request_id, success = await perform_taps(websocket, request_id, taps_to_do, "Основная серия:")
            if not success: return "RECONNECT"
            last_sent_id = request_id - 1
            print(f"-> Основная серия отправлена. ID: {last_sent_id}. Ждем подтверждения...")
            try:
                async with asyncio.timeout(15):
                    while shared_state.get('last_ack_id', 0) < last_sent_id:
                        if not websocket.open: return "RECONNECT"
                        await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                print("!!! Таймаут ожидания ответа. Переподключаемся.");
                return "RECONNECT"
            print(f"-> Синхронизация прошла. Актуальная энергия: {shared_state['current_energy']}")
            final_taps_to_do = shared_state['current_energy'] // 20
            if final_taps_to_do > 0:
                request_id, success = await perform_taps(websocket, request_id, final_taps_to_do, "Добиваем остатки:")
                if not success: return "RECONNECT"
        print("-> Энергия потрачена. Проверяем рефиллы.")
        await asyncio.sleep(1)
        if current_refills > 0 and account_name != "Аккаунт 2":
            print(f"-> Используем рефилл (осталось {current_refills})...")
            await websocket.send(json.dumps({"id": request_id, "method": "RestoreEnergy"}))
            request_id += 1;
            current_refills -= 1;
            shared_state['current_energy'] = 10500
            print("-> Рефилл использован. Начинаем следующую сессию тапов.")
            await asyncio.sleep(1.5)
        else:
            if account_name == "Аккаунт 2" and current_refills > 0:
                print(f"-> [{account_name}] Пропускаем использование рефилла согласно настройкам.")
            return "SUCCESS"


async def main():
    """
    Основная функция, которая обрабатывает все аккаунты ОДИН РАЗ и завершается.
    """
    print(f"\n{'=' * 50}\n--- ЗАПУСК ЦИКЛА ОБРАБОТКИ АККАУНТОВ ---\n{'=' * 50}")

    for i, account in enumerate(ACCOUNTS):
        await supervisor_for_account(account)
        print(f"\n--- ЗАВЕРШЕНА РАБОТА С АККАУНТОМ: {account['name']} ---")

        if i < len(ACCOUNTS) - 1:
            pause_duration = random.randint(20, 60)
            print(f"--- Пауза {pause_duration} секунд перед следующим аккаунтом... ---")
            await asyncio.sleep(pause_duration)

    print("\n\n--- ВСЕ АККАУНТЫ ОБРАБОТАНЫ. ЗАВЕРШЕНИЕ РАБОТЫ СКРИПТА. ---")


if __name__ == "__main__":

    asyncio.run(main())
