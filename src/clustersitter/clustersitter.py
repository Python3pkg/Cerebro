import threading
import time
from requests import async


class ClusterSitter:
    def __init__(self):
        self.worker_thread_count = 1
        self.monitors = []
        self.machines = {}
        self.zones = []

    def start(self):
        # Spin up all the monitoring threads
        for threadnum in range(self.worker_thread_count):
            machinemonitor = MachineMonitor(parent=self,
                                            number=threadnum)
            thread = threading.Thread(target=self._run_monitor,
                                      args=(machinemonitor))
            thread.start()
            self.monitors.append((machinemonitor, thread))

        self.calculator = threading.Thread(target=self._calculator)
        self.calculator.start()

    def _calculator(self):
        self.calculate_idle_machines()
        time.sleep(500)

    def add_job(self, job):
        # Step 1: Ensure we have enough machines in each SFZ
        # Step 1a: Check for idle machines and reserve as we find them
        new_machines = []
        reserved_machines = []
        for zone in self.job.get_shared_fate_zones():
            idle_available = self.get_idle_machines_in_zone(zone)
            idle_required = job.get_required_machines_in_zone(zone)
            required_new_machine_count = (len(idle_required) -
                                          len(idle_available))
            usable_machines = []
            if required_new_machine_count > 0:
                spawned_machines = self.begin_adding_machines(
                    zone,
                    required_new_machine_count)

                # len(spawned) + len(idle_available) = len(idle_required)
                usable_machines.extend(spawned_machines)
                usable_machines.extend(idle_available)
                new_machines.extend(spawned_machines)
            else:
                # idle_available > idle_required, so use just as many
                # as we need
                usable_machines = idle_available[:len(idle_required)]

            # Now reserve part of the machine for this job
            reserved_machines.extend(usable_machines)
            for machine in usable_machines:
                machine.start_task(job)

        # Step 2: Wait for new machines to be available
        ready = False
        while not ready:
            not_ready = 0
            for machine in new_machines:
                if not machine.is_available():
                    not_ready += 1

            if not_ready == 0:
                ready = True
                break

            logging.info("Waiting for %s more machines to be available" % \
                             not_ready)
            time.sleep(5)

        # Done!
        return reserved_machines

    def begin_adding_machines(zone, count):
        # This should run some kind of modular procedure
        # to bring up the machines, ASYNCHRONOUSLY (in a new thread?)
        # and return objects representing the machiens on their way up.
        pass

    def get_idle_machines_in_zone(self, zone):
        return self.idle_machines[zone]

    def calculate_idle_machines(self):
        idle_machines = {}
        for zone in self.zones:
            idle_machines[zone] = []
            for machine in self.machines[zone]:
                tasks = machine.get_running_tasks()
                if not tasks:
                    idle_machines[zone].append(machine)

        # The DICT swap must be atomic, or else another
        # thread could get a bad value during calculation.
        self.idle_machines = idle_machines

    def _run_monitor(self, monitor):
        # Assume we're in our own thread here
        monitor.start()


class MachineProfile(object):
    def __init__(self, cpu=None, mem=None):
        self.cpu = cpu
        self.mem = mem


class ProductionJob(object):
    def __init__(self,
                 task_configuration,
                 deployment_layout):
        # The config to pass to a machinesitter / tasksitter
        self.task_configuration = task_configuration

        # A mapping of SharedFateZoneObj : (# Jobs, CPU, Mem)
        self.deployment_layout = deployment_layout

    def get_required_machines_in_zone(self, zone):
        zoneinfo = self.deployment_layout[zone]
        profiles = []
        for _ in range(zoneinfo[0]):
            profiles.append(MachineProfile(cpu=zoneinfo[1],
                                           mem=zoneinfo[2]))

        return profiles

    def get_name(self):
        return self.task_configuration['name']

class HasMachineSitter(object):
    """
    Everything is asynchronous -- always returns a request
    object that can be run later.
    """
    def __init__(self):
        self.machinesitter_port = None
        self.hostname = None

    def _api_start_task(self, name):
        pass

    def _api_identify_sitter(self, port):
        pass

    def _api_run_request(self, request):
        """
        Explicitly run the async object    
        """
        result = async.map(request)

    def _api_set_port(self, port):
        self.machinesitter_port = port

    def _api_get_endpoint(self, path):
        return "http://%s:%s/%s" % (self.hostname,
                                    self.machinesitter_port,
                                    path)

class MonitoredMachine(HasMachineSitter):
    """
    An interface for a single
    machine to monitor.  Some functions
    Should be implemented per cloud provider.
    Note: It it assumed that the MachineMonitor
    keeps all MonitoredMachines up to date, and that
    with the exception of functions explicitly about
    downloading data, all calls are accessing LOCAL
    CACHED data and NOT making network calls.
    """
    def __init__(self, hostname, machine_number):
        self.hostname = hostname
        self.running_tasks = []
        self.machine_number = machine_number

    def get_running_tasks(self):
        """
        Return cached data about running task status
        """
        pass

    def start_task(self, job):
        # If the machine is up and initalized, make the API call
        # Otherwise, spawn a thread to wait for the machine to be up
        # and then make the call
        if self.is_initialized():
            self._api_run_request(self._api_start_task(job.get_name())))

    def begin_initialization(self):
        # Start an async request to find the 
        # machinesitter port number
        # and load basic configuration
        pass

    def is_initalized(self):
        return self.machinesitter_port != None

class MachineMonitor:
    def __init__(self, parent, number, monitored_machines=[]):
        self.clustersitter = parent
        self.number = number
        self.monitored_machines = []

    def add_machines(self, monitored_machines):
        self.monitored_machines.extend(monitored_machines)

    def start(self):
        # Find the sitter port for each machine
        remaining_machines = [m for m in self.monitored_machines]
        while remaining_machines != []:
            next_port = 40000
            requests = []
            for machine in remaining_machines:
                requests.append(machine._api_identify_sitter(next_port))

            async.map(requests)

            validated_machines = []
            for index, req in requests:
                if req.status_code == 200:
                    validated_machines.append(index)

            # Pop in reverse order so as not to screw up the
            # indexes (largest -> smallest doesn't cause any cascading index
            # changes for elements we care about)
            validated_machines.reverse()
            for i in validated_machines:
                machine = remaining_machines.pop(i)
                machine._api_set_port(next_port)

            next_port += 1

        while True:
            requests = []
            for machine in machines:
                if machine.is_initalized():
                    requests.append(machine._api_get_stats())
            time.sleep(.1)

        # Run all requests with a time limit
        
