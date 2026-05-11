"""
对象存储后端

支持本地文件系统、S3、OSS、COS 等多种存储后端
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    def save(self, file_path: str, data: bytes) -> str:
        """保存文件，返回访问 URL"""
        pass

    @abstractmethod
    def load(self, file_path: str) -> bytes:
        """加载文件"""
        pass

    @abstractmethod
    def delete(self, file_path: str):
        """删除文件"""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """获取文件访问 URL"""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """列出指定前缀的文件"""
        pass


class LocalStorage(StorageBackend):
    """本地文件存储"""

    def __init__(self, root_path: str):
        """
        初始化本地存储

        Args:
            root_path: 存储根目录
        """
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def save(self, file_path: str, data: bytes) -> str:
        """保存文件"""
        full_path = self.root_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(data)

        return str(full_path)

    def load(self, file_path: str) -> bytes:
        """加载文件"""
        full_path = self.root_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, file_path: str):
        """删除文件"""
        full_path = self.root_path / file_path

        if full_path.exists():
            full_path.unlink()

    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self.root_path / file_path
        return full_path.exists()

    def get_url(self, file_path: str) -> str:
        """获取文件的完整文件系统路径"""
        return str(self.root_path / file_path)

    def list_files(self, prefix: str = "") -> List[str]:
        """列出指定前缀的文件"""
        result: List[str] = []
        search_path = self.root_path / prefix if prefix else self.root_path

        if not search_path.exists():
            return result

        if search_path.is_file():
            return [prefix] if prefix else [search_path.name]

        for file_path in sorted(search_path.rglob("*")):
            if file_path.is_file():
                relative = file_path.relative_to(self.root_path)
                result.append(str(relative))

        return result


class S3Storage(StorageBackend):
    """AWS S3 存储"""

    def __init__(self, config: Dict):
        """
        初始化 S3 存储

        Args:
            config: S3 配置 {bucket, region, access_key, secret_key}
        """
        self.bucket = config.get("bucket", "diting-storage")
        self.region = config.get("region", "us-east-1")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self._client = None

    def _get_client(self):
        """懒加载获取 boto3 S3 客户端"""
        if self._client is None:
            import boto3

            kwargs: Dict = {"region_name": self.region}
            if self.access_key and self.secret_key:
                kwargs["aws_access_key_id"] = self.access_key
                kwargs["aws_secret_access_key"] = self.secret_key
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def save(self, file_path: str, data: bytes) -> str:
        """保存文件到 S3"""
        client = self._get_client()
        client.put_object(Bucket=self.bucket, Key=file_path, Body=data)
        return f"s3://{self.bucket}/{file_path}"

    def load(self, file_path: str) -> bytes:
        """从 S3 加载文件"""
        client = self._get_client()
        response = client.get_object(Bucket=self.bucket, Key=file_path)
        return response["Body"].read()

    def delete(self, file_path: str):
        """删除 S3 文件"""
        client = self._get_client()
        client.delete_object(Bucket=self.bucket, Key=file_path)

    def exists(self, file_path: str) -> bool:
        """检查 S3 文件是否存在"""
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        """生成 S3 预签名 URL"""
        client = self._get_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": file_path},
            ExpiresIn=3600,
        )
        return url

    def list_files(self, prefix: str = "") -> List[str]:
        """列出 S3 指定前缀的文件"""
        client = self._get_client()
        kwargs: Dict = {"Bucket": self.bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        response = client.list_objects_v2(**kwargs)
        return [obj["Key"] for obj in response.get("Contents", [])]


class OSSStorage(StorageBackend):
    """阿里云 OSS 存储"""

    def __init__(self, config: Dict):
        """
        初始化 OSS 存储

        Args:
            config: OSS 配置 {bucket, endpoint, access_key_id, access_key_secret}
        """
        self.bucket_name = config.get("bucket", "diting-storage")
        self.endpoint = config.get("endpoint", "oss-cn-hangzhou.aliyuncs.com")
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self._bucket = None

    def _get_bucket(self):
        """懒加载获取 oss2 Bucket 对象"""
        if self._bucket is None:
            import oss2

            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        return self._bucket

    def save(self, file_path: str, data: bytes) -> str:
        """保存文件到 OSS"""
        bucket = self._get_bucket()
        bucket.put_object(file_path, data)
        return f"oss://{self.bucket_name}/{file_path}"

    def load(self, file_path: str) -> bytes:
        """从 OSS 加载文件"""
        bucket = self._get_bucket()
        response = bucket.get_object(file_path)
        return response.read()

    def delete(self, file_path: str):
        """删除 OSS 文件"""
        bucket = self._get_bucket()
        bucket.delete_object(file_path)

    def exists(self, file_path: str) -> bool:
        """检查 OSS 文件是否存在"""
        bucket = self._get_bucket()
        return bucket.object_exists(file_path)

    def get_url(self, file_path: str) -> str:
        """生成 OSS 签名 URL"""
        bucket = self._get_bucket()
        url = bucket.sign_url("GET", file_path, 3600)
        return url

    def list_files(self, prefix: str = "") -> List[str]:
        """列出 OSS 指定前缀的文件"""
        bucket = self._get_bucket()
        result = bucket.list_objects(prefix=prefix)
        return [obj.key for obj in result.object_list]


class COSStorage(StorageBackend):
    """腾讯云 COS 存储"""

    def __init__(self, config: Dict):
        """
        初始化 COS 存储

        Args:
            config: COS 配置 {bucket, region, secret_id, secret_key}
        """
        self.bucket = config.get("bucket", "diting-storage")
        self.region = config.get("region", "ap-guangzhou")
        self.secret_id = config.get("secret_id")
        self.secret_key = config.get("secret_key")
        self._client = None

    def _get_client(self):
        """懒加载获取 COS 客户端"""
        if self._client is None:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            self._client = CosS3Client(cos_config)
        return self._client

    def save(self, file_path: str, data: bytes) -> str:
        """保存文件到 COS"""
        client = self._get_client()
        client.put_object(Bucket=self.bucket, Body=data, Key=file_path)
        return f"cos://{self.bucket}/{file_path}"

    def load(self, file_path: str) -> bytes:
        """从 COS 加载文件"""
        client = self._get_client()
        response = client.get_object(Bucket=self.bucket, Key=file_path)
        return response["Body"].get_raw_stream().read()

    def delete(self, file_path: str):
        """删除 COS 文件"""
        client = self._get_client()
        client.delete_object(Bucket=self.bucket, Key=file_path)

    def exists(self, file_path: str) -> bool:
        """检查 COS 文件是否存在"""
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        """生成 COS 预签名 URL"""
        client = self._get_client()
        url = client.get_presigned_url(
            Method="GET", Bucket=self.bucket, Key=file_path
        )
        return url

    def list_files(self, prefix: str = "") -> List[str]:
        """列出 COS 指定前缀的文件"""
        client = self._get_client()
        kwargs: Dict = {"Bucket": self.bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        response = client.list_objects(**kwargs)
        return [obj["Key"] for obj in response.get("Contents", [])]


class StorageManager:
    """存储管理器"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化存储管理器

        Args:
            config: 存储配置
        """
        self.config: Dict = config or {}
        self.backend = self._create_backend()

    def _create_backend(self) -> StorageBackend:
        """创建存储后端"""
        backend_type = self.config.get("backend", "local")

        if backend_type == "local":
            root_path = self.config.get("local", {}).get(
                "root_path", "/tmp/diting-storage"
            )
            return LocalStorage(root_path)

        elif backend_type == "s3":
            s3_config = self.config.get("s3", {})
            return S3Storage(s3_config)

        elif backend_type == "oss":
            oss_config = self.config.get("oss", {})
            return OSSStorage(oss_config)

        elif backend_type == "cos":
            cos_config = self.config.get("cos", {})
            return COSStorage(cos_config)

        else:
            # 默认本地存储
            return LocalStorage("/tmp/diting-storage")

    def save(self, file_path: str, data: bytes) -> str:
        """保存文件"""
        return self.backend.save(file_path, data)

    def load(self, file_path: str) -> bytes:
        """加载文件"""
        return self.backend.load(file_path)

    def delete(self, file_path: str):
        """删除文件"""
        self.backend.delete(file_path)

    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return self.backend.exists(file_path)

    def get_url(self, file_path: str) -> str:
        """获取文件访问 URL"""
        return self.backend.get_url(file_path)

    def list_files(self, prefix: str = "") -> List[str]:
        """列出指定前缀的文件"""
        return self.backend.list_files(prefix)


# 使用示例
if __name__ == "__main__":
    import tempfile

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    # 创建存储管理器
    config = {"backend": "local", "local": {"root_path": temp_dir}}
    storage = StorageManager(config)

    print("✅ 存储管理器初始化成功")

    # 测试保存
    data = b"Hello, World!"
    path = storage.save("test/file.txt", data)
    print(f"✅ 保存文件：{path}")

    # 测试加载
    loaded_data = storage.load("test/file.txt")
    assert loaded_data == data
    print(f"✅ 加载文件：{loaded_data}")

    # 测试存在检查
    exists = storage.exists("test/file.txt")
    assert exists
    print(f"✅ 文件存在：{exists}")

    # 测试删除
    storage.delete("test/file.txt")
    exists = storage.exists("test/file.txt")
    assert not exists
    print(f"✅ 删除文件：{exists}")

    # 清理
    shutil.rmtree(temp_dir)
