import asyncio
from datetime import datetime
import aiofiles

import configargparse


def get_parser():

    p = configargparse.ArgParser()
    p.add('--host', env_var='HOST', help='host for connection')
    p.add('--port', env_var='PORT', help='Port for connection')
    p.add('-history', env_var='HISTORY_PATH', help='Path for chat history')

    args = p.parse_args()
    return args


async def get_messsages(date, args):
    reader, _ = await asyncio.open_connection(
        args.host, args.port)

    while True:

        data = await reader.readline()
        print(f'Received: {data.decode()!r}')

        async with aiofiles.open(args.history, 'ab') as file:
            message = f'{date} {data.decode()!r} \r'
            await file.write(message.encode())


if __name__ == "__main__":
    args = get_parser()
    now = datetime.now()
    formatted_date = now.strftime("[%d.%m.%Y %H:%M]")

    asyncio.run(get_messsages(formatted_date, args))
