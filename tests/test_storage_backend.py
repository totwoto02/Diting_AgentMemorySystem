"""
Storage Backend 存储后端测试用例

目标：覆盖率 90%+
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from diting.storage_backend import (
    COSStorage,
    LocalStorage,
    OSSStorage,
    S3Storage,
    StorageBackend,
    StorageManager,
)


class TestLocalStorage:
    """本地存储测试"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建临时存储目录"""
        return LocalStorage(str(tmp_path))

    def test_init_creates_directory(self, tmp_path):
        """测试初始化创建目录"""
        new_dir = tmp_path / "new_storage"
        storage = LocalStorage(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_save_and_load(self, storage):
        """测试保存和加载"""
        data = b"Hello World"

        result_path = storage.save("test.txt", data)

        assert os.path.exists(result_path)
        loaded_data = storage.load("test.txt")
        assert loaded_data == data

    def test_save_creates_parent_directories(self, storage):
        """测试保存时创建父目录"""
        data = b"Nested file"

        result_path = storage.save("nested/dir/file.txt", data)

        assert os.path.exists(result_path)
        assert Path(result_path).parent.exists()

    def test_load_nonexistent_file(self, storage):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            storage.load("nonexistent.txt")

    def test_delete_existing_file(self, storage):
        """测试删除存在的文件"""
        storage.save("to_delete.txt", b"data")

        assert storage.exists("to_delete.txt")

        storage.delete("to_delete.txt")

        assert not storage.exists("to_delete.txt")

    def test_delete_nonexistent_file(self, storage):
        """测试删除不存在的文件（不应抛出异常）"""
        storage.delete("nonexistent.txt")

    def test_exists_true(self, storage):
        """测试文件存在"""
        storage.save("exists.txt", b"data")

        assert storage.exists("exists.txt") is True

    def test_exists_false(self, storage):
        """测试文件不存在"""
        assert storage.exists("not_exists.txt") is False

    def test_save_overwrite(self, storage):
        """测试覆盖已有文件"""
        storage.save("file.txt", b"original")
        storage.save("file.txt", b"overwritten")

        loaded = storage.load("file.txt")
        assert loaded == b"overwritten"

    def test_load_binary_data(self, storage):
        """测试加载二进制数据"""
        data = bytes(range(256))

        storage.save("binary.bin", data)
        loaded = storage.load("binary.bin")

        assert loaded == data

    def test_save_empty_file(self, storage):
        """测试保存空文件"""
        storage.save("empty.txt", b"")

        assert storage.exists("empty.txt")
        loaded = storage.load("empty.txt")
        assert loaded == b""

    def test_unicode_filename(self, storage):
        """测试 Unicode 文件名"""
        storage.save("中文文件.txt", b"data")

        assert storage.exists("中文文件.txt")
        loaded = storage.load("中文文件.txt")
        assert loaded == b"data"

    def test_special_characters_in_path(self, storage):
        """测试路径中的特殊字符"""
        storage.save("file-with_special.chars.txt", b"data")

        assert storage.exists("file-with_special.chars.txt")

    def test_get_url(self, storage, tmp_path):
        """测试获取文件 URL"""
        storage.save("test.txt", b"data")
        url = storage.get_url("test.txt")

        assert url == str(tmp_path / "test.txt")

    def test_list_files(self, storage):
        """测试列出文件"""
        storage.save("a.txt", b"data")
        storage.save("b.txt", b"data")
        storage.save("sub/c.txt", b"data")

        files = storage.list_files()

        assert "a.txt" in files
        assert "b.txt" in files
        assert "sub/c.txt" in files

    def test_list_files_with_prefix(self, storage):
        """测试按前缀列出文件"""
        storage.save("dir1/a.txt", b"data")
        storage.save("dir1/b.txt", b"data")
        storage.save("dir2/c.txt", b"data")

        files = storage.list_files("dir1")

        assert "dir1/a.txt" in files
        assert "dir1/b.txt" in files
        assert "dir2/c.txt" not in files

    def test_list_files_empty(self, storage):
        """测试列出不存在目录的文件"""
        files = storage.list_files("nonexistent")

        assert files == []

    def test_list_files_prefix_single_file(self, storage):
        """测试前缀匹配单个文件"""
        storage.save("target.txt", b"data")

        files = storage.list_files("target.txt")

        assert files == ["target.txt"]


class TestS3Storage:
    """S3 存储测试"""

    @pytest.fixture
    def mock_boto3_client(self):
        """模拟 boto3 客户端"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            yield mock_boto3, mock_client

    @pytest.fixture
    def storage(self):
        """创建 S3 存储实例"""
        return S3Storage({
            "bucket": "test-bucket",
            "region": "us-east-1",
            "access_key": "AK_TEST",
            "secret_key": "SK_TEST",
        })

    def test_init_default_config(self):
        """测试默认配置初始化"""
        storage = S3Storage({})

        assert storage.bucket == "diting-storage"
        assert storage.region == "us-east-1"
        assert storage.access_key is None
        assert storage.secret_key is None

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "bucket": "my-bucket",
            "region": "cn-north-1",
            "access_key": "AK_TEST",
            "secret_key": "SK_TEST",
        }
        storage = S3Storage(config)

        assert storage.bucket == "my-bucket"
        assert storage.region == "cn-north-1"
        assert storage.access_key == "AK_TEST"
        assert storage.secret_key == "SK_TEST"

    def test_init_partial_config(self):
        """测试部分配置初始化"""
        config = {"bucket": "custom-bucket"}
        storage = S3Storage(config)

        assert storage.bucket == "custom-bucket"
        assert storage.region == "us-east-1"

    def test_save(self, storage, mock_boto3_client):
        """测试保存文件"""
        mock_boto3, mock_client = mock_boto3_client

        result = storage.save("test.txt", b"hello")

        assert result == "s3://test-bucket/test.txt"
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt", Body=b"hello"
        )

    def test_load(self, storage, mock_boto3_client):
        """测试加载文件"""
        mock_boto3, mock_client = mock_boto3_client
        mock_response = {"Body": MagicMock()}
        mock_response["Body"].read.return_value = b"file content"
        mock_client.get_object.return_value = mock_response

        result = storage.load("test.txt")

        assert result == b"file content"
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_delete(self, storage, mock_boto3_client):
        """测试删除文件"""
        mock_boto3, mock_client = mock_boto3_client

        storage.delete("test.txt")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_exists_true(self, storage, mock_boto3_client):
        """测试文件存在"""
        mock_boto3, mock_client = mock_boto3_client

        result = storage.exists("test.txt")

        assert result is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_exists_false(self, storage, mock_boto3_client):
        """测试文件不存在"""
        mock_boto3, mock_client = mock_boto3_client
        mock_client.head_object.side_effect = Exception("Not Found")

        result = storage.exists("test.txt")

        assert result is False

    def test_get_url(self, storage, mock_boto3_client):
        """测试获取预签名 URL"""
        mock_boto3, mock_client = mock_boto3_client
        mock_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/test.txt?signed"
        )

        url = storage.get_url("test.txt")

        assert url == "https://s3.amazonaws.com/test-bucket/test.txt?signed"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "test.txt"},
            ExpiresIn=3600,
        )

    def test_list_files(self, storage, mock_boto3_client):
        """测试列出文件"""
        mock_boto3, mock_client = mock_boto3_client
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "dir/a.txt"},
                {"Key": "dir/b.txt"},
            ]
        }

        files = storage.list_files("dir/")

        assert files == ["dir/a.txt", "dir/b.txt"]
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket", Prefix="dir/"
        )

    def test_list_files_empty(self, storage, mock_boto3_client):
        """测试列出空文件列表"""
        mock_boto3, mock_client = mock_boto3_client
        mock_client.list_objects_v2.return_value = {}

        files = storage.list_files()

        assert files == []
        mock_client.list_objects_v2.assert_called_once_with(Bucket="test-bucket")

    def test_get_client_without_credentials(self):
        """测试无凭证时创建客户端"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        storage = S3Storage({"bucket": "test", "region": "us-west-2"})

        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            client = storage._get_client()

        assert client is mock_client
        mock_boto3.client.assert_called_once_with("s3", region_name="us-west-2")


class TestOSSStorage:
    """OSS 存储测试"""

    @pytest.fixture
    def mock_oss2(self):
        """模拟 oss2 模块"""
        mock_oss2 = MagicMock()
        mock_auth = MagicMock()
        mock_bucket = MagicMock()
        mock_oss2.Auth.return_value = mock_auth
        mock_oss2.Bucket.return_value = mock_bucket

        with patch.dict("sys.modules", {"oss2": mock_oss2}):
            yield mock_oss2, mock_auth, mock_bucket

    @pytest.fixture
    def storage(self):
        """创建 OSS 存储实例"""
        return OSSStorage({
            "bucket": "test-oss-bucket",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "access_key_id": "OSS_AK",
            "access_key_secret": "OSS_SK",
        })

    def test_init_default_config(self):
        """测试默认配置初始化"""
        storage = OSSStorage({})

        assert storage.bucket_name == "diting-storage"
        assert storage.endpoint == "oss-cn-hangzhou.aliyuncs.com"
        assert storage.access_key_id is None
        assert storage.access_key_secret is None

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "bucket": "my-oss-bucket",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "access_key_id": "OSS_AK",
            "access_key_secret": "OSS_SK",
        }
        storage = OSSStorage(config)

        assert storage.bucket_name == "my-oss-bucket"
        assert storage.endpoint == "oss-cn-beijing.aliyuncs.com"
        assert storage.access_key_id == "OSS_AK"
        assert storage.access_key_secret == "OSS_SK"

    def test_save(self, storage, mock_oss2):
        """测试保存文件"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2

        result = storage.save("test.txt", b"hello")

        assert result == "oss://test-oss-bucket/test.txt"
        mock_bucket.put_object.assert_called_once_with("test.txt", b"hello")

    def test_load(self, storage, mock_oss2):
        """测试加载文件"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_response = MagicMock()
        mock_response.read.return_value = b"oss content"
        mock_bucket.get_object.return_value = mock_response

        result = storage.load("test.txt")

        assert result == b"oss content"
        mock_bucket.get_object.assert_called_once_with("test.txt")

    def test_delete(self, storage, mock_oss2):
        """测试删除文件"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2

        storage.delete("test.txt")

        mock_bucket.delete_object.assert_called_once_with("test.txt")

    def test_exists_true(self, storage, mock_oss2):
        """测试文件存在"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_bucket.object_exists.return_value = True

        result = storage.exists("test.txt")

        assert result is True
        mock_bucket.object_exists.assert_called_once_with("test.txt")

    def test_exists_false(self, storage, mock_oss2):
        """测试文件不存在"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_bucket.object_exists.return_value = False

        result = storage.exists("test.txt")

        assert result is False

    def test_get_url(self, storage, mock_oss2):
        """测试获取签名 URL"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_bucket.sign_url.return_value = (
            "https://test-oss-bucket.oss-cn-beijing.aliyuncs.com/test.txt?signed"
        )

        url = storage.get_url("test.txt")

        assert "signed" in url
        mock_bucket.sign_url.assert_called_once_with("GET", "test.txt", 3600)

    def test_list_files(self, storage, mock_oss2):
        """测试列出文件"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_obj1 = MagicMock()
        mock_obj1.key = "dir/a.txt"
        mock_obj2 = MagicMock()
        mock_obj2.key = "dir/b.txt"
        mock_result = MagicMock()
        mock_result.object_list = [mock_obj1, mock_obj2]
        mock_bucket.list_objects.return_value = mock_result

        files = storage.list_files("dir/")

        assert files == ["dir/a.txt", "dir/b.txt"]
        mock_bucket.list_objects.assert_called_once_with(prefix="dir/")

    def test_list_files_empty(self, storage, mock_oss2):
        """测试列出空文件列表"""
        mock_oss2_mod, mock_auth, mock_bucket = mock_oss2
        mock_result = MagicMock()
        mock_result.object_list = []
        mock_bucket.list_objects.return_value = mock_result

        files = storage.list_files()

        assert files == []
        mock_bucket.list_objects.assert_called_once_with(prefix="")


class TestCOSStorage:
    """COS 存储测试"""

    @pytest.fixture
    def mock_qcloud_cos(self):
        """模拟 qcloud_cos 模块"""
        mock_cos = MagicMock()
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_cos.CosConfig.return_value = mock_config
        mock_cos.CosS3Client.return_value = mock_client

        with patch.dict("sys.modules", {"qcloud_cos": mock_cos}):
            yield mock_cos, mock_config, mock_client

    @pytest.fixture
    def storage(self):
        """创建 COS 存储实例"""
        return COSStorage({
            "bucket": "test-cos-bucket",
            "region": "ap-guangzhou",
            "secret_id": "COS_ID",
            "secret_key": "COS_KEY",
        })

    def test_init_default_config(self):
        """测试默认配置初始化"""
        storage = COSStorage({})

        assert storage.bucket == "diting-storage"
        assert storage.region == "ap-guangzhou"
        assert storage.secret_id is None
        assert storage.secret_key is None

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "bucket": "my-cos-bucket",
            "region": "ap-shanghai",
            "secret_id": "COS_ID",
            "secret_key": "COS_KEY",
        }
        storage = COSStorage(config)

        assert storage.bucket == "my-cos-bucket"
        assert storage.region == "ap-shanghai"
        assert storage.secret_id == "COS_ID"
        assert storage.secret_key == "COS_KEY"

    def test_save(self, storage, mock_qcloud_cos):
        """测试保存文件"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos

        result = storage.save("test.txt", b"hello")

        assert result == "cos://test-cos-bucket/test.txt"
        mock_client.put_object.assert_called_once_with(
            Bucket="test-cos-bucket", Body=b"hello", Key="test.txt"
        )

    def test_load(self, storage, mock_qcloud_cos):
        """测试加载文件"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos
        mock_body = MagicMock()
        mock_body.get_raw_stream.return_value.read.return_value = b"cos content"
        mock_client.get_object.return_value = {"Body": mock_body}

        result = storage.load("test.txt")

        assert result == b"cos content"
        mock_client.get_object.assert_called_once_with(
            Bucket="test-cos-bucket", Key="test.txt"
        )

    def test_delete(self, storage, mock_qcloud_cos):
        """测试删除文件"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos

        storage.delete("test.txt")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-cos-bucket", Key="test.txt"
        )

    def test_exists_true(self, storage, mock_qcloud_cos):
        """测试文件存在"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos

        result = storage.exists("test.txt")

        assert result is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-cos-bucket", Key="test.txt"
        )

    def test_exists_false(self, storage, mock_qcloud_cos):
        """测试文件不存在"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos
        mock_client.head_object.side_effect = Exception("Not Found")

        result = storage.exists("test.txt")

        assert result is False

    def test_get_url(self, storage, mock_qcloud_cos):
        """测试获取预签名 URL"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos
        mock_client.get_presigned_url.return_value = (
            "https://test-cos-bucket.cos.ap-guangzhou.myqcloud.com/test.txt?signed"
        )

        url = storage.get_url("test.txt")

        assert "signed" in url
        mock_client.get_presigned_url.assert_called_once_with(
            Method="GET", Bucket="test-cos-bucket", Key="test.txt"
        )

    def test_list_files(self, storage, mock_qcloud_cos):
        """测试列出文件"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos
        mock_client.list_objects.return_value = {
            "Contents": [
                {"Key": "dir/a.txt"},
                {"Key": "dir/b.txt"},
            ]
        }

        files = storage.list_files("dir/")

        assert files == ["dir/a.txt", "dir/b.txt"]
        mock_client.list_objects.assert_called_once_with(
            Bucket="test-cos-bucket", Prefix="dir/"
        )

    def test_list_files_empty(self, storage, mock_qcloud_cos):
        """测试列出空文件列表"""
        mock_cos, mock_config, mock_client = mock_qcloud_cos
        mock_client.list_objects.return_value = {}

        files = storage.list_files()

        assert files == []
        mock_client.list_objects.assert_called_once_with(Bucket="test-cos-bucket")


