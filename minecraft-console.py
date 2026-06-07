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
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    try:
        while not stop_event.is_set():
            line = process.stdout.readline()
            if not line:
                break
            log_queue.put(line.decode(errors='replace'))
    finally:
        process.terminate()

def draw_input(win, command):
    win.erase()
    win.addstr(0, 0, "Enter command (Ctrl-C to exit): ")
    try:
        win.addstr(command)
    except curses.error:
        # Command longer than the input window; ignore the overflow
        pass
    win.noutrefresh()

def main(stdscr):
    if not os.path.exists(FIFO_PATH):
        curses.endwin()
        print(f"Error: {FIFO_PATH} not found — is the minecraft service running?")
        return

    curses.curs_set(1)
    curses.noecho()
    stdscr.clear()

    height, width = stdscr.getmaxyx()
    input_height = 2
    journal_height = max(1, height - input_height)

    journal_win = stdscr.subwin(journal_height, width, 0, 0)
    journal_win.scrollok(True)
    input_win = stdscr.subwin(input_height, width, journal_height, 0)
    input_win.keypad(True)
    # Block on input for at most 100ms so log lines stay live without busy-looping
    input_win.timeout(100)

    log_queue = queue.Queue()
    stop_event = threading.Event()

    thread = threading.Thread(target=run_journalctl, args=(log_queue, stop_event), daemon=True)
    thread.start()

    command = ""
    try:
        with open(FIFO_PATH, 'a') as f:
            draw_input(input_win, command)
            while True:
                # Drain any pending log lines into the journal pane
                drained = False
                while not log_queue.empty():
                    try:
                        journal_win.addstr(log_queue.get_nowait())
                    except curses.error:
                        pass
                    drained = True
                if drained:
                    journal_win.noutrefresh()
                    # Redraw input last so the cursor stays in the input pane
                    draw_input(input_win, command)

                try:
                    ch = input_win.getch()
                except KeyboardInterrupt:
                    break

                if ch == -1:
                    # Timed out waiting for input; just flush any queued redraws
                    pass
                elif ch in (curses.KEY_ENTER, 10, 13):
                    if command:
                        f.write(command + "\n")
                        f.flush()
                        command = ""
                    draw_input(input_win, command)
                elif ch in (curses.KEY_BACKSPACE, 127, 8):
                    command = command[:-1]
                    draw_input(input_win, command)
                elif 0 <= ch < 256:
                    command += chr(ch)
                    draw_input(input_win, command)

                curses.doupdate()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()

if __name__ == "__main__":
    curses.wrapper(main)
