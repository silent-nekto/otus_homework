import os
import datetime
import re
import dataclasses


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
        m = re.match(pattern, name)
        if m:
            d = datetime.datetime.strptime(m.group(1), "%Y%m%d")
            if last_log is None or d > last_log.date:
                last_log = LastLog(os.path.join(log_dir, name), name, d, m.group(2))
                pass
    return last_log


def main():
    log_file = find_last_log(config["LOG_DIR"])
    print(log_file)


if __name__ == "__main__":
    main()
