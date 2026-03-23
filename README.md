# Image Encryption and Decryption using Triple DES (3DES)

This is a Flask-based web application for encrypting and decrypting images using Triple DES (3DES).

## Features
- Upload an image and encrypt it into `.enc`
- Upload a `.enc` file and decrypt it back to original image bytes
- Uses the same password for encryption and decryption
- Detects wrong key/tampered file using HMAC verification
- Handles invalid uploads and errors safely
- Modern responsive UI with status messages and image preview

## Security Note
3DES is implemented to satisfy internship requirements. In production, use modern authenticated encryption such as AES-GCM.

## Folder Structure
```text
project/
|-- app.py
|-- templates/
|   `-- index.html
|-- static/
|   |-- style.css
|   `-- script.js
|-- uploads/
|-- outputs/
`-- requirements.txt
```

## How to Run
1. Open a terminal in the `project` directory.
2. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
```

On Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the Flask app:

```bash
python app.py
```

5. Open in browser:

```text
http://127.0.0.1:5000
```

## Quick Start Without Activation (Windows)
If PowerShell blocks `Activate.ps1`, run the app directly with:

```powershell
cd "d:\exposys data labs\project stuff\raw stuff\project"
\.venv\Scripts\python.exe app.py
```

or simply:

```powershell
run_app.bat
```

## Important About "Go Live"
VS Code `Go Live`/Five Server serves static files only, so it cannot run Flask backend routes.
Use Flask (`python app.py` or `run_app.bat`) and open `http://127.0.0.1:5000`.
