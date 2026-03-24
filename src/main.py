import sys
import os
from textual.app import App
from textual.widgets import Header, Footer, DataTable, Input, Static
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import AuditApp

def main():
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
    else:
        file_to_open = "data/rancher-api-audit.log"

    if os.path.exists(file_to_open) == False:
        print("========================================")
        print(f"ERROR: File does not exists: {file_to_open}")
        print("Please check if the file is inside the 'data' folder.")
        print("===========================================")
        return

    app = AuditApp(file_to_open)
    app.run()

if __name__ == "__main__":
    main()
