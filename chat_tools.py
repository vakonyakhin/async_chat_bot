import logging
import logging.config
import yaml
import configargparse


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


def get_parser():
    """
    Configure and return a command-line argument parser for a chat application.

    This function creates an `ArgParser` instance from the `configargparse`
    module, defines supported command-line arguments and their corresponding
    environment variables, and returns the parsed arguments.
    It supports configuration via both command-line flags and
    environment variables.

    Args (command-line/environment):
        --host (str): Host address for server connection (environment: HOST).
        --port (str): Port number for server connection (environment: PORT).
        -history (str): File path for storing chat history
        (environment: HISTORY_PATH).

    Returns:
        argparse.Namespace: An object containing parsed command-line arguments.
            Attributes:
                host (str): Host address provided via command-line
                or environment.
                port (str): Port number provided via command-line
                or environment.
                history (str): Chat history file path provided via command-line
                or environment.
    """
    p = configargparse.ArgParser()
    p.add('--host', env_var='HOST', help='host for connection')
    p.add('--port', env_var='PORT', help='Port for connection')
    p.add('-history', env_var='HISTORY_PATH', help='Path for chat history')

    args = p.parse_args()
    return args
