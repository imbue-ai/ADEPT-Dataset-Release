from datetime import datetime
from multiprocessing import Event
from multiprocessing import Pipe
from multiprocessing import Process
from multiprocessing.connection import Connection
from queue import Empty
from sys import stderr
from typing import Callable
from typing import Sequence


class Worker(Process):
    def __init__(self, func: Callable, pipe: Connection, stop: Event, init: Callable = None):
        Process.__init__(self)
        self.func = func
        self.pipe = pipe
        self.stop = stop
        self.init = init

    def run(self):
        try:
            if callable(self.init):
                self.init()

            while True:
                try:
                    i, args = self.pipe.recv()
                except EOFError:
                    break

                if self.stop.is_set():
                    break

                v = self.func(*args)

                if self.stop.is_set():
                    break

                self.pipe.send((i, v))
        except:
            self.pipe.close()
            self.stop.set()
            raise


def pool_map(work_function: Callable, worker_args: Sequence, work_n: int, initializer=None):
    """
    Basically Pool.starmap, but more resistant to hard enough crashes.
    """
    assert work_n >= 0
    if work_n == 0:
        return sorted(work_function(*args) for args in worker_args)

    sent = 0
    seen = 0
    size = len(worker_args)
    stop = Event()

    def stat(text: str):
        time = datetime.now().isoformat(" ")
        stderr.write("{} {:>5} {:>5} {} \n".format(text, sent, size - seen, time))
        stderr.flush()

    work_n = min(work_n, size)
    channel = []
    workers = []
    results = []

    for _ in range(work_n):
        ch_1, ch_2 = Pipe(duplex=True)
        workers.append(Worker(work_function, ch_1, stop, initializer))
        channel.append(ch_2)

    stat("QSIZE:")

    for worker, pipe in zip(workers, channel):
        pipe.send((sent, worker_args[sent]))
        sent += 1
        worker.start()

    while True:
        if stop.wait(0.01):
            stat("ABORT.")
            break

        dead = 0
        done = 0

        for worker, pipe in zip(workers, channel):
            if pipe.poll():
                done += 1
                results.append(pipe.recv())
                seen += 1
                if sent != size:
                    pipe.send((sent, worker_args[sent]))
                    sent += 1
            if worker.exitcode:
                dead += 1
                stat("X%+04d" % worker.exitcode)

        if dead:
            stop.set()
            break

        if done:
            stat("QSIZE:")

        if seen == size:
            break

    stat("JOIN1.")

    for pipe in channel:
        pipe.close()

    for worker in workers:
        worker.join()

    assert len(worker_args) == len(results), "some workers have crashed!"
    results = [v for i,v in sorted(results)]

    return results
