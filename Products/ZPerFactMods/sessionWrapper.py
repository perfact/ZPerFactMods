#
# Hook into event handlers to call layout_init/layout_end
#

import zope.component
import ZPublisher.pubevents
import types
import logging
import six

logger = logging.getLogger('Products.ZPerFactMods.protectedURLs')


def call_hook(event, method):
    if isinstance(event.request.PUBLISHED, types.MethodType):
        # For methods we need the immediate parent
        obj = event.request.PARENTS[0]
    else:
        # For product instances we take the object itself.
        obj = event.request.PUBLISHED
    title = getattr(obj, 'title', None)
    if title is not None:
        if callable(title):
            title = title()
        if (
                isinstance(title, six.binary_type)
                and b'NO_SESSWRAP' in title
                or isinstance(title, six.text_type)
                and u'NO_SESSWRAP' in title
        ):
            return

    f = getattr(obj, method)
    if callable(f):
        f()


@zope.component.adapter(ZPublisher.pubevents.PubStart)
def perfact_layout_init(event):
    call_hook(event, 'layout_init')


@zope.component.adapter(ZPublisher.pubevents.PubBeforeCommit)
def perfact_layout_end(event):
    call_hook(event, 'layout_end')


zope.component.provideHandler(perfact_layout_init)
zope.component.provideHandler(perfact_layout_end)
