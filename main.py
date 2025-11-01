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
    get_connection,
    with_logger
)


class InvalidToken(Exception):
    pass


@with_logger('sender')
async def authentication(logger, reader, writer, token, status_queue):
    """
    Аутентифицирует пользователя на сервере чата.

    Args:
        logger: Экземпляр логгера.
        reader: StreamReader для получения ответов от сервера.
        writer: StreamWriter для отправки данных на сервер.
        token: Токен аутентификации. Если None, токен будет прочитан из файла.
        status_queue: Очередь для отправки обновлений статуса в GUI.

    Returns:
        Кортеж (username, reader, writer) в случае успеха.

    Raises:
        InvalidToken: Если сервер вернул `null` в ответ на токен.
    """
    if not token:
        token = read_token()

    await reader.readline()
    logger.debug('Отправка токена на сервер')
    writer.write(f'{token}\n'.encode())

    await writer.drain()

    response_data = await reader.readline()
    logger.debug(await reader.readline())
    try:
        if response_data.decode().strip() == 'null':

            messagebox.showinfo(
                    'Неверный токен',
                    'Проверьте токен, сервер его не узнал'
                    )
            raise InvalidToken
        else:
            username = json.loads(response_data.decode())['nickname']
            logger.debug(f'Выполнена аутентификация. Пользователь {username}')
    except InvalidToken:
        sys.exit()
    status_queue.put_nowait(gui.NicknameReceived(username))
    return username, reader, writer


async def read_logs(filepath, queue):
    """
    Загружает историю сообщений из файла.

    Args:
        filepath: Путь к файлу с логами.
        queue: Очередь для добавления отформатированных сообщений.
    """
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
    """
    Читает входящие сообщения из сокета и помещает их в очередь.

    Args:
        reader: StreamReader для чтения сообщений из сети.
        writer: StreamWriter (не используется напрямую, но нужен для сигнатуры).
        filepath: Путь к файлу для загрузки истории сообщений.
        queue: Основная очередь сообщений для отображения в GUI.
        save_queue: Очередь для сохранения сообщений в файл.
        status_queue: Очередь для обновления статуса соединения в GUI.
        watchdog_queue: Очередь для мониторинга активности соединения.
    """

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
    """
    Сохраняет сообщения из очереди в файл.

    Args:
        filepath: Путь к файлу для сохранения.
        queue: Очередь с сообщениями для сохранения.
    """
    while True:
        msg = await queue.get()
        if filepath:
            with open(filepath, 'a') as f:
                f.write(f'{msg}\n')
                queue.task_done()

@with_logger('sender')
async def send_messages(
        logger,
        writer,
        username,
        send_queue,
        save_queue,
        status_queue,
        watchdog_queue
        ):
    """
    Отправляет сообщения пользователя на сервер.

    Args:
        logger: Экземпляр логгера.
        writer: StreamWriter для отправки сообщений в сеть.
        username: Имя текущего пользователя.
        send_queue: Очередь с сообщениями для отправки.
        save_queue: Очередь для сохранения отправленных сообщений.
        status_queue: Очередь для обновления статуса соединения в GUI.
        watchdog_queue: Очередь для мониторинга активности соединения.
    """

    status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)

    if writer:
        status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

    while True:
        message = await send_queue.get()
        logger.debug(f'{message}')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()
        now = datetime.now().strftime('[%d.%m.%Y %H:%M:%S]')
        frmt_message = f'{now} {username}: {message}'

        await save_queue.put(frmt_message)
        watchdog_queue.put_nowait(f'Connection is alive. Message sent')


@with_logger('watcher')
async def watch_for_connection(logger, watchdog_queue):
    """
    Следит за состоянием соединения, ожидая сообщений в watchdog_queue.

    Если в течение таймаута не поступает ни одного сообщения,
    вызывает исключение, что приводит к перезапуску соединения.

    Args:
        logger: Экземпляр логгера.
        watchdog_queue: Очередь для получения сообщений о состоянии соединения.
    """

    while True:
        try:
            async with asyncio.timeout(3):
                message = await watchdog_queue.get()
                timestamp = datetime.timestamp(datetime.now())
                logger.debug(f'{timestamp} {message}')

        except TimeoutError:
            logger.debug(f'{datetime.timestamp(datetime.now())} TimeoutError')
            raise get_cancelled_exc_class()


