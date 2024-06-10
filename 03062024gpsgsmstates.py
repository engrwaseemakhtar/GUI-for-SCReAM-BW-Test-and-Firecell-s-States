import tkinter as tk
from tkinter import ttk
import paramiko
import time
import csv
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# Global variables
stop_thread = False
data_lock = threading.Lock()

def ssh_command(host, port, username, password, csv_filename, data_dict):
    global stop_thread
    try:
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username, password=password)
        channel = client.invoke_shell()

        # Wait for the prompt indicating readiness for commands
        while True:
            output = channel.recv(65535).decode('utf-8').strip()
            if output.endswith('#'):
                break

        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['TIME_STAMP', 'LATITUDE', 'LONGITUDE', 'ACCURACY', 'TX', 'RX', 'RSSI', 'RSRP', 'SINR', 'RSRQ'])
            while not stop_thread:
                channel.send('gpsctl -t -i -x -u; gsmctl -e eth0 -r eth0 -q\n')
                #time.sleep(0.003)
                output_all = channel.recv(65535).decode('utf-8').strip()
                parsed_data_all = parse_output_gpsctl_t(output_all)

                if parsed_data_all and "root@RUTX50" not in parsed_data_all.values():
                    writer.writerow([
                        parsed_data_all.get('TIME_STAMP', ''), parsed_data_all.get('LATITUDE', ''), parsed_data_all.get('LONGITUDE', ''),
                        parsed_data_all.get('ACCURACY', ''), parsed_data_all.get('TX', ''), parsed_data_all.get('RX', ''),
                        parsed_data_all.get('RSSI', ''), parsed_data_all.get('RSRP', ''), parsed_data_all.get('SINR', ''), parsed_data_all.get('RSRQ', '')
                    ])
                    csvfile.flush()

                    with data_lock:
                        for key in ['RSSI', 'RSRP', 'SINR', 'RSRQ', 'TX', 'RX']:
                            if key in parsed_data_all:
                                try:
                                    data_dict[key].append(float(parsed_data_all[key]))
                                except ValueError:
                                    data_dict[key].append(None)
                            else:
                                data_dict[key].append(None)

                    # After updating data_dict, trigger immediate update of graphs
                    update_graphs()

    except Exception as e:
        print(f"Error: {e}")

def parse_output_gpsctl_t(output_all):
    parsed_data = {}
    lines = output_all.split('\n')

    if len(lines) >= 7:
        parsed_data["TIME_STAMP"] = lines[1].strip()
        parsed_data["LATITUDE"] = lines[2].strip()
        parsed_data["LONGITUDE"] = lines[3].strip()
        parsed_data["ACCURACY"] = lines[4].strip()
        parsed_data["TX"] = lines[5].strip()
        parsed_data["RX"] = lines[6].strip()
    else:
        return None

    for line in lines:
        if line.startswith("RSSI:") or line.startswith("RSRP:") or line.startswith("SINR:") or line.startswith("RSRQ:"):
            key, value = line.strip().split(": ", 1)
            parsed_data[key.strip()] = value.strip()
    return parsed_data

def start_ssh_command():
    global stop_thread
    stop_thread = False
    #csv_filename = csv_filename_entry.get().strip()  # Ensure to strip any whitespace
    csv_filename = f"PHY_TEST_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

    if not csv_filename:
        print("CSV Filename is empty. Please enter a valid filename.")
        return

    thread = threading.Thread(target=ssh_command, args=(host, port, username, password, csv_filename, data_dict))
    thread.start()

def stop_ssh_command():
    global stop_thread
    stop_thread = True

def terminate_application(root):
    global stop_thread
    stop_thread = True
    root.destroy()

def update_graphs():
    with data_lock:
        for ax in axes:
            ax.clear()

        # Plot RSSI, RSRP, and RSRQ on the same subplot
        axes[0].plot(data_dict['RSSI'], label='RSSI')
        axes[0].plot(data_dict['RSRP'], label='RSRP')
        axes[0].plot(data_dict['RSRQ'], label='RSRQ')
        axes[0].set_title('RSSI, RSRP, RSRQ')
        axes[0].set_xlabel('Time')
        axes[0].set_ylabel('Values')
        axes[0].legend()

        # Plot SINR on a separate subplot
        axes[1].plot(data_dict['SINR'], label='SINR')
        axes[1].set_title('SINR')
        axes[1].set_xlabel('Time')
        axes[1].set_ylabel('SINR')
        axes[1].legend()

        # Plot TX on a separate subplot
        axes[2].plot(data_dict['TX'], label='TX')
        axes[2].set_title('TX')
        axes[2].set_xlabel('Time')
        axes[2].set_ylabel('TX')
        axes[2].legend()

        # Plot RX on a separate subplot
        axes[3].plot(data_dict['RX'], label='RX')
        axes[3].set_title('RX')
        axes[3].set_xlabel('Time')
        axes[3].set_ylabel('RX')
        axes[3].legend()

        # Refresh canvas
        canvas.draw()

def main():
    global host, port, username, password, csv_filename_entry, data_dict, axes, canvas

    data_dict = {'RSSI': [], 'RSRP': [], 'SINR': [], 'RSRQ': [], 'TX': [], 'RX': []}
#
    #root = tk.Tk()
    #root.title("SSH Command Runner")
    
    # Tkinter GUI setup
    root = tk.Tk()
    root.title("OAI-GUI-BY-WASEEM")

    # Top frame for the CSN title
    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X)

    # Add the CSN title label
    title_label = tk.Label(top_frame, text="OAI Research & Development \n Communication Systems and Networks (CSN) \n Mid Sweden University (MIUN)", font=("Helvetica", 20))
    title_label.pack()

    # Main notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    host = '192.168.1.1'
    port = 22
    username = 'root'
    password = 'Firecell123456'

    csv_filename_frame = tk.Frame(root)
    csv_filename_frame.pack(pady=5)
    tk.Label(csv_filename_frame, text="CSV Filename:").pack(side=tk.LEFT)
    csv_filename_entry = tk.Entry(csv_filename_frame)
    csv_filename_entry.pack(side=tk.LEFT)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)
    start_button = tk.Button(button_frame, text="Start", command=start_ssh_command)
    start_button.pack(side=tk.LEFT, padx=10)
    stop_button = tk.Button(button_frame, text="Stop", command=stop_ssh_command)
    stop_button.pack(side=tk.LEFT, padx=10)
    terminate_button = tk.Button(button_frame, text="Terminate", command=lambda: terminate_application(root))
    terminate_button.pack(side=tk.LEFT, padx=10)

    fig, axes = plt.subplots(4, 1, figsize=(10, 20))  # Create a 4x1 grid of subplots
    fig.subplots_adjust(hspace=0.5)  # Adjust space between subplots
    axes = axes.flatten()

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()

    # Start initial SSH command execution
    #start_ssh_command()

    root.mainloop()

if __name__ == "__main__":
    main()

