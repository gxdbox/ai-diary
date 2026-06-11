#!/usr/bin/env python3
"""
存量重复实体合并脚本

识别并合并 characters 表中的重复人物，将别名记录到 character_aliases 表。

运行方式：
    cd backend && python -m scripts.merge_duplicate_entities

安全：只读模式（--dry-run 默认），传入 --apply 才真正执行写入。
"""
import argparse
import logging
import sys
from datetime import datetime
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, '.')
from app.db.database import SYNC_DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 亲属称谓 — 如果不确定是否同一个人，保持谨慎
KINSHIP_TERMS = {"儿子", "女儿", "爸爸", "妈妈", "老爸", "老妈",
                 "爷爷", "奶奶", "外公", "外婆", "老公", "老婆",
                 "丈夫", "妻子", "哥哥", "弟弟", "姐姐", "妹妹",
                 "表哥", "表弟", "表姐", "表妹", "表哥", "表弟",
                 "侄子", "侄女", "舅舅", "阿姨", "叔叔", "姑姑",
                 "岳父", "岳母", "公公", "婆婆"}


def char_overlap(a: str, b: str) -> float:
    """计算两个字符串的字符重叠率"""
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def is_related(a: str, b: str) -> bool:
    """判断两个名称是否可能指向同一实体"""
    if a == b:
        return False
    if len(a) <= 1 or len(b) <= 1:
        return False
    if a in KINSHIP_TERMS and b in KINSHIP_TERMS:
        return False
    # 子串包含
    if a in b or b in a:
        return True
    # 字符重叠率 >= 40%
    if char_overlap(a, b) >= 0.4:
        return True
    return False


def find_duplicates(db: Session):
    """找出可能的重复人物组"""
    result = db.execute(
        text("SELECT id, name, appearance_count FROM characters ORDER BY appearance_count DESC")
    )
    rows = result.fetchall()

    if not rows:
        logger.info("数据库中无人物数据")
        return []

    logger.info(f"共 {len(rows)} 个人物，开始识别重复...")

    # 构建相似度图
    candidates = {}
    for row in rows:
        candidates[row.id] = {"name": row.name, "count": row.appearance_count}

    # 找出相似对
    pairs = []
    char_ids = list(candidates.keys())
    for i in range(len(char_ids)):
        for j in range(i + 1, len(char_ids)):
            a_id, b_id = char_ids[i], char_ids[j]
            name_a, name_b = candidates[a_id]["name"], candidates[b_id]["name"]
            if is_related(name_a, name_b):
                pairs.append((a_id, b_id, name_a, name_b))

    # 用并查集合并连通分量
    parent = {cid: cid for cid in char_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for a_id, b_id, _, _ in pairs:
        union(a_id, b_id)

    groups = defaultdict(list)
    for cid in char_ids:
        groups[find(cid)].append(cid)

    result_groups = []
    for root_id, member_ids in groups.items():
        if len(member_ids) < 2:
            continue
        members = []
        for mid in member_ids:
            members.append({
                "id": mid,
                "name": candidates[mid]["name"],
                "count": candidates[mid]["count"]
            })
        # 降序排列（出现次数多的在前面）
        members.sort(key=lambda x: x["count"], reverse=True)
        result_groups.append(members)

    return result_groups


def merge_group(db: Session, members: list, dry_run: bool):
    """
    合并一组重复人物

    members: 按出现次数降序排列，第一个为 canonical
    """
    canonical = members[0]
    canonical_id = canonical["id"]
    aliases = members[1:]  # 剩下的都是别名

    logger.info(f"  合并目标: {canonical['name']}(id={canonical_id}, count={canonical['count']})")

    for alias in aliases:
        alias_id = alias["id"]

        # 检查重名行是否已被删（脚本重跑安全）
        row = db.execute(
            text("SELECT id FROM characters WHERE id = :id"),
            {"id": alias_id}
        ).fetchone()
        if not row:
            logger.info(f"    [跳过] 别名 {alias['name']}(id={alias_id}) 已不存在")
            continue

        logger.info(f"    别名: {alias['name']}(id={alias_id}, count={alias['count']})")
        if dry_run:
            continue

        # 1. 记录别名
        existing_alias = db.execute(
            text("SELECT id FROM character_aliases WHERE alias = :alias AND character_id = :cid"),
            {"alias": alias["name"], "cid": canonical_id}
        ).fetchone()
        if not existing_alias:
            db.execute(
                text("""
                    INSERT INTO character_aliases (character_id, alias, source, confidence, created_at)
                    VALUES (:cid, :alias, 'manual', 1.0, :now)
                """),
                {
                    "cid": canonical_id,
                    "alias": alias["name"],
                    "now": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"      → 添加别名记录")

        # 2. 迁移 relationships（别名角色作 A）
        db.execute(
            text("""
                UPDATE relationships SET character_a_id = :canonical_id
                WHERE character_a_id = :alias_id AND character_a_id != character_b_id
            """),
            {"canonical_id": canonical_id, "alias_id": alias_id}
        )

        # 3. 迁移 relationships（别名角色作 B）
        db.execute(
            text("""
                UPDATE relationships SET character_b_id = :canonical_id
                WHERE character_b_id = :alias_id AND character_a_id != character_b_id
            """),
            {"canonical_id": canonical_id, "alias_id": alias_id}
        )

        # 4. 删除可能出现的自引用关系 (A=A)
        db.execute(
            text("""
                DELETE FROM relationships
                WHERE character_a_id = character_b_id
                  AND character_a_id = :canonical_id
            """),
            {"canonical_id": canonical_id}
        )

        # 5. 合并出现次数
        db.execute(
            text("""
                UPDATE characters
                SET appearance_count = appearance_count + :alias_count,
                    updated_at = :now
                WHERE id = :canonical_id
            """),
            {
                "alias_count": alias["count"],
                "canonical_id": canonical_id,
                "now": datetime.utcnow().isoformat()
            }
        )

        # 6. 删除重复角色行
        db.execute(
            text("DELETE FROM characters WHERE id = :id"),
            {"id": alias_id}
        )

        logger.info(f"      ✓ 合并完成")

    if not dry_run:
        db.commit()
        logger.info(f"  ✓ 组提交完成")


def main():
    parser = argparse.ArgumentParser(description="合并重复人物实体")
    parser.add_argument("--apply", action="store_true",
                        help="实际执行合并（默认 dry-run）")
    parser.add_argument("--group-threshold", type=int, default=2,
                        help="组内最少成员数才被视为重复（默认 2）")
    args = parser.parse_args()

    engine = create_engine(SYNC_DATABASE_URL, echo=False)
    db = Session(bind=engine)

    try:
        groups = find_duplicates(db)
        logger.info(f"发现 {len(groups)} 组重复人物")

        if not groups:
            logger.info("没有需要合并的重复人物")
            return

        for i, members in enumerate(groups, 1):
            print(f"\n组 #{i}:")
            for m in members:
                print(f"  - {m['name']} (id={m['id']}, count={m['count']})")

        if args.apply:
            print("\n" + "=" * 60)
            confirm = input("确认执行合并？此操作不可逆！(yes/no): ")
            if confirm.lower() != "yes":
                print("取消合并")
                return

            for members in groups:
                merge_group(db, members, dry_run=False)
            logger.info(f"全部合并完成！")
        else:
            print(f"\n[Dry-Run] 使用 --apply 参数执行实际合并")
            for members in groups:
                merge_group(db, members, dry_run=True)

    finally:
        db.close()


if __name__ == "__main__":
    main()
