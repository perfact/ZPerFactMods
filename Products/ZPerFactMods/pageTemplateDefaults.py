#
# Alter the default source code for new Page Templates
#

import os
from App.Common import package_home
from Products.PageTemplates import ZopePageTemplate

# Perform a monkey patch to point Page Templates to a different
# template.

template = os.path.join(package_home(globals()),
                        'www', 'default_pt.html')

ZopePageTemplate.ZopePageTemplate._default_content_fn = template
ZopePageTemplate.ZopePageTemplate.output_encoding = 'utf-8'


