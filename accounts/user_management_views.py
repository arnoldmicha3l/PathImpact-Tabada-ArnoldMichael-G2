
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_http_methods,
    require_safe,
)

from .academic_views import paginate
from .administrator_views import administrator_only
from .models import CustomUser


def manageable_account(account, administrator):

    return (
        account.pk != administrator.pk
        and account.role == CustomUser.Role.STUDENT
        and not account.is_superuser
        and not account.is_staff
    )


@administrator_only
@require_safe
def users(request):

    query = request.GET.get("q", "").strip()[:150]

    selected_role = request.GET.get(
        "role", ""
    )

    selected_status = request.GET.get(
        "status", ""
    )

    summary = CustomUser.objects.aggregate(

        total_count=Count("pk"),

        student_count=Count(
            "pk",
            filter=Q(
                role=CustomUser.Role.STUDENT
            ),
        ),

        active_count=Count(
            "pk",
            filter=Q(is_active=True),
        ),

        inactive_count=Count(
            "pk",
            filter=Q(is_active=False),
        ),

    )

    records = CustomUser.objects.order_by(
        "-date_joined",
        "-pk",
    )

    if query:

        records = records.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    if selected_role in CustomUser.Role.values:

        records = records.filter(
            role=selected_role
        )

    else:

        selected_role = ""

    if selected_status == "active":

        records = records.filter(
            is_active=True
        )

    elif selected_status == "inactive":

        records = records.filter(
            is_active=False
        )

    else:

        selected_status = ""

    page = paginate(request, records)

    for account in page.object_list:

        account.can_manage_status = manageable_account(
            account,
            request.user,
        )

    context = {

        **summary,

        "page": page,

        "query": query,

        "roles": CustomUser.Role.choices,

        "selected_role": selected_role,

        "selected_status": selected_status,

        "filtered_count": page.paginator.count,

    }

    return render(
        request,
        "accounts/user_list.html",
        context,
    )


@administrator_only
@require_safe
def user_detail(request, pk):

    account = get_object_or_404(
        CustomUser,
        pk=pk,
    )

    context = {

        "account": account,

        "can_manage_status": manageable_account(
            account,
            request.user,
        ),

    }

    return render(
        request,
        "accounts/user_detail.html",
        context,
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def user_status(request, pk, action):

    if action not in ("activate", "deactivate"):

        from django.http import Http404

        raise Http404("Invalid account action.")

    desired_status = action == "activate"

    if request.method == "POST":

        with transaction.atomic():

            account = get_object_or_404(
                CustomUser.objects.select_for_update(),
                pk=pk,
            )

            if not manageable_account(
                account,
                request.user,
            ):

                messages.error(
                    request,
                    "This account is protected and its "
                    "access status cannot be changed.",
                )

                return redirect(
                    "accounts:user_detail",
                    pk=pk,
                )

            if account.is_active == desired_status:

                messages.info(
                    request,
                    "The account already has the "
                    "requested access status.",
                )

                return redirect(
                    "accounts:user_detail",
                    pk=pk,
                )

            account.is_active = desired_status

            account.save(
                update_fields=["is_active"]
            )

        messages.success(
            request,
            (
                "Student account activated successfully."
                if desired_status
                else "Student account deactivated successfully."
            ),
        )

        return redirect(
            "accounts:user_detail",
            pk=pk,
        )

    account = get_object_or_404(
        CustomUser,
        pk=pk,
    )

    if not manageable_account(
        account,
        request.user,
    ):

        messages.error(
            request,
            "This account is protected and its "
            "access status cannot be changed.",
        )

        return redirect(
            "accounts:user_detail",
            pk=pk,
        )

    return render(
        request,
        "accounts/user_status.html",
        {
            "account": account,
            "action": action,
            "desired_status": desired_status,
            "already_set": (
                account.is_active == desired_status
            ),
        },
    )
