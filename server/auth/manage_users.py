import json
import os
import configparser
from werkzeug.security import generate_password_hash

config = configparser.ConfigParser()
config.read('server/auth/config.ini')

file_path = config['DEFAULT']['file_path']

def load_users():
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as file:
        return json.load(file)

def save_users(users):
    with open(file_path, 'w') as file:
        json.dump(users, file, indent=4)

def add_user(username, password):
    users = load_users()
    if username in users:
        print(f"User '{username}' already exists.")
        return
    users[username] = generate_password_hash(password)
    save_users(users)
    print(f"User '{username}' added successfully.")

def modify_user(username, password):
    users = load_users()
    if username not in users:
        print(f"User '{username}' does not exist.")
        return
    users[username] = generate_password_hash(password)
    save_users(users)
    print(f"User '{username}' modified successfully.")

def delete_user(username):
    users = load_users()
    if username not in users:
        print(f"User '{username}' does not exist.")
        return
    del users[username]
    save_users(users)
    print(f"User '{username}' deleted successfully.")

def main():
    while True:
        print("1. Add User")
        print("2. Modify User")
        print("3. Delete User")
        print("4. Exit")
        choice = input("Enter your choice: ")
        if choice == '1':
            username = input("Enter username: ")
            password = input("Enter password: ")
            add_user(username, password)
        elif choice == '2':
            username = input("Enter username: ")
            password = input("Enter new password: ")
            modify_user(username, password)
        elif choice == '3':
            username = input("Enter username: ")
            delete_user(username)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

