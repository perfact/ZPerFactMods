import logging
logger = logging.getLogger('Products.ZPerFactMods')

fixes = [
    'defaultError',
    'pageTemplateDefaults',
    'protectedURLs',
    'disableConnectOnLoad',
    # 'logAllEvents',
    ]


# Apply the fixes
for fix in fixes:
    __import__('Products.PerFactPatches201301.%s' % fix)
    try:
        logger.info('Applied %s patch' % fix)
    except:
        logger.warn('Could not apply %s' % fix)
logger.info('Patches installed')
