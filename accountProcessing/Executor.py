from multiprocessing.pool import ThreadPool
from multiprocessing import Manager
from threading import Event
from accountProcessing.thread import runWorker
from client.connection.credentials import getFreePorts
from time import sleep
import logging
from collections import deque
from accountProcessing.Progress import Progress
import PySimpleGUI as sg
from typing import Any, Dict

class Executor:
    def __init__(self, settings: Dict[str, Any], progressBar: sg.Text, exitEvent: Event) -> None:
        """
        Initializes a Executor instance.

        :param settings: Execution settings.
        :param progressBar: The progress bar object.
        :param exitEvent: The exit event to stop execution.
        """
        self.__settings = settings
        self.__progressBar = progressBar
        self.__exitEvent = exitEvent
        self.__threadCount = int(self.__settings["threadCount"])
        self.__allowPatching = self.__threadCount == 1
        self.__argQueue = deque()
        self.__threadResults = []
    
    def run(self, accounts: Dict[str, Any]) -> None:
        """
        Executes tasks on given accounts.

        :param accounts: The list of accounts to execute tasks on.
        """
        self.__argQueue.clear()
        self.__threadResults.clear()
        self.__progress = Progress(len(accounts), self.__progressBar)

        with Manager() as manager:
            exitFlag = manager.Event()
            nextRiotLaunch = manager.Value("d", 0.0)
            riotLock = manager.Lock()
            nextLeagueLaunch = manager.Value("d", 0.0)
            leagueLock = manager.Lock()
            portQueue = manager.Queue()
            for port in getFreePorts(self.__threadCount * 100):
                portQueue.put(port)

            self.__argQueue.extend((account, self.__settings, self.__progress, exitFlag, self.__allowPatching, portQueue, nextRiotLaunch, riotLock, nextLeagueLaunch, leagueLock) for account in accounts)

            with ThreadPool(processes=self.__threadCount) as pool:
                self.__addWork(pool)

                while len(self.__threadResults) > 0:
                    if self.__exitEvent.is_set():
                        logging.info("Stopping execution...")
                        exitFlag.set()
                        pool.close()
                        pool.join()
                        logging.info("Execution stopped!")
                        break
                    else:
                        self.__removeFinishedThreads()
                        self.__addWork(pool)
                    sleep(0.1)


    def __addWork(self, pool: ThreadPool) -> None:
        """
        Adds work to the thread pool until the maximum number of threads is reached or the argument queue is empty.

        :param pool: The thread pool to add work to.
        """
        while len(self.__threadResults) < self.__threadCount and len(self.__argQueue) > 0:
            self.__threadResults.append(pool.apply_async(runWorker, args=self.__argQueue.popleft()))

    def __removeFinishedThreads(self) -> None:
        """
        Removes finished thread results from the result list.
        """
        self.__threadResults[:] = (result for result in self.__threadResults if not result.ready())