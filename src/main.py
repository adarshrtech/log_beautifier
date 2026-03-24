import sys
import os

# Setup path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from app import AuditApp
except ImportError:
    from src.app import AuditApp

def show_help():
    """Displays usage instructions for the tool."""
    print("""
Rancher & RKE2 Audit Log Navigator
----------------------------------
Usage:
  ./run.sh <path_to_audit_log>

Options:
  -h, --help    Show this help message and exit

Examples:
  ./run.sh data/rancher-api-audit.log
  ./run.sh /var/log/rke2/audit.log
    """)

def main():
    # 1. Check if user asked for help or provided no arguments
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        show_help()
        return

    # 2. Get the file path from the first argument
    file_to_open = sys.argv[1]

    # 3. Validate that the file actually exists
    if not os.path.exists(file_to_open):
        print("=" * 50)
        print(f"ERROR: File does not exist: {file_to_open}")
        print("Please provide a valid path to a Rancher or RKE2 audit log.")
        print("=" * 50)
        return

    # 4. Run the app
    try:
        app = AuditApp(file_to_open)
        app.run()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
