import asyncio
from datetime import datetime
import aiofiles


async def get_messsages(date):
    reader, _ = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    while True:

        data = await reader.readline()
        print(f'Received: {data.decode()!r}')

        async with aiofiles.open('chat_history.txt', 'ab') as file:
            message = f'{date} {data.decode()!r} \r'
            await file.write(message.encode())


if __name__ == "__main__":
    now = datetime.now()
    formatted_date = now.strftime("[%d.%m.%Y %H:%M]")

    asyncio.run(get_messsages(formatted_date))
