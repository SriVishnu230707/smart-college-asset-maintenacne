"""Authored ticket comments for loader and workflow examples."""
from alembic import op
import sqlalchemy as sa

revision = '0005_comments'
down_revision = '0004_feed'
branch_labels = depends_on = None

def upgrade():
    op.create_table('ticket_comments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ticket_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("body !~ '^[[:space:]]*$'", name='ck_ticket_comments_body'),
        sa.PrimaryKeyConstraint('id', name='pk_ticket_comments'),
        sa.ForeignKeyConstraint(['ticket_id'], ['maintenance_tickets.id'], name='fk_ticket_comments_ticket_id_maintenance_tickets', ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], name='fk_ticket_comments_author_id_users', ondelete='RESTRICT', onupdate='RESTRICT'))
    for column in ('ticket_id', 'author_id'):
        op.create_index('ix_ticket_comments_'+column, 'ticket_comments', [column])

def downgrade():
    op.drop_table('ticket_comments')
