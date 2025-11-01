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
    """
    _configure_logging()
    return logging.getLogger(name)


def with_logger(name):
    """
    Декоратор, который внедряет логгер в качестве первого аргумента в оборачиваемую функцию.
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
    Configure and return a logger instance based on a YAML configuration file.

    This function:
    1. Loads logging configuration from 'logger_config.yaml'.
    2. Applies the configuration using `logging.config.dictConfig()`.
    3. Returns a named logger instance as specified by the `name` argument.

    Args:
        name (str): Name of the logger to retrieve. Typically corresponds to the module name
                    or a custom identifier for the logging context.

    Returns:
        logging.Logger: A configured logger instance ready for use.

    Raises:
        FileNotFoundError: If 'logger_config.yaml' does not exist.
        yaml.YAMLError: If the YAML file contains invalid syntax or structure.
        ValueError: If the logging configuration dictionary is invalid.
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

    """
    Creates and returns an instance of the ArgParser configured to load parameters from the specified configuration file.

    :param config_paths: List of paths to configuration files.
    :return: Configured ArgParser.
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
    parser.add('--filepath', type=str, default='./', env_var='FILEPATH',
          help='Filepath for read and save messages (default: ./)')
    parser.add('-u', '--username', type=str, default='', env_var='USERNAME',
          help='Username for authentication (default: empty string)')
    parser.add('--text', type=str, env_var='TEXT', default='',
          help='Required text parameter that must be passed on the command line.')
    parser.add('-t', '--token', type=str, default='', env_var='TOKEN',
          help='Authentication token (default: empty string)')

    return parser


def get_parse_arguments(arg_parser):
    """Parses command line arguments."""
    return arg_parser.parse_args()


def read_token():

    with open('token.json', 'r') as file:
        token = json.load(file)
    return token['account_hash']


async def get_connection(config):
    host = config.host
    port = config.port

    reader, writer = await asyncio.open_connection(host, port)

    return [reader, writer]
