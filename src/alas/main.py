import getpass
import os
import sys
import json
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
# Holy deps bro but its all std lib (most) anyway so who cares
# I probs have too high standards for imports/deps but ehh idk

# Argument parsers set-up
parser = argparse.ArgumentParser(prog="alas", description="A productivity system for minimalists.")
subparsers = parser.add_subparsers(dest="subcommand", help="Specify the subsystem to use", required=False)
notesparser = subparsers.add_parser("notes", help="Relating to the Notes subsystem")
notesparser.add_argument("action", help="Specify the action to do")
notesparser.add_argument("object", nargs="?", help="Specify the object to be acted upon")
notesparser.add_argument("context", nargs="?", help="Specify the context for the action")
vaultssparser = subparsers.add_parser("vaults", help="Relating to the Vaults subsystem")
vaultssparser.add_argument("action", help="Specify the action to do")
vaultssparser.add_argument("object", nargs="?", help="Specify the object to be acted upon")
vaultssparser.add_argument("context", nargs="?", help="Specify the context for the action")

args = parser.parse_args()

home = Path("~/.config/alas").expanduser()
vaults = Path(home / "vaults")

# Check if this is the first run.
def firstrun_check():
    confdir = Path("~/.config/alas").expanduser()
    confdir.mkdir(parents=True, exist_ok=True)
    vaults.mkdir(parents=True, exist_ok=True)
    configfile = confdir / "config.conf"
    configfile.touch(exist_ok=True)
    return not any(vaults.glob("*.vault"))

# Work in progress
def firstrun():
    try:
        print("Hello and welcome to alas! Let's set it up.\n" +
              div() + "\n"
              "[1/3] Vault setup")
        vault = input("Vault name [personal]: ")
        if vault.strip() == "":
            vault = "personal"
        print("[2/3] Vault encryption")
        passwd = getpass.getpass("Encryption password (leave blank to disable; can be changed later): ").strip()
        if passwd == "":
            print("Vault encryption disabled.")
        print("[3/3] Configure alas")
        lr = input("Set the ordering of the Notes column relative to the To-do column [l/R] ").strip().lower()
        quotes = input("Would you like to download quotes at this time? An internet connection is required [Y/n]").strip().lower()
        # Work in progress
        vault_create(vault, passwd)
        print(div() + "\n" +
              "Onboarding is done! Run 'alas' next to get started.")
    except:
        home.rmdir()
        print(div())
        print("Uh oh! It looks like the program crashed. Changes have been reversed.")

def vault_encrypt(name, password):
    if vault_exists(name):
        # Encrypt vault using AESGCM. Scrypt is used here to make brute-forcing take more time.
        if not password: raise ValueError("Password must not be empty")
        # Parameter-setting and preparing to encrypt
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        kdf = Scrypt(salt = salt, length = 32, n = 2**17, r = 8, p = 1)
        key = kdf.derive(password.encode("utf-8"))
        path = Path(vaults) / (name + ".vault")
        try:
            plaintext = path.read_bytes()
        except FileNotFoundError:
            raise FileNotFoundError("File not found")
        # Encryption here
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        output = b"ALAS1" + salt + nonce + ciphertext
        # Write encrypted data separately first, avoiding data loss in the event that the write fails.
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(output)
        temp.replace(path)

def vault_decrypt(name, password):
    if vault_exists(name):
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

def vaults_exists(name):
    name = name.strip()
    if not name or Path(name).name != name or name in {".", ".."}:
        return True
    vaults.mkdir(parents=True, exist_ok=True)
    path = vaults / f"{name}.vault"
    if path.exists():
        return True
    return False

# Vault creation
def vault_create(name, password):
    if not vaults_exists(name):
        now = timestamp = datetime.now().astimezone().isoformat(timespec="seconds").strip()
        # Boilerplate; default contents of all vaults
        boiler = {
            "meta": {
                "name": name,
                "version": "01",
                "created": now,
                "updated": now,
            },
            "notes": {},
            "to-dos": {},
        }
        # Write to vault
        path.write_text(json.dumps(boiler, indent=4, ensure_ascii=False), encoding="utf-8")
        if password:
            try: vault_encrypt(name, password)
            except:
                path.unlink(missing_ok=True)
                raise

# Check if a vault is encrypted. Useful for future features where blindly appending to an encrypted vault could cause bugs, errors, or straight up data loss.
def isencrypted(name):
    with open(vaults / (name + ".vault"), "rb") as file:
        header = file.read(5)
    return header == b"ALAS1"

# Work in progress
def notes_add(target, note):
    if isencrypted(target):
        raise TypeError("This vault is encrypted; run 'alas vaults decrypt <vault> <password>' to decrypt")

# Function to prompt for missing arguments.
def promptmissing(style):
    if style == "vault":
        objstr = "Vault: "
        contstr = "Password: "
        contgp = True
    if args.object is None:
        args.object = input(objstr).strip()
    if args.context is None:
        if contgp:
            args.context = getpass.getpass(contstr).strip()
        else:
            args.context = input(contstr).strip()

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
        if args.subcommand == "notes":
            pass
        if args.subcommand == "vaults":
            if args.action == "encrypt":
                promptmissing("vault")
                vault_encrypt((args.object), str(args.context))
            if args.action == "decrypt":
                promptmissing("vault")
                vault_decrypt((args.object), str(args.context))
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