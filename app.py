from __future__ import annotations

import hmac
import os
import time
from io import BytesIO
from pathlib import Path

from Crypto.Cipher import AES, DES3
from Crypto.Hash import HMAC, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

# 3DES is used to satisfy project requirements. For real-world applications,
# modern authenticated encryption like AES-GCM should be preferred.

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"

MAGIC_3DES = b"3DESIMG1"
MAGIC_AES_GCM = b"AESGCMV1"
SALT_SIZE = 16
IV_SIZE = 8
NONCE_SIZE = 12
TAG_SIZE = 16
MAC_SIZE = 32
BLOCK_SIZE = 8
PBKDF2_ITERATIONS = 200_000
MAX_EXT_LEN = 20
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class CryptoError(Exception):
    """Raised for encryption/decryption validation errors."""


def derive_3des_keys(password: str, salt: bytes) -> tuple[bytes, bytes]:
    if not password:
        raise CryptoError("Secret key cannot be empty.")

    key_material = PBKDF2(
        password=password.encode("utf-8"),
        salt=salt,
        dkLen=56,
        count=PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256,
    )

    raw_des3_key = key_material[:24]
    hmac_key = key_material[24:]

    try:
        des3_key = DES3.adjust_key_parity(raw_des3_key)
    except ValueError:
        fallback = SHA256.new(raw_des3_key).digest()[:24]
        des3_key = DES3.adjust_key_parity(fallback)

    return des3_key, hmac_key


def derive_aes_key(password: str, salt: bytes) -> bytes:
    if not password:
        raise CryptoError("Secret key cannot be empty.")
    return PBKDF2(
        password=password.encode("utf-8"),
        salt=salt,
        dkLen=32,
        count=PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256,
    )


def compute_mac(hmac_key: bytes, data: bytes) -> bytes:
    mac = HMAC.new(hmac_key, digestmod=SHA256)
    mac.update(data)
    return mac.digest()


def validate_image_bytes(data: bytes) -> None:
    if not data:
        raise CryptoError("Uploaded image is empty.")
    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise CryptoError("Invalid image file. Please upload a valid image.") from exc


def sanitize_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise CryptoError("Unsupported image format. Use PNG/JPG/JPEG/BMP/GIF/TIFF/WEBP.")
    if len(ext) > MAX_EXT_LEN:
        raise CryptoError("File extension metadata is too long.")
    return ext


def encrypt_bytes_3des(image_bytes: bytes, password: str, extension: str) -> bytes:
    salt = get_random_bytes(SALT_SIZE)
    iv = get_random_bytes(IV_SIZE)
    des3_key, hmac_key = derive_3des_keys(password, salt)

    cipher = DES3.new(des3_key, DES3.MODE_CBC, iv=iv)
    ciphertext = cipher.encrypt(pad(image_bytes, BLOCK_SIZE))

    ext_bytes = extension.encode("ascii")
    header = MAGIC_3DES + salt + iv + bytes([len(ext_bytes)]) + ext_bytes
    mac = compute_mac(hmac_key, header + ciphertext)
    return header + ciphertext + mac


def encrypt_bytes_aes_gcm(image_bytes: bytes, password: str, extension: str) -> bytes:
    salt = get_random_bytes(SALT_SIZE)
    nonce = get_random_bytes(NONCE_SIZE)
    aes_key = derive_aes_key(password, salt)

    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(image_bytes)

    ext_bytes = extension.encode("ascii")
    header = MAGIC_AES_GCM + salt + nonce + bytes([len(ext_bytes)]) + ext_bytes
    return header + ciphertext + tag


