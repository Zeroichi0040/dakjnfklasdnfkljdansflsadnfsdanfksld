"""Add bakery catalogue ordering and simulated payments

Revision ID: 2e96d6aea48d
Revises: 6fdee4623110
Create Date: 2026-10-26 11:59:53.910258

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e96d6aea48d'
down_revision = '6fdee4623110'
branch_labels = None
depends_on = None


def upgrade():
    # Reviewed additive bakery schema; no existing tables or data are altered.
    op.create_table('bakery_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bakery_categories')),
    sa.UniqueConstraint('name', name=op.f('uq_bakery_categories_name')),
    sa.UniqueConstraint('slug', name=op.f('uq_bakery_categories_slug'))
    )
    op.create_table('bakery_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('checkout_token', sa.String(length=36), nullable=False),
    sa.Column('customer_name', sa.String(length=80), nullable=False),
    sa.Column('phone', sa.String(length=24), nullable=False),
    sa.Column('pickup_note', sa.String(length=300), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('stock_restored', sa.Boolean(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('pending','preparing','ready','completed','cancelled')", name=op.f('ck_bakery_orders_bakery_order_status')),
    sa.CheckConstraint('total > 0', name=op.f('ck_bakery_orders_bakery_order_total')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bakery_orders_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bakery_orders')),
    sa.UniqueConstraint('user_id', 'checkout_token', name='bakery_checkout_once')
    )
    with op.batch_alter_table('bakery_orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bakery_orders_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_bakery_orders_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_bakery_orders_user_id'), ['user_id'], unique=False)

    op.create_table('bakery_products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('stock', sa.Integer(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('image', sa.String(length=30), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint('price > 0 AND price <= 999999.99', name=op.f('ck_bakery_products_bakery_product_price')),
    sa.CheckConstraint('stock >= 0', name=op.f('ck_bakery_products_bakery_product_stock')),
    sa.ForeignKeyConstraint(['category_id'], ['bakery_categories.id'], name=op.f('fk_bakery_products_category_id_bakery_categories')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bakery_products'))
    )
    with op.batch_alter_table('bakery_products', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bakery_products_active'), ['active'], unique=False)
        batch_op.create_index(batch_op.f('ix_bakery_products_category_id'), ['category_id'], unique=False)

    op.create_table('bakery_order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('product_name', sa.String(length=120), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.CheckConstraint('quantity > 0 AND quantity <= 99', name=op.f('ck_bakery_order_items_bakery_item_quantity')),
    sa.CheckConstraint('unit_price > 0', name=op.f('ck_bakery_order_items_bakery_item_price')),
    sa.ForeignKeyConstraint(['order_id'], ['bakery_orders.id'], name=op.f('fk_bakery_order_items_order_id_bakery_orders'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['bakery_products.id'], name=op.f('fk_bakery_order_items_product_id_bakery_products')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bakery_order_items')),
    sa.UniqueConstraint('order_id', 'product_id', name='bakery_item_product_once')
    )
    with op.batch_alter_table('bakery_order_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bakery_order_items_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bakery_order_items_product_id'), ['product_id'], unique=False)

    op.create_table('bakery_payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('method', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('scenario', sa.String(length=20), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.CheckConstraint("method IN ('gcash','card','cash')", name=op.f('ck_bakery_payments_bakery_payment_method')),
    sa.CheckConstraint("scenario IN ('success','declined','insufficient','cancelled')", name=op.f('ck_bakery_payments_bakery_payment_scenario')),
    sa.CheckConstraint("status IN ('paid','unpaid','failed','cancelled','refunded')", name=op.f('ck_bakery_payments_bakery_payment_status')),
    sa.CheckConstraint('amount > 0', name=op.f('ck_bakery_payments_bakery_payment_amount')),
    sa.ForeignKeyConstraint(['order_id'], ['bakery_orders.id'], name=op.f('fk_bakery_payments_order_id_bakery_orders'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bakery_payments')),
    sa.UniqueConstraint('order_id', name=op.f('uq_bakery_payments_order_id'))
    )



def downgrade():
    # Reviewed additive bakery schema; no existing tables or data are altered.
    op.drop_table('bakery_payments')
    with op.batch_alter_table('bakery_order_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bakery_order_items_product_id'))
        batch_op.drop_index(batch_op.f('ix_bakery_order_items_order_id'))

    op.drop_table('bakery_order_items')
    with op.batch_alter_table('bakery_products', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bakery_products_category_id'))
        batch_op.drop_index(batch_op.f('ix_bakery_products_active'))

    op.drop_table('bakery_products')
    with op.batch_alter_table('bakery_orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bakery_orders_user_id'))
        batch_op.drop_index(batch_op.f('ix_bakery_orders_status'))
        batch_op.drop_index(batch_op.f('ix_bakery_orders_created_at'))

    op.drop_table('bakery_orders')
    op.drop_table('bakery_categories')
