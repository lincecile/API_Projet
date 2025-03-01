import json
import os
import configparser

config = configparser.ConfigParser()
config.read('server/auth/config.ini')

file_path = config['DEFAULT']['file_path']

if not os.path.exists(file_path):
    raise FileNotFoundError('The file does not exist, please create it first using the create_users.py script.')

with open(file_path, 'r') as file:
    users = json.load(file)