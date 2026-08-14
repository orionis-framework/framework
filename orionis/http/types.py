from orionis.http.response import Response

# Every object built by the ``response`` factory derives from ``Response``,
# so this single alias annotates any handler regardless of its content type.
type HttpResponse = Response
