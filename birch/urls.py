from django.conf.urls import url, include

import views

app_name = 'birch'


urlpatterns = [
    url(r'^slack$', views.SlackHook.as_view(), name='slack_hook'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
