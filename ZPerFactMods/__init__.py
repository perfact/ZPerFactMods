import logging
logger = logging.getLogger('Products.ZPerFactMods')

fixes = [
    'dbutilsPermissions',
    'defaultError',
    'pageTemplateDefaults',
    'protectedURLs',
    'disableConnectOnLoad',
    # 'logAllEvents',
    ]


# Apply the fixes
for fix in fixes:
    __import__('Products.ZPerFactMods.%s' % fix)
    try:
        logger.info('Applied %s patch' % fix)
    except:
        logger.warn('Could not apply %s' % fix)
logger.info('Patches installed')
