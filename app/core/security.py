"""
安全工具模块

提供 API Key 加密存储和其他安全相关功能
使用 AES-256 加密算法（通过 Fernet）
"""
import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_encryption_key() -> bytes:
    """
    获取加密密钥
    
    从环境变量 ENCRYPTION_KEY 获取，如果不存在则生成一个基于 SECRET_KEY 的密钥
    
    Returns:
        32 字节的加密密钥（Base64 编码）
    """
    # 优先使用专用的加密密钥
    key = os.environ.get("ENCRYPTION_KEY")
    if key:
        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'briefly_salt',  # 固定盐值，生产环境应使用随机盐
            iterations=100000,
        )
        key_bytes = kdf.derive(key.encode())
        return base64.urlsafe_b64encode(key_bytes)
    
    # 回退到 SECRET_KEY
    secret = os.environ.get("SECRET_KEY", "briefly-default-secret-key-change-in-production")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'briefly_salt',
        iterations=100000,
    )
    key_bytes = kdf.derive(secret.encode())
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    """
    获取 Fernet 实例
    
    Returns:
        Fernet 加密实例
    """
    key = get_encryption_key()
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    加密 API Key（使用 AES-256）
    
    Args:
        api_key: 明文 API Key
        
    Returns:
        加密后的 Base64 编码字符串
    """
    if not api_key:
        return ""
    
    try:
        fernet = _get_fernet()
        data = api_key.encode('utf-8')
        
        # 使用 Fernet 加密
        encrypted = fernet.encrypt(data)
        
        # Base64 编码
        encoded = base64.b64encode(encrypted).decode('utf-8')
        
        return f"enc_v2:{encoded}"
    except Exception as e:
        # 如果加密失败，记录错误并返回空字符串
        print(f"加密失败: {e}")
        return ""


def decrypt_api_key(encrypted_key: str) -> str:
    """
    解密 API Key
    
    Args:
        encrypted_key: 加密的 API Key
        
    Returns:
        明文 API Key
    """
    if not encrypted_key:
        return ""
    
    # 如果没有加密前缀，返回原值（向后兼容）
    if not encrypted_key.startswith("enc"):
        return encrypted_key
    
    try:
        fernet = _get_fernet()
        
        # 处理新版本加密格式
        if encrypted_key.startswith("enc_v2:"):
            encoded = encrypted_key[7:]  # 移除 "enc_v2:" 前缀
            encrypted = base64.b64decode(encoded.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode('utf-8')
        
        # 处理旧版本 XOR 加密格式（向后兼容）
        elif encrypted_key.startswith("enc:"):
            # 使用旧的 XOR 解密方法
            return _decrypt_legacy_xor(encrypted_key)
        
        # 没有前缀，返回原值
        return encrypted_key
        
    except Exception as e:
        # 解密失败，返回空字符串
        print(f"解密失败: {e}")
        return ""


def _decrypt_legacy_xor(encrypted_key: str) -> str:
    """
    解密旧版本的 XOR 加密数据（向后兼容）
    
    Args:
        encrypted_key: 旧版加密的 API Key
        
    Returns:
        明文 API Key
    """
    try:
        # 获取密钥（使用 SHA256 哈希）
        secret = os.environ.get("SECRET_KEY", "briefly-default-secret-key-change-in-production")
        key = hashlib.sha256(secret.encode()).digest()
        
        encoded = encrypted_key[4:]  # 移除 "enc:" 前缀
        encrypted = base64.b64decode(encoded.encode('utf-8'))
        
        # XOR 解密
        key_repeated = (key * ((len(encrypted) // len(key)) + 1))[:len(encrypted)]
        decrypted = bytes(a ^ b for a, b in zip(encrypted, key_repeated))
        
        return decrypted.decode('utf-8')
    except Exception:
        return ""


def is_encrypted(value: str) -> bool:
    """
    检查值是否已加密
    
    Args:
        value: 要检查的值
        
    Returns:
        是否已加密
    """
    if not value:
        return False
    return value.startswith("enc:") or value.startswith("enc_v2:")


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    遮蔽 API Key 用于显示
    
    Args:
        api_key: API Key
        visible_chars: 可见字符数
        
    Returns:
        遮蔽后的 API Key
    """
    if not api_key:
        return ""
    
    if len(api_key) <= visible_chars * 2:
        return "*" * len(api_key)
    
    return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"
