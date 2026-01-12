from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Student App (Root URL for Login)
    path('', include('StudentApp.urls')),
    
    # BDM / CRM App (New)
    path('bdm/', include('BdmApp.urls')),
    # Trainer App
    path('trainer/', include('TrainerApp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)