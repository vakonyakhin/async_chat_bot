import asyncio
import gui

from chat_tools import get_logger, create_arg_parser, get_parse_arguments


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