"""Enhanced features - social media capabilities

Revision ID: 002_enhanced_features
Revises: 001_initial_schema
Create Date: 2025-08-21 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_enhanced_features'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add enhanced features tables for social media capabilities."""
    
    # Create photo_metadata table
    op.create_table(
        'photo_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=True),
        sa.Column('mode', sa.String(length=20), nullable=True),
        sa.Column('has_transparency', sa.Boolean(), nullable=True),
        sa.Column('date_taken', sa.DateTime(timezone=True), nullable=True),
        sa.Column('camera_make', sa.String(length=100), nullable=True),
        sa.Column('camera_model', sa.String(length=100), nullable=True),
        sa.Column('lens_model', sa.String(length=100), nullable=True),
        sa.Column('software', sa.String(length=100), nullable=True),
        sa.Column('exposure_time', sa.String(length=50), nullable=True),
        sa.Column('f_number', sa.Float(), nullable=True),
        sa.Column('iso_speed', sa.Integer(), nullable=True),
        sa.Column('focal_length', sa.Float(), nullable=True),
        sa.Column('orientation', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('image_hash', sa.String(length=32), nullable=True),
        sa.Column('processed_sizes', sa.JSON(), nullable=True),
        sa.Column('color_space', sa.String(length=50), nullable=True),
        sa.Column('dominant_colors', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_metadata_id'), 'photo_metadata', ['id'], unique=False)
    op.create_index(op.f('ix_photo_metadata_photo_id'), 'photo_metadata', ['photo_id'], unique=True)
    op.create_index(op.f('ix_photo_metadata_date_taken'), 'photo_metadata', ['date_taken'], unique=False)
    op.create_index(op.f('ix_photo_metadata_image_hash'), 'photo_metadata', ['image_hash'], unique=False)

    # Create photo_tags table
    op.create_table(
        'photo_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=100), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_tags_id'), 'photo_tags', ['id'], unique=False)
    op.create_index(op.f('ix_photo_tags_photo_id'), 'photo_tags', ['photo_id'], unique=False)
    op.create_index(op.f('ix_photo_tags_tag'), 'photo_tags', ['tag'], unique=False)
    op.create_index('ix_photo_tags_photo_tag', 'photo_tags', ['photo_id', 'tag'], unique=False)

    # Create photo_likes table
    op.create_table(
        'photo_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_likes_id'), 'photo_likes', ['id'], unique=False)
    op.create_index(op.f('ix_photo_likes_photo_id'), 'photo_likes', ['photo_id'], unique=False)
    op.create_index(op.f('ix_photo_likes_user_id'), 'photo_likes', ['user_id'], unique=False)
    op.create_index('ix_photo_likes_unique', 'photo_likes', ['photo_id', 'user_id'], unique=True)

    # Create photo_comments table
    op.create_table(
        'photo_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['photo_comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_comments_id'), 'photo_comments', ['id'], unique=False)
    op.create_index(op.f('ix_photo_comments_photo_id'), 'photo_comments', ['photo_id'], unique=False)
    op.create_index(op.f('ix_photo_comments_user_id'), 'photo_comments', ['user_id'], unique=False)
    op.create_index(op.f('ix_photo_comments_created_at'), 'photo_comments', ['created_at'], unique=False)

    # Create user_follows table
    op.create_table(
        'user_follows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('following_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['following_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_follows_id'), 'user_follows', ['id'], unique=False)
    op.create_index(op.f('ix_user_follows_follower_id'), 'user_follows', ['follower_id'], unique=False)
    op.create_index(op.f('ix_user_follows_following_id'), 'user_follows', ['following_id'], unique=False)
    op.create_index('ix_user_follows_unique', 'user_follows', ['follower_id', 'following_id'], unique=True)

    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('avatar_photo_id', sa.Integer(), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=True),
        sa.Column('following_count', sa.Integer(), nullable=True),
        sa.Column('photos_count', sa.Integer(), nullable=True),
        sa.Column('likes_received_count', sa.Integer(), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=True),
        sa.Column('allow_comments', sa.Boolean(), nullable=True),
        sa.Column('allow_tags', sa.Boolean(), nullable=True),
        sa.Column('show_location', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['avatar_photo_id'], ['photos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=True)
    op.create_index(op.f('ix_user_profiles_followers_count'), 'user_profiles', ['followers_count'], unique=False)
    op.create_index(op.f('ix_user_profiles_photos_count'), 'user_profiles', ['photos_count'], unique=False)
    op.create_index(op.f('ix_user_profiles_is_private'), 'user_profiles', ['is_private'], unique=False)

    # Create albums table
    op.create_table(
        'albums',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_photo_id', sa.Integer(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('photos_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cover_photo_id'], ['photos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_albums_id'), 'albums', ['id'], unique=False)
    op.create_index(op.f('ix_albums_user_id'), 'albums', ['user_id'], unique=False)
    op.create_index(op.f('ix_albums_is_public'), 'albums', ['is_public'], unique=False)
    op.create_index(op.f('ix_albums_created_at'), 'albums', ['created_at'], unique=False)

    # Create album_photos table
    op.create_table(
        'album_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('album_id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['album_id'], ['albums.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_album_photos_id'), 'album_photos', ['id'], unique=False)
    op.create_index(op.f('ix_album_photos_album_id'), 'album_photos', ['album_id'], unique=False)
    op.create_index(op.f('ix_album_photos_photo_id'), 'album_photos', ['photo_id'], unique=False)
    op.create_index('ix_album_photos_unique', 'album_photos', ['album_id', 'photo_id'], unique=True)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=True),
        sa.Column('photo_id', sa.Integer(), nullable=True),
        sa.Column('album_id', sa.Integer(), nullable=True),
        sa.Column('comment_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['album_id'], ['albums.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['photo_comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)

    # Create photo_shares table
    op.create_table(
        'photo_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('shared_by', sa.Integer(), nullable=False),
        sa.Column('share_token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_views', sa.Integer(), nullable=True),
        sa.Column('current_views', sa.Integer(), nullable=True),
        sa.Column('allow_download', sa.Boolean(), nullable=True),
        sa.Column('allow_comments', sa.Boolean(), nullable=True),
        sa.Column('password_protected', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['photo_id'], ['photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_shares_id'), 'photo_shares', ['id'], unique=False)
    op.create_index(op.f('ix_photo_shares_photo_id'), 'photo_shares', ['photo_id'], unique=False)
    op.create_index(op.f('ix_photo_shares_share_token'), 'photo_shares', ['share_token'], unique=True)
    op.create_index(op.f('ix_photo_shares_expires_at'), 'photo_shares', ['expires_at'], unique=False)
    op.create_index(op.f('ix_photo_shares_is_active'), 'photo_shares', ['is_active'], unique=False)


def downgrade() -> None:
    """Drop enhanced features tables."""
    op.drop_table('photo_shares')
    op.drop_table('notifications')
    op.drop_table('album_photos')
    op.drop_table('albums')
    op.drop_table('user_profiles')
    op.drop_table('user_follows')
    op.drop_table('photo_comments')
    op.drop_table('photo_likes')
    op.drop_table('photo_tags')
    op.drop_table('photo_metadata')