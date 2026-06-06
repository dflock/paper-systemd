#!/usr/bin/python3
import curses
import os
import queue
import subprocess
import threading

FIFO_PATH = '/run/minecraft.stdin'

def run_journalctl(log_queue, stop_event):
    process = subprocess.Popen(
        ['journalctl', '-u', 'minecraft', '--follow', '-n', '100'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        while not stop_event.is_set():
            line = process.stdout.readline()
            if not line:
                break
            log_queue.put(line.decode(errors='replace'))
    finally:
        process.terminate()

def input_commands(win, f):
    while True:
        win.clear()
        win.addstr("Enter command (Ctrl-C to exit): ")
        curses.echo()
        win.move(1, 0)
        command = win.getstr().decode(errors='replace')
        f.write(command + "\n")
        f.flush()
        curses.noecho()
        win.clear()

def main(stdscr):
    if not os.path.exists(FIFO_PATH):
        curses.endwin()
        print(f"Error: {FIFO_PATH} not found — is the minecraft service running?")
        return

    curses.curs_set(1)
    stdscr.clear()

    height, width = stdscr.getmaxyx()
    journal_height = int(height * 0.9)
    input_height = height - journal_height

    journal_win = stdscr.subwin(journal_height, width, 0, 0)
    journal_win.scrollok(True)
    input_win = stdscr.subwin(input_height, width, journal_height, 0)

    log_queue = queue.Queue()
    stop_event = threading.Event()
    lock = threading.Lock()

    thread = threading.Thread(target=run_journalctl, args=(log_queue, stop_event), daemon=True)
    thread.start()

    try:
        with open(FIFO_PATH, 'a') as f:
            while True:
                # Drain any pending log lines before blocking on input
                while not log_queue.empty():
                    line = log_queue.get_nowait()
                    with lock:
                        try:
                            journal_win.addstr(line)
                            journal_win.refresh()
                        except curses.error:
                            pass

                input_commands(input_win, f)

    except KeyboardInterrupt:
        stdscr.clear()
        stdscr.refresh()
    finally:
        stop_event.set()

if __name__ == "__main__":
    curses.wrapper(main)
