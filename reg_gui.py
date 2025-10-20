import tkinter as tk
from tkinter import messagebox
import anyio
import asyncio
import json

from chat_tools import (
    get_logger, 
    create_arg_parser,
    get_parse_arguments,
    get_connection
)

from gui import update_tk, TkAppClosed


async def registration(reg_queue, args):

    while True:
        try:
            username = await reg_queue.get()

            if not username:
                print('Queue is empty')

            else:

                reader, writer = await get_connection(args)
                if reader:
                    print(await reader.readline())
                    writer.write(b'\n')
                    print(await reader.readline())

                    writer.write(f'{username}\n'.encode())

                    response = await reader.readline()
                    print(f'response data = {response.decode()}')
                    await reader.readline()
                    await writer.drain()

                    print('Get token')
                    token = json.loads(response.decode())
                    if token:
                        with open('token.json', 'w') as file:
                            print('Safe token to file')
                            json.dump(token, file, indent=4)
                            messagebox.showinfo('Done','Вы зарегистрированы!')

        except OSError:
            print('Отсутствуте соединение')   
        except json.JSONDecodeError:
            print('JSON decoding error')
            messagebox.showerror('Token error','Ошибка чтения токена. Повторите попытку')

        finally:
            
            print('Close connection')
            raise TkAppClosed()


def get_username(input_field, reg_queue):
    username = input_field.get()

    if username:
        reg_queue.put_nowait(username)


async def get_gui(req_queue):

    root = tk.Tk()

    root.title('Регистрация')
    root_frame = tk.Frame()
    root_frame.pack()

    label_frame = tk.Label(root_frame, text='Введите логин', width=18, height=2)
    label_frame.pack()

    input_field = tk.Entry(root_frame, textvariable='Test')
    input_field.pack(side="left", fill=tk.X, expand=True)

    send_button = tk.Button(root_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: get_username(input_field, req_queue)
    send_button.pack(side="left")

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(
            update_tk,
            root_frame
        )


async def main(args):

    reg_queue = asyncio.Queue()
    try:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(
                get_gui,
                reg_queue
            )
            task_group.start_soon(
                registration,
                reg_queue,
                args
            )
    except* (asyncio.CancelledError, TkAppClosed, KeyboardInterrupt) as exc:
        for exc in exc.exceptions:
            print(f'Cancelled tasks {exc}')


if __name__ == '__main__':
    logger = get_logger('second')
    config_path = ['./configs/reg.ini']
    arg_parser = create_arg_parser(config_path)
    arguments = get_parse_arguments(arg_parser)

    asyncio.run(main(arguments))
