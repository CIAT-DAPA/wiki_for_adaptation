"""
Bulk-import indicators / metrics / SOPs from the SOP masterfile spreadsheet.

Thin console wrapper around ``catalog.sop_import.run_import`` (the same engine
used by the Wagtail admin upload view).

    python manage.py import_sops --source SOP_masterfile.xlsx           # creates DRAFTS
    python manage.py import_sops --source SOP_masterfile.xlsx --dry-run # preview only
    python manage.py import_sops --source SOP_masterfile.xlsx --publish # publish instead of draft
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from catalog.sop_import import SopImportError, run_import


class Command(BaseCommand):
    help = "Bulk-import Indicators/Metrics/SOPs from the SOP masterfile spreadsheet."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="Path to SOP_masterfile.xlsx")
        parser.add_argument("--sheet", default="SOPs", help="Sheet name (default: SOPs)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing to the database.")
        parser.add_argument("--publish", action="store_true", help="Publish pages instead of creating drafts.")

    def handle(self, *args, **options):
        try:
            report = run_import(
                options["source"],
                sheet=options["sheet"],
                dry_run=options["dry_run"],
                publish=options["publish"],
            )
        except SopImportError as exc:
            raise CommandError(str(exc))

        self.stdout.write(f"Importing {report['total']} row(s) [{report['mode'].upper()}]\n")
        for r in report["rows"]:
            if r["action"] == "error":
                self.stdout.write(self.style.ERROR(f"  [ERROR] {r['sop_id']}: {r['error']}"))
            else:
                self.stdout.write(f"  [{r['action'].upper()}] {r['sop_id']}: {r['title'][:60]}")

        style = self.style.WARNING if options["dry_run"] else self.style.SUCCESS
        self.stdout.write(style(
            f"\nDone. created={report['created']} updated={report['updated']} errors={report['errors']}"
            + (" (dry run — nothing written)" if options["dry_run"] else "")
        ))
