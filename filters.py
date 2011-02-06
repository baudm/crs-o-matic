from google.appengine.ext.webapp import template
register = template.create_template_register()


def page_id(value):
    return int(value) / 10 + 1


def page_start(value):
    return int(value) % 10 == 1


def page_end(value, arg):
    return int(value) % 10 == 0 or int(value) == len(arg)


register.filter(page_id)
register.filter(page_start)
register.filter(page_end)
