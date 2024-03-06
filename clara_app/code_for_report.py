@login_required
@user_has_a_project_role
def clone_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    project_internal = CLARAProjectInternal(project.internal_id,
                                            project.l2,
                                            project.l1)

    if request.method == 'POST':
        form = ProjectCreationForm(request.POST)
        # Extract the title and the new L2 and L1 language selections
        new_title = form.cleaned_data['title']
        new_l2 = form.cleaned_data['l2']
        new_l1 = form.cleaned_data['l1']
        # Created the cloned project with a new internal ID
        new_project = CLARAProject(title=new_title, user=request.user,
                                   l2=new_l2, l1=new_l1)
        new_internal_id = create_internal_project_id(new_title,
                                                     new_project.id)
        new_project.internal_id = new_internal_id
        new_project.save()
        # Create a new internal project using the new internal ID
        new_project_internal = CLARAProjectInternal(new_internal_id,
                                                    new_l2, new_l1)
        # Copy relevant files from the old project
        project_internal.copy_files_to_new_project(new_project_internal)

        # Redirect and show a success message
        messages.success(request, "Cloned project created")
        return redirect('project_detail', project_id=new_project.id)
    
    else:
        # Prepopulate the form 
        new_title = project.title + " - copy"
        form = ProjectCreationForm(initial={'title': new_title,
                                            'l2': project.l2,
                                            'l1': project.l1})
        return render(request, 'clara_app/create_cloned_project.html',
                      {'form': form, 'project': project})
