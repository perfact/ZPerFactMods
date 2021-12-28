#
# Hook into event handlers to call request_init/request_end
#

import zope.component
import ZPublisher.pubevents
import six
import logging

logger = logging.getLogger('Products.ZPerFactMods.requestWrapper')


def call_hook(event, method):
    """
    Find a method named `method` in the current context and call it, unless the
    published object has a title that contains NO_REQWRAP.
    This is also called for a lot of internal methods like ZMI ressources,
    which sometimes have to title property. Such errors as well as the
    situation where the hook is not present are caught and ignored.
    """
    hook = None
    try:
        title = event.request.PUBLISHED.title
        if callable(title):
            title = title()
        if isinstance(title, six.binary_type) and b'NO_REQWRAP' in title:
            return
        if isinstance(title, six.text_type) and u'NO_REQWRAP' in title:
            return

        hook = getattr(event.request.PARENTS[0], method)
    except Exception:
        # Hook not implemented, published object has no title, ...
        return

    hook()


@zope.component.adapter(ZPublisher.pubevents.PubAfterTraversal)
def request_init(event):
    call_hook(event, 'request_init')


@zope.component.adapter(ZPublisher.pubevents.PubBeforeCommit)
def request_end(event):
    call_hook(event, 'request_end')


zope.component.provideHandler(request_init)
zope.component.provideHandler(request_end)
