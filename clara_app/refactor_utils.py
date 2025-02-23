from redbaron import RedBaron
import pprint

from .clara_utils import (
    read_txt_file,
    write_txt_file,
    absolute_file_name
    )

def get_function_names_from_file(filepath):
    """
    Parse a .py file and return the names of all functions defined in it.
    """
    source_code = read_txt_file(filepath)

    red = RedBaron(source_code)
    function_nodes = red.find_all("def")  # All function definitions

    # Collect the 'name' attribute of each function node.
    return [fn.name for fn in function_nodes] 

def get_imports_from_file(filepath):
    """
    Parse a .py file and return a list of all import statements (both 'import' and 'from import').
    """
    source_code = read_txt_file(filepath)

    red = RedBaron(source_code)

    # 'import' statements: e.g. "import os", "import re"
    import_nodes = red.find_all("import")

    # 'from_import' statements: e.g. "from django.shortcuts import render"
    from_import_nodes = red.find_all("from_import")

##    # Convert each node to its source representation
##    imports = [node.dumps().strip() for node in import_nodes]
##    from_imports = [node.dumps().strip() for node in from_import_nodes]
##
##    return imports + from_imports

    return import_nodes + from_import_nodes

def get_functions_called_by_function(function_node, skip_method_calls=True):
    """
    Given a RedBaron function node, return the names of all functions it calls.

    This handles cases like:
      bar.baz()
      get_user_config(request.user)['clara_version']
      MyClass().some_method().another_method()

    By default (skip_method_calls=True), we skip any call that includes a dot in the chain,
    i.e. 'bar.baz()' won't appear in the results. If skip_method_calls=False, we include them.

    We also store results in a set to remove duplicates.
    """
    called_functions = set()

    # 1. Find all "atomtrailers" in the function body
    atom_nodes = function_node.find_all("atomtrailers")

    for atom in atom_nodes:
        trailer_list = atom.value  # e.g. [NameNode('bar'), DotNode('.'), NameNode('baz'), CallNode(...)]
        
        # We'll walk the chain looking for CallNodes
        trailer_list_fst = trailer_list.fst()
        for i, node in enumerate(trailer_list_fst):
            if node['type'] == "call":
                # We found a function invocation
                # Now let's look backward to find:
                #   (a) The function name (the last NameNode before this CallNode)
                #   (b) Whether there was a DotNode before that NameNode
                fn_name = None
                dot_found = False

                # We'll search from i-1 down to 0
                j = i - 1
                while j >= 0:
                    t = trailer_list_fst[j]
                    #print(t)
                    if t['type'] == "dot":
                        dot_found = True
                    elif t['type'] == "name" and fn_name is None:
                        # Record the first name we find going backward
                        fn_name = t['value']
                    j -= 1

                # If we found a function name
                if fn_name:
                    # If skip_method_calls is True and we encountered a dot, skip
                    if skip_method_calls and dot_found:
                        continue

                    # Otherwise add it
                    called_functions.add(fn_name)

    return list(called_functions)

def get_functions_called_in_file(filepath, function_name, skip_method_calls=True):
    """
    Parse a file with RedBaron, find `function_name`, then call
    get_functions_called_by_function on it.

    skip_method_calls determines whether we exclude object.method() calls.
    """
    source_code = read_txt_file(filepath)

    red = RedBaron(source_code)
    fn_node = red.find("def", name=function_name)
    if not fn_node:
        print(f"No function named '{function_name}' in {filepath}")
        return []

    return get_functions_called_by_function(fn_node, skip_method_calls=skip_method_calls)

def get_view_functions_from_urls(filepath):
    """
    Parse urls.py and return the function names referenced, e.g. if it has:
        path('...', views.some_view, name='...'),
    we capture "some_view".
    
    This approach:
    1) Finds atomtrailers nodes that start with "path" or "re_path"
    2) Extracts the single call child
    3) Reads the arguments from that call
    4) Grabs the second positional argument if it references a function
    """
    source_code = read_txt_file(filepath)

    red = RedBaron(source_code)
    function_names = []

    # 1. Find all atomtrailers like "path(...)" or "re_path(...)"
    #    Each atomtrailers typically has children: [NameNode("path"), CallNode(...)]
    path_atoms = [
        node
        for node in red.find_all("atomtrailers")
        if len(node) >= 2
           and node[0].type == "name"
           and node[0].value in ("path", "re_path")
           and node[1].type == "call"
    ]

    print(f'{len(path_atoms)} path_atoms found')

    # 2. For each matching atomtrailers node, get the call node
    for atom in path_atoms:
        #pprint.pprint(atom.fst())
        # The second node is the call node (the argument list to path(...))
        call_node = atom[1]
        # call_node.value is a list like: [call_argument, comma, call_argument, comma, call_argument, ...]
        # So let's pull out just the call_argument items
        call_args = [item for item in call_node.value if item.type == "call_argument"]

        # We expect at least 2 call_argument nodes for a typical path: 
        #   path('...', views.some_view, ...)
        if len(call_args) < 2:
            continue

        second_arg = call_args[1].value  # e.g. an atomtrailers node for "views.some_view"

        if second_arg.type == "atomtrailers":
            # Usually: [NameNode('views'), DotNode('.'), NameNode('some_view')]
            # The function name is in the last name node
            trailer_list = second_arg.value
            if trailer_list and trailer_list[-1].type == "name":
                function_names.append(trailer_list[-1].value)

        elif second_arg.type == "dot":
            # If for some reason it's parsed as a DotNode,
            # you'd do a similar approach: second_arg.value[-1] might be the name node
            last_part = second_arg.value[-1]
            if last_part.type == "name":
                function_names.append(last_part.value)

        elif second_arg.type == "name":
            # e.g. user imported the view directly: from .views import home
            # so we have: path('...', home, name='...')
            function_names.append(second_arg.value)

        # If it’s a class-based view with .as_view(), it might be atomtrailers with more items.
        # Add more logic if you want to parse "MyView.as_view()" specifically.

    return function_names


