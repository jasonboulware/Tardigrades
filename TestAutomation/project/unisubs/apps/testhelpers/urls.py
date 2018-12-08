from django.conf.urls import  url

from testhelpers import views

urlpatterns = [
    url(r'echo-json/$', views.echo_json, name="echo-json"),
    url(r'^load-teams-fixture/$', views.load_team_fixtures, name='load_team_fixture'),
]
