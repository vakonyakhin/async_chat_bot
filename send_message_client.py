import asyncio
import logging


async def send_message():

    reader, writer = await asyncio.open_connection('minechat.dvmn.org', 5050)

    data = await reader.readline()
    logging.debug(data.decode())
    token = '9aa4f76e-52a7-11f0-a5a4-0242ac110003\n'

    writer.write(token.encode())
    await writer.drain()
    logging.debug(await reader.readline())
    logging.debug(await reader.readline())

    while True:

        input_data = input('')

        message = f'{input_data} \n\n'
        writer.write(message.encode())
        logging.debug(f'Send message - {message}')
        await writer.drain()
        logging.debug(f'Sent message was successed')


if __name__ == "__main__":

    logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)
    asyncio.run(send_message())
