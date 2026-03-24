# Rancher & RKE2 Audit Log Beautifier / Parser

- A simple Terminal User Interface (TUI) tool that makes **Rancher** and **RKE2 (WIP)** audit logs easier to read and analyze.

- Raw audit logs are typically long, unformatted JSON lines that are difficult to inspect manually. This tool transforms them into a clean, searchable table and provides formatted JSON views for deeper inspection.

---

##  Features :

* **Table View:** It takes the JSON and shows the important data (Time, User, Code, URI) in columns.

* **Color Highlights:** Successful HTTP status code(200) are green and errors (4xx/5xx) are red, so you can spot problems quickly.

* **Search:** Filter logs instantly by Username, HTTP status code, URL / URI, timestamp

* **Detailed JSON View:** Select any log entry and press **Enter** to see the fully formatted JSON payload for detailed inspection.

---

## Overview : 

### 1. Filter/search for log :

 > Example: Filter logs with 500 status code : 


<img width="1295" height="438" alt="image" src="https://github.com/user-attachments/assets/16977a4a-51e1-4d89-b81a-75ee16b707a9" />

### 2. View complete JSON : 

 > Note: Select auditlog entry and press 'enter' or 'double click' to get the full JSON.

<img width="1101" height="249" alt="image" src="https://github.com/user-attachments/assets/218aed31-f565-4390-859a-cc10caeaee3d" />

### 3. Using palette option to change the theme and capture screenshot : 

<img width="1030" height="350" alt="image" src="https://github.com/user-attachments/assets/6125c20f-f205-4ab2-bb06-f6cf2cf2fa68" />

##  Getting Started :

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/pdegave-suse/log_beautifier.git
```

### 2️⃣ Navigate to the Project Directory

```bash
cd log_beautifier
```

### 3️⃣ Make the Script Executable

```bash
chmod +x run.sh
```

### 4️⃣ Run the Tool

```bash
./run.sh <audit-file-name>
```

The script will automatically:
- Set up the Python virtual environment
- Install required dependencies (`textual` and `rich`)

---

## Using a Custom Log File : 

To analyze a specific audit log file:

```bash
./run.sh path/to/your/file.log
```

 >> Note : Sample **rancher-api-audit.log** file is available in project `data' directory and currently the 'rancher-api-audit.log path is hardcoded in main.py. 
 
---

##  keyboard controls : 

| Key | Action |
|-----|--------|
| **Tab** | Switch between search bar and log list |
| **Enter** | View full log details |
| **Esc** | Close detail window |
| **C** | Clear search filter |
| **Q** | Quit the application |

---

## Requirements : 

- Linux / macOS / Windows(Testing in progress)
- Python 3.9+ (recommended)

---

##  Current Status : 

- Rancher Audit Logs:  Supported  
- RKE2 Audit Logs: Supported  

## Improvement(WIP) : 

- Sort the list with max hit count/Duration (eg: summary)
- Audit to CSV
- Load/stress testing
