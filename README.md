📡 CryptoChat_CN - Team 1 (Secure Socket Chat App) 🚀
-------------------------------------------------------------
📌 Project Title:

Secure Multi-User Chat System using Python Sockets & MongoDB
------------------------------------------------------------
🔥 Problem Statement

Design and implement a secure, real-time, multi-user chat application using raw sockets in Python. The application must support encryption, emoji sharing, file transfers, private messaging, and authenticated login using MongoDB.
------------------------------------------------------------
📌 Tech Stack
Python 🐍

Socket Programming 🔌

SSL/TLS Encryption 🔐

MongoDB 🍃

Tkinter (for GUI) 🎨 (if used)

JSON & File Handling 📁
------------------------------------------------------------
📁 Project Structure

pgsql

Copy

Edit

CryptoChat_CN/

│

├── 📜 README.md

├── 📂 certs/

│   ├── cert.pem

│   ├── key.pem

│   └── server.crt

├── 📂 src/

│   ├── server.py         # Server-side chat handling

│   ├── client.py         # Client-side chat interface

│   └── users.json        # Stored user data

├── 📂 screenshots/

│   └── chat_demo.png     # Demo screenshot (optional)

├── 📜 TEAM_1_MP2_SCREENSHOT.pdf

├── 📜 .gitignore
------------------------------------------------------------
⚡ Installation & Setup

1️⃣ Clone the repository:

bash

Copy

Edit

git clone https://github.com/NehaRajkumarPatil/CryptoChat_CN.git

cd CryptoChat_CN

2️⃣ Install dependencies:

bash

Copy

Edit

pip install pymongo

3️⃣ Run the Server:

bash

Copy

Edit

python src/server.py

4️⃣ Run the Client:

bash

Copy

Edit

python src/client.py
------------------------------------------------------------
⚠️ Make sure MongoDB is running and SSL certificates are valid.
------------------------------------------------------------
🚀 Usage

👤 Register or login securely via MongoDB

💬 Send public messages

🗣️ Send private messages to specific users

📁 Share files in base64 format

😄 Express with emojis

✍️ See who is typing in real-time
------------------------------------------------------------
🏆 Features

✅ Secure Messaging via SSL

✅ MongoDB User Authentication

✅ Real-Time Broadcast Chat

✅ File Sharing (Text/Images in base64)

✅ Emoji Support 😃

✅ Private Messaging 🧑‍🤝‍🧑

✅ Typing Indicators ✍️

✅ Message Logging
------------------------------------------------------------
🎯 Future Scope

🚀 Add audio/video chat using WebRTC

🔒 Implement end-to-end encryption with RSA

📱 Build a mobile version using Kivy or Flutter

📊 Admin Dashboard for Chat Monitoring

🌐 WebSocket support for browser-based clients
------------------------------------------------------------
📜 License

This project is developed for academic purposes under PES University’s CN Mini Project guidelines.
