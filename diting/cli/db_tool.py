"""
Diting 数据库维护工具 CLI

用法：
    python -m diting.cli.db_tool vacuum
    python -m diting.cli.db_tool analyze
    python -m diting.cli.db_tool archive --days 90
    python -m diting.cli.db_tool health
    python -m diting.cli.db_tool rebuild
    python -m diting.cli.db_tool cleanup-archived --days 365 [--dry-run] [--force]
"""

import argparse
import os
import sys

from ..config import Config
from ..db_maintenance import DatabaseMaintenance


def _confirm_deletion():
    """双重确认机制"""
    # 第一次确认
    print("\n⚠️  WARNING: This operation will PERMANENTLY delete archived data!")
    print("This action cannot be undone.\n")

    confirm1 = input("Type 'DELETE' to confirm: ")
    if confirm1.strip() != "DELETE":
        print("❌ Confirmation failed. Operation cancelled.")
        return False

    # 第二次确认
    confirm2 = input("Type 'archived_memory' to finalize: ")
    if confirm2.strip() != "archived_memory":
        print("❌ Confirmation failed. Operation cancelled.")
        return False

    return True


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

    # T049: cleanup-archived 子命令
    cleanup_parser = subparsers.add_parser(
        "cleanup-archived", help="清理归档数据（需要双重确认）"
    )
    cleanup_parser.add_argument(
        "--days", type=int, default=365, help="保留天数（默认: 365）"
    )
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="仅预览不删除"
    )
    cleanup_parser.add_argument(
        "--force", action="store_true", help="跳过确认提示"
    )

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

    elif args.command == "cleanup-archived":
        try:
            if args.dry_run:
                result = maintenance.cleanup_archived_data(
                    retention_days=args.days, dry_run=True
                )
                print("\n📋 预览模式（不会删除任何数据）")
                print(f"保留天数: {result['retention_days']}")
                print(f"截止日期: {result['cutoff_date']}")
                print("\n将要清理的记录:")
                for table, count in result["tables"].items():
                    if count > 0:
                        print(f"  {table}: {count} 条")
                print(f"\n总计: {result['total_to_cleanup']} 条")
            else:
                # 安全机制：检测 OpenClaw 环境
                if os.environ.get("OPENCLAW_AGENT"):
                    print("❌ ERROR: OPENCLAW_AGENT environment variable detected.")
                    print("This operation must be triggered by a human user.")
                    return 1

                # 安全机制：双重确认（除非 --force）
                if not args.force:
                    if not _confirm_deletion():
                        return 1

                result = maintenance.cleanup_archived_data(
                    retention_days=args.days, dry_run=False
                )
                print("\n✅ 清理完成")
                print(f"保留天数: {result['retention_days']}")
                print(f"截止日期: {result['cutoff_date']}")
                print("\n已删除记录:")
                for table, count in result["details"].items():
                    if count > 0:
                        print(f"  {table}: {count} 条")
                print(f"\n总计: {result['deleted']} 条")
        except RuntimeError as e:
            print(f"❌ ERROR: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
