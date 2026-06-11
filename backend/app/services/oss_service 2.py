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
            auth = self._create_auth()
            self.bucket = oss2.Bucket(
                auth, f"https://{self.endpoint}", self.bucket_name, region=self.region
            )
        except Exception as e:
            print(f"[OSS] 初始化失败（音频功能不可用）: {e}")
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
                ecs_metadata_url = (
                    "http://100.100.100.200/latest/meta-data/"
                    f"ram/security-credentials/{self.ram_role_name}"
                )
                credentials = oss2.credentials.EcsRamRoleCredentialsProvider(
                    ecs_metadata_url
                )
                return oss2.ProviderAuthV4(credentials)
            except Exception as e:
                print(f"[OSS] ECS RAM 角色认证失败，回落 AccessKey: {e}")

        # 2. 回落 AccessKey（开发环境）
        ak = os.getenv("OSS_ACCESS_KEY_ID")
        sk = os.getenv("OSS_ACCESS_KEY_SECRET")
        if ak and sk:
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
        self.bucket.put_object(key, content)

        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    def get_signed_url(self, url: str, expires: int = 3600) -> str:
        """生成私有 Bucket 的临时签名 URL（默认 1 小时有效）"""
        self._ensure_bucket()
        prefix = f"https://{self.bucket_name}.{self.endpoint}/"
        if url.startswith(prefix):
            key = url[len(prefix) :]
            return self.bucket.sign_url("GET", key, expires)
        return url

    def delete(self, url: str) -> None:
        """从 OSS 删除音频文件"""
        self._ensure_bucket()
        prefix = f"https://{self.bucket_name}.{self.endpoint}/"
        if url.startswith(prefix):
            key = url[len(prefix) :]
            self.bucket.delete_object(key)


# 模块级单例
oss_service = OSSService()
