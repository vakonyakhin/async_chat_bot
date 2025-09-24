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
        print(f'Размер очереди после считывания истории сообщений {queue.qsize()}')
        
    while True:
        message = await reader.readline()
        now = datetime.now().strftime('[%d.%m.%Y %H:%M]')
        frmt_message = f'{now} {message.decode().strip()}'
        
        await queue.put(frmt_message)
        print(queue.qsize())
        await save_queue.put(frmt_message)
        

async def main():

    config_path = ['./configs/reader.ini']
    arg_parser = create_arg_parser(config_path)
    arguments = get_parse_arguments(arg_parser)

    messages_queue = asyncio.Queue() 
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()



if __name__ == "__main__":
    logger = get_logger('reader')
    asyncio.run(main())