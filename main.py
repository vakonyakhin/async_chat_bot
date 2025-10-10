import asyncio
from datetime import datetime
from tkinter import messagebox
import sys
import json

import anyio
from anyio import create_task_group, get_cancelled_exc_class


import gui
from chat_tools import get_logger, create_arg_parser, get_parse_arguments, read_token


async def authentication(reader, writer, token, status_queue):
    if not token:
        token = read_token()
        
    
    logger.debug('Send token to server')
    writer.write(f'{token}\n'.encode())

    await writer.drain()
    InvalidToken = Exception('Invalid token')
    response_data = await reader.readline()
    
    try:
        if response_data.decode().strip() == 'null':
            
            messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер его не узнал')
            raise InvalidToken
        else:
            username = json.loads(response_data.decode())['nickname']
            print(f'Выполнена аутентификация. Пользователь {username}')

    except InvalidToken:
        
        sys.exit()
    #nickname = {key : value for key, value in response_data.decode().strip()}
    #print(type(nickname))
    status_queue.put_nowait(gui.NicknameReceived(username))
    return username


async def read_logs(filepath, queue):
    if filepath:
        with open(filepath, 'r') as f:
            for line in f:
                await queue.put(line.strip())
    return


async def read_msgs(host, port, filepath, queue, save_queue, status_queue, watchdog_queue):

    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    reader, _ = await asyncio.open_connection(host, port)
    # if reader:
    #     status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
    if filepath:
        await read_logs(filepath, queue)

        while True:
                            
            message = await reader.readline()
            status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)    
            now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
            frmt_message = f'{now} {message.decode().strip()}'
                    
            await queue.put(frmt_message)
            await watchdog_queue.put(f'{now} Connection is alive. New message in chat')
            
            await save_queue.put(frmt_message)


async def save_messages(filepath, queue):
    while True:
        msg = await queue.get()
        if filepath:
            with open(filepath, 'a') as f:
                f.write(f'{msg}\n')
                queue.task_done()


async def send_messages(host, port, token, send_queue, save_queue, message_queue, status_queue, watchdog_queue):
    
    status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host, port)
    if reader:
        status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
    await reader.readline()

    if reader and writer:
        logger.debug('Do authentification')
        username = await authentication(reader, writer, token, status_queue)

    logger.debug(await reader.readline())
    while True:
        message = await send_queue.get()
        print(f'{message}')
        now = datetime.now().strftime('[%d.%m.%Y %H:%M:%S]')
        frmt_message = f'{now} {username}: {message}'

        
        await save_queue.put(frmt_message)
        await message_queue.put(frmt_message)
        await watchdog_queue.put(f'{now} Connection is alive. Message sent')

async def watch_for_connection(watchdog_queue):
    while True:
        try:
            
            async with asyncio.timeout(4):
                message = await watchdog_queue.get()
                times = datetime.timestamp(datetime.now())
                print(f'{times} {message}')
                    
        except TimeoutError:
            print(f'{times} TimeoutError')
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
    reader, writer = await asyncio.open_connection(send_host, send_port)
    await reader.readline()
    
    while True:
        print("Starting new connection cycle")
        
        try:
            async with create_task_group() as task_group:
                # Запуск основных задач
                #task_group.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
                task_group(
                    authentication,
                    reader,writer,
                    send_token,
                    status_updates_queue
                )
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
                # task_group.start_soon(save_messages, read_filepath, save_messages_queue)
                # task_group.start_soon(
                #     send_messages,
                #     send_host,
                #     send_port,
                #     send_token,
                #     sending_queue,
                #     save_messages_queue,
                #     messages_queue,
                #     status_updates_queue,
                #     watchdog_queue
                #)
                task_group.start_soon(watch_for_connection, watchdog_queue)
              
        except ConnectionError as ce:
           
                print(f"Connection failed: {ce}, restarting in 5 seconds...")
                raise get_cancelled_exc_class()# asyncio.CancelledError
        except get_cancelled_exc_class() as exc:
            
                print('CancelledError for all tasks')
                task_group.cancel_scope.cancel()
                raise
        finally:
            print('Closing connections...')

        print("Restarting connections...")

    

async def main():

    config_path = ['./configs/reader.ini']
    send_parser = create_arg_parser(['./configs/sender.ini'])
    read_parser = create_arg_parser(config_path)
    read_arguments = get_parse_arguments(read_parser)
    send_arguments = get_parse_arguments(send_parser)

    messages_queue = asyncio.Queue() 
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    # draw_task = asyncio.create_task(gui.draw(messages_queue, sending_queue, status_updates_queue))
    # read_task = asyncio.create_task(read_msgs(read_arguments.host, read_arguments.port, read_arguments.filepath, messages_queue, save_messages_queue, status_updates_queue, watchdog_queue))
    # save_task = asyncio.create_task(save_messages(read_arguments.filepath, save_messages_queue))
    # send_task = asyncio.create_task(send_messages(send_arguments.host, send_arguments.port, send_arguments.token, sending_queue, save_messages_queue, messages_queue, status_updates_queue,watchdog_queue))
    # #auth_task = asyncio.create_task(authentication(reader,writer))
    # watchdog_task = asyncio.create_task(watch_for_connection(watchdog_queue))
    

    #await asyncio.gather(draw_task, read_task, save_task, send_task, watchdog_task)

    # async with create_task_group() as task_group:
    #     # Замена asyncio.create_task на task_group.start_soon
    #     task_group.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
    #     task_group.start_soon(
    #         read_msgs,
    #         read_arguments.host,
    #         read_arguments.port,
    #         read_arguments.filepath,
    #         messages_queue,
    #         save_messages_queue,
    #         status_updates_queue,
    #         watchdog_queue
    #     )
    #     task_group.start_soon(save_messages, read_arguments.filepath, save_messages_queue)
    #     task_group.start_soon(
    #         send_messages,
    #         send_arguments.host,
    #         send_arguments.port,
    #         send_arguments.token,
    #         sending_queue,
    #         save_messages_queue,
    #         messages_queue,
    #         status_updates_queue,
    #         watchdog_queue
    #     )
    #     task_group.start_soon(watch_for_connection, watchdog_queue)
    #     task_group.start_soon(handle_connection)

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
        task_group.start_soon(gui.draw,messages_queue, sending_queue, status_updates_queue)

        
if __name__ == "__main__":
    logger = get_logger('reader')
    asyncio.run(main())
