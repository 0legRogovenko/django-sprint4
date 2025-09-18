
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
    path('', include('blog.urls', namespace='blog')),
    path('auth/', include('django.contrib.auth.urls')),
    path('auth/registration/',
         CreateView.as_view(
            template_name='registration/registration_form.html',
            form_class=UserCreationForm,
            success_url='/',
         ),
         name='registration'
    ),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
]


urlpatterns += static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT,
)


handler404 = 'pages.views.error_404'
handler403 = 'pages.views.error_403'
handler500 = 'pages.views.error_500'