def decrypt_bytes_3des(encrypted_blob: bytes, password: str) -> tuple[bytes, str, str]:
    min_size = len(MAGIC_3DES) + SALT_SIZE + IV_SIZE + 1 + 1 + BLOCK_SIZE + MAC_SIZE
    if len(encrypted_blob) < min_size:
        raise CryptoError("Encrypted file is too small or invalid.")

    cursor = 0
    magic = encrypted_blob[cursor : cursor + len(MAGIC_3DES)]
    cursor += len(MAGIC_3DES)
    if magic != MAGIC_3DES:
        raise CryptoError("Invalid encrypted file format.")

    salt = encrypted_blob[cursor : cursor + SALT_SIZE]
    cursor += SALT_SIZE

    iv = encrypted_blob[cursor : cursor + IV_SIZE]
    cursor += IV_SIZE

    ext_len = encrypted_blob[cursor]
    cursor += 1
    if ext_len == 0 or ext_len > MAX_EXT_LEN:
        raise CryptoError("Encrypted file metadata is invalid.")

    if len(encrypted_blob) < cursor + ext_len + MAC_SIZE + BLOCK_SIZE:
        raise CryptoError("Encrypted file is truncated or corrupted.")

    ext_bytes = encrypted_blob[cursor : cursor + ext_len]
    cursor += ext_len

    try:
        original_ext = ext_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CryptoError("Encrypted file metadata is invalid.") from exc

    ciphertext = encrypted_blob[cursor:-MAC_SIZE]
    provided_mac = encrypted_blob[-MAC_SIZE:]

    if len(ciphertext) == 0 or len(ciphertext) % BLOCK_SIZE != 0:
        raise CryptoError("Encrypted file content is invalid.")

    des3_key, hmac_key = derive_3des_keys(password, salt)
    expected_mac = compute_mac(hmac_key, encrypted_blob[:cursor] + ciphertext)
    if not hmac.compare_digest(expected_mac, provided_mac):
        raise CryptoError("Incorrect key or tampered encrypted file.")

    cipher = DES3.new(des3_key, DES3.MODE_CBC, iv=iv)
    try:
        plaintext = unpad(cipher.decrypt(ciphertext), BLOCK_SIZE)
    except ValueError as exc:
        raise CryptoError("Decryption failed. Wrong key or corrupted file.") from exc

    return plaintext, original_ext, "3DES"


def decrypt_bytes_aes_gcm(encrypted_blob: bytes, password: str) -> tuple[bytes, str, str]:
    min_size = len(MAGIC_AES_GCM) + SALT_SIZE + NONCE_SIZE + 1 + 1 + TAG_SIZE
    if len(encrypted_blob) < min_size:
        raise CryptoError("Encrypted file is too small or invalid.")

    cursor = 0
    magic = encrypted_blob[cursor : cursor + len(MAGIC_AES_GCM)]
    cursor += len(MAGIC_AES_GCM)
    if magic != MAGIC_AES_GCM:
        raise CryptoError("Invalid encrypted file format.")

    salt = encrypted_blob[cursor : cursor + SALT_SIZE]
    cursor += SALT_SIZE

    nonce = encrypted_blob[cursor : cursor + NONCE_SIZE]
    cursor += NONCE_SIZE

    ext_len = encrypted_blob[cursor]
    cursor += 1
    if ext_len == 0 or ext_len > MAX_EXT_LEN:
        raise CryptoError("Encrypted file metadata is invalid.")

    if len(encrypted_blob) < cursor + ext_len + TAG_SIZE:
        raise CryptoError("Encrypted file is truncated or corrupted.")

    ext_bytes = encrypted_blob[cursor : cursor + ext_len]
    cursor += ext_len

    try:
        original_ext = ext_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CryptoError("Encrypted file metadata is invalid.") from exc

    ciphertext = encrypted_blob[cursor:-TAG_SIZE]
    tag = encrypted_blob[-TAG_SIZE:]
    if len(ciphertext) == 0:
        raise CryptoError("Encrypted file content is invalid.")

    aes_key = derive_aes_key(password, salt)
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise CryptoError("Incorrect key or tampered encrypted file.") from exc

    return plaintext, original_ext, "AES-GCM"


def decrypt_bytes(encrypted_blob: bytes, password: str) -> tuple[bytes, str, str]:
    magic = encrypted_blob[:8]
    if magic == MAGIC_3DES:
        return decrypt_bytes_3des(encrypted_blob, password)
    if magic == MAGIC_AES_GCM:
        return decrypt_bytes_aes_gcm(encrypted_blob, password)
    raise CryptoError("Unsupported encrypted file format.")


