#
# Hook into event handlers to add security for protected URLs.
#

import zope.component
import ZPublisher.pubevents
import zope.event
import types
import AccessControl
import logging
import six

logger = logging.getLogger('Products.ZPerFactMods.protectedURLs')


def is_protected(obj):
    # If there's an ID, we control private behaviour by ending the
    # name with an underscore (_)
    if hasattr(obj, 'getId') and obj.getId().endswith('_'):
        return True

    title = getattr(obj, 'title', None)
    if title is not None:
        if callable(title):
            title = title()
        if (
                isinstance(title, six.binary_type)
                and title.startswith(b'_protected')
                or isinstance(title, six.text_type)
                and title.startswith(u'_protected')
                ):
            return True

    # break recursion if in root object
    if obj.isTopLevelPrincipiaApplicationObject:
        return False
    # recurse to parent
    return is_protected(obj.aq_parent)


@zope.component.adapter(ZPublisher.pubevents.PubAfterTraversal)
def protectedURLHandler(event):
    # Managers may view anything they want.
    if event.request.AUTHENTICATED_USER.has_role('Manager'):
        return

    # Default to unprotected
    protected = False

    # Two possibilities: either we have an instancemethod, or a
    # product instance (Python Script or others)
    if isinstance(event.request.PUBLISHED, types.MethodType):
        # For methods we need the immediate parent
        obj = event.request.PARENTS[0]
    else:
        # For product instances we take the object itself.
        obj = event.request.PUBLISHED

    protected = is_protected(obj)

    # Private items which were attempted to publish directly
    # land in the log file and get "Unauthorized"
    if protected:
        logger.info('PROTECTED: '+str(event.request.URL))
        raise AccessControl.Unauthorized()


zope.component.provideHandler(protectedURLHandler)
