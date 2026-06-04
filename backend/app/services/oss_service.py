"""
阿里云 OSS 对象存储服务
用于存储日记图片和音频文件，私用 Bucket + 签名 URL 模式
"""
import os
import uuid
from typing import List

import oss2


# OSS 客户端延迟初始化
_client = None


def _get_client() -> oss2.Bucket:
    """获取 OSS 客户端（延迟初始化，首次调用时创建连接）"""
    global _client
    if _client is None:
        access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
        access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
        bucket_name = os.getenv("OSS_BUCKET_NAME")
        endpoint = os.getenv("OSS_ENDPOINT")

        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            raise RuntimeError("OSS not configured: missing environment variables")

        auth = oss2.Auth(access_key_id, access_key_secret)
        _client = oss2.Bucket(auth, endpoint, bucket_name)
    return _client


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "heic"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def upload_image(file_data: bytes, file_ext: str) -> str:
    """
    上传图片到 OSS

    Args:
        file_data: 图片二进制数据
        file_ext: 文件扩展名（不含点号）

    Returns:
        OSS object key，如 "diary_images/a1b2c3d4.jpg"

    Raises:
        ValueError: 格式不支持或文件过大
        RuntimeError: OSS 上传失败
    """
    ext = file_ext.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    if len(file_data) > MAX_FILE_SIZE:
        raise ValueError(f"图片过大: {len(file_data)} bytes，最大 {MAX_FILE_SIZE} bytes")

    key = f"diary_images/{uuid.uuid4()}.{ext}"

    client = _get_client()
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "heic": "image/heic",
    }
    headers = {
        "Content-Type": content_type_map.get(ext, "application/octet-stream"),
        "Content-Disposition": "inline",
    }

    result = client.put_object(key, file_data, headers=headers)
    if result.status != 200:
        raise RuntimeError(f"OSS 上传失败: status={result.status}")

    return key


def delete_image(object_key: str) -> None:
    """
    从 OSS 删除图片

    Args:
        object_key: OSS object key
    """
    client = _get_client()
    client.delete_object(object_key)


def batch_delete(keys: List[str]) -> None:
    """
    批量删除 OSS 对象

    Args:
        keys: OSS object key 列表
    """
    client = _get_client()
    for key in keys:
        try:
            client.delete_object(key)
        except Exception:
            pass  # 删除失败不中断批量操作


def sign_url(object_key: str, expires: int = 3600) -> str:
    """
    生成签名 URL（临时访问链接）

    Args:
        object_key: OSS object key
        expires: 有效期（秒），默认 1 小时

    Returns:
        签名后的完整 HTTPS URL
    """
    client = _get_client()
    return client.sign_url("GET", object_key, expires)
"""
阿里云 OSS 音频存储服务 — 私有 Bucket + 签名 URL
"""
import oss2
import os
import uuid
from datetime import datetime
from fastapi import UploadFile


