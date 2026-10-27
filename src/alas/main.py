import getpass
import os
import sys
import argparse
import shutil
import random
from pathlib import Path
from datetime import datetime
import locale

# Set up the argument parser; Work in progress
#parser = argparse.ArgumentParser()
#parser.add_argument("subsystem")
#parser.add_argument("action")
#parser.add_argument("target")

#args = parser.parse_args()

def firstrun_check():
    confdir = Path("~/.config/alas").expanduser()
    if not confdir.exists():
        #confdir.mkdir(parents=True, exist_ok=True)
        return True
    else: return False

# Work in progress
def firstrun():
    print("Hello and welcome to alas! Let's set it up."
          "[1/3] Vault setup")
    vault = input("Vault name [personal]: ")
    print("[2/3] Vault encryption")
    passwd = getpass("Master password (leave blank to disable): ")
    if passwd.strip() == "":
        print("Vault encryption disabled.")
    else:
        print("A duress password is a discreet way of signaling you are being forced to access a system or account. Entering the duress password will permanently wipe the currently selected vault.")
        duressyn = input("Would you like to add a duress password?")
        # Work in progress
    print("[3/3] Configure alas")
    # Work in progress

# Function to print the welcome message.
def welc():
    # This part looks funny because variables have been collapsed
    username = os.environ.get("USER", "unknown")
    columns = shutil.get_terminal_size().columns
    # Format time according to the user's locale configuration
    locale.setlocale(locale.LC_TIME, "")
    timestr = datetime.now().strftime(locale.nl_langinfo(locale.T_FMT)).strip()
    # Pad the welcome message so that it is as wide as the divider (see div())
    padding = max(1, min(48, columns) - len(f"Welcome, {username}") - len(timestr))
    return f"Welcome, {username}" + (" " * padding) + timestr

# Function to print a divider.
def div():
    cols = min(shutil.get_terminal_size().columns, 48)
    return "—" * cols

# Function to get and print a quote.
def quote():
    path = Path("~/.config/alas/quotes.txt").expanduser()
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        return random.choice(lines).rstrip("\n")
    except FileNotFoundError:
        return "Quote could not be loaded at this time."

# Main execution starts here
def main():
    if firstrun_check():
        firstrun()
    else:
        print(welc())
        print(div())
        print(div())
        print(quote())

if __name__ == "__main__":
    main()