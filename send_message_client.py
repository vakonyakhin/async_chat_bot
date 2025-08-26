import asyncio
import json
import sys

from chat_tools import get_logger, get_parser


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
        sys.exit()
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
            logger.debug(f'Send message {message}')
            writer.write(f'{message}\n\n'.encode())
            await writer.drain()
            print(await reader.readline())
    except KeyboardInterrupt:
        if writer:
            logger.debug('Interrupt connection')
            writer.close()
            await writer.wait_closed()


async def main():
    args = get_parser()

    try:
        with open('token.json', 'r') as file:
            logger.debug('Read token from file')
            creds = file.read()
            if not creds:
                logger.debug(
                    'You dont have token. ' \
                    'Please launch registration.py.'
                    )
                sys.exit()
            token = json.loads(creds)
    except FileNotFoundError:
        print('Cant found file. Please launch registration.py.')
    except json.JSONDecodeError:
        print('Cant decoded JSON. Please launch registration.py.')

    reader, writer = await asyncio.open_connection(args.host, args.port)
    if reader and writer:
        logger.debug('Do authentification')
        await authentication(reader, writer, token['account_hash'])
    logger.debug('Start sending messages')
    await send_message(reader, writer)


if __name__ == "__main__":
    logger = get_logger('sender')
    asyncio.run(main())
