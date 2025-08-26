import asyncio
import configargparse

from chat_tools import get_logger, get_parser


async def get_messsages(args):
    """
    Continuously receive and log messages from a network connection.

    Establishes an asynchronous connection to a server using
    host and port from `args`.
    Reads incoming messages line by line in an infinite loop and
    logs them with debug level.

    Args:
        args (object): Configuration object containing:
            - host (str): Server hostname or IP address.
            - port (int): Server port number.

    Returns:
        None: This function runs indefinitely until the connection is closed.

    Raises:
        ConnectionRefusedError: If the server refuses the connection.
        OSError: For general network-related errors during connection setup.
    """

    reader, _ = await asyncio.open_connection(args.host, args.port)

    while True:

        message = await reader.readline()
        logger.debug(f'{message.decode().strip()!r}')


if __name__ == "__main__":
    logger = get_logger('reader')
    args = get_parser()

    asyncio.run(get_messsages(args))
