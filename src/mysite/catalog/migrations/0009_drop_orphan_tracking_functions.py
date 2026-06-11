from django.db import migrations


class Migration(migrations.Migration):
    """Drop the orphaned ``tracking_functions`` column.

    An earlier version of ``MetricPage`` had a ``tracking_functions`` JSON field
    that was later replaced by ``tracks_vulnerability`` /
    ``tracks_intervention_impacts`` / ``adaptation_tracking_function`` (migration
    0007). The column was never dropped from existing databases, and because it
    is NOT NULL with no default, inserting a new MetricPage fails with a
    NotNullViolation. This removes the leftover column where it still exists.
    """

    dependencies = [
        ('catalog', '0008_soppage_estimated_time_soppage_method_type'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE catalog_metricpage DROP COLUMN IF EXISTS tracking_functions;',
            reverse_sql='ALTER TABLE catalog_metricpage ADD COLUMN IF NOT EXISTS tracking_functions jsonb NULL;',
        ),
    ]
