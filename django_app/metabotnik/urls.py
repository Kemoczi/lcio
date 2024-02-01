from django.urls import re_path, include, path
import metabotnik.views
import metabotnik.composites
import metabotnik.auth
from django.contrib import admin
admin.site.index_template = 'custom_admin_index.html'
admin.autodiscover()

urlpatterns = [    
    re_path(r'^$', metabotnik.views.home, name='home'),
    re_path(r'^help/(\w+)$', metabotnik.views.help, name='help'),

    re_path(r'^folders/$', metabotnik.views.folders, name='folders'),
    re_path(r'^projects/$', metabotnik.views.projects, name='projects'),    
    re_path(r'^projects/([0-9]+)/$', metabotnik.views.project, name='project'),
    re_path(r'^projects/([0-9]+)/edit$', metabotnik.views.edit_project, name='edit_project'),
    re_path(r'^projects/([0-9]+)/metadata$', metabotnik.views.metadata_project, name='metadata_project'),
    re_path(r'^projects/([0-9]+)/sorting$', metabotnik.views.sorting_project, name='sorting_project'),
    re_path(r'^projects/([0-9]+)/generate$', metabotnik.views.generate, name='generate'),
    re_path(r'^projects/([0-9]+)/delete$', metabotnik.views.delete_project, name='delete_project'),
    re_path(r'^projects/([0-9]+)/getdropbox$', metabotnik.views.getdropbox_project, name='getdropbox_project'),
    re_path(r'^projects/([0-9]+)/num_files_local$', metabotnik.views.num_files_local, name='num_files_local'),
    re_path(r'^projects/([0-9]+)/savesection$', metabotnik.views.savesection, name='savesection'),
    re_path(r'^projects/([0-9]+)/json$', metabotnik.views.json_project, name='json_project'),
    re_path(r'^composites/$', metabotnik.composites.main, name='composites'),
    re_path(r'^composites/([0-9A-Za-z]+)/$', metabotnik.composites.view, name='composite_view'),

    # Only to be used in development and only works if DEBUG is True
    re_path(r'^s/(.*)$', metabotnik.views.s),

    # Authentication
    re_path(r'^login$', metabotnik.auth.loginview, name='login'),
    re_path(r'^logout$', metabotnik.auth.logoutview, name='logout'),
    re_path(r'^dropboxauthredirect$', metabotnik.auth.dropboxauthredirect, name='dropboxauthredirect'),

    re_path(r'^admin/', admin.site.urls),
]
