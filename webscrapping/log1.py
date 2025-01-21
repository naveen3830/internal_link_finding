import logging

logging.basicConfig(filename="intro1.log",level=logging.DEBUG,format='%(asctime)s')

logger=logging.getLogger()

logger.info("This is an info message")