from django.shortcuts import render
from django.views.generic import TemplateView


class AboutPageView(TemplateView):
    template_name = 'pages/about.html'


class RulesPageView(TemplateView):
    template_name = 'pages/rules.html'


def error_404(request, exception):
    """Обработчик ошибки 404."""

    return render(request, 'pages/404.html', status=404)


def error_403(request, exception):
    """Обработчик ошибки 403."""

    return render(request, 'pages/403csrf.html', status=403)


def error_500(request):
    """Обработчик ошибки 500."""

    return render(request, 'pages/500.html', status=500)


def csrf_failure(request, reason=''):
    """Обработчик CSRF-ошибки."""

    return render(request, 'pages/403csrf.html', status=403)
