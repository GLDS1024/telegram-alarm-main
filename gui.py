import os
import sys
import configparser
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk, messagebox

import monitor


def get_project_path():
    if getattr(sys, 'frozen', False):
        # 打包后
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def run_gui():
    path = get_project_path()
    file = os.path.join(path, 'config.ini')

    con = configparser.ConfigParser()
    if not os.path.exists(file):
        messagebox.showerror('Error', f'config.ini not found at {file}')
        return
    con.read(file, encoding='utf-8')

    if 'app' not in con.sections():
        messagebox.showerror('Error', 'Section [app] missing in config.ini')
        return

    root = tk.Tk()
    root.title('설정')

    frame = ttk.Frame(root, padding=12)
    frame.grid(row=0, column=0, sticky='nsew')

    entries = {}

    items = dict(con.items('app'))

    row = 0
    for key, val in items.items():
        lbl = ttk.Label(frame, text=key)
        lbl.grid(row=row, column=0, sticky='w', padx=(0,8), pady=6)
        ent = ttk.Entry(frame)
        ent.insert(0, val)
        ent.grid(row=row, column=1, sticky='ew', pady=6)
        entries[key] = ent
        row += 1

    frame.columnconfigure(1, weight=1)

    def save_and_close():
        for k, ent in entries.items():
            con.set('app', k, ent.get())
        try:
            with open(file, 'w', encoding='utf-8') as f:
                con.write(f)
            messagebox.showinfo('성공', '설정 저장됨')
            root.destroy()
        except Exception as e:
            messagebox.showerror('저장 실패', str(e))

    def save_keep():
        for k, ent in entries.items():
            con.set('app', k, ent.get())
        try:
            with open(file, 'w', encoding='utf-8') as f:
                con.write(f)
            messagebox.showinfo('성공', '설정 저장됨')
        except Exception as e:
            messagebox.showerror('저장 실패', str(e))

    btn_frame = ttk.Frame(root, padding=(12,8))
    btn_frame.grid(row=1, column=0, sticky='ew')
    btn_frame.columnconfigure((0,1,2), weight=1)


    # start/stop controls and status
    monitor_thread = None
    stop_event = None

    ctrl_frame = ttk.Frame(root, padding=(12,8))
    ctrl_frame.grid(row=2, column=0, sticky='ew')
    ctrl_frame.columnconfigure((0,1,2), weight=1)

    status_var = tk.StringVar(value='Ready')
    status_lbl = ttk.Label(ctrl_frame, textvariable=status_var)
    status_lbl.grid(row=0, column=0, sticky='w')

    def append_log(msg):
        def _append():
            try:
                log.configure(state='normal')
                log.insert('end', msg + '\n')
                log.see('end')
                # keep log size reasonable
                lines = int(log.index('end-1c').split('.')[0])
                if lines > 2000:
                    log.delete('1.0', f'{lines-1000}.0')
                log.configure(state='disabled')
            except Exception:
                pass
        try:
            root.after(0, _append)
        except Exception:
            _append()

    def set_status(msg):
        try:
            status_var.set(msg)
        except Exception:
            pass
        append_log(msg)

    def _disable_entries():
        for e in entries.values():
            e.config(state='disabled')

    def _enable_entries():
        for e in entries.values():
            e.config(state='normal')

    def start_monitor():
        nonlocal monitor_thread, stop_event
        if monitor_thread and monitor_thread.is_alive():
            messagebox.showinfo('Info', 'Monitor already running')
            return
        save_keep()
        stop_event = threading.Event()
        monitor_thread = threading.Thread(target=monitor.run_monitor, args=(path, stop_event, set_status), daemon=True)
        _disable_entries()
        monitor_thread.start()
        set_status('Running')

    def stop_monitor():
        nonlocal monitor_thread, stop_event
        if not monitor_thread:
            return
        stop_event.set()
        monitor_thread.join(timeout=5)
        monitor_thread = None
        stop_event = None
        _enable_entries()
        set_status('Stopped')

    start_btn = ttk.Button(ctrl_frame, text='시작', command=start_monitor)
    start_btn.grid(row=0, column=1, sticky='ew', padx=4)
    stop_btn = ttk.Button(ctrl_frame, text='중지', command=stop_monitor)
    stop_btn.grid(row=0, column=2, sticky='ew', padx=4)

    


   
   

    # log window
    log_frame = ttk.Frame(root, padding=(12,8))
    log_frame.grid(row=4, column=0, sticky='nsew')
    root.rowconfigure(4, weight=1)
    log = scrolledtext.ScrolledText(log_frame, wrap='word', height=12, state='disabled')
    log.pack(fill='both', expand=True)

    # compute a reasonable window size based on number of fields
    try:
        height = max(480, 40 * (row + 3))
        width = 600
        root.resizable(False, False)
        root.geometry(f'{width}x{height}')
    except Exception:
        root.minsize(600, 480)
    root.mainloop()
