import flask

filters = flask.Blueprint('filters', __name__)


@filters.app_template_filter()
def page_id(value):
    return value // 10 + 1


@filters.app_template_filter()
def page_start(value):
    return value % 10 == 1


@filters.app_template_filter()
def page_end(value, arg):
    return value % 10 == 0 or value == len(arg)


@filters.app_template_filter()
def pluralize(value, singular='', plural='s'):
    """Very simple drop-in replacement for Django's pluralize filter"""
    try:
        length = len(value)
    except TypeError:
        # Assume value is int
        length = value
    return singular if length == 1 else plural
