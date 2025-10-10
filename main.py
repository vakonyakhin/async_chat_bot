import asyncio
from datetime import datetime
import tkinter as tk
import sys

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
            
            tk.messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер его не узнал')
            raise InvalidToken
        else:
            username = json.loads(response_data.decode())['nickname']
            print(f'Выполнена аутентификация. Пользователь {username}')

    except InvalidToken:
        logger.debug(f'Exit client. Invalid token')
        sys.exit()
    nickname = {key : value for key, value in response_data.decode().strip()}
    print(type(nickname))
    status_queue.put_nowait(gui.NicknameReceived(username))
    return username



async def read_logs(filepath, queue):
    if filepath:
        with open(filepath, 'r') as f:
            for line in f:
                await queue.put(line.strip())
    return


async def read_msgs(host, port, filepath, queue, save_queue):

    reader, _ = await asyncio.open_connection(host, port)

    if filepath:
        await read_logs(filepath, queue)

    while True:
        message = await reader.readline()
        now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
        frmt_message = f'{now} {message.decode().strip()}'

        await queue.put(frmt_message)
        await save_queue.put(frmt_message)


async def save_messages(filepath, queue):
    while True:
        msg = await queue.get()
        if filepath:
            with open(filepath, 'a') as f:
                f.write(f'{msg}\n')
                queue.task_done()


async def send_messages(host, port, send_queue, save_queue, message_queue):
    
    reader, writer = await asyncio.open_connection(host, port)
    await reader.readline()

    if reader and writer:
        logger.debug('Do authentification')
        username = await authentication(reader, writer)

    logger.debug(await reader.readline())
    while True:
        message = await send_queue.get()
        print(f'{message}')
        now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
        frmt_message = f'{now} {username}: {message}'

        await save_queue.put(frmt_message)
        await message_queue.put(frmt_message)


async def main():

    config_path = ['./configs/reader.ini']
    send_parser = create_arg_parser(['./configs/sender.ini'])
    read_parser = create_arg_parser(config_path)
    read_arguments = get_parse_arguments(read_parser)
    send_arguments = get_parse_arguments(send_parser)

    reader, writer = await asyncio.open_connection(send_arguments.host, send_arguments.port)

    messages_queue = asyncio.Queue() 
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    draw_task = asyncio.create_task(gui.draw(messages_queue, sending_queue, status_updates_queue))
    read_task = asyncio.create_task(read_msgs(read_arguments.host, read_arguments.port, read_arguments.filepath, messages_queue, save_messages_queue))
    save_task = asyncio.create_task(save_messages(read_arguments.filepath, save_messages_queue))
    send_task = asyncio.create_task(send_messages(send_arguments.host, send_arguments.port, sending_queue, save_messages_queue, messages_queue))
    auth_task = asyncio.create_task(authentication(reader,writer))

    await asyncio.gather(draw_task, read_task, save_task, send_task)


if __name__ == "__main__":
    logger = get_logger('reader')
    asyncio.run(main())
