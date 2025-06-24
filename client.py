# CLIENT CODE (c2_.py)
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog, ttk
import bcrypt
import base64
import os
from pymongo import MongoClient
import json
from datetime import datetime
import time
import ssl  # Add SSL support

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Chat Room")
        self.root.configure(bg="#F0F0F0")
        self.typing = False
        self.dark_mode = False
        self.online_users = []
        self.current_recipient = "Everyone"
        
        # Configure styles
        self.configure_styles()
        
        # Try to connect to MongoDB
        try:
            self.client_mongo = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            self.client_mongo.server_info()  # Will raise exception if connection fails
            self.db = self.client_mongo["chat_app"]
            self.users_collection = self.db["users"]
            self.messages_collection = self.db["messages"]
        except Exception as e:
            messagebox.showerror("Database Error", f"Cannot connect to MongoDB: {str(e)}")
            self.root.quit()
            return

        if not self.authenticate_user():
            self.root.quit()
            return

        self.setup_gui()
        self.connect_to_server()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def configure_styles(self):
        self.light_theme = {
            "bg": "#F0F0F0",
            "fg": "#000000",
            "button_bg": "#007BFF",
            "button_fg": "white",
            "entry_bg": "white",
            "chat_bg": "white",
            "accent": "#FFD700"
        }
        
        self.dark_theme = {
            "bg": "#2D2D2D",
            "fg": "#FFFFFF",
            "button_bg": "#0056b3",
            "button_fg": "white",
            "entry_bg": "#3D3D3D",
            "chat_bg": "#3D3D3D",
            "accent": "#FFA500"
        }
        
        self.current_theme = self.light_theme

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.current_theme = self.dark_theme if self.dark_mode else self.light_theme
        
        # Update UI elements with new theme
        self.root.configure(bg=self.current_theme["bg"])
        self.chat_area.config(bg=self.current_theme["chat_bg"], fg=self.current_theme["fg"])
        self.msg_entry.config(bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"])
        self.typing_label.config(bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        self.send_btn.config(bg=self.current_theme["button_bg"], fg=self.current_theme["button_fg"])
        self.emoji_btn.config(bg=self.current_theme["accent"])
        self.file_btn.config(bg=self.current_theme["accent"])
        self.theme_btn.config(text="🌙" if not self.dark_mode else "☀️")
        self.users_list.config(bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"])
        self.search_entry.config(bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"])

    def authenticate_user(self):
        auth_window = tk.Toplevel(self.root)
        auth_window.title("Authentication")
        auth_window.geometry("400x250")  # Increased from the original size
        auth_window.configure(bg="#F0F0F0")
        auth_window.transient(self.root)
        auth_window.grab_set()
        
        # Center the window
        auth_window.update_idletasks()
        width = auth_window.winfo_width()
        height = auth_window.winfo_height()
        x = (auth_window.winfo_screenwidth() // 2) - (width // 2)
        y = (auth_window.winfo_screenheight() // 2) - (height // 2)
        auth_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create a frame to hold the form elements with proper padding
        form_frame = tk.Frame(auth_window, bg="#F0F0F0", padx=30, pady=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(form_frame, text="Username:", bg="#F0F0F0", font=("Arial", 12)).pack(anchor="w", pady=(10, 5))
        username_entry = tk.Entry(form_frame, width=30, font=("Arial", 12))
        username_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(form_frame, text="Password:", bg="#F0F0F0", font=("Arial", 12)).pack(anchor="w", pady=5)
        password_entry = tk.Entry(form_frame, width=30, show="*", font=("Arial", 12))
        password_entry.pack(fill=tk.X, pady=5)
        
        self.auth_result = False
        self.username = ""
        self.password = ""
        
        def on_login():
            self.username = username_entry.get().strip()
            self.password = password_entry.get().strip()
            
            if not self.username or not self.password:
                messagebox.showerror("Error", "Username and password cannot be empty!", parent=auth_window)
                return
            
            self.auth_result = True
            auth_window.destroy()
        
        def on_cancel():
            auth_window.destroy()
        
        button_frame = tk.Frame(form_frame, bg="#F0F0F0")
        button_frame.pack(pady=15)
        
        login_btn = tk.Button(button_frame, text="Login/Signup", command=on_login, 
                         bg="#007BFF", fg="white", font=("Arial", 11), padx=10, pady=5)
        login_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, 
                          bg="#DC3545", fg="white", font=("Arial", 11), padx=10, pady=5)
        cancel_btn.pack(side=tk.LEFT)
        
        # Set focus to username entry
        username_entry.focus_set()
        
        # Wait for the window to be destroyed
        self.root.wait_window(auth_window)
        return self.auth_result

    def setup_gui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg=self.current_theme["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for chat
        left_panel = tk.Frame(main_frame, bg=self.current_theme["bg"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right panel for users list
        right_panel = tk.Frame(main_frame, bg=self.current_theme["bg"], width=150)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Chat area
        self.chat_area = scrolledtext.ScrolledText(
            left_panel, wrap=tk.WORD, width=50, height=20, 
            font=("Arial", 12), bg=self.current_theme["chat_bg"], fg=self.current_theme["fg"]
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_area.config(state=tk.DISABLED)
        
        # Typing indicator
        self.typing_label = tk.Label(
            left_panel, text="", fg="gray", bg=self.current_theme["bg"], 
            font=("Arial", 10), anchor="w"
        )
        self.typing_label.pack(fill=tk.X, pady=(0, 5))
        
        # Search bar
        search_frame = tk.Frame(left_panel, bg=self.current_theme["bg"])
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.search_entry = tk.Entry(
            search_frame, width=30, font=("Arial", 10),
            bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"]
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.insert(0, "Search messages...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "Search messages..." else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "Search messages...") if not self.search_entry.get() else None)
        self.search_entry.bind("<Return>", self.search_messages)
        
        search_btn = tk.Button(
            search_frame, text="🔍", command=self.search_messages,
            bg=self.current_theme["button_bg"], fg=self.current_theme["button_fg"]
        )
        search_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Message entry and buttons
        input_frame = tk.Frame(left_panel, bg=self.current_theme["bg"])
        input_frame.pack(fill=tk.X)
        
        self.msg_entry = tk.Entry(
            input_frame, width=40, font=("Arial", 12),
            bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"]
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.msg_entry.bind("<Return>", self.send_message)
        self.msg_entry.bind("<Key>", self.send_typing_status)
        
        button_frame = tk.Frame(input_frame, bg=self.current_theme["bg"])
        button_frame.pack(side=tk.RIGHT)
        
        self.send_btn = tk.Button(
            button_frame, text="Send", command=self.send_message,
            bg=self.current_theme["button_bg"], fg=self.current_theme["button_fg"]
        )
        self.send_btn.pack(side=tk.LEFT, padx=2)
        
        self.emoji_btn = tk.Button(
            button_frame, text="😊", command=self.show_emoji_picker,
            bg=self.current_theme["accent"]
        )
        self.emoji_btn.pack(side=tk.LEFT, padx=2)
        
        self.file_btn = tk.Button(
            button_frame, text="📁", command=self.send_file,
            bg=self.current_theme["accent"]
        )
        self.file_btn.pack(side=tk.LEFT, padx=2)
        
        self.theme_btn = tk.Button(
            button_frame, text="🌙", command=self.toggle_theme,
            bg=self.current_theme["accent"]
        )
        self.theme_btn.pack(side=tk.LEFT, padx=2)
        
        # Users list
        tk.Label(
            right_panel, text="Online Users", bg=self.current_theme["bg"],
            fg=self.current_theme["fg"], font=("Arial", 12, "bold")
        ).pack(pady=(0, 5))
        
        self.users_list = tk.Listbox(
            right_panel, bg=self.current_theme["entry_bg"], fg=self.current_theme["fg"],
            selectbackground=self.current_theme["button_bg"], height=15
        )
        self.users_list.pack(fill=tk.BOTH, expand=True)
        self.users_list.insert(tk.END, "Everyone")
        self.users_list.selection_set(0)
        self.users_list.bind("<<ListboxSelect>>", self.select_recipient)
        
        # Status indicator
        self.status_label = tk.Label(
            right_panel, text="Connected", fg="green", bg=self.current_theme["bg"]
        )
        self.status_label.pack(pady=5)

    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Wrap socket with SSL/TLS
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # For self-signed certificates
        
        try:
            self.client_socket = context.wrap_socket(self.client_socket)
            self.client_socket.connect(("127.0.0.1", 5001))
            
            auth_data = f"{self.username}||{self.password}"
            self.client_socket.send(auth_data.encode())

            status = self.client_socket.recv(1024).decode()
            if status not in ["LOGIN_SUCCESS", "SIGNUP_SUCCESS", "WELCOME"]:
                messagebox.showerror("Authentication", "Login or signup failed.")
                self.root.quit()
                return
            
            # Request message history
            self.client_socket.send("HISTORY_REQUEST".encode())
            
            # Start receiving messages
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            # Update status
            self.status_label.config(text="Connected (Secure)", fg="green")
        except Exception as e:
            messagebox.showerror("Connection Error", f"❌ Cannot connect to the server: {str(e)}")
            self.root.quit()

    def select_recipient(self, event):
        selection = self.users_list.curselection()
        if selection:
            self.current_recipient = self.users_list.get(selection[0])
            if self.current_recipient != "Everyone":
                self.chat_area.config(state=tk.NORMAL)
                self.chat_area.insert(tk.END, f"\n--- Private chat with {self.current_recipient} ---\n\n")
                self.chat_area.config(state=tk.DISABLED)
                self.chat_area.yview(tk.END)

    def send_typing_status(self, event=None):
        if not self.typing and event.keysym not in ('Return', 'Escape', 'Tab'):
            self.typing = True
            typing_msg = f"TYPING|{self.username}|{self.current_recipient}|is typing..."
            self.client_socket.send(typing_msg.encode())
            self.root.after(2000, self.reset_typing)

    def reset_typing(self):
        self.typing = False
        typing_msg = f"TYPING|{self.username}|{self.current_recipient}|"
        self.client_socket.send(typing_msg.encode())

    def send_message(self, event=None):
        msg = self.msg_entry.get().strip()
        if msg:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
            if self.current_recipient == "Everyone":
                full_msg = f"MSG|{self.username}|Everyone|{msg}|{timestamp}"
            else:
                full_msg = f"PRIVATE|{self.username}|{self.current_recipient}|{msg}|{timestamp}"
            
            self.client_socket.send(full_msg.encode())
            
            # ✅ Display the message regardless of recipient
            if self.current_recipient == "Everyone":
                self.display_message(f"You ({timestamp}): {msg}")
            else:
                self.display_message(f"You to {self.current_recipient} ({timestamp}): {msg}")
            
            self.msg_entry.delete(0, tk.END)

    def send_file(self):
        if self.current_recipient == "Everyone":
            recipient = "Everyone"
        else:
            recipient = self.current_recipient
            
        file_path = filedialog.askopenfilename()
        if file_path:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Check if file is too large (10MB limit)
            if file_size > 10 * 1024 * 1024:
                messagebox.showerror("File Too Large", "File size exceeds 10MB limit.")
                return
                
            # Create progress bar with improved UI
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Sending File")
            progress_window.geometry("400x150")
            progress_window.configure(bg="#F0F0F0")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Center the window
            progress_window.update_idletasks()
            width = progress_window.winfo_width()
            height = progress_window.winfo_height()
            x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
            y = (progress_window.winfo_screenheight() // 2) - (height // 2)
            progress_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Add file info with icon
            file_frame = tk.Frame(progress_window, bg="#F0F0F0")
            file_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
            
            # Fixed: Removed the problematic line and kept only the correct one
            tk.Label(file_frame, text="📁", font=("Arial", 16), bg="#F0F0F0").pack(side=tk.LEFT, padx=(0, 10))
            
            file_info_frame = tk.Frame(file_frame, bg="#F0F0F0")
            file_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(file_info_frame, text=file_name, font=("Arial", 12, "bold"), bg="#F0F0F0", anchor="w").pack(fill=tk.X)
            size_text = f"Size: {file_size/1024:.1f} KB • To: {recipient}"
            tk.Label(file_info_frame, text=size_text, font=("Arial", 10), fg="gray", bg="#F0F0F0", anchor="w").pack(fill=tk.X)
            
            # Progress bar and status
            progress_frame = tk.Frame(progress_window, bg="#F0F0F0")
            progress_frame.pack(fill=tk.X, padx=20, pady=10)
            
            progress = ttk.Progressbar(progress_frame, length=360, mode="determinate")
            progress.pack(fill=tk.X)
            
            status_label = tk.Label(progress_window, text="Preparing to send...", bg="#F0F0F0")
            status_label.pack(pady=5)
            
            progress_window.update()
            
            # Read and encode file
            with open(file_path, "rb") as f:
                file_data = base64.b64encode(f.read()).decode()
            
            # Send file info first
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_info = f"FILE_INFO|{self.username}|{recipient}|{file_name}|{len(file_data)}|{timestamp}"
            self.client_socket.send(file_info.encode())
            
            status_label.config(text="Sending file...")
            progress_window.update()
            
            # Wait for server acknowledgment
            time.sleep(0.5)
            
            # Send file data in chunks
            chunk_size = 4096
            total_chunks = len(file_data) // chunk_size + (1 if len(file_data) % chunk_size else 0)
            
            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i+chunk_size]
                chunk_msg = f"FILE_CHUNK|{self.username}|{recipient}|{file_name}|{i//chunk_size}|{total_chunks}|{chunk}"
                self.client_socket.send(chunk_msg.encode())
                
                # Update progress
                progress["value"] = (i + len(chunk)) / len(file_data) * 100
                status_label.config(text=f"Sending: {progress['value']:.1f}% complete")
                progress_window.update()
                time.sleep(0.01)  # Small delay to prevent overwhelming the server
            
            # Send file complete message
            complete_msg = f"FILE_COMPLETE|{self.username}|{recipient}|{file_name}|{timestamp}"
            self.client_socket.send(complete_msg.encode())
            
            # Show completion message
            status_label.config(text="File sent successfully!")
            progress_window.update()
            
            # Close progress window after a delay
            progress_window.after(1500, progress_window.destroy)
            
            # Display message in our own chat if private
            if recipient == "Everyone":
                self.display_message(f"You sent a file to Everyone: {file_name}")
            else:
                self.display_message(f"You sent a file to {recipient}: {file_name}")

    def receive_messages(self):
        file_data = {}  # To store file chunks
        
        while True:
            try:
                msg = self.client_socket.recv(65536).decode(errors="ignore")
                if not msg:
                    break
                
                parts = msg.split("|")
                msg_type = parts[0]
                
                if msg_type == "USERS_LIST":
                    self.update_users_list(parts[1:])
                
                elif msg_type == "TYPING":
                    sender = parts[1]
                    recipient = parts[2]
                    typing_text = parts[3]
                    
                    if (recipient == "Everyone" or recipient == self.username or sender == self.current_recipient):
                        if typing_text:
                            self.typing_label.config(text=f"{sender} {typing_text}")
                        else:
                            self.typing_label.config(text="")
                
                elif msg_type == "MSG":
                    sender = parts[1]
                    recipient = parts[2]
                    content = parts[3]
                    timestamp = parts[4]
                    
                    self.display_message(f"{sender} ({timestamp}): {content}")
                
                elif msg_type == "PRIVATE":
                    sender = parts[1]
                    recipient = parts[2]
                    content = parts[3]
                    timestamp = parts[4]
                    
                    if recipient == self.username:
                        self.display_message(f"[Private] {sender} ({timestamp}): {content}")
                
                elif msg_type == "HISTORY":
                    # Format: HISTORY|json_data
                    history_data = "|".join(parts[1:])
                    try:
                        messages = json.loads(history_data)
                        for msg in messages:
                            if msg["type"] == "message":
                                if msg["recipient"] == "Everyone":
                                    self.display_message(f"{msg['sender']} ({msg['timestamp']}): {msg['content']}")
                                elif msg["recipient"] == self.username or msg["sender"] == self.username:
                                    self.display_message(f"[Private] {msg['sender']} to {msg['recipient']} ({msg['timestamp']}): {msg['content']}")
                            elif msg["type"] == "file":
                                if msg["recipient"] == "Everyone":
                                    self.display_message(f"{msg['sender']} sent a file: {msg['filename']}", is_file=True)
                                elif msg["recipient"] == self.username or msg["sender"] == self.username:
                                    self.display_message(f"[Private] {msg['sender']} sent a file to {msg['recipient']}: {msg['filename']}", is_file=True)
                    except json.JSONDecodeError:
                        print("Error decoding message history")
                
                elif msg_type == "FILE_INFO":
                    sender = parts[1]
                    recipient = parts[2]
                    file_name = parts[3]
                    file_size = int(parts[4])
                    timestamp = parts[5]
                    
                    # Initialize file data storage
                    file_key = f"{sender}_{file_name}"
                    file_data[file_key] = {
                        "chunks": {},
                        "total_chunks": 0,
                        "received_chunks": 0,
                        "sender": sender,
                        "recipient": recipient,
                        "timestamp": timestamp
                    }
                    
                    # Create progress window for receiving
                    if recipient == "Everyone" or recipient == self.username or sender == self.username:
                        progress_window = tk.Toplevel(self.root)
                        progress_window.title("Receiving File")
                        progress_window.geometry("300x100")
                        
                        tk.Label(progress_window, text=f"Receiving {file_name} from {sender}...").pack(pady=(10, 5))
                        progress = ttk.Progressbar(progress_window, length=250, mode="determinate")
                        progress.pack(pady=5)
                        
                        file_data[file_key]["progress_window"] = progress_window
                        file_data[file_key]["progress_bar"] = progress
                
                elif msg_type == "FILE_CHUNK":
                    sender = parts[1]
                    recipient = parts[2]
                    file_name = parts[3]
                    chunk_num = int(parts[4])
                    total_chunks = int(parts[5])
                    chunk_data = parts[6]
                    
                    file_key = f"{sender}_{file_name}"
                    if file_key in file_data:
                        file_data[file_key]["chunks"][chunk_num] = chunk_data
                        file_data[file_key]["total_chunks"] = total_chunks
                        file_data[file_key]["received_chunks"] += 1
                        
                        # Update progress bar
                        if "progress_bar" in file_data[file_key]:
                            progress = file_data[file_key]["received_chunks"] / total_chunks * 100
                            file_data[file_key]["progress_bar"]["value"] = progress
                            file_data[file_key]["progress_window"].update()
                
                elif msg_type == "FILE_COMPLETE":
                    sender = parts[1]
                    recipient = parts[2]
                    file_name = parts[3]
                    timestamp = parts[4]
                    
                    file_key = f"{sender}_{file_name}"
                    if file_key in file_data:
                        # Close progress window
                        if "progress_window" in file_data[file_key]:
                            file_data[file_key]["progress_window"].destroy()
                        
                        # Combine chunks
                        chunks = file_data[file_key]["chunks"]
                        total_chunks = file_data[file_key]["total_chunks"]
                        combined_data = ""
                        
                        for i in range(total_chunks):
                            if i in chunks:
                                combined_data += chunks[i]
                        
                        # Store the file data for download
                        file_data[file_key]["data"] = combined_data
                        
                        # Display message
                        if recipient == "Everyone" or recipient == self.username or sender == self.username:
                            self.display_message(
                                f"{sender} sent a file: {file_name}", 
                                is_file=True, 
                                file_name=file_name, 
                                file_data=combined_data
                            )
                
                elif msg_type == "SERVER":
                    self.display_message(f"SERVER: {parts[1]}")
                
                else:
                    self.display_message(msg)
                    
            except Exception as e:
                print(f"Error receiving message: {str(e)}")
                self.status_label.config(text="Disconnected", fg="red")
                break

    def update_users_list(self, users):
        self.online_users = users
        self.users_list.delete(1, tk.END)  # Keep "Everyone" at index 0
        
        for user in users:
            if user != self.username:  # Don't add ourselves to the list
                self.users_list.insert(tk.END, user)

    def search_messages(self, event=None):
        search_term = self.search_entry.get().strip()
        if search_term and search_term != "Search messages...":
            self.client_socket.send(f"SEARCH|{search_term}".encode())

    def display_message(self, message, is_file=False, file_name=None, file_data=None):
        self.chat_area.config(state=tk.NORMAL)
        
        # Add timestamp if not already in message
        if " (" not in message and not message.startswith("SERVER:") and not message.startswith("---"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"{message} ({timestamp})"
        
        self.chat_area.insert(tk.END, message + "\n")

        if is_file and file_name:
            def save_file():
                save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=file_name)
                if save_path:
                    try:
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(file_data))
                        messagebox.showinfo("Download", f"File saved as {save_path}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to save file: {str(e)}")

            btn = tk.Button(
                self.chat_area, text=f"Download {file_name}", 
                command=save_file, fg="blue", cursor="hand2",
                bg=self.current_theme["bg"]
            )
            self.chat_area.window_create(tk.END, window=btn)
            self.chat_area.insert(tk.END, "\n")

        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.yview(tk.END)

    def show_emoji_picker(self):
        picker = tk.Toplevel(self.root)
        picker.title("Select Emoji")
        picker.configure(bg=self.current_theme["bg"])
        
        emojis = [
            "😀", "😁", "😂", "🤣", "😅", "😊", "😍", "😎", "🤩", "👍", 
            "🙏", "👏", "💯", "🔥", "💥", "🎉", "❤️", "👌", "👋", "🤔",
            "😢", "😭", "😡", "🥳", "🤗", "🙄", "😴", "🤑", "🤠", "👻",
            "👽", "🤖", "💩", "🐱", "🐶", "🦊", "🐼", "🐨", "🦁", "🐯"
        ]
        
        row = col = 0
        for emoji in emojis:
            btn = tk.Button(
                picker, text=emoji, font=("Arial", 14), width=2, height=1,
                command=lambda e=emoji: self.insert_emoji(e),
                bg=self.current_theme["bg"]
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 10:
                col = 0
                row += 1

    def insert_emoji(self, emoji):
        self.msg_entry.insert(tk.END, emoji)

    def on_close(self):
        try:
            self.client_socket.send(f"LOGOUT|{self.username}".encode())
            self.client_socket.close()
        except:
            pass
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = ChatClient(root)
    root.mainloop()
