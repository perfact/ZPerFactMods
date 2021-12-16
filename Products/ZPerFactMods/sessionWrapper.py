#
# Hook into event handlers to call layout_init/layout_end
#

import zope.component
import ZPublisher.pubevents
import six

def call_hook(event, method):
    try:
        title = event.request.PUBLISHED.title
        if callable(title):
            title = title()
        if isinstance(title, six.binary_type) and b'NO_SESSWRAP' in title:
            return
        if isinstance(title, six.text_type) and u'NO_SESSWRAP' in title:
            return

        getattr(event.request.PARENTS[0], method)()
    except Exception:
        pass


@zope.component.adapter(ZPublisher.pubevents.PubAfterTraversal)
def layout_init(event):
    call_hook(event, 'layout_init')


@zope.component.adapter(ZPublisher.pubevents.PubBeforeCommit)
def layout_end(event):
    call_hook(event, 'layout_end')


zope.component.provideHandler(layout_init)
zope.component.provideHandler(layout_end)
