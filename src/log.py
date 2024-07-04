# taken from https://stackoverflow.com/questions/45701478/log-from-multiple-python-files-into-single-log-file-in-python#:~:text=Say%20you%20have%20two%20python,your%20master%20file%20master.py%20.&text=Then%20executing%20master.py%20will,py%20and%20py2.py%20).

import logging

# to output the log, change level = logging.XYZ to info
def get_logger(name):
    log_format = '%(asctime)s  %(name)8s  %(levelname)5s  %(message)s'
    logging.basicConfig(level=logging.WARNING,
                        format=log_format,
                        filename='dev.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger(name).addHandler(console)
    return logging.getLogger(name)