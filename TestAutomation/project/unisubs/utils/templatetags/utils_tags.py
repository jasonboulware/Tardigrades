from django import template
from django.utils.translation import ugettext, ungettext
from django.utils.html import escape
from pprint import pformat

from utils import dates
from utils.text import fmt

try:
    from django.utils.safestring import mark_safe
    assert mark_safe # Shut up, Pyflakes.
except ImportError: # v0.96 and 0.97-pre-autoescaping compat
    def mark_safe(x): return x

register = template.Library()

@register.simple_tag
def form_field_as_list(GET_vars, bounded_field, count=0):
    getvars = '?'

    if len(GET_vars.keys()) > 0:
        getvars = "?%s&" % GET_vars.urlencode()

    output = []

    data = bounded_field.data or bounded_field.field.initial

    for i, choice in enumerate(bounded_field.field.choices):
        if choice[0] == data:
            li_attrs = u'class="active"'
        else:
            li_attrs = u''

        href = u'%s%s=%s' % (getvars, bounded_field.name, choice[0])
        li = {
            'attrs': li_attrs,
            'href': href,
            'value': choice[0],
            'fname': bounded_field.html_name,
            'name': choice[1]
        }

        if count and choice[0] == data and i >= count:
            output.insert(count - 1, li)
        else:
            output.append(li)

    if count:
        li = {
            'attrs': u'class="more-link"',
            'href': '#',
            'name': ugettext(u'more...'),
            'fname': '',
            'value': ''
        }
        output.insert(count, li)

        for i in xrange(len(output[count+1:])):
            output[count+i+1]['attrs'] += u' style="display: none"'

    content = [u'<ul>']
    for item in output:
        content.append(u'<li %(attrs)s><a href="%(href)s" name="%(fname)s" value="%(value)s"><span>%(name)s</span></a></li>' % item)
    content.append(u'</ul>')

    return u''.join(content)


@register.filter
def rawdump(x):
    if hasattr(x, '__dict__'):
        d = {
            '__str__':str(x),
            '__unicode__':unicode(x),
            '__repr__':repr(x),
            'dir':dir(x),
        }
        d.update(x.__dict__)
        x = d
    output = pformat(x)+'\n'
    return output

DUMP_TEMPLATE = '<pre class="dump"><code class="python" style="font-family: Menlo, monospace; white-space: pre;">%s</code></pre>'
@register.filter
def dump(x):
    return mark_safe(DUMP_TEMPLATE % escape(rawdump(x)))


@register.filter
def simplify_number(value):
    num = str(value)
    size = len(num)

    # Billions
    if size > 9:
        bils = num[0:-9]
        dec = num[-9:-8]
        if dec != '0':
            return '{0}.{1}b'.format(bils, dec)
        else:
            return '{0}b'.format(bils)

    # Millions
    elif size > 6:
        mils = num[0:-6]
        dec = num[-6:-5]
        if dec != '0':
            return '{0}.{1}m'.format(mils, dec)
        else:
            return '{0}m'.format(mils)

    # Ten-thousands
    elif size > 4:
        thou = num[0:-3]
        dec = num[-3:-2]
        if dec != '0':
            return '{0}.{1}k'.format(thou, dec)
        else:
            return '{0}k'.format(thou)

    else:
        return num

@register.filter
def timesince_short(datetime):
    delta = dates.now() - datetime
    if delta.days != 0:
        return fmt(
            ungettext('%(count)s day ago', '%(count)s days ago', delta.days),
            count=delta.days)
    elif delta.seconds > 3600:
        hours = int(round(delta.seconds / 3600.0))
        return fmt(
            ungettext('%(count)shour ago', '%(count)s hours ago', hours),
            count=hours)
    elif delta.seconds > 60:
        minutes = int(round(delta.seconds / 60.0))
        return fmt(
            ungettext('%(count)s minute ago', '%(count)s minutes ago',
                      minutes),
            count=minutes)
    else:
        return ugettext('Just now')
