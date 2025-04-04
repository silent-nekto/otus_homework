import argparse
import dataclasses
import datetime
import gzip
import json
import re
import statistics
import sys
from string import Template
from typing import Callable, Iterable, Any
from pathlib import Path
import shutil
import structlog


logger = structlog.get_logger()


config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


@dataclasses.dataclass
class LastLog:
    full_path: Path
    file_name: str
    date: datetime.datetime
    extension: str


def find_last_log(log_dir: str):
    # поиск самого свежего лога
    last_log = None

    pattern = re.compile(r"nginx-access-ui.log-(\d{8})(\.gz)?$")
    for item in Path(log_dir).iterdir():
        if item.is_file():
            file_name = item.name
            logger.debug("Processing", name=file_name)
            m = re.match(pattern, item.name)
            if m:
                try:
                    d = datetime.datetime.strptime(m.group(1), "%Y%m%d")
                except ValueError:
                    logger.info("Incorrect date in name of log", date=m.group(1))
                    continue
                if last_log is None or d > last_log.date:
                    last_log = LastLog(item.absolute(), item.name, d, m.group(2))
    return last_log


def init_logger(log_path: str):
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    structlog_processors: Iterable[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.add_log_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.dict_tracebacks,
        timestamper,
        structlog.processors.JSONRenderer(),
    ]
    logger_factory: Callable
    if log_path:
        logger_factory = structlog.WriteLoggerFactory(
            file=open(log_path, mode="wt", encoding="utf-8")
        )
    else:
        logger_factory = structlog.PrintLoggerFactory()
    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=logger_factory,
        cache_logger_on_first_use=False,
    )


def enum_log_records(log: LastLog):
    # перечисление записей в логе (url и время обработки запроса)
    opener = open if not log.extension else gzip.open
    # pattern = re.compile(r'.+?\[.+?\]\s".+?\s(.+?)\s.*?([0-9.]+)$')
    pattern = re.compile(r'[^"]+"\w+\s(.+?)\s.*?([0-9.]+)$')
    with opener(log.full_path, mode="rt", encoding="utf-8") as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                yield m.group(1), float(m.group(2))
            else:
                logger.error("Incorrect format of log record", line=line)


def get_statistic(records_enumerator):
    # подсчет статистики по всем запросам из лога
    result = {"count": 0, "time_sum": 0, "urls": {}}
    for url, time in records_enumerator:
        result["count"] += 1
        result["time_sum"] += time
        if url in result["urls"]:
            info = result["urls"][url]
            info["requests"].append(time)
            info["time_sum"] += time
            info["count"] += 1
        else:
            result["urls"][url] = {"requests": [time], "count": 1, "time_sum": time}
    return result


def extract_json_table(info, urls_count):
    # получение json-таблицы для вставки в шаблон отчета
    # разворачивание словаря в список кортежей с сортировкой по суммарному времени выполнения запроса
    stats = sorted(
        [(url, info["urls"][url]) for url in info["urls"]],
        key=lambda d: d[1]["time_sum"],
        reverse=True,
    )
    stats = stats[:urls_count]

    result = []
    for url, stat in stats:
        result.append(
            {
                "count": stat["count"],
                "count_perc": (stat["count"] / info["count"]) * 100,
                "time_sum": stat["time_sum"],
                "time_perc": (stat["time_sum"] / info["time_sum"]) * 100,
                "time_avg": statistics.mean(stat["requests"]),
                "time_max": max(stat["requests"]),
                "time_med": statistics.median(stat["requests"]),
                "url": url,
            }
        )
    return result


def create_report(path, table):
    with open(r"./template/report.html", mode="rt", encoding="utf-8") as f_in:
        t = Template(f_in.read())
    with open(path, mode="wt", encoding="utf-8") as f_out:
        f_out.write(t.safe_substitute({"table_json": json.dumps(table)}))
    if not (path.parent / "jquery.tablesorter.js").exists():
        shutil.copy(
            "./template/jquery.tablesorter.js", path.parent / "jquery.tablesorter.js"
        )


def update_cfg(path):
    # обновление текущего конфига
    try:
        with open(path, mode="rt", encoding="utf-8") as f:
            new_cfg = json.load(f)
    except Exception:
        raise ValueError(f"Failed to load config file {path}")
    config.update(new_cfg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="", help="Path to log file")
    parser.add_argument("--config", required=False)
    args = parser.parse_args()
    try:
        init_logger(args.log)
        if args.config:
            update_cfg(args.config)

        log_file = find_last_log(config["LOG_DIR"])
        if not log_file:
            logger.error("Last log was not found")
            sys.exit(1)
        logger.info("Parse log", log=log_file.file_name)

        full_info = get_statistic(enum_log_records(log_file))

        table = extract_json_table(full_info, config["REPORT_SIZE"])

        create_report(
            Path(config["REPORT_DIR"])
            / f'report-{log_file.date.strftime("%Y.%m.%d")}.html',
            table,
        )
    except (Exception, KeyboardInterrupt) as e:
        logger.error(e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
