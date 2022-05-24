"""Add unsub behaviour

Revision ID: 21550bd668a8
Revises: 088f23324464
Create Date: 2022-05-24 15:58:38.962924

"""
import sqlalchemy_utils
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = '21550bd668a8'
down_revision = '088f23324464'
branch_labels = None
depends_on = None

def get_enum() -> postgresql.ENUM:
    return postgresql.ENUM('Disable', 'PreserveOriginal', name='unsubscribe_behaviour_enum')


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    unsub_enum = get_enum()
    unsub_enum.create(op.get_bind())
    op.add_column('users', sa.Column('unsub_behaviour', unsub_enum, default='PreserveOriginal', server_default='Disable', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'unsub_behaviour')
    unsub_enum = get_enum()
    unsub_enum.drop(op.get_bind())
    # ### end Alembic commands ###