import logging
import logging.config
import yaml
import configargparse
import json


def get_logger(name):
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

    return logging.getLogger(name)


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
    parser.add('--port', type=int, default=5000, env_var='PORT',
          help='Port number for connection (default: 5000)')
    parser.add('--username', type=str, default='', env_var='USERNAME',
          help='Username for authentication (default: empty string)')
    parser.add('--token', type=str, default='', env_var='TOKEN',
          help='Authentication token (default: empty string)')

    return parser


def get_parse_arguments(arg_parser):
    """Parses command line arguments."""
    return arg_parser.parse_args()
