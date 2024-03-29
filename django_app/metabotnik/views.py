from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from django.db.models.query_utils import Q
from django.conf import settings
import dropbox
from metabotnik.models import Project, new_task
import metabotnik.planodo
import os
import mimetypes
import subprocess
import json

def s(request, path):
    if not settings.DEBUG:
        raise HttpResponseForbidden('Only works in development mode')
    fullpath = os.path.join(settings.STORAGE_PATH, path)
    if os.path.exists(fullpath):
        type, encoding = mimetypes.guess_type(fullpath)
        return HttpResponse(open(fullpath).read(), content_type=type)
    return HttpResponseNotFound('%s not found' % path)

def home(request):    
    return render(request, 'index.html', {'projects':Project.objects.filter(public=True)})

def help(request, page):
    return render(request, 'help/%s.html' % page)

@login_required
def new_project(request):
    path = request.GET.get('new_with_folder')
    if not path:
        path = ''
    filecount = request.GET.get('filecount', 0)        
    project = Project.objects.create(path=path, user=request.user, num_files_on_dropbox=filecount)
    new_task(request.user, {
        'action': 'download_dropboxfiles',
        'project_id': project.pk
    })

    url = reverse('edit_project', args=[project.pk])
    return redirect(url)

@require_POST
def generate(request, project_id):
    preview = True if request.POST.get('preview') else False
    sendemail = True if request.POST.get('sendemail') in ('true', '1') else False
    t = new_task(request.user, {
                'action': 'generate',
                'preview': preview,
                'sendemail': sendemail,
                'project_id': project_id
    })
    project = Project.objects.get(pk=project_id)
    project.layout = request.POST.get('layout', 'horizontal')
    project.status = 'generating'
    project.save()
    return HttpResponse(str(t.pk))

@require_POST
def getdropbox_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    if project.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden('Only the owner can request the fetching of Dropbox data for a project')
    t = new_task(request.user, {
                'action': 'download_dropboxfiles',
                'project_id': project_id
            })
    project.set_status('downloading')
    return HttpResponse(str(t.pk))

@require_POST
def delete_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    if project.user != request.user:
        raise HttpResponseForbidden('Only the owner can delete a project')
    project.status = 'deleted'
    project.save()
    return HttpResponse('Deleted!')

def savesection(request, project_id):
    project = Project.objects.get(pk=project_id)
    section = request.POST.get('section')
    x, y, width, height = section.split(' ')    
    x, y, width, height = int(float(x)), int(float(y)), int(float(width)), int(float(height))
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    # vips returns a 'bad extract area' if the width height is too big,
    # so lets sanitize those too
    if (project.metabotnik_width - x) < width:
        width = project.metabotnik_width - x
    if (project.metabotnik_height - y) < height:
        height = project.metabotnik_height - y

    # Call VIPS to make the DZ
    input_filepath = os.path.join(project.storage_path, 'metabotnik.jpg')
    section_filename = '%s_%s_%s_%s.jpg' % (x, y, width, height)
    output_filepath = os.path.join(project.storage_path, section_filename)
    if not os.path.exists(output_filepath):   
        subprocess.call(['vips', 'crop', input_filepath, output_filepath, 
                         str(x), str(y), str(width), str(height)])
    
    return HttpResponse('/s/project_%s/%s' % (project.pk, section_filename))

def num_files_local(request, project_id):
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return HttpResponseNotFound()
    return HttpResponse(str(project.num_files_local))

def project(request, project_id):
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return HttpResponseNotFound()
    if not project.public and not project.user == request.user and not request.user.is_superuser:
        return HttpResponseNotFound()
    if request.GET.get('kaal'):
        return render(request, 'project_kaal.html', {'project':project})
    return render(request, 'project_public.html', {'project':project})

