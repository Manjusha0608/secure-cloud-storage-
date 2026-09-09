# 🔐 Secure Cloud Storage

A secure cloud storage web application that allows users to upload files and protect them using encryption.

## 📌 Project Overview

This project provides a simple and secure way to upload files through a web interface. Uploaded files are encrypted before being stored on the server, helping protect sensitive data from unauthorized access.

## ✨ Features

* 🔐 File encryption using Fernet symmetric encryption
* 📤 Secure file upload
* 📥 File download and decryption
* 📁 Supports different file types such as images and documents
* 🌐 Web-based interface using Flask
* 🔑 Encryption key management
* 🛡️ Prevents direct storage of uploaded files in their original form

## 🛠️ Technologies Used

* Python
* Flask
* Cryptography
* HTML
* CSS
* JavaScript

## 📂 Project Structure

```text
secure-cloud-storage/
│
├── app.py
├── secret.key
├── uploads/
├── templates/
├── static/
├── requirements.txt
└── README.md
```

> **Note:** `secret.key` and uploaded files should not be committed to GitHub.

## ⚙️ How to Run

### 1. Clone the repository

```bash
git clone https://github.com/Manjusha0608/secure-cloud-storage-.git
```

### 2. Open the project folder

```bash
cd secure-cloud-storage-
```

### 3. Install dependencies

```bash
pip install flask cryptography werkzeug
```

### 4. Run the application

```bash
python app.py
```

### 5. Open in your browser

```text
http://127.0.0.1:5000
```

## 🔒 Security

Files are encrypted before being stored on the server. The encryption key is kept separately and should never be publicly shared or uploaded to GitHub.

## 🎯 Objective

The main objective of this project is to demonstrate how encryption can be used to improve the security and privacy of files stored in a cloud-storage environment.

