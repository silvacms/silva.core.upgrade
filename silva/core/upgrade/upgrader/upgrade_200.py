# Copyright (c) 2002-2009 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

# silva imports
from silva.core.upgrade.upgrade import BaseRefreshAll

#-----------------------------------------------------------------------------
# 1.6.0 to 2.0.0
#-----------------------------------------------------------------------------

VERSION='2.0'

class RefreshAll(BaseRefreshAll):
    pass

refreshAll = RefreshAll(VERSION, 'Silva Root')
