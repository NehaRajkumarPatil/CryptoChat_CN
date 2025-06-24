# SERVER CODE (s2_.py)
import socket
import threading
import bcrypt
import json
from pymongo import MongoClient
from datetime import datetime
import time
import ssl  # Add SSL support

HOST= '127.0.0.1'
PORT = 5001

# Create socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

# Wrap socket with SSL/TLS
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
try:
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    server = context.wrap_socket(server, server_side=True)
    print("✅ SSL/TLS encryption enabled")
except FileNotFoundError:
    print("⚠️ SSL certificate files not found. Running without encryption.")
    print("   Generate certificates with: openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
except ssl.SSLError as e:
    print(f"⚠️ SSL configuration error: {e}")
    print("   Running without encryption.")

print(f"✅ Server started on {HOST}:{PORT}")

clients = {}  # {client_socket: username}
file_transfers = {}  # Track ongoing file transfers

# Connect to MongoDB
try:
    client_mongo = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client_mongo.server_info()  # Will raise exception if connection fails
    db = client_mongo['chat_app']
    users_collection = db['users']
    messages_collection = db['messages']
    
    # Create indexes
    messages_collection.create_index([("content", "text")])
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB connection error: {str(e)}")
    exit(1)

def broadcast_users_list():
    """Send the list of online users to all clients"""
    users = list(clients.values())
    users_msg = "USERS_LIST|" + "|".join(users)
    
    for client in clients:
        try:
            client.send(users_msg.encode())
        except:
            client.close()
            remove_client(client)

def broadcast(message, sender_socket=None, recipient="Everyone"):
    """Send a message to all clients or a specific recipient"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sender = clients.get(sender_socket, "SERVER")
    
    # Store message in database
    if sender != "SERVER" and message:
        messages_collection.insert_one({
            "type": "message",
            "sender": sender,
            "recipient": recipient,
            "content": message,
            "timestamp": timestamp
        })
    
    # Format message for sending
    if recipient == "Everyone":
        formatted_msg = f"MSG|{sender}|{recipient}|{message}|{timestamp}"
        print(f"[Broadcast] {sender}: {message}")
        
        for client in clients:
            try:
                client.send(formatted_msg.encode())
            except:
                client.close()
                remove_client(client)
    else:
        # Private message
        formatted_msg = f"PRIVATE|{sender}|{recipient}|{message}|{timestamp}"
        print(f"[Private] {sender} to {recipient}: {message}")
        
        # Find recipient socket
        recipient_socket = None
        for client, username in clients.items():
            if username == recipient:
                recipient_socket = client
                break
        
        if recipient_socket:
            try:
                recipient_socket.send(formatted_msg.encode())
            except:
                recipient_socket.close()
                remove_client(recipient_socket)

def remove_client(client):
    """Remove a client from the clients dictionary"""
    if client in clients:
        username = clients[client]
        del clients[client]
        broadcast(f"{username} left the chat.")
        print(f"❌ {username} disconnected.")
        broadcast_users_list()

def handle_client(client, username):
    """Handle messages from a client"""
    while True:
        try:
            message = client.recv(65536).decode(errors="ignore")
            if not message:
                break
            
            parts = message.split("|")
            msg_type = parts[0]
            
            if msg_type == "TYPING":
                # Format: TYPING|sender|recipient|typing_text
                sender = parts[1]
                recipient = parts[2]
                typing_text = parts[3]
                
                typing_msg = f"TYPING|{sender}|{recipient}|{typing_text}"
                
                if recipient == "Everyone":
                    # Send to everyone except sender
                    for c in clients:
                        if c != client:
                            try:
                                c.send(typing_msg.encode())
                            except:
                                c.close()
                                remove_client(c)
                else:
                    # Send to specific recipient
                    for c, name in clients.items():
                        if name == recipient:
                            try:
                                c.send(typing_msg.encode())
                            except:
                                c.close()
                                remove_client(c)
            
            elif msg_type == "MSG":
                # Format: MSG|sender|recipient|content|timestamp
                sender = parts[1]
                recipient = parts[2]
                content = parts[3]
                timestamp = parts[4] if len(parts) > 4 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                broadcast(content, client, recipient)
            
            elif msg_type == "PRIVATE":
                # Format: PRIVATE|sender|recipient|content|timestamp
                sender = parts[1]
                recipient = parts[2]
                content = parts[3]
                timestamp = parts[4] if len(parts) > 4 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                broadcast(content, client, recipient)
            
            elif msg_type == "FILE_INFO":
                # Format: FILE_INFO|sender|recipient|filename|filesize|timestamp
                sender = parts[1]
                recipient = parts[2]
                filename = parts[3]
                filesize = parts[4]
                timestamp = parts[5]
                
                # Add this line to log file transfers in the server console
                print(f"[File] {sender} is sending {filename} ({int(filesize)//1024}KB) to {recipient}")
                
                # Store file info in database
                messages_collection.insert_one({
                    "type": "file",
                    "sender": sender,
                    "recipient": recipient,
                    "filename": filename,
                    "filesize": filesize,
                    "timestamp": timestamp
                })
                
                # Forward file info to recipient(s)
                if recipient == "Everyone":
                    for c in clients:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
                else:
                    for c, name in clients.items():
                        if name == recipient:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
            
            elif msg_type == "FILE_CHUNK":
                # Forward file chunks to recipient(s)
                sender = parts[1]
                recipient = parts[2]
                
                if recipient == "Everyone":
                    for c in clients:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
                else:
                    for c, name in clients.items():
                        if name == recipient:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
            
            elif msg_type == "FILE_COMPLETE":
                # Forward file chunks to recipient(s)
                sender = parts[1]
                recipient = parts[2]
                filename = parts[3]
                
                # Add this line to log completed file transfers
                print(f"[File] Transfer complete: {filename} from {sender} to {recipient}")
                
                if recipient == "Everyone":
                    for c in clients:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
                else:
                    for c, name in clients.items():
                        if name == recipient:
                            try:
                                c.send(message.encode())
                            except:
                                c.close()
                                remove_client(c)
            
            elif msg_type == "HISTORY_REQUEST":
                # Send message history to client
                history = list(messages_collection.find(
                    {"$or": [
                        {"recipient": "Everyone"},
                        {"recipient": username},
                        {"sender": username}
                    ]}
                ).sort("timestamp", 1).limit(50))
                
                # Convert ObjectId to string for JSON serialization
                for msg in history:
                    msg["_id"] = str(msg["_id"])
                
                history_json = json.dumps(history)
                history_msg = f"HISTORY|{history_json}"
                
                try:
                    client.send(history_msg.encode())
                except:
                    client.close()
                    remove_client(client)
            
            elif msg_type == "SEARCH":
                # Format: SEARCH|search_term
                search_term = parts[1]
                
                # Search messages in database
                results = list(messages_collection.find(
                    {"$text": {"$search": search_term},
                     "$or": [
                         {"recipient": "Everyone"},
                         {"recipient": username},
                         {"sender": username}
                     ]}
                ).sort("timestamp", -1).limit(20))
                
                # Convert ObjectId to string for JSON serialization
                for msg in results:
                    msg["_id"] = str(msg["_id"])
                
                results_json = json.dumps(results)
                results_msg = f"SEARCH_RESULTS|{results_json}"
                
                try:
                    client.send(results_msg.encode())
                except:
                    client.close()
                    remove_client(client)
            
            elif msg_type == "LOGOUT":
                break
            
            else:
                print(f"[Unknown message type] {msg_type}")
        
        except Exception as e:
            print(f"[Error handling client] {str(e)}")
            break
    
    # Client disconnected
    client.close()
    remove_client(client)

def authenticate(client):
    """Authenticate a user"""
    try:
        data = client.recv(1024).decode()
        username, password = data.split("||")
        user = users_collection.find_one({"username": username})

        if user:
            # Check if password matches
            stored_password = user['password']
            # Handle both string and bytes format for stored password
            if isinstance(stored_password, str):
                password_match = bcrypt.checkpw(password.encode(), stored_password.encode())
            else:
                password_match = bcrypt.checkpw(password.encode(), stored_password)
                
            if password_match:
                client.send("LOGIN_SUCCESS".encode())
                return username
            else:
                client.send("LOGIN_FAILED".encode())
                return None
        else:
            # Create new user
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            users_collection.insert_one({
                "username": username, 
                "password": hashed_pw.decode(),
                "created_at": datetime.now()
            })
            client.send("SIGNUP_SUCCESS".encode())
            return username
    except Exception as e:
        print(f"[ERROR] Auth: {str(e)}")
        client.send("ERROR".encode())
        return None

def receive_connections():
    """Accept new client connections"""
    while True:
        client, addr = server.accept()
        print(f"🔌 Connection from {addr}")

        username = authenticate(client)
        if username:
            # Add client to clients dictionary
            clients[client] = username
            
            # Send welcome message
            client.send("WELCOME".encode())
            
            # Broadcast new user joined
            broadcast(f"✅ {username} joined the chat.")
            
            # Update users list for all clients
            broadcast_users_list()
            
            # Start thread to handle client messages
            thread = threading.Thread(target=handle_client, args=(client, username))
            thread.daemon = True
            thread.start()
        else:
            client.close()

if __name__ == "__main__":
    try:
        receive_connections()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {str(e)}")
    finally:
        server.close()
