# views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Content, CLARAProject
from .clara_main import CLARAProjectInternal
from .forms import ContentPasswordUpdateForm
#from .utils import too_many_attempts  # from earlier rate-limit helper if you want reuse

def _assert_owner(user, project: CLARAProjectInternal):
    if user != project.user:
        raise PermissionDenied("Only the project owner can modify content protection.")

@login_required
def manage_content_passwords(request):
    """
    Show all protected Content rows backed by projects the user owns.
    (If you want 'any role', relax the _assert_owner check below.)
    """
    # Get user-owned projects
    owned_projects = CLARAProject.objects.filter(user=request.user)

    # Select their content rows which are protected (have password_hash)
    protected = (
        Content.objects
        .filter(project__in=owned_projects)
        .exclude(password_hash__isnull=True)
        .order_by('-updated_at')
    )

    # A small form per row for changing password (reuses the same form)
    forms_by_id = {c.id: ContentPasswordUpdateForm(initial={
        "content_id": c.id,
        "password_hint": c.password_hint or "",
    }) for c in protected}

    return render(request, "clara_app/manage_content_passwords.html", {
        "protected_contents": protected,
        "forms_by_id": forms_by_id,
    })


@login_required
def clear_content_password(request):
    """
    POST-only. Clears the password on a Content object if the user owns the project.
    """
    if request.method != "POST":
        return redirect("manage_content_passwords")

    content_id = request.POST.get("content_id")
    content = get_object_or_404(Content, id=content_id)

    # Security: must own the backing project
    _assert_owner(request.user, content.project)

    content.set_password(None)
    content.password_hint = ""
    content.save(update_fields=["password_hash", "password_hint", "password_last_set"])

    messages.success(request, f"Password removed for “{content.title}”.")
    return redirect("manage_content_passwords")


@login_required
def set_content_password(request):
    """
    POST-only. Set or change password + hint on a Content object if the user owns the project.
    """
    if request.method != "POST":
        return redirect("manage_content_passwords")

    form = ContentPasswordUpdateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the errors in the form.")
        return redirect("manage_content_passwords")

    content = get_object_or_404(Content, id=form.cleaned_data["content_id"])

    _assert_owner(request.user, content.project)

    raw = form.cleaned_data.get("password") or None
    hint = form.cleaned_data.get("password_hint") or ""

    # If raw is empty, treat as "clear" (sometimes users want a one-click clear via this route)
    if not raw:
        content.set_password(None)
        content.password_hint = ""
        content.save(update_fields=["password_hash", "password_hint", "password_last_set"])
        messages.success(request, f"Password removed for “{content.title}”.")
    else:
        content.set_password(raw)
        content.password_hint = hint
        content.save(update_fields=["password_hash", "password_hint", "password_last_set"])
        messages.success(request, f"Password updated for “{content.title}”.")

    return redirect("manage_content_passwords")
