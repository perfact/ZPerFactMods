#
# Hook into event handlers to call request_init/request_end
#

import zope.component
import ZPublisher.pubevents
import six
import logging

logger = logging.getLogger('Products.ZPerFactMods.requestWrapper')


def get_context(event):
    """
    Look up the context of the published object. Returns None for some
    irregular requests, for example for builtin ZMI assets that have no title
    or when publishing a File object.
    Also returns None if the context's title contains NO_REQWRAP.
    """
    try:
        title = event.request.PUBLISHED.title
        if callable(title):
            title = title()
        if isinstance(title, six.binary_type) and b'NO_REQWRAP' in title:
            return None
        if isinstance(title, six.text_type) and u'NO_REQWRAP' in title:
            return None

        return event.request.PARENTS[0]
    except Exception:
        # Hook not implemented, published object has no title, ...
        return None


@zope.component.adapter(ZPublisher.pubevents.PubAfterTraversal)
def request_init(event):
    """
    Call request_init before calling the published object. If it is not found,
    call layout_init as compatibility fallback, but remove the layer counter
    from the request. This ensures that calls to layout_init and layout_end
    that are done by the published method itself still are executed and assume
    that they are the outermost layer, otherwise some older versions of
    layout_end might ignore the optional `redirect` parameter.
    """
    context = get_context(event)

    if hasattr(context, 'request_init'):
        return context.request_init()

    if hasattr(context, 'layout_init'):
        context.layout_init()
        event.request.set('__layout_init', None)


@zope.component.adapter(ZPublisher.pubevents.PubBeforeCommit)
def request_end(event):
    """
    Call request_end after the published object itself was called, but before
    commiting it. If it is not found, call layout_end instead. For systems that
    did not switch to using request_init/request_end yet, this will result in
    layout_end being called twice, but this is the compromise that I think we
    can live with the most. All other solutions would either run into the
    danger of ignoring redirects or require additional care whenever code is
    ported between a system that already switched to request_init/request_end
    and one that has not.
    """
    context = get_context(event)

    if hasattr(context, 'request_end'):
        return context.request_end()

    if hasattr(context, 'layout_end'):
        return context.layout_end()


zope.component.provideHandler(request_init)
zope.component.provideHandler(request_end)
