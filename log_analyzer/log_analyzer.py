# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  
#                     '$request_time';
import os
import datetime
import re
import dataclasses
import structlog
logger = structlog.get_logger()


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


@dataclasses.dataclass
class LastLog:
    full_path: str
    file_name: str
    date: datetime
    extension: str


def find_last_log(log_dir: str):
    last_log = None
    pattern = re.compile(r'nginx-access-ui.log-(\d{8})(\.gz)?$')
    for name in os.listdir(log_dir):
        logger.info('Processing', name=name)
        m = re.match(pattern, name)
        if m:
            d = datetime.datetime.strptime(m.group(1), '%Y%m%d')
            if last_log is None or d > last_log.date:
                last_log = LastLog(os.path.join(log_dir, name), name, d, m.group(2))
                pass
    return last_log


def try_logger():
    # Препроцессор timestamper, добавляющий к каждому логу унифицированные  метки времени
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Препроцессоры Structlog
    structlog_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.add_log_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.dict_tracebacks,
        timestamper,
    ]
    from structlog.processors import JSONRenderer
    logger_factory = structlog.WriteLoggerFactory(file=open(f'analyzer.log', mode='wt', encoding='utf-8'))  # or structlog.PrintLoggerFactory()
    structlog.configure(
        processors=structlog_processors + [JSONRenderer()],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=logger_factory,
        cache_logger_on_first_use=False,
    )


def main():
    log_file = find_last_log(config["LOG_DIR"])
    print(log_file)
    try_logger()


if __name__ == "__main__":
    main()
