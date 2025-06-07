from loguru import logger as raw_logger
import uuid

logger = raw_logger

def log_init(config: dict):
    global logger
    log_config = dict(config.get('log', {}))
    try:
        if not log_config:
            return
        
        log_level = 'INFO'
        if 'level' in log_config:
            log_level = str(log_config.get('level')).upper()
        
        raw_logger.add(log_config['output'], level=log_level, format='')
        logger = raw_logger.bind(uuid=str(uuid.uuid4()))
    finally:
        pass
