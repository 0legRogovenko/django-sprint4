
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
    path('', include('blog.urls', namespace='blog')),
    path('login/', include('django.contrib.auth.urls')),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
]


urlpatterns += static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT,
)


handler404 = 'pages.views.error_404'
handler403 = 'pages.views.error_403'
handler500 = 'pages.views.error_500'
