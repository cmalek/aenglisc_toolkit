"""
add remembered annotations

Revision ID: f38623b35077
Revises: 82eb5c3ae099
Create Date: 2026-05-15 12:19:33.422684

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f38623b35077"
down_revision: str | Sequence[str] | None = "82eb5c3ae099"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "remembered_annotations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("token_text", sa.String(), nullable=False),
        sa.Column("pos", sa.String(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("number", sa.String(), nullable=True),
        sa.Column("case", sa.String(), nullable=True),
        sa.Column("declension", sa.String(), nullable=True),
        sa.Column("article_type", sa.String(), nullable=True),
        sa.Column("pronoun_type", sa.String(), nullable=True),
        sa.Column("pronoun_number", sa.String(), nullable=True),
        sa.Column("verb_class", sa.String(), nullable=True),
        sa.Column("verb_tense", sa.String(), nullable=True),
        sa.Column("verb_person", sa.String(), nullable=True),
        sa.Column("verb_mood", sa.String(), nullable=True),
        sa.Column("verb_aspect", sa.String(), nullable=True),
        sa.Column("verb_form", sa.String(), nullable=True),
        sa.Column("verb_direct_object_case", sa.String(), nullable=True),
        sa.Column(
            "verb_requires_infinitive",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "verb_impersonal",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "verb_transitivity",
            sa.String(),
            server_default="transitive",
            nullable=False,
        ),
        sa.Column("prep_case", sa.String(), nullable=True),
        sa.Column("adjective_inflection", sa.String(), nullable=True),
        sa.Column("adjective_degree", sa.String(), nullable=True),
        sa.Column("conjunction_type", sa.String(), nullable=True),
        sa.Column("adverb_degree", sa.String(), nullable=True),
        sa.Column("modern_english_meaning", sa.String(), nullable=True),
        sa.Column("root", sa.String(), nullable=True),
        sa.Column("root_normalized", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "pos IN ('N','V','A','R','D','B','C','E','I', 'L')",
            name="ck_remembered_annotations_pos",
        ),
        sa.CheckConstraint(
            "gender IN ('m','f','n')", name="ck_remembered_annotations_gender"
        ),
        sa.CheckConstraint(
            "number IN ('s','p')", name="ck_remembered_annotations_number"
        ),
        sa.CheckConstraint(
            "\"case\" IN ('n','a','g','d','i')",
            name="ck_remembered_annotations_case",
        ),
        sa.CheckConstraint(
            "declension IN ('s','w','o','i','u','ja','jo','wa','wo','pu', 'r', 'i-mut', 'er', 'nd', 'th')",  # noqa: E501
            name="ck_remembered_annotations_declension",
        ),
        sa.CheckConstraint(
            "pronoun_type IN ('p','rx','r','d','i','m','ind')",
            name="ck_remembered_annotations_pronoun_type",
        ),
        sa.CheckConstraint(
            "pronoun_number IN ('s','d','pl')",
            name="ck_remembered_annotations_pronoun_number",
        ),
        sa.CheckConstraint(
            "article_type IN ('d','i','p','D')",
            name="ck_remembered_annotations_article_type",
        ),
        sa.CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','pp','s1','s2','s3','s4','s5','s6','s7')",  # noqa: E501
            name="ck_remembered_annotations_verb_class",
        ),
        sa.CheckConstraint(
            "verb_tense IN ('p','n')", name="ck_remembered_annotations_verb_tense"
        ),
        sa.CheckConstraint(
            "verb_person IN ('1','2','3')",
            name="ck_remembered_annotations_verb_person",
        ),
        sa.CheckConstraint(
            "verb_mood IN ('i','s','imp')",
            name="ck_remembered_annotations_verb_mood",
        ),
        sa.CheckConstraint(
            "verb_aspect IN ('p','f','prg','gn')",
            name="ck_remembered_annotations_verb_aspect",
        ),
        sa.CheckConstraint(
            "verb_form IN ('f','i','p','ii')",
            name="ck_remembered_annotations_verb_form",
        ),
        sa.CheckConstraint(
            "verb_direct_object_case IN ('n', 'a','d','g','i')",
            name="ck_remembered_annotations_verb_direct_object_case",
        ),
        sa.CheckConstraint(
            "verb_transitivity IN ('transitive','intransitive')",
            name="ck_remembered_annotations_verb_transitivity",
        ),
        sa.CheckConstraint(
            "prep_case IN ('a','d','g','i')",
            name="ck_remembered_annotations_prep_case",
        ),
        sa.CheckConstraint(
            "adjective_inflection IN ('s','w')",
            name="ck_remembered_annotations_adjective_inflection",
        ),
        sa.CheckConstraint(
            "adjective_degree IN ('p','c','s')",
            name="ck_remembered_annotations_adjective_degree",
        ),
        sa.CheckConstraint(
            "conjunction_type IN ('c','s')",
            name="ck_remembered_annotations_conjunction_type",
        ),
        sa.CheckConstraint(
            "adverb_degree IN ('p','c','s')",
            name="ck_remembered_annotations_adverb_degree",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_remembered_annotations_project_id",
        "remembered_annotations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "uq_remembered_annotations_global_token_text",
        "remembered_annotations",
        ["token_text"],
        unique=True,
        sqlite_where=sa.text("project_id IS NULL"),
    )
    op.create_index(
        "uq_remembered_annotations_project_token_text",
        "remembered_annotations",
        ["project_id", "token_text"],
        unique=True,
        sqlite_where=sa.text("project_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_remembered_annotations_project_token_text",
        table_name="remembered_annotations",
    )
    op.drop_index(
        "uq_remembered_annotations_global_token_text",
        table_name="remembered_annotations",
    )
    op.drop_index(
        "idx_remembered_annotations_project_id",
        table_name="remembered_annotations",
    )
    op.drop_table("remembered_annotations")
