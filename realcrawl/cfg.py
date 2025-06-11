"""统一的配置读取函数
配置文件位于
1. 环境变量 REAL_CRAWL_CONFIG_PATH
2. ~/.realcrawl/.realcrawl.jsonc
"""

import os

import commentjson as json
from loguru import logger

from realcrawl.exception.base import ConfigFileNotFoundException


def load_config(suppress_error: bool = False) -> dict:
    """Load the configuration file for the web kit. First try to read the
    configuration file from the environment variable REAL_CRAWL_CONFIG_PATH. If
    the environment variable is not set, use the default configuration file
    path ~/.realcrawl/.realcrawl.jsonc. If the configuration file does not exist, raise
    an exception.

    Raises:
        ConfigFileNotFoundException: REAL_CRAWL_CONFIG_PATH points to a non-exist file
        ConfigFileNotFoundException: cfg_path does not exist

    Returns:
        config(dict): The configuration dictionary
    """
    # 首先从环境变量LLM_WEB_KIT_CFG_PATH 读取配置文件的位置
    # 如果没有配置，就使用默认的配置文件位置
    # 如果配置文件不存在，就抛出异常
    env_cfg_path = os.getenv('REAL_CRAWL_CONFIG_PATH')
    if env_cfg_path:
        cfg_path = env_cfg_path
        if not os.path.exists(cfg_path):
            if suppress_error:
                return {}

            logger.warning(
                f'environment variable REAL_CRAWL_CONFIG_PATH points to a non-exist file: {cfg_path}'
            )
            raise ConfigFileNotFoundException(
                f'environment variable REAL_CRAWL_CONFIG_PATH points to a non-exist file: {cfg_path}'
            )
    else:
        cfg_path = os.path.expanduser('~/.realcrawl/.realcrawl.jsonc')
        if not os.path.exists(cfg_path):
            if suppress_error:
                return {}

            logger.warning(
                f'{cfg_path} does not exist, please create one or set environment variable REAL_CRAWL_CONFIG_PATH to a valid file path'
            )
            raise ConfigFileNotFoundException(
                f'{cfg_path} does not exist, please create one or set environment variable REAL_CRAWL_CONFIG_PATH to a valid file path'
            )

    # 读取配置文件
    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config
