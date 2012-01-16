import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MachineMonitor:
    def __init__(self, parent, number, monitored_machines=[]):
        self.clustersitter = parent
        self.number = number
        # Need to copy the array to deref it so its not shareda
        # amoung threads
        self.monitored_machines = [m for m in monitored_machines]
        self.add_queue = []
        self.pull_failures = {}
        self.failure_threshold = 1

        logger.info("Initialized a machine monitor for %s" % (
                str(self.monitored_machines)))

    def num_monitored_machines(self):
        return len(self.monitored_machines) + len(self.add_queue)

    def add_machines(self, monitored_machines):
        self.add_queue.extend(monitored_machines)
        for m in monitored_machines:
            self.pull_failures[m] = 0

        logger.info("Queued %s for inclusion in next stats run in %s" % (
                [str(a) for a in monitored_machines],
                self.number))

    def initialize_machines(self, monitored_machines):
        for m in monitored_machines:
            if not m._api_identify_sitter():
                self.pull_failures[m] += 1

    def start(self):
        self.initialize_machines(self.monitored_machines)

        while True:
            start_time = datetime.now()
            logger.info("Processing add queue %s at %s" % (self.add_queue,
                                                            self.number))
            while len(self.add_queue) > 0:
                machine = self.add_queue[-1]
                self.initialize_machines([machine])
                self.monitored_machines.append(machine)
                self.add_queue.remove(machine)

            logger.info("Finished processing add queue")
            logger.info("Beggining machine monitoring poll for %s at %s" % (
                    [str(a) for a in self.monitored_machines],
                    self.number))

            for machine in self.monitored_machines:
                if machine.is_initialized():
                    if not machine._api_get_stats():
                        self.pull_failures[machine] += 1
                    else:
                        self.pull_failures[machine] = 0
                else:
                    self.initialize_machines([machine])

            logger.info("Pull Failures: %s" % (
                    [(m.hostname, count) for m, count in \
                         self.pull_failures.items()]))

            for machine, count in self.pull_failures.items():
                if count >= self.failure_threshold:
                    self.monitored_machines.remove(machine)
                    del self.pull_failures[machine]
                    machine.detected_sitter_failures += 1
                    logger.warn(
                        "Removing %s because we can't contact the sitter! " % (
                            machine.hostname))
                    self.clustersitter._register_sitter_failure(machine, self)

            time_spent = datetime.now() - start_time
            sleep_time = self.clustersitter.stats_poll_interval - \
                time_spent.seconds
            logger.info(
                "Finished poll run for %s.  Time_spent: %s, sleep_time: %s" % (
                    [str(a) for a in self.monitored_machines],
                    time_spent,
                    sleep_time))

            if sleep_time > 0:
                time.sleep(sleep_time)
