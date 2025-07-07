from django.urls import path
from .views import landing_page, about_page

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('about/', about_page, name='about_page'),
]