def save_upload(file_storage) -> Path:
    safe_name = secure_filename(file_storage.filename or "")
    if not safe_name:
        raise CryptoError("Please choose a valid file.")
    unique_name = f"{int(time.time() * 1000)}_{safe_name}"
    upload_path = UPLOADS_DIR / unique_name
    file_storage.save(upload_path)
    return upload_path


def save_output(filename: str, data: bytes) -> Path:
    safe_name = secure_filename(filename)
    output_path = OUTPUTS_DIR / safe_name
    output_path.write_bytes(data)
    return output_path


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", download_name=None, selected_algorithm="3DES")


@app.route("/encrypt", methods=["POST"])
def encrypt_route():
    upload = request.files.get("image_file")
    password = (request.form.get("password") or "").strip()
    algorithm = (request.form.get("algorithm") or "3DES").strip().upper()

    if upload is None or not upload.filename:
        flash("Please upload an image file.", "error")
        return redirect(url_for("index"))

    if not password:
        flash("Please enter a secret key.", "error")
        return redirect(url_for("index"))

    start = time.perf_counter()
    upload_path: Path | None = None

    try:
        upload_path = save_upload(upload)
        file_data = upload_path.read_bytes()
        extension = sanitize_extension(upload_path.name)
        validate_image_bytes(file_data)

        if algorithm == "3DES":
            encrypted_blob = encrypt_bytes_3des(file_data, password, extension)
            algo_suffix = "3des"
        elif algorithm == "AES_GCM":
            encrypted_blob = encrypt_bytes_aes_gcm(file_data, password, extension)
            algo_suffix = "aesgcm"
        else:
            raise CryptoError("Invalid encryption type selected.")

        out_name = f"{Path(upload_path.name).stem}_{algo_suffix}.enc"
        output_path = save_output(out_name, encrypted_blob)

        elapsed = time.perf_counter() - start
        flash(f"Encryption successful ({algorithm.replace('_', '-')}) in {elapsed:.4f} seconds.", "success")
        return render_template(
            "index.html",
            download_name=output_path.name,
            mode="encrypt",
            selected_algorithm=algorithm,
        )
    except CryptoError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except Exception:
        flash("Encryption failed due to an unexpected error.", "error")
        return redirect(url_for("index"))
    finally:
        if upload_path and upload_path.exists():
            upload_path.unlink(missing_ok=True)


@app.route("/decrypt", methods=["POST"])
def decrypt_route():
    upload = request.files.get("enc_file")
    password = (request.form.get("password") or "").strip()

    if upload is None or not upload.filename:
        flash("Please upload an encrypted (.enc) file.", "error")
        return redirect(url_for("index"))

    if not password:
        flash("Please enter the secret key.", "error")
        return redirect(url_for("index"))

    start = time.perf_counter()
    upload_path: Path | None = None

    try:
        upload_path = save_upload(upload)
        encrypted_blob = upload_path.read_bytes()

        plaintext, original_ext, detected_algorithm = decrypt_bytes(encrypted_blob, password)

        # Validate that decrypted bytes represent an image.
        validate_image_bytes(plaintext)

        out_name = f"{Path(upload_path.name).stem}_decrypted{original_ext}"
        output_path = save_output(out_name, plaintext)

        elapsed = time.perf_counter() - start
        flash(f"Decryption successful ({detected_algorithm}) in {elapsed:.4f} seconds.", "success")
        return render_template(
            "index.html",
            download_name=output_path.name,
            mode="decrypt",
            selected_algorithm="3DES",
        )
    except CryptoError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except Exception:
        flash("Decryption failed due to an unexpected error.", "error")
        return redirect(url_for("index"))
    finally:
        if upload_path and upload_path.exists():
            upload_path.unlink(missing_ok=True)


@app.route("/download/<path:filename>", methods=["GET"])
def download(filename: str):
    safe_name = secure_filename(filename)
    file_path = (OUTPUTS_DIR / safe_name).resolve()
    if not str(file_path).startswith(str(OUTPUTS_DIR.resolve())) or not file_path.exists():
        flash("Requested file does not exist.", "error")
        return redirect(url_for("index"))

    return send_file(file_path, as_attachment=True, download_name=file_path.name)


if __name__ == "__main__":
    app.run(debug=True)
