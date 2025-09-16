import asyncio
import logging
import json

from chat_tools import get_logger, get_parser, create_arg_parser, get_parse_arguments


async def registration(args):

    """
    Register a new user on the chat server and save the authentication token.

    This function handles the registration process by:
    - Reading initial server prompts.
    - Sending empty input (possibly as part of the protocol).
    - Receiving username to the user.
    - Receiving and parsing the server's JSON response.
    - Saving the returned token to 'token.txt' if valid.

    Args:
        reader (asyncio.StreamReader): Reader object for receiving data from the server.
        writer (asyncio.StreamWriter): Writer object for sending data to the server.

    Returns:
        None

    Raises:
        json.JSONDecodeError: If the server's response cannot be parsed as JSON.
    """

    logger.debug('Open connection for registration')
    reader, writer = await asyncio.open_connection(args.host, args.port)
    await reader.readline()
    logger.debug('Send empty hash')
    writer.write(f'.. \n'.encode())
    await writer.drain()
    await reader.readline()
    
    if args.username:
        username = args.username
        await reader.readline()
    else:
        print('Enter preferred nickname below:')
        await reader.readline()
        username = input('')
    logger.debug('Send prefered username for registraion')
    writer.write(f'{username}\n'.encode())
    await writer.drain()

    response_data = await reader.readline()
    await reader.readline()
    print(response_data.decode())

    print(
        'Welcome to chat! For send messages in ' \
        'chat please launch send_message.py.'
        )

    try:
        logger.debug('Get token')
        token = json.loads(response_data.decode())
        if token:
            with open('token.json', 'w') as file:
                logger.debug('Safe token to file')
                json.dump(token, file, indent=4)
    except json.JSONDecodeError:
        print('JSON decoding error')

    finally:
        logger.debug('Close connection')
        writer.close()
        await writer.wait_closed()

if __name__ == '__main__':
    config_path = ['./configs/sender.ini']

    logger = get_logger('default')
    arg_parser = create_arg_parser(config_path)
    arguments = get_parse_arguments(arg_parser)
    asyncio.run(registration(arguments))
