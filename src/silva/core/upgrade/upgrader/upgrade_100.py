# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import sys

# silva imports
from silva.core.upgrade.upgrade import BaseUpgrader

import zLOG

#-----------------------------------------------------------------------------
# 0.9.3 to 1.0.0
#-----------------------------------------------------------------------------

VERSION='1.0'


class ImageUpgrade(BaseUpgrader):
    """handle view registry beeing moved out of the core"""

    def upgrade(self, image):
        if image.hires_image is None:
            image.hires_image = image.image
        try:
            image._createDerivedImages()
        except:
            exc, e, tb = sys.exc_info()
            del tb
            zLOG.LOG('Silva', zLOG.WARNING,
                    ('Error upgrading image %s: %s - %s; the image object is '
                    'probably broken.') % (image.absolute_url(), exc, e))
        return image


imageUpgrade = ImageUpgrade(VERSION, 'Silva Image')
