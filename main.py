import asyncio
from datetime import datetime
from tkinter import messagebox
import sys
import json
import socket

from anyio import create_task_group, get_cancelled_exc_class

import gui
from chat_tools import (
    get_logger,
    create_arg_parser,
    get_parse_arguments,
    read_token,
    get_connection
)


class InvalidToken(Exception):
    pass


async def authentication(reader, writer, token, status_queue):
    if not token:
        token = read_token()

    await reader.readline()
    send_logger.debug('Отправка токена на сервер')
    writer.write(f'{token}\n'.encode())

    await writer.drain()

    response_data = await reader.readline()
    send_logger.debug(await reader.readline())
    try:
        if response_data.decode().strip() == 'null':

            messagebox.showinfo(
                    'Неверный токен',
                    'Проверьте токен, сервер его не узнал'
                    )
            raise InvalidToken
        else:
            username = json.loads(response_data.decode())['nickname']
            send_logger.debug(f'Выполнена аутентификация. Пользователь {username}')
    except InvalidToken:
        sys.exit()
    status_queue.put_nowait(gui.NicknameReceived(username))
    return username, reader, writer


async def read_logs(filepath, queue):
    if filepath:
        with open(filepath, 'r') as f:
            for line in f:
                await queue.put(line.strip())
    return


async def read_msgs(
        reader,
        writer,
        filepath,
        queue,
        save_queue,
        status_queue,
        watchdog_queue
        ):

    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    if reader:
        status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
    if filepath:
        await read_logs(filepath, queue)

        while True:

            message = await reader.readline()
            now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
            frmt_message = f'{now} {message.decode().strip()}'

            await queue.put(frmt_message)
            watchdog_queue.put_nowait(f'Connection is alive. New message in chat')

            await save_queue.put(frmt_message)


async def save_messages(filepath, queue):
    while True:
        msg = await queue.get()
        if filepath:
            with open(filepath, 'a') as f:
                f.write(f'{msg}\n')
                queue.task_done()


async def send_messages(

        writer,
        username,
        send_queue,
        save_queue,
        status_queue,
        watchdog_queue
        ):

    status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)

    if writer:
        status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

    while True:
        message = await send_queue.get()
        send_logger.debug(f'{message}')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()
        now = datetime.now().strftime('[%d.%m.%Y %H:%M:%S]')
        frmt_message = f'{now} {username}: {message}'

        await save_queue.put(frmt_message)
        watchdog_queue.put_nowait(f'Connection is alive. Message sent')


async def watch_for_connection(watchdog_queue):

    while True:
        try:
            async with asyncio.timeout(3):
                message = await watchdog_queue.get()
                timestamp = datetime.timestamp(datetime.now())
                watch_logger.debug(f'{timestamp} {message}')

        except TimeoutError:
            watch_logger.debug(f'{timestamp} TimeoutError')
            raise get_cancelled_exc_class()


async def ping_pong(writer, watch_queue):

    message = b'\n\n'
    timestamp = datetime.timestamp(datetime.now())

    while True:
        try:
            async with asyncio.timeout(3):
                writer.write(message)
                await writer.drain()
                send_logger.debug(f'Ping pong request to server')
            await watch_queue.put('ping')
            await asyncio.sleep(10)
        except TimeoutError:
            watch_logger.debug(f'{timestamp} TimeoutError')
            raise get_cancelled_exc_class()


async def handle_connections(
    read_parcer,
    send_parcer,
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
        try:
            read_streams = await get_connection(read_parcer)
            write_streams = await get_connection(send_parcer)
            default_logger.debug("Запуск коррутин....")

            username, _ , writer = await authentication(
                *write_streams,
                send_parcer.token,
                status_updates_queue
            )
            async with create_task_group() as task_group:
                
                task_group.start_soon(
                    read_msgs,
                    *read_streams,
                    read_parcer.filepath,
                    messages_queue,
                    save_messages_queue,
                    status_updates_queue,
                    watchdog_queue
                )
                task_group.start_soon(
                    send_messages,
                    writer,
                    username,
                    sending_queue,
                    save_messages_queue,
                    status_updates_queue,
                    watchdog_queue
                )
                task_group.start_soon(watch_for_connection, watchdog_queue)

                task_group.start_soon(
                    ping_pong,
                    writer,
                    watchdog_queue
                )

        except* (get_cancelled_exc_class, socket.gaierror, Exception) as exc:
            for sub in exc.exceptions:
                default_logger.debug(f"Разрыв соединения. Connection task raised: {sub!r}")

        finally:
            status_updates_queue.put_nowait(
                gui.ReadConnectionStateChanged.CLOSED
                )
            status_updates_queue.put_nowait(
                gui.SendingConnectionStateChanged.CLOSED
                )
            max_retries -= 1
            default_logger.debug(f'Оставшееся количество попыток = {max_retries}')
            if max_retries <= 0:
                default_logger.debug("Использовано максимальное \
                                     количество попыток соединения....")
                messagebox.showinfo(
                    'Отсутстувет подключение к интернету.', 
                    'Количество попыток соединение превышено. ' \
                    'Проверьте соединение или повторите позже.'
                    )
                sys.exit()
            default_logger.debug('Ожидаем перед повторной попыткой')
            await asyncio.sleep(retry_delay)

        default_logger.debug("Переподключение")


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
    try:
        async with create_task_group() as task_group:

            task_group.start_soon(
                handle_connections,
                read_arguments,
                send_arguments,
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
    except* ExceptionGroup as err:
        default_logger.debug(f'Unexcepter error in main {type(err).__name__}')

if __name__ == "__main__":
    read_logger = get_logger('reader')
    send_logger = get_logger('sender')
    watch_logger = get_logger('watcher')
    default_logger = get_logger('default')

    try:
        asyncio.run(main())
    except (
        KeyboardInterrupt,
        gui.TkAppClosed
    ):
        default_logger.debug(f'Чат был закрыт пользователем')

    except ExceptionGroup as err:
        for err in err.exceptions:
            default_logger.debug(f'Unexcepter error {type(err).__name__}')
    finally:
        sys.exit()