@with_logger('sender')
async def ping_pong(logger, writer, watch_queue):
    """
    Поддерживает соединение активным, периодически отправляя ping-запросы (пустые строки).

    Args:
        logger: Экземпляр логгера.
        writer: StreamWriter для отправки ping-сообщений.
        watch_queue: Очередь для уведомления watchdog'а об активности.
    """

    message = b'\n\n'
    timestamp = datetime.timestamp(datetime.now())

    while True:
        try:
            async with asyncio.timeout(3):
                writer.write(message)
                await writer.drain()
                logger.debug(f'Ping pong request to server')
            await watch_queue.put('ping')
            await asyncio.sleep(10)
        except TimeoutError:
            # Используем логгер 'watcher' для этого сообщения
            get_logger('watcher').debug(f'{timestamp} TimeoutError')
            raise get_cancelled_exc_class()


@with_logger('default')
async def handle_connections(
    logger,
    read_parcer,
    send_parcer,
    messages_queue,
    save_messages_queue,
    sending_queue,
    status_updates_queue,
    watchdog_queue
):
    """
    Управляет жизненным циклом соединений, включая переподключение при сбоях.

    Args:
        logger: Экземпляр логгера.
        read_parcer: Конфигурация для соединения на чтение.
        send_parcer: Конфигурация для соединения на отправку.
        messages_queue: Очередь для сообщений, отображаемых в GUI.
        save_messages_queue: Очередь для сообщений, сохраняемых в файл.
        sending_queue: Очередь для сообщений, отправляемых на сервер.
        status_updates_queue: Очередь для обновления статусов в GUI.
        watchdog_queue: Очередь для мониторинга активности соединения.
    """
    max_retries = 5
    retry_delay = 5
    
    while True:
        try:
            read_streams = await get_connection(read_parcer)
            write_streams = await get_connection(send_parcer)
            logger.debug("Запуск коррутин....")

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
                    watchdog_queue,
                )

        except* (get_cancelled_exc_class, socket.gaierror, Exception) as exc:
            for sub in exc.exceptions:
                get_logger('default').debug(f"Разрыв соединения. Connection task raised: {sub!r}")

        finally:
            status_updates_queue.put_nowait(
                gui.ReadConnectionStateChanged.CLOSED
                )
            status_updates_queue.put_nowait(
                gui.SendingConnectionStateChanged.CLOSED
                )
            max_retries -= 1
            logger.debug(f'Оставшееся количество попыток = {max_retries}')
            if max_retries <= 0:
                logger.debug("Использовано максимальное \
                                     количество попыток соединения....")
                messagebox.showinfo(
                    'Отсутстувет подключение к интернету.', 
                    'Количество попыток соединение превышено. ' \
                    'Проверьте соединение или повторите позже.'
                    )
                sys.exit()
            logger.debug('Ожидаем перед повторной попыткой')
            await asyncio.sleep(retry_delay)

        logger.debug("Переподключение")


@with_logger('default')
async def main(logger):
    """
    Главная точка входа в приложение.

    Инициализирует парсеры аргументов, очереди и запускает основные задачи:
    обработчик соединений, GUI и сохранение сообщений.
    """

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
        logger.debug(f'Unexcepter error in main {type(err).__name__}')

if __name__ == "__main__":
    # Логгеры теперь создаются и внедряются декоратором

    try:
        asyncio.run(main())
    except (
        KeyboardInterrupt,
        gui.TkAppClosed
    ) as e:
        get_logger('default').debug(f'Чат был закрыт пользователем: {type(e).__name__}')

    except ExceptionGroup as err:
        for err in err.exceptions:
            get_logger('default').debug(f'Unexcepter error {type(err).__name__}')
    finally:
        sys.exit()
