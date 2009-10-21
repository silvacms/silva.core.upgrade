# Copyright (c) 2002-2009 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from silva.core.upgrade.upgrade import registry
from silva.core.upgrade.upgrade import BaseUpgrader

import martian


class UpgradeGrokker(martian.InstanceGrokker):
    """This lookup Upgrade instance and register them.
    """

    martian.component(BaseUpgrader)
    martian.priority(200)

    def grok(self, name, instance, module_info, config, **kw):
        registry.registerUpgrader(instance)
        return True