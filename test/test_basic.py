import main
import os
import subprocess
import tempfile
import unittest

spin_proc = None


def setUp(self):
    global spin_proc
    spin_proc = subprocess.Popen('yes', stdout=open('/dev/null', 'w'))


def tearDown(self):
    global spin_proc
    spin_proc.terminate()


class BasicTests(unittest.TestCase):

    def run_check(self, args, retval=0):
        try:
            main.main(args)
        except SystemExit, e:
            self.assertEqual(e.code, retval)

    def test_quick_command(self):
        self.run_check(["--command", "ls >/dev/null"])

    def test_quick_command_cpu_constraint(self):
        self.run_check(["--cpu=.1", "--command", "ls >/dev/null"])

    def test_quick_command_mem_constraint(self):
        self.run_check(["--mem=10", "--command", "ls >/dev/null"])

    def test_quick_command_cpu_mem_constraint(self):
        self.run_check(["--cpu=.2", "--mem=10", "--command", "ls >/dev/null"])

    def test_slow_command(self):
        self.run_check(["--command", "ls >/dev/null; sleep .21"])

    def test_slow_command_cpu_constraint(self):
        self.run_check(["--cpu=.5", "--command", "ls >/dev/null; sleep .21"])

    def test_slow_command_mem_constraint(self):
        self.run_check(["--mem=10", "--command", "ls >/dev/null; sleep .21"])

    def test_slow_command_cpu_mem_constraint(self):
        self.run_check(["--cpu=.5", "--mem=10",
                        "--command", "ls >/dev/null; sleep .31"])

    def test_cpu_constraint(self):
        self.run_check(["--cpu=.5", "--command", "./test/spin.sh"], 9)

    def test_cpu_constraint_redirect(self):
        self.run_check(["--cpu=.1", "--command",
                        "bash -c './test/spin.sh 2>/dev/null'"],
                       9)

    def test_cpu_constraint_subprocess(self):
        self.run_check(["--cpu=.1", "--command",
                        "bash -c 'bash -c \'./test/spin.sh\''"],
                       9)

    def test_mem_constraint(self):
        self.run_check(["--mem=3", "--command", "./test/mem.sh"],
                       9)

    def test_mem_constraint_redirect_subprocess(self):
        self.run_check(["--mem=3", "--command",
                        "bash -c 'bash -c \'./test/mem.sh\''"],
                       9)

    def test_mem_constraint_redirect(self):
        self.run_check(["--mem=3",
                        "--command", "./test/mem.sh 2>/dev/null"], 9)

    def test_restarting(self):
        filename = tempfile.mktemp()
        self.run_check(["--cpu=.5", "--restart", "--max-restarts=2",
                        "--command",
                        "echo '1' >> %s ; ./test/spin.sh" % filename], 9)

        lines = open(filename).readlines()
        print lines
        os.unlink(filename)
        self.assertEqual(3, len(lines))

    def test_ensure_alive(self):
        filename = tempfile.mktemp()
        self.run_check(["--ensure-alive", "--restart", "--max-restarts=2",
                        "--command",
                        "echo '1' >> %s" % filename])

        lines = open(filename).readlines()
        print lines
        os.unlink(filename)
        self.assertEqual(3, len(lines))

    def test_ensure_alive_many_times(self):
        filename = tempfile.mktemp()
        self.run_check(["--ensure-alive", "--restart", "--max-restarts=551",
                        "--command",
                        "echo '1' >> %s" % filename])

        lines = open(filename).readlines()
        print lines
        os.unlink(filename)
        self.assertEqual(552, len(lines))
