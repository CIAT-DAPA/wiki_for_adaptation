"""Wagtail admin view to bulk-import the SOP masterfile from an uploaded file."""
from __future__ import annotations

from io import BytesIO

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from wagtail.admin.auth import require_admin_access, permission_denied

from .sop_import import SopImportError, run_import

# Wagtail group whose members may run the bulk import (plus superusers).
IMPORT_GROUP = "Content Developers"

# The template columns, in order, with guidance shown to editors and written to
# the downloadable template's "Instructions" sheet. Method columns (Option A)
# are appended for up to 5 methods per metric.
CORE_COLUMNS = [
    ("sop_id", "Stable SOP ID, e.g. SOP001 (used to match rows on re-import)"),
    ("indicator_id", "Stable Indicator ID, e.g. IND001"),
    ("indicator_name", "Indicator title"),
    ("indicator_description", "Indicator description"),
    ("indicator_properties", "Adaptation dimension: Climate hazard / Adaptation practice / Adaptation impact"),
    ("indicator_related_metrics", "Related metrics (reference only — not imported)"),
    ("metric_name", "Metric title"),
    ("metric_description", "Metric description"),
    ("metric_purpose", "Metric purpose"),
    ("metric_tracking_function", "e.g. 'Tracking vulnerability; Assessing intervention impacts'"),
    ("sop_title", "SOP title (a 'Standard Operating Procedure - ' prefix is optional)"),
    ("sop_definition", "Definition"),
    ("sop_data_sources", "Data sources (one item per line, or separated by semicolons)"),
    ("sop_units", "Units"),
    ("sop_frequency", "Frequency"),
    ("sop_scale", "Geographic scale"),
    ("sop_capacity", "Technical capacity considerations"),
    ("sop_activities_steps", "Activities and steps (one per line → numbered list)"),
    ("sop_robustness", "Options for enhancing robustness (one per line)"),
    ("sop_cost", "Options for reducing costs (one per line)"),
    ("sop_tools", "Available tools (URLs become clickable links)"),
    ("sop_references", "References (separate with semicolons; URLs become links)"),
    ("sop_flagship_status", "Flagship method status"),
    ("sop_example_applications", "Example applications (separate with semicolons)"),
    ("sop_unfccc_alignment", "UNFCCC Belém Adaptation Indicators"),
    ("sop_visual_content", "Visual content (description)"),
]

_METHOD_SUBFIELDS = [
    ("name", "title"),
    ("description", "description"),
    ("resolution", "resolution"),
    ("advantages", "advantages (one per line)"),
    ("limitations", "limitations (one per line)"),
    ("use_case", "use case"),
    ("resources", "resources (URLs become links)"),
]


def _all_columns():
    cols = list(CORE_COLUMNS)
    for n in range(1, 6):
        for sub, label in _METHOD_SUBFIELDS:
            cols.append((f"method{n}_{sub}", f"Method {n}: {label} (optional)"))
    return cols


def can_import_sops(user):
    return bool(
        user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=IMPORT_GROUP).exists())
    )


class SopImportForm(forms.Form):
    file = forms.FileField(label="SOP masterfile (.xlsx)")
    mode = forms.ChoiceField(
        label="Mode",
        choices=[
            ("dry_run", "Dry run — preview only, nothing is saved"),
            ("draft", "Import as drafts (recommended)"),
            ("publish", "Import and publish immediately"),
        ],
        initial="dry_run",
    )
    sheet = forms.CharField(label="Sheet name", initial="SOPs", required=False)

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Please upload an .xlsx file.")
        return f


@require_admin_access
def sop_import_view(request):
    # Restricted to superusers and members of the Content Developers group.
    if not can_import_sops(request.user):
        return permission_denied(request)

    report = None
    if request.method == "POST":
        form = SopImportForm(request.POST, request.FILES)
        if form.is_valid():
            mode = form.cleaned_data["mode"]
            sheet = form.cleaned_data.get("sheet") or "SOPs"
            try:
                report = run_import(
                    request.FILES["file"],
                    sheet=sheet,
                    dry_run=(mode == "dry_run"),
                    publish=(mode == "publish"),
                    owner=request.user,
                )
            except SopImportError as exc:
                messages.error(request, str(exc))
            else:
                if report["errors"] and not report["created"] and not report["updated"]:
                    messages.error(request, "Import finished with errors — see the report below.")
                elif mode == "dry_run":
                    messages.info(request, "Dry run complete — nothing was saved.")
                else:
                    messages.success(
                        request,
                        f"Import complete: {report['created']} created, "
                        f"{report['updated']} updated, {report['errors']} errors.",
                    )
    else:
        form = SopImportForm()

    return render(
        request,
        "catalog/admin/sop_import.html",
        {"form": form, "report": report, "columns": _all_columns()},
    )


@require_admin_access
def sop_import_template(request):
    """Download a blank .xlsx template with the expected columns and guidance."""
    if not can_import_sops(request.user):
        return permission_denied(request)

    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("openpyxl is not installed.", status=500)

    columns = _all_columns()
    wb = Workbook()
    ws = wb.active
    ws.title = "SOPs"
    ws.append([name for name, _ in columns])

    guide = wb.create_sheet("Instructions")
    guide.append(["Column", "What to enter"])
    for name, desc in columns:
        guide.append([name, desc])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="SOP_import_template.xlsx"'
    return response
