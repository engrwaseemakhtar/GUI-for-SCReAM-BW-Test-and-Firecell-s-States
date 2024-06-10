import tkinter as tk
import subprocess
import signal
import os
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import time
import csv
from datetime import datetime

# Global variables
process = None
stop_thread = False
data_lock = threading.Lock()
data_dict = {
    "Queue Delay": [],
    "RTT": [],
    "Transmit Rate": [],
    "Packet Loss Rate": []
}
max_data_points = 10000

def execute_command(receiver_ip, port, options):
    global process, stop_thread
    stop_thread = False

    # Adjust command based on options
    cmd = ["./scream-master/bin/scream_bw_test_tx"] + options + [receiver_ip, port]

    # If logging option is selected, append filename to options and redirect stdout to file
    log_filename = "MWA_Demo1.csv"
    if "-log" in options:
        cmd += [log_filename]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    else:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    threading.Thread(target=read_process_output, args=(process, log_filename, "-log" in options)).start()

def read_process_output(process, log_filename, is_logging):
    global stop_thread
    try:
        if is_logging:
            while not stop_thread:
                time.sleep(1)
                read_log_file(log_filename)
        else:
            if process.stdout:
                for line in process.stdout:
                    if stop_thread:
                        break
                    parse_output(line.strip())
    except Exception as e:
        print(f"Error reading process output: {e}")
    finally:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

def read_log_file(filename):
    with data_lock:
        try:
            if not os.path.exists(filename):
                print(f"Log file {filename} does not exist yet.")
                return

            with open(filename, 'r') as csvfile:
                csvreader = csv.reader(csvfile)
                headers = next(csvreader)
                for row in csvreader:
                    if len(row) < len(headers):
                        continue
                    append_data("Queue Delay", float(row[1]))  # Adjust index as per the actual log file format
                    append_data("RTT", float(row[2]))  # Adjust index as per the actual log file format
                    append_data("Transmit Rate", float(row[3]))  # Adjust index as per the actual log file format
                    append_data("Packet Loss Rate", float(row[11]))  # Adjust index as per the actual log file format
        except Exception as e:
            print(f"Error reading log file: {e}")

def append_data(key, value):
    if len(data_dict[key]) >= max_data_points:
        data_dict[key].pop(0)
    data_dict[key].append(value)

def parse_output(output):
    with data_lock:
        # Example parsing logic: Adjust according to your actual output format
        if "Estimated queue delay [s]" in output:
            append_data("Queue Delay", float(output.split(":")[1].strip()))
        elif "RTT [s]" in output:
            append_data("RTT", float(output.split(":")[1].strip()))
        elif "Total transmit bitrate [bps]" in output:
            append_data("Transmit Rate", float(output.split(":")[1].strip()))
        elif "Packet loss" in output:
            append_data("Packet Loss Rate", float(output.split(":")[1].strip()))

def start_script():
    global process, data_dict
    receiver_ip = ip_entry.get()
    port = port_entry.get()
    command_option = command_var.get()

    if command_option not in command_options:
        print("Invalid command option")
        return

    # Clear previous data
    with data_lock:
        for key in data_dict:
            data_dict[key].clear()

    # Execute the corresponding function based on the command option
    options = command_options[command_option]
    execute_command(receiver_ip, port, options)

def stop_script():
    global process, stop_thread
    if process:
        stop_thread = True
        process.terminate()
        process = None
        print("Script stopped")

def terminate_script():
    global process, stop_thread
    if process:
        stop_thread = True
        process.send_signal(signal.SIGINT)
        os._exit(0)
        print("Script terminated")

def update_graphs(i):
    with data_lock:
        for ax in axes:
            ax.clear()

        # Plot data on respective subplots
        axes[0].plot(data_dict["Queue Delay"], label="Queue Delay")
        axes[0].set_title("Queue Delay")
        axes[0].set_xlabel("Time")
        axes[0].set_ylabel("Seconds")
        axes[0].legend()

        axes[1].plot(data_dict["RTT"], label="RTT")
        axes[1].set_title("RTT")
        axes[1].set_xlabel("Time")
        axes[1].set_ylabel("Seconds")
        axes[1].legend()

        axes[2].plot(data_dict["Transmit Rate"], label="Transmit Rate")
        axes[2].set_title("Transmit Rate")
        axes[2].set_xlabel("Time")
        axes[2].set_ylabel("Bits per second")
        axes[2].legend()

        axes[3].plot(data_dict["Packet Loss Rate"], label="Packet Loss Rate")
        axes[3].set_title("Packet Loss Rate")
        axes[3].set_xlabel("Time")
        axes[3].set_ylabel("Rate")
        axes[3].legend()

def main():
    global ip_entry, port_entry, command_var, axes

    root = tk.Tk()
    root.title("Script Runner")

    # Frame for IP address input
    ip_frame = tk.Frame(root)
    ip_frame.pack(pady=10)
    tk.Label(ip_frame, text="Receiver IP Address:").pack(side=tk.LEFT)
    ip_entry = tk.Entry(ip_frame)
    ip_entry.pack(side=tk.LEFT)

    # Frame for Port number input
    port_frame = tk.Frame(root)
    port_frame.pack(pady=10)
    tk.Label(port_frame, text="Port Number:").pack(side=tk.LEFT)
    port_entry = tk.Entry(port_frame)
    port_entry.pack(side=tk.LEFT)

    # Frame for Command option input
    command_frame = tk.Frame(root)
    command_frame.pack(pady=10)
    tk.Label(command_frame, text="Command Option:").pack(side=tk.LEFT)
    command_var = tk.StringVar()
    command_menu = tk.OptionMenu(command_frame, command_var, *command_options.keys())
    command_menu.pack(side=tk.LEFT)

    # Frame for start button
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)
    start_button = tk.Button(button_frame, text="Start Script", command=start_script)
    start_button.pack(side=tk.LEFT, padx=10)

    # Frame for stop button
    stop_button = tk.Button(button_frame, text="Stop Script", command=stop_script)
    stop_button.pack(side=tk.LEFT, padx=10)

    # Frame for terminate button
    terminate_button = tk.Button(button_frame, text="Terminate", command=terminate_script)
    terminate_button.pack(side=tk.LEFT, padx=10)

    # Create matplotlib figure and axes
    fig, axes = plt.subplots(4, 1, figsize=(10, 20))
    fig.subplots_adjust(hspace=0.9)  # Adjust the space between the subplots
    axes = axes.flatten()

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()

    ani = animation.FuncAnimation(fig, update_graphs, interval=1000)

    root.mainloop()

# Mapping command options to corresponding options
command_options = {
    "-verbose": ["-verbose"],
    "-log": ["-log", "MWA_Demo1.csv", "-itemlist"],
    "-key": ["-key", "2", "10", "MWA_Demo1.csv", "-itemlist"],
    "-minrate": ["-minrate", "2000", "MWA_Demo1.csv", "-itemlist"],
    "-maxrate": ["-maxrate", "20000", "MWA_Demo1.csv", "-itemlist"],
    "-delaytarget": ["-delaytarget", "0.05", "MWA_Demo1.csv", "-itemlist"]
}

if __name__ == "__main__":
    main()