class OSSService:
    """阿里云 OSS 音频存储服务"""

    def __init__(self):
        self.endpoint = os.getenv("OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
        self.bucket_name = os.getenv("OSS_BUCKET_NAME", "pine-diary-audio")
        self.ram_role_name = os.getenv("OSS_RAM_ROLE_NAME")
        # 从 endpoint 提取 region（oss-cn-hangzhou.aliyuncs.com → cn-hangzhou）
        self.region = self.endpoint.split(".")[0].replace("oss-", "")

        self.bucket = None  # 延迟初始化，认证失败不阻塞启动
        self.max_size_mb = int(os.getenv("AUDIO_MAX_SIZE_MB", "15"))
        self.allowed_formats = os.getenv(
            "AUDIO_ALLOWED_FORMATS", "m4a,wav,mp3,aac"
        ).split(",")

        self._init_bucket()

    def _init_bucket(self):
        """初始化 OSS Bucket，认证失败不阻塞启动"""
        try:
            print(f"[OSS] 开始初始化音频Bucket: bucket={self.bucket_name}, endpoint={self.endpoint}, region={self.region}")
            auth = self._create_auth()
            self.bucket = oss2.Bucket(
                auth, f"https://{self.endpoint}", self.bucket_name, region=self.region
            )
            # 测试连接
            self.bucket.get_bucket_info()
            print(f"[OSS] 音频Bucket初始化成功")
        except Exception as e:
            print(f"[OSS] 初始化失败（音频功能不可用）: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.bucket = None

    def _ensure_bucket(self):
        """确保 bucket 已初始化"""
        if self.bucket is None:
            raise RuntimeError("OSS 未配置，音频功能不可用")

    def _create_auth(self):
        """创建认证器：优先 ECS RAM 角色，回落 AccessKey"""
        # 1. ECS RAM 角色（生产环境）
        if self.ram_role_name:
            try:
                print(f"[OSS] 尝试使用ECS RAM角色: {self.ram_role_name}")
                ecs_metadata_url = (
                    "http://100.100.100.200/latest/meta-data/"
                    f"ram/security-credentials/{self.ram_role_name}"
                )
                credentials = oss2.credentials.EcsRamRoleCredentialsProvider(
                    ecs_metadata_url
                )
                return oss2.ProviderAuthV4(credentials)
            except Exception as e:
                print(f"[OSS] ECS RAM 角色认证失败，回落 AccessKey: {type(e).__name__}: {e}")

        # 2. 回落 AccessKey（开发环境）
        ak = os.getenv("OSS_ACCESS_KEY_ID")
        sk = os.getenv("OSS_ACCESS_KEY_SECRET")
        if ak and sk:
            print(f"[OSS] 使用AccessKey认证")
            return oss2.Auth(ak, sk)

        raise RuntimeError("OSS 认证失败：无 ECS RAM 角色且无 AccessKey")

    def _validate(self, file: UploadFile) -> None:
        """校验文件格式和大小"""
        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.allowed_formats:
            raise ValueError(f"不支持的格式: .{ext}，仅支持 {self.allowed_formats}")

        content_type = file.content_type or ""
        if not content_type.startswith("audio/"):
            raise ValueError(f"不是音频文件: {content_type}")

        if hasattr(file, "size") and file.size:
            if file.size > self.max_size_mb * 1024 * 1024:
                raise ValueError(f"文件过大 (>{self.max_size_mb}MB)")

    async def upload(self, file: UploadFile) -> str:
        """上传音频到 OSS，返回完整 OSS URL"""
        try:
            print(f"[OSS] 开始上传音频: filename={file.filename}, size={getattr(file, 'size', 'unknown')}")
            self._ensure_bucket()
            self._validate(file)

            now = datetime.utcnow()
            ext = (
                file.filename.rsplit(".", 1)[-1].lower()
                if file.filename and "." in file.filename
                else "m4a"
            )
            key = f"audio/{now.year}/{now.month:02d}/{now.day:02d}/{uuid.uuid4().hex}.{ext}"

            content = await file.read()
            print(f"[OSS] 上传到key: {key}, 大小: {len(content)} bytes")
            self.bucket.put_object(key, content)
            
            url = f"https://{self.bucket_name}.{self.endpoint}/{key}"
            print(f"[OSS] 上传成功: {url}")
            return url
        except Exception as e:
            print(f"[OSS] 上传失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_signed_url(self, url: str, expires: int = 3600) -> str:
        """生成私有 Bucket 的临时签名 URL（默认 1 小时有效）"""
        try:
            self._ensure_bucket()
            prefix = f"https://{self.bucket_name}.{self.endpoint}/"
            if url.startswith(prefix):
                key = url[len(prefix):]
                print(f"[OSS] 生成签名URL: key={key}, expires={expires}")
                signed = self.bucket.sign_url("GET", key, expires)
                return signed
            return url
        except Exception as e:
            print(f"[OSS] 生成签名URL失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def delete(self, url: str) -> None:
        """从 OSS 删除音频文件"""
        try:
            self._ensure_bucket()
            prefix = f"https://{self.bucket_name}.{self.endpoint}/"
            if url.startswith(prefix):
                key = url[len(prefix):]
                print(f"[OSS] 删除音频: key={key}")
                self.bucket.delete_object(key)
        except Exception as e:
            print(f"[OSS] 删除音频失败: {type(e).__name__}: {e}")


# 模块级单例
oss_service = OSSService()
