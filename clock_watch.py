import time
from datetime import datetime
from typing import Callable


class clock_watch:
    def __init__(self, reporter: Callable, name: str):
        self.name = name
        self.start = datetime.now()
        self.reporter = reporter

    def __enter__(self):
        self.start = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.print('Done')

    def print(self, message: str):
        if callable(self.reporter):
            self.reporter(
                f'{self.start:%H:%M:%S} - {datetime.now():%H:%M:%S} {(datetime.now() - self.start).total_seconds():.2f}[s] : '
                f'{self.name} : {message}')


if __name__ == '__main__':
    with clock_watch(print, 'sample') as cw:
        time.sleep(1)
        cw.print('done half')
        time.sleep(1.5)
