from rest_framework import renderers

class AmaraHTMLFormRenderer(renderers.HTMLFormRenderer):
    template_pack = 'api/fields'

class AmaraBrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    form_renderer_class = AmaraHTMLFormRenderer
    template = 'api/api.html'
