# Python API - Cryptocurrency Market Data & TWAP Paper Trading API

This project provides a Python API for accessing cryptocurrency market data and implementing a TWAP (Time-Weighted Average Price) paper trading strategy. It is part of our curriculum at University Paris Dauphine-PSL for the first semester of the M272 "Economics and Financial Engineering". 

It aims to teach us the main concepts of APIs and how to use them in Python by providing an environment for cryptocurrency mock-trading, using Binance and Kraken.

## Features

### Server Component
The server component handles the backend logic and data processing. It is located in the [server](server/) directory.

### Client Component
The client component interacts with the server to fetch market data and execute trades. It is located in the [client](client/) directory.

### Graphical User Interface
The GUI provides a user-friendly interface for interacting with the API. It is located in the [gui](gui/) directory.

## Installation

To install the required dependencies, run:
```sh
pip install -r requirements.txt
```
Then : 
```sh
pip install -e .
```
## Usage

### Server startup

To use this tool, you first have to start the server :
```sh
python ./server/main.py
```

Alternativaly you can use :
```sh
uvicorn server.main:app
```

### Client

The client component is designed to interact with the server to fetch market data and execute trades. Below are several examples of how to use the client.

In the directory named [Exemple](client/exemple/), several examples demonstrate how to use the client to log in, fetch supported exchanges, get trading pairs, retrieve klines, connect to WebSocket, subscribe to real-time data, create a TWAP order, and track the order status.

### Authentication feature

Default username and passwords are set to "Tristan".
If you wish to modify/add credentials, please look at [this script](server/auth/manage_users.py) and run : 
```sh
python ./server/auth/manage_users.py
```


### GUI

We have extended this project by creating a simple [GUI](gui/API_interface.py), allowing the user to test the client implementation.

To open it, please run the following command : 
```sh
python ./gui/API_interface.py
```

## API Documentation

To access the Swagger API documentation, please open [this link](http://localhost:8000/docs#/).