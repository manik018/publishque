import calendar
from collections import defaultdict
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone
from urllib.parse import urlencode

from .forms import PostComposerForm
from .models import Post, PostTarget
from apps.profiles.models import ConnectedProfile


def group_profiles_by_platform(profiles):
    grouped = {}
    for profile in profiles:
        grouped.setdefault(profile.get_platform_display(), []).append(profile)
    return grouped.items()


def get_filter_params(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "platform": request.GET.get("platform", "").strip(),
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
    }


def build_querystring(params, exclude=None, page=None):
    exclude = set(exclude or [])
    values = {key: value for key, value in params.items() if value and key not in exclude}
    if page is not None:
        values["page"] = page
    return urlencode(values)


def get_active_filter_chips(params):
    labels = {
        "q": "Search",
        "status": "Status",
        "platform": "Platform",
        "date_from": "From",
        "date_to": "To",
    }
    status_labels = dict(PostTarget.Status.choices)
    platform_labels = dict(ConnectedProfile.Platform.choices)
    chips = []
    for key, value in params.items():
        if not value:
            continue
        display_value = value
        if key == "status":
            display_value = status_labels.get(value, value)
        elif key == "platform":
            display_value = platform_labels.get(value, value)
        chips.append(
            {
                "label": labels[key],
                "value": display_value,
                "remove_url": f"?{build_querystring(params, exclude=[key])}",
            }
        )
    return chips


def filter_posts(queryset, params):
    if params["q"]:
        queryset = queryset.filter(
            Q(title__icontains=params["q"]) | Q(content__icontains=params["q"])
        )
    if params["status"]:
        queryset = queryset.filter(targets__status=params["status"])
    if params["platform"]:
        queryset = queryset.filter(targets__connected_profile__platform=params["platform"])
    if params["date_from"]:
        date_from = parse_date(params["date_from"])
        if date_from:
            queryset = queryset.filter(targets__scheduled_time__date__gte=date_from)
    if params["date_to"]:
        date_to = parse_date(params["date_to"])
        if date_to:
            queryset = queryset.filter(targets__scheduled_time__date__lte=date_to)
    return queryset.distinct()


def get_requested_month(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if month < 1 or month > 12:
            raise ValueError
    except (TypeError, ValueError):
        year = today.year
        month = today.month
    return year, month


def get_adjacent_month(year, month, offset):
    month_index = (year * 12 + (month - 1)) + offset
    return month_index // 12, (month_index % 12) + 1


def build_calendar_weeks(year, month, targets_by_day):
    calendar_obj = calendar.Calendar(firstweekday=0)
    today = timezone.localdate()
    weeks = []
    for week in calendar_obj.monthdatescalendar(year, month):
        week_days = []
        for day in week:
            targets = targets_by_day.get(day, [])
            week_days.append(
                {
                    "date": day,
                    "day": day.day,
                    "in_month": day.month == month,
                    "is_today": day == today,
                    "targets": targets[:3],
                    "more_count": max(len(targets) - 3, 0),
                }
            )
        weeks.append(week_days)
    return weeks


def get_month_targets(user, year, month):
    first_day = date(year, month, 1)
    next_year, next_month = get_adjacent_month(year, month, 1)
    first_next_month = date(next_year, next_month, 1)
    return (
        PostTarget.objects.filter(
            post__owner=user,
            scheduled_time__date__gte=first_day,
            scheduled_time__date__lt=first_next_month,
        )
        .select_related("post", "connected_profile")
        .order_by("scheduled_time")
    )


@login_required
def post_list(request):
    params = get_filter_params(request)
    base_queryset = Post.objects.filter(owner=request.user)
    total_posts = base_queryset.count()
    filtered_queryset = filter_posts(base_queryset, params).prefetch_related(
        "targets__connected_profile"
    ).order_by("-created_at")
    paginator = Paginator(filtered_queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    active_filters = get_active_filter_chips(params)
    context = {
        "page_obj": page_obj,
        "posts": page_obj.object_list,
        "filter_params": params,
        "active_filters": active_filters,
        "has_active_filters": any(params.values()),
        "total_posts": total_posts,
        "filtered_count": paginator.count,
        "status_choices": PostTarget.Status.choices,
        "platform_choices": ConnectedProfile.Platform.choices,
        "base_querystring": build_querystring(params),
    }
    template_name = (
        "posts/partials/post_results.html"
        if request.headers.get("HX-Request")
        else "posts/post_list.html"
    )
    return render(request, template_name, context)


@login_required
def calendar_view(request):
    year, month = get_requested_month(request)
    targets = get_month_targets(request.user, year, month)
    targets_by_day = defaultdict(list)
    for target in targets:
        targets_by_day[timezone.localtime(target.scheduled_time).date()].append(target)

    previous_year, previous_month = get_adjacent_month(year, month, -1)
    next_year, next_month = get_adjacent_month(year, month, 1)
    context = {
        "calendar_weeks": build_calendar_weeks(year, month, targets_by_day),
        "month_name": calendar.month_name[month],
        "year": year,
        "month": month,
        "previous_year": previous_year,
        "previous_month": previous_month,
        "next_year": next_year,
        "next_month": next_month,
        "weekday_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    }
    template_name = (
        "posts/partials/calendar_grid.html"
        if request.headers.get("HX-Request")
        else "posts/calendar.html"
    )
    return render(request, template_name, context)


@login_required
def calendar_day_detail(request):
    day = parse_date(request.GET.get("date", ""))
    targets = []
    if day:
        targets = (
            PostTarget.objects.filter(
                post__owner=request.user,
                scheduled_time__date=day,
            )
            .select_related("post", "connected_profile")
            .order_by("scheduled_time")
        )
    return render(
        request,
        "posts/partials/calendar_day_detail.html",
        {"day": day, "targets": targets},
    )


@login_required
def new_post(request):
    if request.method == "POST":
        form = PostComposerForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.owner = request.user
                post.save()
                scheduled_time = form.cleaned_data["scheduled_time"]
                connected_profiles = form.cleaned_data["connected_profiles"]
                PostTarget.objects.bulk_create(
                    [
                        PostTarget(
                            post=post,
                            connected_profile=profile,
                            scheduled_time=scheduled_time,
                            board_id=request.POST.get(f"board_id_{profile.pk}", "")
                            or None,
                            board_name=request.POST.get(
                                f"board_name_{profile.pk}", ""
                            )
                            or None,
                        )
                        for profile in connected_profiles
                    ]
                )
            messages.success(request, "Post scheduled successfully.")
            return redirect("posts:list")
    else:
        form = PostComposerForm(user=request.user)

    profiles = form.fields["connected_profiles"].queryset
    return render(
        request,
        "posts/post_form.html",
        {
            "form": form,
            "profiles_by_platform": group_profiles_by_platform(profiles),
        },
    )
