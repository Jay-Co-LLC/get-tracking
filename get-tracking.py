import sys
import datetime
import logging
import taw
import meyer
import config
import errors

log_file = f"LOG-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
logger = logging.getLogger('get-tracking')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler(log_file))
logger.addHandler(logging.StreamHandler())


def get_tracking():
    taw.get_tracking()
    meyer.get_tracking()


if __name__ == '__main__':
    try:
        arg = sys.argv[1]
    except IndexError:
        logger.info("No argument passed, defaulting to TEST mode.")
        arg = '-t'

    try:
        config.set_mode(arg)
    except errors.UnsupportedArgument:
        logger.error("Unsupported argument passed in.")
        raise

    get_tracking()
