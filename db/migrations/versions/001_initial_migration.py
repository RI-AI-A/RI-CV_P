"""Initial migration - Create all tables.

Revision ID: 001
Revises: 
Create Date: 2026-02-08 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('customer_id', name=op.f('pk_customers'))
    )

    # Create branches table
    op.create_table(
        'branches',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('peak_time', sa.String(length=10), nullable=True),
        sa.Column('neighbors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('expiry', sa.DateTime(), nullable=True),
        sa.Column('restocking_schedule', sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_branches'))
    )

    # Create employees table
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_employees'))
    )

    # Create customer_branch_movement table
    op.create_table(
        'customer_branch_movement',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_id', sa.String(length=100), nullable=False),
        sa.Column('enter_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('exit_time', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('action_type', sa.Enum('PASSED', 'ENTERED', name='actiontype'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name=op.f('fk_customer_branch_movement_branch_id_branches')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], name=op.f('fk_customer_branch_movement_customer_id_customers')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_customer_branch_movement'))
    )
    op.create_index('ix_customer_branch_movement_enter_time', 'customer_branch_movement', ['enter_time'])
    op.create_index('ix_customer_branch_movement_exit_time', 'customer_branch_movement', ['exit_time'])
    op.create_index('ix_customer_branch_movement_branch_id_enter_time', 'customer_branch_movement', ['branch_id', 'enter_time'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('branch_id', sa.String(length=100), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name=op.f('fk_tasks_branch_id_branches')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_tasks_employee_id_employees')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks'))
    )
    op.create_index('ix_tasks_branch_id', 'tasks', ['branch_id'])
    op.create_index('ix_tasks_employee_id', 'tasks', ['employee_id'])
    op.create_index('ix_tasks_time', 'tasks', ['time'])

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('repetition', sa.String(length=50), nullable=True),
        sa.Column('global_event', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_events'))
    )
    op.create_index('ix_events_start_time', 'events', ['start_time'])
    op.create_index('ix_events_type', 'events', ['type'])

    # Create promotions table
    op.create_table(
        'promotions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('branch_id', sa.String(length=100), nullable=True),
        sa.Column('item_name', sa.String(length=200), nullable=True),
        sa.Column('promotion_type', sa.String(length=100), nullable=False),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name=op.f('fk_promotions_branch_id_branches')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_promotions'))
    )
    op.create_index('ix_promotions_branch_id', 'promotions', ['branch_id'])
    op.create_index('ix_promotions_start_date', 'promotions', ['start_date'])

    # Create branch_kpi_timeseries table
    op.create_table(
        'branch_kpi_timeseries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('branch_id', sa.String(length=100), nullable=False),
        sa.Column('time_window_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('time_window_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('traffic_index', sa.Float(), nullable=True),
        sa.Column('conversion_proxy', sa.Float(), nullable=True),
        sa.Column('congestion_level', sa.Float(), nullable=True),
        sa.Column('growth_momentum', sa.Float(), nullable=True),
        sa.Column('utilization_ratio', sa.Float(), nullable=True),
        sa.Column('staffing_adequacy_index', sa.Float(), nullable=True),
        sa.Column('bottleneck_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name=op.f('fk_branch_kpi_timeseries_branch_id_branches')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_branch_kpi_timeseries'))
    )
    op.create_index('ix_branch_kpi_timeseries_branch_id', 'branch_kpi_timeseries', ['branch_id'])
    op.create_index('ix_branch_kpi_timeseries_time_window_start', 'branch_kpi_timeseries', ['time_window_start'])
    op.create_index('ix_branch_kpi_timeseries_branch_id_time_window', 'branch_kpi_timeseries', ['branch_id', 'time_window_start'])


def downgrade() -> None:
    op.drop_table('branch_kpi_timeseries')
    op.drop_table('promotions')
    op.drop_table('events')
    op.drop_table('tasks')
    op.drop_table('customer_branch_movement')
    op.drop_table('employees')
    op.drop_table('branches')
    op.drop_table('customers')
