import getpass
import os
import sys
import argparse
import shutil
import random
import secrets
import locale
from pathlib import Path
from datetime import datetime
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Set up the argument parser; Work in progress
# Kinda fucked up ts part lwk
#parser = argparse.ArgumentParser(
    #prog = "alas",
    #description = "A productivity system for minimalists."
#)
#parser.add_argument("object")
#parser.add_argument("target")
#subparsers = parser.add_subparsers(dest="subcommand, "help="Specify the subsystem to use", required=False)
#notesparser = subparsers.add_argument("notes", help=" Relating to the Notes subsystem")
#notesparser.add_argument("action" help="Specify the action to do")
#notesparser.add_argument("object" help="Specify the object to be acted upon")

#args = parser.parse_args()

def firstrun_check():
    confdir = Path("~/.config/alas").expanduser()
    if not confdir.is_dir():
        confdir.mkdir(parents=True, exist_ok=True)
        global home, vaults
        home = Path("~/.config/alas").expanduser()
        vaults = Path(home / "vaults")
        vaults.mkdir()
        with open(home / "config.conf", "w") as file:
            file.write("INITIAL CONFIGURATION HERE; WORK IN PROGRESS / TO BE DECIDED")
        return True
    else: return False

# Work in progress
def firstrun():
    print("Hello and welcome to alas! Let's set it up.\n" +
          div() + "\n"
          "[1/3] Vault setup")
    vault = input("Vault name [personal]: ")
    if vault.strip() == "":
        vault = "personal"
    print("[2/3] Vault encryption")
    passwd = getpass.getpass("Master password (leave blank to disable): ").strip()
    if passwd == "":
        print("Vault encryption disabled.")
    print("[3/3] Configure alas")
    lr = input("Set the ordering of the Notes column relative to the To-do column [l/R] ").strip().lower()
    # Work in progress
    vault_create(vault, passwd)
    print(div() + "\n" +
          "Onboarding is done! Run 'alas' next to get started.")

def vault_encrypt(name, password):
    # Encrypt vault using AESGCM. Scrypt is used here to make brute-forcing take more time.
    if not password: raise ValueError("Password must not be empty")
    # Parameter-setting and preparing to encrypt
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    kdf = Scrypt(salt = salt, length = 32, n = 2**17, r = 8, p = 1)
    key = kdf.derive(password.encode("utf-8"))
    try:
        path = Path(vaults) / (name + ".vault")
    except FileNotFoundError:
        raise FileNotFoundError("File not found")
    plaintext = path.read_bytes()
    # Encryption here
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    output = b"ALAS1" + salt + nonce + ciphertext
    # Write encrypted data separately first, avoiding data loss in the event that the write fails.
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(output)
    temp.replace(path)

def vault_decrypt(name, password):
    # Matching decryption function for encryption function above.
    if not password: raise ValueError("Password must not be empty")
    path = Path(vaults) / (name + ".vault")
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise FileNotFoundError("File not found")
    # Validate provided vault by checking the magic header. Side note, why *magic* header? Sounds silly.
    if len(data) < 49 or data[:5] != b"ALAS1":
        raise ValueError("Invalid or corrupted vault file")
    # Recover salt, nonce, and ciphertext
    salt = data[5:21]
    nonce = data[21:33]
    ciphertext = data[33:]
    # Derive same 256-bit key used during encryption.
    kdf = Scrypt(salt = salt, length = 32, n = 2**17, r = 8, p = 1)
    key = kdf.derive(password.encode("utf-8"))
    # Decrypt and authenticate. Invalid passwords or tampering raise cryptography.exceptions.InvalidTag.
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    # As always, write decrypted data separately before overwriting vault to avoid data loss.
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(plaintext)
    temp.replace(path)

def vault_create(name, password):
    home = Path("~/.config/alas").expanduser()
    vaults = Path(home / "vaults")
    with open(vaults / (name + ".vault"), "w") as file:
        file.write(datetime.now().strftime(locale.nl_langinfo(locale.D_T_FMT)).strip())
    try:
        vault_encrypt(name, password)
    except ValueError:
        # For future expansion
        pass

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
        # This is what 'alas list' does.
        print(welc())
        print(div())
        # Print available vaults here
        print(div())
        # Print notes and to-dos in dual-column. Left-right order configurable.
        print(quote())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + div())
        print("See you again!")
        sys.exit(0)