"""
Diting 数据库维护工具 CLI

用法：
    python -m diting.cli.db_tool vacuum
    python -m diting.cli.db_tool analyze
    python -m diting.cli.db_tool archive --days 90
    python -m diting.cli.db_tool health
    python -m diting.cli.db_tool rebuild
"""

import argparse
import sys

from ..config import Config
from ..db_maintenance import DatabaseMaintenance


def main():
    config = Config()
    db_path = config.db_path

    parser = argparse.ArgumentParser(description="Diting 数据库维护工具")
    parser.add_argument(
        "--db", default=db_path, help="数据库路径（默认: ~/.diting/memory.db）"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("vacuum", help="压缩数据库")
    subparsers.add_parser("analyze", help="分析数据库统计")

    archive_parser = subparsers.add_parser("archive", help="归档过期数据")
    archive_parser.add_argument(
        "--days", type=int, default=90, help="保留天数（默认: 90）"
    )

    subparsers.add_parser("health", help="健康检查")
    subparsers.add_parser("rebuild", help="重建 FTS 索引")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    maintenance = DatabaseMaintenance(args.db)

    if args.command == "vacuum":
        result = maintenance.vacuum()
        print(f"压缩完成: 节省 {result['saved_mb']:.2f}MB ({result['saved_percent']:.1f}%)")

    elif args.command == "analyze":
        result = maintenance.analyze()
        print(f"总记录数: {result['total_records']}")
        print(f"数据库大小: {result['db_size_mb']:.2f}MB")
        print(f"表数量: {result['file_count']}")
        for table, count in result["tables"].items():
            print(f"  {table}: {count} 条")

    elif args.command == "archive":
        result = maintenance.archive_expired(args.days)
        print(f"归档完成: 归档 {result['total_archived']} 条记录到 archived_* 表")
        print(f"  保留天数: {result['retention_days']}")
        for key, value in result.items():
            if key.endswith("_archived") and key != "total_archived":
                print(f"  {key}: {value}")

    elif args.command == "health":
        result = maintenance.health_check()
        print(f"数据库大小: {result['db_size_mb']:.2f}MB")
        print(f"表数量: {result['table_count']}")
        status = "✅ 正常" if result["healthy"] else "❌ 有问题"
        print(f"健康状态: {status}")
        for issue in result["issues"]:
            print(f"  ⚠️ {issue}")

    elif args.command == "rebuild":
        result = maintenance.rebuild_fts_index()
        print(f"重建完成: {result['table_count']} 个 FTS 表")
        for table in result["rebuilt_tables"]:
            print(f"  {table}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
