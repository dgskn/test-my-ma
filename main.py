import asyncio
import websockets
import json
import random
import time
import requests
import os
from datetime import datetime, timezone, timedelta

# --- НАСТРОЙКИ ---
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")
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

# --- Проверка всех переменных окружения ---
required_vars = {
    "WEBSOCKET_URL": WEBSOCKET_URL,
    "TARGET_ORIGIN": TARGET_ORIGIN,
}
for i, acc in enumerate(ACCOUNTS):
    if acc["cookie"] is not None:
        required_vars[f"ACCOUNT_{i+1}_COOKIE"] = acc["cookie"]

missing_vars = [key for key, value in required_vars.items() if value is None]

if missing_vars:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Следующие переменные окружения не установлены: {', '.join(missing_vars)}")
    exit(1)


# --- ЛОГИКА КЛИКЕРА ---
shared_state = {'last_ack_id': 0, 'current_energy': 0}

async def receiver(websocket):
    try:
        async for message in websocket:
            if message == "2": await websocket.send("3")
            elif message.startswith("P"): await websocket.send("PING")
            try:
                data = json.loads(message)
                if data.get('id') is not None: shared_state['last_ack_id'] = data['id']
                result = data.get('result')
                if isinstance(result, list) and len(result) > 0 and result[0].get('type') == 'AlchemyMachine':
                    if 'available_energy' in result[0]: shared_state['current_energy'] = result[0]['available_energy']
            except (json.JSONDecodeError, AttributeError): pass
    except websockets.exceptions.ConnectionClosed: pass
    except Exception as e: print(f"!!! ОШИБКА в receiver: {e}")

async def perform_taps(websocket, start_id, taps_to_do, session_name=""):
    print(f"-> {session_name} Начинаем сессию: {taps_to_do} тапов.")
    request_id, taps_made, chunk_size = start_id, 0, 70
    while taps_made < taps_to_do:
        if not websocket.open: return request_id, False
        for _ in range(chunk_size):
            if taps_made >= taps_to_do: break
            await websocket.send(json.dumps({"id": request_id, "method": "Tap"}))
            request_id += 1; taps_made += 1
            await asyncio.sleep(0.01)
        print(f"-> {session_name} Отправлено {taps_made}/{taps_to_do} тапов.")
        if taps_made < taps_to_do: await asyncio.sleep(random.uniform(0.1, 0.3))
    return request_id, True

async def main_game_loop(websocket, initial_state, account_name, refill_tracker):
    request_id = 3
    current_refills = initial_state.get('result', [{}])[0].get('remaining_refills', 0)
    shared_state['current_energy'] = initial_state.get('result', [{}])[0].get('available_energy', 0)

    if initial_state.get('result', [{}])[0].get('available_offline_income') is not None:
        print("-> Логика: найден оффлайн-доход. Отправляем клейм...")
        await websocket.send(json.dumps({"id": request_id, "method": "ClaimOfflineIncome"}))
        request_id += 1; await asyncio.sleep(2)
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
                print("!!! Таймаут ожидания ответа. Переподключаемся."); return "RECONNECT"
            print(f"-> Синхронизация прошла. Актуальная энергия: {shared_state['current_energy']}")
            final_taps_to_do = shared_state['current_energy'] // 20
            if final_taps_to_do > 0:
                request_id, success = await perform_taps(websocket, request_id, final_taps_to_do, "Добиваем остатки:")
                if not success: return "RECONNECT"
        
        print("-> Энергия потрачена. Проверяем рефиллы.")
        await asyncio.sleep(1)

        if current_refills > 0:
            # Проверка на баг перед использованием рефилла
            if refill_tracker['used'] >= refill_tracker['initial']:
                print(f"-> ❌ [{account_name}] ОБНАРУЖЕН БАГ! Попытка использовать рефилл ({refill_tracker['used'] + 1}) сверх начального лимита ({refill_tracker['initial']}). Прерываем работу.")
                return "SUCCESS" # Безопасно завершаем

            print(f"-> Используем рефилл ({refill_tracker['used'] + 1}/{refill_tracker['initial']})...")
            await websocket.send(json.dumps({"id": request_id, "method": "RestoreEnergy"}))
            request_id += 1
            current_refills -= 1
            refill_tracker['used'] += 1 # Увеличиваем наш надежный счетчик
            shared_state['current_energy'] = 10500
            print("-> Рефилл использован. Начинаем следующую сессию тапов.")
            await asyncio.sleep(1.5)
        else:
            return "SUCCESS"

