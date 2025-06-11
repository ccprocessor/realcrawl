import inspect
from pathlib import Path

import commentjson as json


class ErrorMsg:
    """Error message manager class."""
    _errors = {}

    @classmethod
    def _load_errors(cls):
        """Load error codes and messages from JSON file."""
        exception_defs_file_path = Path(__file__).parent / 'exception.jsonc'
        with open(exception_defs_file_path, 'r', encoding='utf-8') as file:
            jso = json.load(file)
            for module, module_defs in jso.items():
                for err_name, err_info in module_defs.items():
                    err_code = err_info['code']
                    cls._errors[str(err_code)] = {
                        'message': err_info['message'],
                        'module': module,
                        'error_name': err_name,
                    }

    @classmethod
    def get_error_message(cls, error_code: int):
        # 根据错误代码获取错误消息
        if str(error_code) not in cls._errors:
            return f'unknown error code {error_code}'
        return cls._errors[str(error_code)]['message']

    @classmethod
    def get_error_code(cls, module: str, error_name: str) -> int:
        """根据模块名和错误名获取错误代码."""
        for code, info in cls._errors.items():
            if info['module'] == module and info['error_name'] == error_name:
                return int(code)
        raise ValueError(f'error code not found: module={module}, error_name={error_name}')


ErrorMsg._load_errors()


class RealCrawlBaseException(Exception):
    """Base exception class for realcrawl."""

    def __init__(self, custom_message: str | None = None, error_code: int | None = None):
        if error_code is None:
            error_code = ErrorMsg.get_error_code('realcrawlBase', 'realcrawlBaseException')

        self.error_code = error_code
        self.message = ErrorMsg.get_error_message(self.error_code)
        self.custom_message = custom_message
        self.dataset_name = ''
        super().__init__(self.message)
        frame = inspect.currentframe().f_back
        self.__py_filename = frame.f_code.co_filename
        self.__py_file_line_number = frame.f_lineno

    def __str__(self):
        return (
            f'{self.__py_filename}: {self.__py_file_line_number}#{self.error_code}#{self.message}#{self.custom_message}'
        )


##############################################################################
#
#  Config Exceptions
#
##############################################################################

class ConfigBaseException(RealCrawlBaseException):
    """Base exception class for Config."""
    def __init__(self, custom_message: str | None = None, error_code: int | None = None):
        if error_code is None:
            error_code = ErrorMsg.get_error_code('Config', 'ConfigBaseException')
        super().__init__(custom_message, error_code)


class ConfigFileNotFoundException(ConfigBaseException):
    """Config file not found exception."""
    def __init__(self, custom_message: str | None = None, error_code: int | None = None):
        if error_code is None:
            error_code = ErrorMsg.get_error_code('Config', 'ConfigFileNotFoundException')
        super().__init__(custom_message, error_code)
