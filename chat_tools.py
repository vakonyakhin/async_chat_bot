import logging
import logging.config
import yaml
import configargparse
import json
import asyncio
import functools


class InvalidToken(Exception):
    pass


def get_logger(name):
    """
    Возвращает именованный экземпляр логгера.
    Конфигурация логирования будет применена при первом вызове.

    Args:
        name (str): Имя логгера.

    Returns:
        logging.Logger: Сконфигурированный экземпляр логгера.

    """
    _configure_logging()
    return logging.getLogger(name)


def with_logger(name):
    """
    Декоратор, который внедряет логгер в качестве первого аргумента в оборачиваемую функцию.

    Args:
        name (str): Имя логгера, который будет создан и передан.

    Returns:
        Callable: Асинхронная функция-обертка.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(name)
            return await func(logger, *args, **kwargs)
        return wrapper
    return decorator


@functools.lru_cache(maxsize=1)
def _configure_logging():
    """
    Загружает и применяет конфигурацию логирования из файла 'logger_config.yaml'.

    Функция выполняется только один раз благодаря декоратору `lru_cache`.

    Raises:
        FileNotFoundError: Если файл 'logger_config.yaml' не найден.
        yaml.YAMLError: Если файл YAML содержит некорректный синтаксис.
        ValueError: Если словарь конфигурации логирования невалиден.
    """
    try:
        with open('logger_config.yaml', 'r') as file:
            logger_config = yaml.safe_load(file)
        logging.config.dictConfig(logger_config)
    except FileNotFoundError:
        print('Logger_config.yaml does not exist.')
    except yaml.YAMLError:
        print('YAML file contains invalid syntax or structure')
    except ValueError:
        print('Logging configuration dictionary is invalid.')


def create_arg_parser(config_path=None):

    """Создает и возвращает парсер аргументов командной строки.

    Парсер настроен для загрузки параметров из указанного конфигурационного файла.

    Args:
        config_path (list, optional): Список путей к файлам конфигурации. Defaults to None.

    Returns:
        configargparse.ArgParser: Сконфигурированный парсер.
    """
    parser = configargparse.ArgParser(
        description='TCP client for interacting with a chat server.',
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        default_config_files=config_path
    )

    parser.add('-c', '--config', is_config_file=True, help='Path to configuration file')
    parser.add('--host', type=str, default='minechat.dvmn.org', env_var='HOST',
          help='Host address for connection (default: minechat.dvmn.org)')
    parser.add('-p','--port', type=int, default=5000, env_var='PORT',
          help='Port number for connection (default: 5000)')
    parser.add('-t', '--token', type=str, default='', env_var='TOKEN',
          help='Authentication token (default: empty string)')

    return parser


def get_parse_arguments(arg_parser):
    """
    Разбирает аргументы командной строки с помощью предоставленного парсера.

    Args:
        arg_parser (configargparse.ArgParser): Экземпляр парсера.

    Returns:
        argparse.Namespace: Объект с разобранными аргументами.
    """
    return arg_parser.parse_args()


def read_token():
    """
    Читает токен аутентификации из файла 'token.json'.

    Returns:
        str: Значение ключа 'account_hash' из JSON-файла.

    """
    with open('token.json', 'r') as file:
        token = json.load(file)
    return token['account_hash']


async def get_connection(config):
    host = config.host
    port = config.port
    """
    Устанавливает асинхронное сетевое соединение.

    Args:
        config (argparse.Namespace): Объект конфигурации, содержащий `host` и `port`.

    Returns:
        list: Кортеж из (StreamReader, StreamWriter).

    """

    reader, writer = await asyncio.open_connection(host, port)

    return [reader, writer]