async def supervisor_for_account(account):
    print(f"\n\n{'=' * 50}\n--- НАЧАТА СЕССИЯ КЛИКЕРА для {account['name']} ---\n{'=' * 50}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Origin": TARGET_ORIGIN,
        "Cookie": account['cookie']
    }
    
    # Получаем начальное состояние для защиты от бага
    try:
        # Увеличиваем таймаут для первоначального подключения
        async with asyncio.timeout(30):
             async with websockets.connect(WEBSOCKET_URL, extra_headers=headers, ping_interval=15, ping_timeout=20) as websocket:
                initial_message = await websocket.recv()
                while not initial_message.startswith('{'): initial_message = await websocket.recv()
                initial_state = json.loads(initial_message)
                initial_refills = initial_state.get('result', [{}])[0].get('remaining_refills', 0)
                print(f"-> Начальное состояние: {initial_state.get('result', [{}])[0].get('available_energy', 0)} энергии, {initial_refills} рефиллов.")
    except Exception as e:
        print(f"!!! [{account['name']}] Не удалось получить начальное состояние: {e}. Пропускаем аккаунт.")
        return

    # Создаем "надежный" счетчик рефиллов
    refill_tracker = {'initial': initial_refills, 'used': 0}

    # Цикл реконнектов
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URL, extra_headers=headers, ping_interval=15, ping_timeout=20) as websocket:
                im = await websocket.recv();
                while not im.startswith('{'): im = await websocket.recv()
                current_initial_state = json.loads(im)
                
                energy = current_initial_state.get('result', [{}])[0].get('available_energy', 0)
                refills = current_initial_state.get('result', [{}])[0].get('remaining_refills', 0)

                if energy < 100 and refills == 0 and refill_tracker['used'] >= refill_tracker['initial']:
                    print(f"--- Кликер для {account['name']} уже отработал. ---")
                    return

                # Передаем счетчик в основной игровой цикл
                result = await asyncio.gather(main_game_loop(websocket, current_initial_state, account['name'], refill_tracker), receiver(websocket))
                if result[0] == "SUCCESS": return

        except Exception as e:
            print(f"!!! ГЛОБАЛЬНАЯ ОШИБКА КЛИКЕРА: {e}. Повторная попытка через 10 секунд... ---")
            await asyncio.sleep(10)

async def main():
    TARGET_MINUTE = 37
    now_utc = datetime.now(timezone.utc)
    current_minute = now_utc.minute
    current_second = now_utc.second
    print(f"--- Скрипт запущен GitHub в {now_utc.strftime('%H:%M:%S')} UTC. Целевое время выполнения: XX:{TARGET_MINUTE}:00 UTC. ---")
    if current_minute < TARGET_MINUTE:
        wait_seconds = (TARGET_MINUTE - current_minute) * 60 - current_second
        if wait_seconds > 0:
            print(f"--- Ожидаем {wait_seconds} секунд для синхронизации времени... ---", flush=True)
            await asyncio.sleep(wait_seconds)
    elif current_minute > TARGET_MINUTE:
        print(f"--- Запуск произошел с опозданием. Начинаем выполнение немедленно. ---")
    else:
        print(f"--- Запуск произошел точно в целевое время. Начинаем выполнение. ---")
    start_time = datetime.now(timezone.utc)
    print(f"\n{'=' * 50}\n--- НАЧАЛО РАБОТЫ: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC ---\n{'=' * 50}")
    
    active_accounts = [acc for acc in ACCOUNTS if acc.get("cookie")]
    for i, account in enumerate(active_accounts):
        if not account["cookie"]:
            print(f"--- Пропускаем закомментированный аккаунт #{i+1} ---")
            continue
        await supervisor_for_account(account)
        print(f"\n--- ЗАВЕРШЕНА РАБОТА С АККАУНТОМ: {account['name']} ---")
        
        is_last_active = all(not acc["cookie"] for acc in ACCOUNTS[i + 1:])
        if not is_last_active:
            pause_duration = random.randint(5, 15)
            print(f"--- Пауза {pause_duration} секунд перед следующим аккаунтом... ---")
            await asyncio.sleep(pause_duration)
            
    end_time = datetime.now(timezone.utc)
    print(f"\n\n--- ВСЕ АККАУНТЫ ОБРАБОТАНЫ. ЗАВЕРШЕНИЕ РАБОТЫ: {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC ---")

if __name__ == "__main__":
    asyncio.run(main())