class TestStorageManager:
    """存储管理器测试"""

    def test_init_default_local(self, tmp_path):
        """测试默认本地存储初始化"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        assert isinstance(manager.backend, LocalStorage)

    def test_init_s3_backend(self):
        """测试 S3 后端初始化"""
        config = {
            "backend": "s3",
            "s3": {"bucket": "test-bucket"},
        }
        manager = StorageManager(config)

        assert isinstance(manager.backend, S3Storage)
        assert manager.backend.bucket == "test-bucket"

    def test_init_oss_backend(self):
        """测试 OSS 后端初始化"""
        config = {
            "backend": "oss",
            "oss": {"bucket": "test-oss-bucket"},
        }
        manager = StorageManager(config)

        assert isinstance(manager.backend, OSSStorage)
        assert manager.backend.bucket_name == "test-oss-bucket"

    def test_init_cos_backend(self):
        """测试 COS 后端初始化"""
        config = {
            "backend": "cos",
            "cos": {"bucket": "test-cos-bucket", "region": "ap-beijing"},
        }
        manager = StorageManager(config)

        assert isinstance(manager.backend, COSStorage)
        assert manager.backend.bucket == "test-cos-bucket"
        assert manager.backend.region == "ap-beijing"

    def test_init_default_fallback(self):
        """测试默认回退到本地存储"""
        config = {"backend": "unknown"}
        manager = StorageManager(config)

        assert isinstance(manager.backend, LocalStorage)

    def test_save_and_load(self, tmp_path):
        """测试管理器保存和加载"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        manager.save("test.txt", b"data")
        loaded = manager.load("test.txt")

        assert loaded == b"data"

    def test_delete(self, tmp_path):
        """测试管理器删除"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        manager.save("to_delete.txt", b"data")
        assert manager.exists("to_delete.txt")

        manager.delete("to_delete.txt")
        assert not manager.exists("to_delete.txt")

    def test_exists(self, tmp_path):
        """测试管理器存在检查"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        assert manager.exists("nonexistent.txt") is False
        manager.save("exists.txt", b"data")
        assert manager.exists("exists.txt") is True

    def test_get_url(self, tmp_path):
        """测试管理器获取 URL"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        manager.save("test.txt", b"data")
        url = manager.get_url("test.txt")

        assert url == str(tmp_path / "test.txt")

    def test_list_files(self, tmp_path):
        """测试管理器列出文件"""
        config = {
            "backend": "local",
            "local": {"root_path": str(tmp_path)},
        }
        manager = StorageManager(config)

        manager.save("a.txt", b"data")
        manager.save("b.txt", b"data")

        files = manager.list_files()

        assert "a.txt" in files
        assert "b.txt" in files


class TestStorageBackendAbstract:
    """抽象基类测试"""

    def test_abstract_methods(self):
        """测试抽象方法必须实现"""
        with pytest.raises(TypeError):
            StorageBackend()

    def test_concrete_implementation(self, tmp_path):
        """测试具体实现"""
        storage = LocalStorage(str(tmp_path))

        storage.save("test.txt", b"data")
        data = storage.load("test.txt")
        assert data == b"data"
        assert storage.exists("test.txt")
        storage.delete("test.txt")
        assert not storage.exists("test.txt")
        assert storage.get_url("test.txt") == str(tmp_path / "test.txt")
        assert storage.list_files() == []


class TestStorageManagerEdgeCases:
    """StorageManager 边界测试"""

    def test_init_empty_config(self):
        """测试空配置初始化"""
        manager = StorageManager({})

        assert isinstance(manager.backend, LocalStorage)

    def test_init_none_config(self):
        """测试 None 配置初始化"""
        manager = StorageManager(None)

        assert isinstance(manager.backend, LocalStorage)
