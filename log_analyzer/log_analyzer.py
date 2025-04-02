import gzip
import os
import datetime
import re
import dataclasses
import structlog
logger = structlog.get_logger()


config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


@dataclasses.dataclass
class LastLog:
    full_path: str
    file_name: str
    date: datetime
    extension: str


def find_last_log(log_dir: str):
    last_log = None
    pattern = re.compile(r"nginx-access-ui.log-(\d{8})(\.gz)?$")
    for name in os.listdir(log_dir):
        logger.info('Processing', name=name)
        m = re.match(pattern, name)
        if m:
            d = datetime.datetime.strptime(m.group(1), "%Y%m%d")
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


def analyze_it(log: LastLog):
    opener = open if not log.extension else gzip.open
    # pattern = re.compile(r'.+?\[.+?\]\s".+?\s(.+?)\s.*?([0-9.]+)$')
    pattern = re.compile(r'[^"]+"\w+\s(.+?)\s.*?([0-9.]+)$')
    with opener(log.full_path, mode='rt', encoding='utf-8') as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                yield m.group(1), float(m.group(2))
            else:
                print(f'Incorrect log format: {line}')


def get_statistic(reader):
    result = {
        'count': 0,
        'time_sum': 0,
        'urls': {}
    }
    for url, time in reader:
        result['count'] += 1
        result['time_sum'] += time
        if url in result['urls']:
            info = result[url]
            info['requests'].append(time)
            info['time_sum'] += time
            info['count'] += 1
        else:
            result[url] = {'requests': [time], 'count': 1, 'time_sum': time}
    return result


def main():
    log_file = find_last_log(config["LOG_DIR"])
    print(log_file)
    stat = get_statistic(analyze_it(log_file))
    print(stat['count'])
    print(stat['time_sum'])
    s = sorted([(url, stat['urls'][url]) for url in stat['urls']], key=lambda d: d[1]['time_sum'])
    print(s[:10])
    # try_logger()


if __name__ == "__main__":
    main()
