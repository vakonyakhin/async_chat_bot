import asyncio
from datetime import datetime

import gui
from chat_tools import get_logger, create_arg_parser, get_parse_arguments


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


async def send_messages(host, port, queue):

    while True:
        msg = await queue.get()
        print(f'{msg}')


async def main():

    config_path = ['./configs/reader.ini']
    arg_parser = create_arg_parser(config_path)
    arguments = get_parse_arguments(arg_parser)

    messages_queue = asyncio.Queue() 
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    draw_task = asyncio.create_task(gui.draw(messages_queue, sending_queue, status_updates_queue))
    read_task = asyncio.create_task(read_msgs(arguments.host, arguments.port, arguments.filepath, messages_queue, save_messages_queue))
    save_task = asyncio.create_task(save_messages(arguments.filepath, save_messages_queue))
    send_task = asyncio.create_task(send_messages(arguments.host, arguments.port, sending_queue))

    await asyncio.gather(draw_task, read_task, save_task, send_task)


if __name__ == "__main__":
    logger = get_logger('reader')
    asyncio.run(main())
