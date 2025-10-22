import asyncio
from datetime import datetime
from tkinter import messagebox
import sys
import json
import socket


import anyio
from anyio import create_task_group, get_cancelled_exc_class

import gui
from chat_tools import (
    get_logger,
    create_arg_parser,
    get_parse_arguments,
    read_token
)


async def authentication(reader, writer, token, status_queue):
    if not token:
        token = read_token()

    send_logger.debug('Send token to server')
    writer.write(f'{token}\n'.encode())

    await writer.drain()
    InvalidToken = Exception('Invalid token')
    response_data = await reader.readline()

    try:
        if response_data.decode().strip() == 'null':

            messagebox.showinfo(
                'Неверный токен',
                'Проверьте токен, сервер его не узнал'
                )
            raise InvalidToken
        else:
            username = json.loads(response_data.decode())['nickname']
            print(f'Выполнена аутентификация. Пользователь {username}')

    except InvalidToken:
        sys.exit()

    status_queue.put_nowait(gui.NicknameReceived(username))
    return username


async def ping_pong(host, port, token, status_queue, watch_queue):

    message = b'\n\n'
    reader, writer = await asyncio.open_connection(host, port)
    await reader.readline()

    if reader and writer:
        send_logger.debug('Do authentification')
        username = await authentication(reader, writer, token, status_queue)
        #status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        print({username})
    while True:
        writer.write(message)
        await writer.drain()
        print(f'Ping pong request to {host} {port}')
        await watch_queue.put('ping')
        await asyncio.sleep(3)


async def read_logs(filepath, queue):
    if filepath:
        with open(filepath, 'r') as f:
            for line in f:
                await queue.put(line.strip())
    return


async def read_msgs(
        host,
        port,
        filepath,
        queue,
        save_queue,
        status_queue,
        watchdog_queue
        ):

    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    reader, _ = await asyncio.open_connection(host, port)
    if reader:
        status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
    if filepath:
        await read_logs(filepath, queue)

        while True:

            message = await reader.readline()
            now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
            frmt_message = f'{now} {message.decode().strip()}'

            await queue.put(frmt_message)
            await watchdog_queue.put(f'{now} Connection is alive. New message in chat')
            print(f'{now} Connection is alive. New message in chat')
            await save_queue.put(frmt_message)


async def save_messages(filepath, queue):
    while True:
        msg = await queue.get()
        if filepath:
            with open(filepath, 'a') as f:
                f.write(f'{msg}\n')
                queue.task_done()


async def send_messages(
        host,
        port,
        token,
        send_queue,
        save_queue,
        message_queue,
        status_queue,
        watchdog_queue
        ):

    status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host, port)

    await reader.readline()

    if reader and writer:
        send_logger.debug('Do authentification')
        username = await authentication(reader, writer, token, status_queue)
        status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

    send_logger.debug(await reader.readline())
    while True:
        message = await send_queue.get()
        print(f'{message}')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()
        now = datetime.now().strftime('[%d.%m.%Y %H:%M:%S]')
        frmt_message = f'{now} {username}: {message}'

        await save_queue.put(frmt_message)
        await message_queue.put(frmt_message)
        await watchdog_queue.put(f'{now} Connection is alive. Message sent')


async def watch_for_connection(watchdog_queue):
    while True:
        try:

            async with asyncio.timeout(15):
                message = await watchdog_queue.get()
                times = datetime.timestamp(datetime.now())
                watch_logger.debug(f'{times} {message}')

        except TimeoutError:
            print(f'{datetime.timestamp(datetime.now())} TimeoutError')
            raise get_cancelled_exc_class()


async def handle_connections(
    read_host: str,
    read_port: int,
    read_filepath: str,
    send_host: str,
    send_port: int,
    send_token: str,
    messages_queue,
    save_messages_queue,
    sending_queue,
    status_updates_queue,
    watchdog_queue
):
    """
    Управляет подключениями и перезапускает задачи при сбоях.

    Args:
        read_host: Хост для чтения сообщений
        read_port: Порт для чтения сообщений
        read_filepath: Путь к файлу для чтения логов
        send_host: Хост для отправки сообщений
        send_port: Порт для отправки сообщений
        send_token: Токен для аутентификации
        messages_queue: Очередь для входящих сообщений
        save_messages_queue: Очередь для сохранения сообщений
        sending_queue: Очередь для исходящих сообщений
        status_updates_queue: Очередь для обновления статуса
        watchdog_queue: Очередь для отслеживания состояния подключения
    """
    max_retries = 5
    retry_delay = 5
    while True:

        print("Starting new connection cycle")

        try:
            async with create_task_group() as task_group:
                # Запуск основных задач
                task_group.start_soon(
                    read_msgs,
                    read_host,
                    read_port,
                    read_filepath,
                    messages_queue,
                    save_messages_queue,
                    status_updates_queue,
                    watchdog_queue
                )
                task_group.start_soon(
                    send_messages,
                    send_host,
                    send_port,
                    send_token,
                    sending_queue,
                    save_messages_queue,
                    messages_queue,
                    status_updates_queue,
                    watchdog_queue
                )
                task_group.start_soon(watch_for_connection, watchdog_queue)

                task_group.start_soon(
                    ping_pong,
                    send_host,
                    send_port,
                    send_token,
                    status_updates_queue,
                    watchdog_queue
                )
        except* (anyio.get_cancelled_exc_class(), socket.gaierror, Exception) as exc:
            for e in exc.exceptions:
                print(f"Connection failed, waiting for tasks to complete...")
                #if e.errno == -3:
                    #print('Cannot convert a website or servers domain name into an IP address')
                #print(f"Contained exception: {type(e).__name__}: {e}")

            # Ограничиваем количество попыток
                max_retries -= 1
                if max_retries <= 0:
                    print("Max retry attempts reached, exiting...")
                    break

            # Ожидаем завершения всех задач в группе
            await anyio.sleep(retry_delay)

        finally:
            print(f'max_retries = {max_retries}')
            if max_retries <= 0:
                messagebox.showinfo(
                    'Отсутстувет подключение к интернету.', 
                    'Количество попыток соединение превышено. ' \
                    'Проверьте соединение или повторите позже.'
                    )
                sys.exit()
        # После завершения группы задач переходим к следующему циклу
        print("Restarting connections...")


async def main():

    config_reader_path = ['./configs/reader.ini']
    config_sender_path = ['./configs/sender.ini']
    send_parser = create_arg_parser(config_sender_path)
    read_parser = create_arg_parser(config_reader_path)
    read_arguments = get_parse_arguments(read_parser)
    send_arguments = get_parse_arguments(send_parser)

    messages_queue = asyncio.Queue() 
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    async with create_task_group() as task_group:
        task_group.start_soon(
            handle_connections,
            read_arguments.host,
            read_arguments.port,
            read_arguments.filepath,
            send_arguments.host,
            send_arguments.port,
            send_arguments.token,
            messages_queue,
            save_messages_queue,
            sending_queue,
            status_updates_queue,
            watchdog_queue
        )
        task_group.start_soon(
            gui.draw,
            messages_queue,
            sending_queue,
            status_updates_queue)

        task_group.start_soon(
            save_messages,
            read_arguments.filepath,
            save_messages_queue
            )

if __name__ == "__main__":
    read_logger = get_logger('reader')
    send_logger = get_logger('sender')
    watch_logger = get_logger('watch')

    try:
        asyncio.run(main())
    except* (
        KeyboardInterrupt,
        gui.TkAppClosed
    ) as err:
        for e in err.exceptions:
            print('KeyboardInterrupt')
            sys.exit()
