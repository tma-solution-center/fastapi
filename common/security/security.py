from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # Hoặc thư viện bạn đã sử dụng để mã hóa JWT
from cryptography.fernet import Fernet
import base64

from common.utils.VaultUtils import VaultUtils

vault_utils = VaultUtils()
secret_data = vault_utils.read_secret(path='cdp-app-key')
validate_jwt_cdp_app_secret_key = secret_data['validate_jwt_cdp_app_secret_key']
# Key phải có độ dài chính xác 32 bytes
encryption_secret_key = secret_data['encryption_secret_key']
fernet = Fernet(encryption_secret_key)
security = HTTPBearer()


def validate_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Giải mã token và kiểm tra thông tin
        decoded_token = jwt.decode(token, validate_jwt_cdp_app_secret_key, algorithms=["HS256"])
        return decoded_token  # Trả về thông tin từ token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_secret_key(jwt_secret: str):
    # Mã hóa chuỗi bí mật thành byte
    secret_bytes = jwt_secret.encode('utf-8')

    # Mã hóa bằng base64
    encoded = base64.b64encode(secret_bytes).decode('utf-8')
    print(encoded)
    # Trả về khóa dưới dạng chuỗi
    return encoded


def encrypt_data(data: str) -> str:
    """
    Mã hóa dữ liệu trước khi lưu xuống MySQL.

    Args:
        data (str): Dữ liệu cần mã hóa.

    Returns:
        str: Dữ liệu đã được mã hóa (chuỗi base64).
    """
    encrypted_data = fernet.encrypt(data.encode())  # Mã hóa dữ liệu
    return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')  # Chuyển đổi thành chuỗi để lưu


def decrypt_data(encrypted_data: str) -> str:
    """
    Giải mã dữ liệu đã được mã hóa từ MySQL.

    Args:
        encrypted_data (str): Dữ liệu đã được mã hóa (chuỗi base64).

    Returns:
        str: Dữ liệu đã được giải mã.
    """
    decoded_data = base64.urlsafe_b64decode(encrypted_data)  # Giải mã base64 thành chuỗi bytes
    return fernet.decrypt(decoded_data).decode('utf-8')  # Giải mã dữ liệu
