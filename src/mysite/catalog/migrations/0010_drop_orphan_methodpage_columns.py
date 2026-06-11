from django.db import migrations


class Migration(migrations.Migration):
    """Drop orphaned ``MethodPage`` columns left over from an earlier model.

    ``catalog_methodpage`` still carries ``cost_level``, ``estimated_time``,
    ``method_type`` and ``scale`` columns that are no longer part of the
    ``MethodPage`` model nor any migration. Because they are NOT NULL with no
    default, creating a new Method fails with a NotNullViolation. Remove them
    where they still exist (no-op on databases that never had them).
    """

    dependencies = [
        ('catalog', '0009_drop_orphan_tracking_functions'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE catalog_methodpage DROP COLUMN IF EXISTS cost_level;'
                'ALTER TABLE catalog_methodpage DROP COLUMN IF EXISTS estimated_time;'
                'ALTER TABLE catalog_methodpage DROP COLUMN IF EXISTS method_type;'
                'ALTER TABLE catalog_methodpage DROP COLUMN IF EXISTS scale;'
            ),
            reverse_sql=(
                'ALTER TABLE catalog_methodpage ADD COLUMN IF NOT EXISTS cost_level varchar(150) NULL;'
                'ALTER TABLE catalog_methodpage ADD COLUMN IF NOT EXISTS estimated_time varchar(150) NULL;'
                'ALTER TABLE catalog_methodpage ADD COLUMN IF NOT EXISTS method_type varchar(150) NULL;'
                'ALTER TABLE catalog_methodpage ADD COLUMN IF NOT EXISTS scale varchar(150) NULL;'
            ),
        ),
    ]
