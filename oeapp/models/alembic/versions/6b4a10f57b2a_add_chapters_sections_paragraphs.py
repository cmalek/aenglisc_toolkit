"""add_chapters_sections_paragraphs

Revision ID: 6b4a10f57b2a
Revises: da1c8ae30409
Create Date: 2026-01-31 19:56:46.090798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b4a10f57b2a'
down_revision: Union[str, Sequence[str], None] = 'da1c8ae30409'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create new tables
    op.create_table('chapters',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sections',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('chapter_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('paragraphs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('section_id', sa.Integer(), nullable=False),
    sa.Column('order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Add paragraph_id to sentences (nullable initially for migration)
    with op.batch_alter_table('sentences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('paragraph_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_sentences_paragraph_id', 'paragraphs', ['paragraph_id'], ['id'], ondelete='CASCADE')

    # Data migration
    connection = op.get_bind()
    
    # Get all projects
    projects = connection.execute(sa.text("SELECT id FROM projects")).fetchall()
    
    for project in projects:
        project_id = project[0]
        
        # Create one chapter for the project
        connection.execute(
            sa.text("INSERT INTO chapters (project_id, number) VALUES (:project_id, 1)"),
            {"project_id": project_id}
        )
        chapter_id = connection.execute(sa.text("SELECT last_insert_rowid()")).scalar()
        
        # Create one section for the chapter
        connection.execute(
            sa.text("INSERT INTO sections (chapter_id, number) VALUES (:chapter_id, 1)"),
            {"chapter_id": chapter_id}
        )
        section_id = connection.execute(sa.text("SELECT last_insert_rowid()")).scalar()
        
        # Get all sentences for this project, ordered by display_order
        sentences = connection.execute(
            sa.text("SELECT id, is_paragraph_start FROM sentences WHERE project_id = :project_id ORDER BY display_order"),
            {"project_id": project_id}
        ).fetchall()
        
        current_paragraph_id = None
        paragraph_order = 0
        
        for sentence_id, is_paragraph_start in sentences:
            # Create a new paragraph if is_paragraph_start is True or if it's the first sentence
            if is_paragraph_start or current_paragraph_id is None:
                paragraph_order += 1
                connection.execute(
                    sa.text("INSERT INTO paragraphs (section_id, [order]) VALUES (:section_id, :order)"),
                    {"section_id": section_id, "order": paragraph_order}
                )
                current_paragraph_id = connection.execute(sa.text("SELECT last_insert_rowid()")).scalar()
            
            # Assign the sentence to the current paragraph
            connection.execute(
                sa.text("UPDATE sentences SET paragraph_id = :paragraph_id WHERE id = :id"),
                {"paragraph_id": current_paragraph_id, "id": sentence_id}
            )

    # Finalize schema changes: drop old columns and constraints
    with op.batch_alter_table('sentences', schema=None) as batch_op:
        batch_op.drop_constraint('uq_sentences_paragraph_sentence', type_='unique')
        batch_op.drop_column('paragraph_number')
        batch_op.drop_column('is_paragraph_start')
        batch_op.drop_column('sentence_number_in_paragraph')


def downgrade() -> None:
    """Downgrade schema."""
    # Restore old columns to sentences
    with op.batch_alter_table('sentences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sentence_number_in_paragraph', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('is_paragraph_start', sa.BOOLEAN(), nullable=True))
        batch_op.add_column(sa.Column('paragraph_number', sa.INTEGER(), nullable=True))
    
    # Data migration back (approximate)
    connection = op.get_bind()
    
    # This is a complex downgrade, we'll try to restore the numbers
    # based on the new hierarchy
    sentences = connection.execute(sa.text("""
        SELECT s.id, p.[order] as p_order, s.display_order, s.paragraph_id
        FROM sentences s
        JOIN paragraphs p ON s.paragraph_id = p.id
        ORDER BY s.display_order
    """)).fetchall()
    
    last_p_id = None
    s_in_p = 0
    for s_id, p_order, d_order, p_id in sentences:
        if p_id != last_p_id:
            s_in_p = 1
            is_start = True
            last_p_id = p_id
        else:
            s_in_p += 1
            is_start = False
        
        connection.execute(sa.text("""
            UPDATE sentences 
            SET paragraph_number = :p_num, 
                sentence_number_in_paragraph = :s_num,
                is_paragraph_start = :is_start
            WHERE id = :id
        """), {"p_num": p_order, "s_num": s_in_p, "is_start": is_start, "id": s_id})

    # Finalize schema changes for downgrade
    with op.batch_alter_table('sentences', schema=None) as batch_op:
        batch_op.alter_column('sentence_number_in_paragraph', nullable=False)
        batch_op.alter_column('is_paragraph_start', nullable=False)
        batch_op.alter_column('paragraph_number', nullable=False)
        batch_op.create_unique_constraint('uq_sentences_paragraph_sentence', ['project_id', 'paragraph_number', 'sentence_number_in_paragraph'])
        batch_op.drop_constraint('fk_sentences_paragraph_id', type_='foreignkey')
        batch_op.drop_column('paragraph_id')

    op.drop_table('paragraphs')
    op.drop_table('sections')
    op.drop_table('chapters')
