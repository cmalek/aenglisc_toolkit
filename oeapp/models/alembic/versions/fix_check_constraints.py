"""
Fix CHECK constraints to match model definitions

Revision ID: fix_check_constraints
Revises: 58e7d5ea71cd
Create Date: 2025-11-30 20:40:00.000000

"""

import re
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "fix_check_constraints"
down_revision: "str | Sequence[str] | None" = "58e7d5ea71cd"
branch_labels: "str | Sequence[str] | None" = None
depends_on: "str | Sequence[str] | None" = None


def upgrade() -> None:
    """
    Upgrade schema - update CHECK constraints to match model definitions.

    SQLite doesn't support ALTER TABLE DROP CONSTRAINT for CHECK constraints,
    so we need to recreate the table with the updated constraints.
    """
    # SQLite requires recreating the table to change CHECK constraints
    # We'll use raw SQL to recreate the table with updated constraints
    # Get the current table structure and modify the constraints
    conn = op.get_bind()

    # Read current table schema
    result = conn.execute(
        sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='annotations'"
        )
    )
    old_sql = result.scalar()

    if old_sql:
        # Replace the old constraint definitions with new ones using regex
        # to handle whitespace variations
        new_sql = old_sql

        # Update verb_form constraint: add 'ii'
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_form CHECK \(verb_form IN \('f','i','p'\)\)",
            "CONSTRAINT ck_annotations_verb_form CHECK (verb_form IN ('f','i','p','ii'))",
            new_sql,
        )

        # Update verb_class constraint: add 'pp' (before 's1')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_class CHECK \(verb_class IN \('a','w1','w2','w3','s1'",
            "CONSTRAINT ck_annotations_verb_class CHECK (verb_class IN ('a','w1','w2','w3','pp','s1'",
            new_sql,
        )

        # Update verb_person constraint: remove 'pl'
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_person CHECK \(verb_person IN \('1','2','3','pl'\)\)",
            "CONSTRAINT ck_annotations_verb_person CHECK (verb_person IN ('1','2','3'))",
            new_sql,
        )

        # Update prep_case constraint: add 'i'
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_prep_case CHECK \(prep_case IN \('a','d','g'\)\)",
            "CONSTRAINT ck_annotations_prep_case CHECK (prep_case IN ('a','d','g','i'))",
            new_sql,
        )

        # Update pronoun_type constraint: add 'rx' after 'p' and 'm' at the end
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_pronoun_type CHECK \(pronoun_type IN \('p','r','d','i'\)\)",
            "CONSTRAINT ck_annotations_pronoun_type CHECK (pronoun_type IN ('p','rx','r','d','i','m'))",
            new_sql,
        )

        # Recreate the table with new constraints
        # Step 1: Create new table
        new_table_name = "annotations_new"
        new_sql = new_sql.replace(
            "CREATE TABLE annotations", f"CREATE TABLE {new_table_name}"
        )
        conn.execute(sa.text(new_sql))

        # Step 2: Copy data using explicit column names to avoid column order issues
        # Get column names from the old table and quote them (case is a reserved keyword)
        columns_result = conn.execute(sa.text("PRAGMA table_info(annotations)"))
        column_names = [row[1] for row in columns_result]
        # Quote all column names to handle reserved keywords like "case"
        quoted_columns = [f'"{col}"' for col in column_names]
        columns_str = ", ".join(quoted_columns)

        conn.execute(
            sa.text(f"""
            INSERT INTO {new_table_name} ({columns_str})
            SELECT {columns_str} FROM annotations
        """)
        )

        # Step 3: Drop old table
        conn.execute(sa.text("DROP TABLE annotations"))

        # Step 4: Rename new table
        conn.execute(sa.text(f"ALTER TABLE {new_table_name} RENAME TO annotations"))

        # Step 5: Recreate indexes (if they don't already exist)
        # Check if indexes exist first to avoid errors
        indexes_result = conn.execute(
            sa.text("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN ('idx_annotations_pos', 'idx_annotations_uncertain')
        """)
        )
        existing_indexes = {row[0] for row in indexes_result}

        if "idx_annotations_pos" not in existing_indexes:
            conn.execute(
                sa.text("CREATE INDEX idx_annotations_pos ON annotations(pos)")
            )
        if "idx_annotations_uncertain" not in existing_indexes:
            conn.execute(
                sa.text(
                    "CREATE INDEX idx_annotations_uncertain ON annotations(uncertain)"
                )
            )

        # Note: Alembic handles transaction commits, so we don't need conn.commit()


def downgrade() -> None:
    """
    Downgrade schema - revert to old constraint definitions.
    """
    conn = op.get_bind()

    # Read current table schema
    result = conn.execute(
        sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='annotations'"
        )
    )
    old_sql = result.scalar()

    if old_sql:
        new_sql = old_sql

        # Revert verb_form constraint (remove 'ii')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_form CHECK \(verb_form IN \('f','i','p','ii'\)\)",
            "CONSTRAINT ck_annotations_verb_form CHECK (verb_form IN ('f','i','p'))",
            new_sql,
        )

        # Revert verb_class constraint (remove 'pp')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_class CHECK \(verb_class IN \('a','w1','w2','w3','pp','s1'",
            "CONSTRAINT ck_annotations_verb_class CHECK (verb_class IN ('a','w1','w2','w3','s1'",
            new_sql,
        )

        # Revert verb_person constraint (add 'pl')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_verb_person CHECK \(verb_person IN \('1','2','3'\)\)",
            "CONSTRAINT ck_annotations_verb_person CHECK (verb_person IN ('1','2','3','pl'))",
            new_sql,
        )

        # Revert prep_case constraint (remove 'i')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_prep_case CHECK \(prep_case IN \('a','d','g','i'\)\)",
            "CONSTRAINT ck_annotations_prep_case CHECK (prep_case IN ('a','d','g'))",
            new_sql,
        )

        # Revert pronoun_type constraint (remove 'rx' and 'm')
        new_sql = re.sub(
            r"CONSTRAINT ck_annotations_pronoun_type CHECK \(pronoun_type IN \('p','rx','r','d','i','m'\)\)",
            "CONSTRAINT ck_annotations_pronoun_type CHECK (pronoun_type IN ('p','r','d','i'))",
            new_sql,
        )

        # Recreate the table with old constraints
        new_table_name = "annotations_old"
        new_sql = new_sql.replace(
            "CREATE TABLE annotations", f"CREATE TABLE {new_table_name}"
        )
        conn.execute(sa.text(new_sql))

        # Copy data using explicit column names (quote to handle reserved keywords)
        columns_result = conn.execute(sa.text("PRAGMA table_info(annotations)"))
        column_names = [row[1] for row in columns_result]
        # Quote all column names to handle reserved keywords like "case"
        quoted_columns = [f'"{col}"' for col in column_names]
        columns_str = ", ".join(quoted_columns)

        conn.execute(
            sa.text(f"""
            INSERT INTO {new_table_name} ({columns_str})
            SELECT {columns_str} FROM annotations
        """)
        )

        # Drop current table
        conn.execute(sa.text("DROP TABLE annotations"))

        # Rename
        conn.execute(sa.text(f"ALTER TABLE {new_table_name} RENAME TO annotations"))

        # Recreate indexes (if they don't already exist)
        indexes_result = conn.execute(
            sa.text("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN ('idx_annotations_pos', 'idx_annotations_uncertain')
        """)
        )
        existing_indexes = {row[0] for row in indexes_result}

        if "idx_annotations_pos" not in existing_indexes:
            conn.execute(
                sa.text("CREATE INDEX idx_annotations_pos ON annotations(pos)")
            )
        if "idx_annotations_uncertain" not in existing_indexes:
            conn.execute(
                sa.text(
                    "CREATE INDEX idx_annotations_uncertain ON annotations(uncertain)"
                )
            )

        # Note: Alembic handles transaction commits, so we don't need conn.commit()
