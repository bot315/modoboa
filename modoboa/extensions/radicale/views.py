"""
Radicale extension views.
"""
from itertools import chain

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import (
    login_required, permission_required, user_passes_test
)
from django.utils.translation import ugettext as _

from modoboa.lib.webutils import (
    _render_to_string, render_to_json_response
)
from modoboa.lib.exceptions import NotFound, PermDeniedException
from modoboa.extensions.radicale.forms import (
    UserCalendarWizard, SharedCalendarForm, UserCalendarEditionForm
)
from modoboa.extensions.radicale.models import UserCalendar, SharedCalendar


@login_required
def index(request):
    return render(request, "radicale/calendars.html", {
        "selection": "radicale"
    })


@login_required
def calendars(request, tplname="radicale/calendar_list.html"):
    """Display calendars list.

    The content depends on current user's role.
    """
    if request.user.group == "SimpleUsers":
        mbox = request.user.mailbox_set.all()[0]
        cals = UserCalendar.objects.filter(mailbox=mbox).select_related().all()
    else:
        cals = chain(
            UserCalendar.objects.get_for_admin(request.user),
            SharedCalendar.objects.get_for_admin(request.user)
        )
    return render_to_json_response({
        "table": _render_to_string(request, tplname, {
            "calendars": cals
        })
    })


@login_required
def new_user_calendar(request):
    """Calendar creation view.
    """
    return UserCalendarWizard(request).process()


@login_required
def user_calendar(request, pk):
    """
    """
    try:
        ucal = UserCalendar.objects.get(pk=pk)
    except UserCalendar.DoesNotExist:
        raise NotFound
    instances = {"general": ucal, "rights": ucal}
    if request.method == "DELETE":
        # Check ownership
        ucal.delete()
        return render_to_json_response(_("Calendar removed"))
    return UserCalendarEditionForm(request, instances=instances).process()


@login_required
@permission_required("radicale.add_sharedcalendar")
def new_shared_calendar(request):
    """Shared calendar creation view.
    """
    if request.method == "POST":
        form = SharedCalendarForm(request.POST)
        if form.is_valid():
            form.save()
            return render_to_json_response(_("Calendar created"))
        return render_to_json_response(
            {"form_errors": form.errors}, status=400
        )
    form = SharedCalendarForm()
    return render(request, "common/generic_modal_form.html", {
        "form": form,
        "formid": "sharedcal_form",
        "title": _("New shared calendar"),
        "action": reverse("new_shared_calendar"),
        "action_classes": "submit",
        "action_label": _("Submit")
    })


@login_required
@permission_required("radicale.add_sharedcalendar")
@user_passes_test(
    lambda u: u.has_perm("radicale.change_sharedcalendar")
              or u.has_perm("radicale.delete_sharedcalendar")
)
def shared_calendar(request, pk):
    """
    """
    try:
        scal = SharedCalendar.objects.get(pk=pk)
    except SharedCalendar.DoesNotExist:
        raise NotFound
    if not request.user.can_access(scal.domain):
        raise PermDeniedException
    if request.method == "DELETE":
        scal.delete()
        return render_to_json_response(_("Calendar removed"))
    if request.method == "POST":
        form = SharedCalendarForm(request.POST, instance=scal)
        if form.is_valid():
            form.save()
            return render_to_json_response(_("Calendar updated"))
        return render_to_json_response(
            {"form_errors": form.errors}, status=400
        )
    form = SharedCalendarForm(instance=scal)
    return render(request, "common/generic_modal_form.html", {
        "form": form,
        "formid": "sharedcal_form",
        "title": scal.name,
        "action": reverse("shared_calendar", args=[scal.pk]),
        "action_classes": "submit",
        "action_label": _("Submit")
    })


@login_required
def username_list(request):
    """Get the list of username the current user can see.
    """
    from modoboa.extensions.admin.models import Mailbox

    result = []
    for mb in Mailbox.objects.prefetch_related("user").all():
        result.append(mb.user.username)
    return render_to_json_response(result)
