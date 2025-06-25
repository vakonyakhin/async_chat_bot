import asyncio


async def get_messsages():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    while True:
        data = await reader.readline()
        print(f'Received: {data.decode()!r}')


if __name__ == "__main__":
    asyncio.run(get_messsages())
