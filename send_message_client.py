import asyncio
import json
import sys
import re

from chat_tools import get_logger, create_arg_parser, get_parse_arguments, read_token


async def authentication(reader, writer, token):
    """
    Authenticate to the chat server using a provided token.

    Attempts to authenticate with the given token. If the server returns `None`, the token is valid.
    Otherwise, initiates a registration process to obtain a new token.

    Args:
        reader (asyncio.StreamReader): Reader object for receiving data from the server.
        writer (asyncio.StreamWriter): Writer object for sending data to the server.
        token (str): Authentication token. Defaults to a hardcoded value.

    Returns:
        None

    Raises:
        json.JSONDecodeError: If the server's response cannot be parsed as JSON.
    """
    logger.debug(await reader.readline())
    logger.debug('Send token to server')
    writer.write(f'{token}\n'.encode())
    await writer.drain()

    response_data = await reader.readline()
    if response_data.decode().strip() == 'null':
        print('Your token is incorrect. Please launch registration.py again')
        return False    
    else:
        logger.debug('Token checked successfully')


async def send_message(reader, writer):
    """
    Send messages to the chat server and handle server responses.

    This function:
    1. Reads the initial server message.
    2. Sends user input to the server.
    3. Handles potential errors during message transmission.

    Args:
        reader (asyncio.StreamReader): Reader object for receiving data from the server.
        writer (asyncio.StreamWriter): Writer object for sending data to the server.

    Returns:
        None

    Raises:
        RuntimeError: If the connection to the server is lost unexpectedly.
        json.JSONDecodeError: If the server's response contains invalid JSON.
    """

    print(await reader.readline())
    try:
        while True:

            message = input('')
            escape_message = re.sub(r'\\n', ' ', message)
            logger.debug(f'Send message {escape_message}')
            writer.write(f'{escape_message}\n\n'.encode())
            await writer.drain()
            print(await reader.readline())
    except KeyboardInterrupt:
        if writer:
            logger.debug('Interrupt connection')
            writer.close()
            await writer.wait_closed()


async def main(args):
    
    if args.token:
        token = args.token
    else:
        token = read_token()

    reader, writer = await asyncio.open_connection(args.host, args.port)
    if reader and writer:
        logger.debug('Do authentification')
        await authentication(reader, writer, token)
    logger.debug('Start sending messages')
    if args.text:
        message = re.sub(r'\n', ' ', args.text)
        logger.debug(f'Send message {message}')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()

    await send_message(reader, writer)


if __name__ == "__main__":
    config_paths = ['./configs/sender.ini']
    logger = get_logger('sender')
    arg_parser = create_arg_parser(config_paths)
    arguments = get_parse_arguments(arg_parser)
    asyncio.run(main(arguments))
