import logging

class CustomExceptionFormatter(logging.Formatter):
    """
    The custom logging formatter for re-format exception stacktrace
    So it can be written in single log record in CloudWatch
    """
    def formatException(self, exc_info):
        """
        Replace newline symbol to shifted line symbol
        :param exc_info: The exception info
        :return: formatted exception's string
        """
        return super().formatException(exc_info).replace('\n', '\r')

    def format(self, record):
        """
        format a log record
        :param record: The Log record
        :return: the formatted record
        """
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # Split traceback text to a new shifted line
            s = s + '\r' + record.exc_text
        if record.stack_info:
            s = s + '\r' + self.formatStack(record.stack_info)
        return s


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            '()': CustomExceptionFormatter,
            'format': '%(asctime)s.%(msecs)03d | %(levelname)s | %(threadName)s - %(thread)d |'
                      ' %(module)s - %(funcName)s() - line %(lineno)d: %(message)s ',
            'datefmt': '%Y-%m-%dT%I:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'  # stdout: normal output, stderr: output string same error (red color)
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        }
    }
}
