# -*- coding: utf-8 -*-
"""
BIP 开放平台 自建应用 事件订阅 消息解密/验签
—— 与 Java 版 com.yonyou.openapi.crypto.PrivateAppCrypto / EventCrypto 对齐

依赖：
    pip install pycryptodome
"""

import base64
import hmac
import hashlib
import json
import struct
from typing import Tuple

from Crypto.Cipher import AES


# =========================================================
# 异常
# =========================================================
class CryptoException(Exception):
    """加解密/验签 相关异常"""
    pass


# =========================================================
# PKCS7 —— 注意：Java 版块长度是 32，而不是常见的 16
# =========================================================
_BLOCK_SIZE = 32


def _pkcs7_encode(text_len: int) -> bytes:
    """对指定长度生成 PKCS7 填充字节（块长 32）"""
    amount_to_pad = _BLOCK_SIZE - (text_len % _BLOCK_SIZE)
    if amount_to_pad == 0:
        amount_to_pad = _BLOCK_SIZE
    return bytes([amount_to_pad & 0xFF] * amount_to_pad)


def _pkcs7_decode(decrypted: bytes) -> bytes:
    """去掉 PKCS7 填充字节（块长 32）"""
    pad = decrypted[-1]
    if pad < 1 or pad > 32:
        pad = 0
    return decrypted[:len(decrypted) - pad]


# =========================================================
# 签名 —— HmacSHA256(token, sorted([timestamp, nonce, encrypt]).join())
# =========================================================
def _sha256_sign(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    arr = sorted([str(timestamp), nonce, encrypt])
    raw = "".join(arr).encode("utf-8")
    mac = hmac.new(token.encode("utf-8"), raw, hashlib.sha256).digest()
    # Java 端用的是 org.apache.commons.codec.binary.Base64（无换行）
    return base64.b64encode(mac).decode("utf-8")


# =========================================================
# EventCrypto —— 与 Java EventCrypto 一一对应
# =========================================================
class EventCrypto:
    """
    对应 Java: com.yonyou.openapi.crypto.EventCrypto

    参数:
        token           —— 对应 Java: 开发者设置的 token（自建应用中即 appSecret）
        encoding_aes_key—— 43 位字符串
        suite_key       —— 套件 suiteKey（自建应用中即 appKey）
    """

    def __init__(self, token: str, encoding_aes_key: str, suite_key: str):
        if len(encoding_aes_key) != 43:
            raise CryptoException("无效的 AES key（长度必须为 43）")
        self.token = token
        self.suite_key = suite_key
        # 与 Java 端保持一致：拼接 "=" 后再 Base64 解码，得到 32 字节
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        if len(self.aes_key) != 32:
            raise CryptoException("AES key 解码后长度必须为 32 字节")

    # ---------- 解密 ----------
    def decrypt(self, text: str) -> str:
        """
        对密文（base64）进行 AES/CBC/NoPadding 解密，并校验 suiteKey。
        返回真实明文。
        """
        try:
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv=self.aes_key[:16])
            encrypted = base64.b64decode(text)
            original = cipher.decrypt(encrypted)
        except Exception as e:
            raise CryptoException(f"AES 解密失败: {e}") from e

        try:
            # 去补位
            data = _pkcs7_decode(original)

            # 结构: [0:16]=随机串, [16:20]=内容长度(大端), [20:20+len]=message, [剩余]=suiteKey
            xml_length = struct.unpack(">I", data[16:20])[0]
            message = data[20:20 + xml_length].decode("utf-8")
            from_suite_key = data[20 + xml_length:].decode("utf-8")
        except Exception as e:
            raise CryptoException(f"无效的 AES key（拆包失败）: {e}") from e

        if from_suite_key != self.suite_key:
            raise CryptoException("suiteKey 校验失败")
        return message

    # ---------- 验签 + 解密 ----------
    def decrypt_msg(self,
                    msg_signature: str,
                    timestamp,
                    nonce: str,
                    encrypt: str) -> str:
        """
        对应 Java: decryptMsg(signature, timestamp, nonce, encrypt)
        1) HmacSHA256 生成签名并与 msg_signature 比对
        2) 通过后 AES 解密
        """
        signature = _sha256_sign(self.token, timestamp, nonce, encrypt)
        if signature != msg_signature:
            raise CryptoException(f"签名校验失败！expect={signature}, got={msg_signature}")
        return self.decrypt(encrypt)

    def decrypt_msg_json(self, json_msg: str) -> str:
        """输入整个 JSON 报文（含 signature/timestamp/nonce/encrypt），返回解密后的明文"""
        holder = json.loads(json_msg)
        return self.decrypt_msg(
            holder["signature"],
            holder["timestamp"],
            holder["nonce"],
            holder["encrypt"],
        )

    # ---------- 加密（对称实现，方便自测；线上收消息一般用不到） ----------
    def encrypt(self, random_str: str, text: str) -> str:
        text_bytes = text.encode("utf-8")
        suite_key_bytes = self.suite_key.encode("utf-8")

        buf = bytearray()
        buf += random_str.encode("utf-8")           # 16 字节随机串
        buf += struct.pack(">I", len(text_bytes))   # 4 字节 大端 长度
        buf += text_bytes
        buf += suite_key_bytes
        buf += _pkcs7_encode(len(buf))              # PKCS7 (块长 32)

        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv=self.aes_key[:16])
        encrypted = cipher.encrypt(bytes(buf))
        return base64.b64encode(encrypted).decode("utf-8")


# =========================================================
# PrivateAppCrypto —— 自建应用工厂
# =========================================================
class PrivateAppCrypto(EventCrypto):
    """
    对应 Java: com.yonyou.openapi.crypto.PrivateAppCrypto
    自建应用通过 (appKey, appSecret) 派生 AES key
    """

    def __init__(self, app_key: str, app_secret: str, encoding_aes_key: str):
        # Java: super(appSecret, encodingAesKey, appKey)
        super().__init__(token=app_secret,
                         encoding_aes_key=encoding_aes_key,
                         suite_key=app_key)

    @classmethod
    def new_crypto(cls, app_key: str, app_secret: str) -> "PrivateAppCrypto":
        return cls(app_key, app_secret, cls.build_aes_key_from_secret(app_secret))

    # ---------- AES key 派生规则 ----------
    @staticmethod
    def build_aes_key_from_secret(app_secret: str) -> str:
        """
        1) 移除 '-'
        2) 长度不足 43 时末尾补 '0'
        3) 长度大于 43 时截取前 43
        """
        s = app_secret.replace("-", "")
        if len(s) == 43:
            return s
        if len(s) > 43:
            return s[:43]
        return s + "0" * (43 - len(s))


# =========================================================
# 与 Controller 里 body 结构对齐的 DTO（可选）
# =========================================================
def decrypt_event_body(app_key: str, app_secret: str, body: dict) -> Tuple[str, dict]:
    """
    模拟 ARSetToNCCController.eventSubscribe 中的调用：

        EventCrypto crypto = PrivateAppCrypto.newCrypto(appKey, appSecret);
        String decryptMessage = crypto.decryptMsg(body.signature,
                                                  body.timestamp,
                                                  body.nonce,
                                                  body.encrypt);

    返回:  (原始 JSON 字符串, 解析后的 dict)
    """
    crypto = PrivateAppCrypto.new_crypto(app_key, app_secret)
    plain = crypto.decrypt_msg(
        body["signature"],
        body["timestamp"],
        body["nonce"],
        body["encrypt"],
    )
    return plain, json.loads(plain)