#
# Produce logger entries for all ZPublisher events.
#

import ZPublisher.pubevents
import zope.event
import types
import AccessControl
import logging
logger = logging.getLogger('Products.ZPerFactMods.logAllEvents')

def logAllEventsHandler(event):
    logger.info(event)
    
zope.event.subscribers.append(logAllEventsHandler)
