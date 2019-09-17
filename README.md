# SPARTAN MESSENGERS 

### The repository is recently made public. 

### Features
1. End-to-End Encryption on the client side.
2. LRU cache per user to store recent messages.
3. Rate limiting.

## The repository contains following files
1. server.py (To implement the one to one chat feature uncomment the single chat application code in server.py)
2. client.py
3. config.proto
4. config.yaml
5. config_pb2.py
6. config_pb2_grpc.py

### On compiling the config.proto file additional 2 files are generated. You need to import these 2 files in client.py and server.py
The generated files are also added to the repository. 

### config.yaml contains the data which is loaded in the application.

### A dependencies.txt file provides the list of dependencies you need to import.
