# Image Encryption and Decryption (Flask + 3DES + AES-GCM)

A Flask web application to encrypt and decrypt image files.

This project supports:
- 3DES-CBC with HMAC-SHA256 integrity protection
- AES-GCM authenticated encryption

Users can upload an image, choose an encryption algorithm, download a `.enc` output, and later decrypt it back to the original image.

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How Encryption Works](#how-encryption-works)
- [Prerequisites](#prerequisites)
- [Setup and Run](#setup-and-run)
- [Daily Run Commands](#daily-run-commands)
- [Troubleshooting](#troubleshooting)
- [Usage Flow](#usage-flow)
- [Security Notes](#security-notes)
- [API Routes](#api-routes)

## Features
- Encrypt supported image types into `.enc`
- Decrypt `.enc` files back to original image bytes
- Auto-detect decryption algorithm from encrypted file header
- Secret-key based key derivation using PBKDF2-SHA256
- Tamper/wrong-key detection
- Upload validation and error-safe handling
- Responsive UI with image preview and status messages

## Tech Stack
- Python 3.10+
- Flask
- PyCryptodome
- Pillow
- HTML/CSS/JavaScript frontend

## Project Structure
```text
project/
|-- app.py                  # Flask app and crypto logic
|-- requirements.txt        # Python dependencies
|-- run_app.bat             # Windows batch launcher
|-- run_app.ps1             # Windows PowerShell launcher
|-- index.html              # Optional static launcher page for Go Live users
|-- templates/
|   `-- index.html          # Main Flask-rendered page
|-- static/
|   |-- style.css
|   `-- script.js
|-- uploads/                # Temporary upload storage
|   `-- .gitkeep
|-- outputs/                # Generated encrypted/decrypted files
|   `-- .gitkeep
`-- .gitignore
```

## How Encryption Works

### 3DES output format
`MAGIC_3DES | salt | iv | ext_len | ext | ciphertext | hmac`

- Magic: `3DESIMG1`
- Salt: 16 bytes
- IV: 8 bytes
- Extension length: 1 byte
- Extension: ASCII bytes (for example `.png`)
- Cipher mode: 3DES-CBC with PKCS#7 padding
- Integrity: HMAC-SHA256 (32 bytes)

### AES-GCM output format
`MAGIC_AES_GCM | salt | nonce | ext_len | ext | ciphertext | tag`

- Magic: `AESGCMV1`
- Salt: 16 bytes
- Nonce: 12 bytes
- Extension length: 1 byte
- Extension: ASCII bytes
- Cipher mode: AES-GCM
- Authentication tag: 16 bytes

## Prerequisites
- Windows, macOS, or Linux
- Python installed and available in PATH

## Setup and Run

1. Open terminal inside the `project` folder.

2. Create virtual environment:

```bash
python -m venv .venv
```

3. Activate virtual environment.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start the Flask app:

```bash
python app.py
```

6. Open browser:

```text
http://127.0.0.1:5000
```

## Daily Run Commands

After first-time setup, you can run using any one option:

### Option A: Activated environment
```bash
python app.py
```

### Option B: Direct launcher (no activation needed)
```powershell
run_app.bat
```

or

```powershell
PowerShell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Launcher scripts auto-detect virtual environment in:
- `project/.venv`
- parent folder `.venv`

## Troubleshooting

### "Go Live" opens page but app does not work
`Go Live` or `Five Server` serves static files only. It does not execute Flask routes.

Fix:
- Start Flask with `python app.py` (or launcher scripts)
- Open `http://127.0.0.1:5000`

### `python app.py` does not run
Check:
- You are inside the `project` directory
- Dependencies are installed from `requirements.txt`
- Virtual environment is active, or use launcher scripts

### PowerShell blocks activation script
Use:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\run_app.ps1
```

## Usage Flow

### Encrypt
1. Select image file
2. Choose algorithm (3DES or AES-GCM)
3. Enter secret key
4. Click Encrypt
5. Download generated `.enc` file

### Decrypt
1. Upload `.enc` file
2. Enter same secret key used during encryption
3. Click Decrypt
4. Download restored image

## Security Notes
- 3DES is included for internship/project requirement compatibility.
- For modern production systems, prefer AES-GCM.
- `FLASK_SECRET_KEY` should be set from environment in production.
- Flask built-in server is for development only.

## API Routes
- `GET /` : main UI
- `POST /encrypt` : encrypt uploaded image
- `POST /decrypt` : decrypt uploaded `.enc` file
- `GET /download/<filename>` : download generated file
