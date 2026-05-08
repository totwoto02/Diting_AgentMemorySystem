"""
完整性校验模块

计算备份目录的 MD5 校验和，用于验证备份完整性。
"""

import hashlib
import json
import os


class IntegrityChecker:
    """备份完整性校验器"""

    def calculate_checksum(self, path: str) -> str:
        """
        计算目录的 MD5 校验和

        遍历目录下所有文件（排序保证一致性），逐块计算 MD5。

        Args:
            path: 目录路径

        Returns:
            MD5 校验和字符串
        """
        md5 = hashlib.md5()
        for root, dirs, files in os.walk(path):
            for file in sorted(files):
                if file == "metadata.json":
                    continue
                filepath = os.path.join(root, file)
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        md5.update(chunk)
        return md5.hexdigest()

    def verify(self, backup_path: str) -> bool:
        """
        验证备份完整性

        读取 metadata.json 中的校验和，与当前计算结果对比。

        Args:
            backup_path: 备份目录路径

        Returns:
            校验通过返回 True，否则返回 False
        """
        metadata_path = os.path.join(backup_path, "metadata.json")
        if not os.path.exists(metadata_path):
            return False

        with open(metadata_path) as f:
            metadata = json.load(f)

        current_checksum = self.calculate_checksum(backup_path)
        return current_checksum == metadata.get("checksum")
