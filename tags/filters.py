from google.appengine.ext.webapp import template
register = template.create_template_register()


@register.filter
def page_id(value):
    return int(value) / 10 + 1


@register.filter
def page_start(value):
    return int(value) % 10 == 1


@register.filter
def page_end(value, arg):
    return int(value) % 10 == 0 or int(value) == len(arg)
