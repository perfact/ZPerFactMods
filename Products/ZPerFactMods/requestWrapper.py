#
# Hook into event handlers to call request_init/request_end
#

import zope.component
import ZPublisher.pubevents
import six
import logging

logger = logging.getLogger('Products.ZPerFactMods.requestWrapper')

def call_hook(event, method):
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

    try:
        hook()
    except Exception as err:
        logger.exception("Error while calling " + method)
        pass


@zope.component.adapter(ZPublisher.pubevents.PubAfterTraversal)
def request_init(event):
    call_hook(event, 'request_init')


@zope.component.adapter(ZPublisher.pubevents.PubBeforeCommit)
def request_end(event):
    call_hook(event, 'request_end')


zope.component.provideHandler(request_init)
zope.component.provideHandler(request_end)
