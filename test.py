# import logging
import logging.handlers

root_logger= logging.getLogger()
root_logger.setLevel(logging.DEBUG) # or whatever
handler = logging.handlers.RotatingFileHandler('test.log', encoding='utf-8') # or whatever
handler.setFormatter(logging.Formatter('%(name)s %(message)s')) # or whatever
root_logger.addHandler(handler)
logging.debug('你好')
