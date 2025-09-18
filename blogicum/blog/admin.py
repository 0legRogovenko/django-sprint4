from django.contrib import admin

from .models import Category, Location, Post, Comment


admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Comment)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Настройки административной панели для модели Post."""

    list_display = ('category', 'is_published', 'pub_date', 'title')
    list_filter = ('category', 'is_published', 'pub_date')
    search_fields = ('text', 'title')
