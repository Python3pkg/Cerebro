import curses
import os
import socket
import subprocess

from datetime import datetime
from menu import MenuFactory, MenuOption, MenuChanger
from machinedata import MachineData

MACHINE_DATA = None
MENUFACTORY = None
SCR = None
YPOS = 0
CURRENT_LOC = "mainmenu"
AUX = None
MACHINESITTER_URL = None


def add_line(msg):
    global YPOS
    SCR.addstr(YPOS, 0, msg)
    YPOS += 1


def refresh():
    global YPOS
    SCR.clear()
    SCR.refresh()
    YPOS = 0


def header():
    add_line("#" * 80)
    add_line(
        "MachineSitter at %s - Curses UI %s" % (
            MACHINESITTER_URL, datetime.now()))
    add_line("#" * 80)


def change_menu(newmenu, aux=None):
    global CURRENT_LOC, AUX
    CURRENT_LOC = newmenu
    AUX = aux


def mainmenu():
    menu = MENUFACTORY.new_menu("Main Menu")
    menu.add_option_vals("Refresh Window", action=dir, hotkey="*")
    menu.add_option_vals("Add a new task",
                    action=lambda: change_menu('addtask'))

    menu.add_option_vals("Show machine sitter logs",
                    action=lambda: change_menu('show_machinesitter_logs'))

    menu.render(SCR, add_line)


def show_machinesitter_logs():
    logs = MACHINE_DATA.get_sitter_logs()
    menu = MENUFACTORY.new_menu("Machine Sitter Logs")
    menu.add_option_vals("Main Menu",
                    action=lambda: change_menu('mainmenu'), hotkey="*")

    for logname, logfile in logs.items():
        menu.add_option_vals("%s (%s)" % (logname, logfile),
                         action=MenuChanger(tail_file, logfile))

    menu.render(SCR, add_line)


def tail_file(filename):
    curses.endwin()
    os.system("clear")
    subprocess.call(["echo", filename])
    try:
        subprocess.call(["tail", "-n", "100", "-f", filename])
    except:
        pass


def show_log(task, stderr=False):
    tail_file(MACHINE_DATA.get_logfile(task, stderr))


def start_task(task):
    MACHINE_DATA.start_task(task)


def stop_task(task):
    MACHINE_DATA.stop_task(task)


def show_task():
    name, task = AUX
    reload_data()
    task = MACHINE_DATA.tasks[name]

    menu = MENUFACTORY.new_menu("%s (%s)" % (name,
                                             task['command']))

    menu.add_option_vals("Main Menu",
                    action=lambda: change_menu('mainmenu'), hotkey="*")

    if task['running'] == "False":
        menu.add_option_vals("Start Task",
                             action=lambda: start_task(task))
    else:
        menu.add_option_vals("Stop Task",
                             action=lambda: stop_task(task))

        menu.add_option_vals("Show stdout",
                         action=lambda: show_log(task, False))

        menu.add_option_vals("Show stderr",
                             action=lambda: show_log(task, True))

    menu.add_option_vals("Show historic task log files",
                         action=lambda: change_menu('showrecords', task))

    menu.render(SCR, add_line)


def basic_tasks():
    global MENUFACTORY
    add_line("-" * 80)

    reload_data()

    running = []
    not_running = []
    MENUFACTORY = MenuFactory()

    for name, task in MACHINE_DATA.tasks.items():
        line = ""
        line = "%s (%s)" % (task['name'],
                            task['command'])

        if task['running'] == "True":
            running.append(line)
        else:
            not_running.append(line)

        option = MenuOption(
                task['name'],
                action=MenuChanger(change_menu, "show_task",
                                   (name, task)),
                hotkey=str(len(running) + len(not_running)),
                hidden=True)

        MENUFACTORY.add_default_option(option)

    add_line("Running Tasks:")
    for num, l in enumerate(running):
        add_line("%s. %s" % ((num + 1), l))

    add_line("Stopped Tasks:")
    for num, l in enumerate(not_running):
        add_line("%s. %s" % ((len(running) + num + 1), l))

    add_line("-" * 80)


def reload_data():
    global MACHINE_DATA
    if not MACHINE_DATA:
        MACHINE_DATA = MachineData(MACHINESITTER_URL)

    MACHINE_DATA.reload()


def main():
    global SCR, MENUFACTORY
    SCR = curses.initscr()

    refresh()
    reload_data()

    while True:
        refresh()
        header()
        basic_tasks()
        globals()[CURRENT_LOC]()


def find_sitter_url():
    port = 40000
    found = False
    while not found:
        try:
            sock = socket.socket(socket.AF_INET)
            sock.connect(("localhost", port))
            sock.close()
            found = True
        except:
            port += 1
            if port > 41000:
                return None

    return "http://localhost:%s" % port


def run():
    global MACHINESITTER_URL
    try:
        MACHINESITTER_URL = find_sitter_url()
        if not MACHINESITTER_URL:
            print "Couldn't find a running machine sitter!"
            return

        main()
    except:
        curses.endwin()
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run()
