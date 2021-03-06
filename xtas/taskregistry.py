"""Task registry singleton."""

from functools import wraps

import requests

from .util import getconf, slashjoin


# Task registry (singletons).
SYNC_TASKS = []
ASYNC_TASKS = []


def task(sync=False, methods=('GET',), takes='document'):
    """Decorator to register a function as a task.

    This puts a wrapper around the task that makes it fetch its input from
    Elasticsearch and routes it through a URL via Flask. The front-end server
    will then treat the wrapper as a Celery task.

    The original function is still usable as a vanilla Python function with
    its original argument list.

    The url is determined from the module name of the function, __module__
    (not __name__!).

    Parameters
    ----------
    path : string
        Path component of URL. Interpreted by Flask.
    sync : boolean, optional
        Whether the task is synchronous (executed on the web server frontend)
        or asynchronous (default, executed on worker nodes).
    methods : sequence, optional
        Allowed HTTP methods.
    takes : string, optional
        Type of input. 'document' for strings representing entire documents,
        None for no input.
    """

    def wrap(f):
        global SYNC_TASKS, ASYNC_TASKS

        if takes == 'document':
            url = slashjoin(['/', f.__module__.rsplit('.', 1)[-1],
                             '<index>/<doc_type>/<int:id>/<bodyfield>'])

            @wraps(f)
            def f_task(doc_type, id, index, bodyfield, config):
                es = getconf(config, 'main elasticsearch', error='raise')
                doc = requests.get(slashjoin([es, index, doc_type, str(id)]))
                content = doc.json()['_source'][bodyfield]

                return f(content, config)

        elif takes == None:
            url = '/' + f.__module__.rsplit('.', 1)[-1]
            f_task = f

        (SYNC_TASKS if sync else ASYNC_TASKS).append((f_task, url, methods))

        return f

    return wrap