def edit_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    templatename = 'project.html'
    if project.user == request.user or request.user.is_superuser:        
        if request.method == 'POST':            
            newname = request.POST.get('name')
            if newname:
                project.name = newname
            public = request.POST.get('public')
            if public == '1':
                project.public = True
            if public == '0':
                project.public = False
            description = request.POST.get('description')
            if description:
                project.description = description
                if description == '__clear__':
                    project.description = ''
            project.save()
    else:
        return redirect(reverse('project', args=[project.pk]))
    project.calc_storage_size()
    context = {
        'project':project, 
        'img_data':json.dumps(project.layout_as_dict())
    }
    return render(request, templatename, context)

def json_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    if project.user != request.user and not request.user.is_superuser:
        return redirect(reverse('project', args=[project.pk]))

    if request.method == 'POST':
        layout = request.POST.get('layout', 'horizontal')
        frame = request.POST.get('frame', '0')
        background_color = request.POST.get('background_color', '#fff')        

        project.layout_mode = layout
        project.background_color = background_color
        project.layout_data = json.dumps(metabotnik.planodo.layout(project, frame=frame))
        project.save()

    return HttpResponse(json.dumps(project.layout_as_dict()), content_type='application/json')


def metadata_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    if project.user != request.user and not request.user.is_superuser:
        return redirect(reverse('project', args=[project.pk]))

    # Use a POST to this method to save the sortorder of the files
    if request.method == 'POST':
        file_list = request.POST.get('file_list', u'').strip(' \n\r')
        project.set_metadata(file_list)
        project.layout_data = json.dumps(metabotnik.planodo.layout(project))
        project.save()
        return HttpResponse('OK')

    textarea_rows = min(project.files.count(), 20)
    return render(request, 'metadata.html', 
                 {'project':project, 'textarea_rows':textarea_rows, 'img_data':project.layout_data})


def sorting_project(request, project_id):
    project = Project.objects.get(pk=project_id)
    if project.user != request.user and not request.user.is_superuser:
        return redirect(reverse('project', args=[project.pk]))

    # Use a POST to this method to save the sortorder of the files
    if request.method == 'POST':
        file_list = request.POST.get('file_list', u'').strip(' \n\r').split('\n')
        project.set_file_order(file_list)
        project.layout_data = json.dumps(metabotnik.planodo.layout(project))
        project.save()
        return HttpResponse('OK')

    textarea_rows = min(project.files.count(), 20)
    return render(request, 'sorting.html', 
                 {'project':project, 'textarea_rows':textarea_rows, 'img_data':json.dumps(project.layout_as_dict())
                 }) 

def projects(request):
    if 'new_with_folder' in request.GET:
        return new_project(request)
    criteria = Q(public=True)
    if not request.user.is_anonymous():
        criteria = criteria | Q(user=request.user)    
    queryset = Project.objects.exclude(status='deleted')
    if not request.user.is_superuser:
        queryset = queryset.filter(criteria)
    return render(request, 'projects.html', 
                  {'projects':queryset})

@login_required
def folders(request):
    client = dropbox.Dropbox(request.user.dropboxinfo.access_token)
    path = request.GET.get('path', '')

    # Given a path like: /a/b/c
    # We want the pathsplit to look like:
    # [('/', '/'), ('/a', 'a'), ('/a/b', 'b'), ('/a/b/c', 'c')]
    # So that we can easily build up a navtree in the template
    pathsplit = path.split('/')
    pathsplit = [('/'.join(pathsplit[:i+1]), x) for i,x in enumerate(pathsplit)]
    pathsplit = pathsplit[1:]

    # Count the number of JPEG files and their cumulative size
    jpeg_files = []
    filesize_total = 0

    # Maintain a list of folders so we can display the header to browse to them nicely
    folders = []

    for x in client.files_list_folder(path).entries:
        if type(x) == dropbox.files.FolderMetadata:
            folders.append(x.path_lower)
            continue
        # skip really small files, they are probably bogus or in transit
        if x.size < 1024:
            continue
        if x.path_lower.endswith('.jpg') or x.path_lower.endswith('.jpeg'):
            filesize_total += x.size
            jpeg_files.append(x)

    return render(request, 'folders.html', 
                  {'folders': folders,
                   'path':path, 
                   'pathsplit': pathsplit,
                   'filesize_total': filesize_total, 
                   'jpeg_files': jpeg_files,
                  })