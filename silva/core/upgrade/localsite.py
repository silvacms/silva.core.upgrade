# Copyright (c) 2008-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

try:
    # Old FiveSiteManager. This have been removed in Zope 2.12.
    from Products.Five.site.interfaces import IFiveSiteManager
except ImportError:
    IFiveSiteManager = None

from zope.app.intid.interfaces import IIntIds
from zope.location.interfaces import ISite
from zope.app.component.hooks import setSite
from zope.component import queryUtility

from silva.core.services.base import IntIdService
from five.localsitemanager import make_objectmanager_site
try:
    from five.grok.meta import setupUtility
except ImportError:
    from grokcore.site.meta import setupUtility


def clean_old_five_sm(context, create=True):
    """Disable the old Five sucky SM.
    """
    from Products.Five.site.localsite import disableLocalSiteHook
    std_msg = 'Please deinstall products using the local site feature.'
    disableLocalSiteHook(context)
    if not create:
        return None
    create_new_sm(context)
    return context.getSiteManager()


def create_new_sm(context):
    """Create a new SM.
    """
    make_objectmanager_site(context)
    setSite(context)


def setup_intid(context):
    """Setup intids.
    """
    service = queryUtility(IIntIds)
    if service is None:
        setupUtility(context, IntIdService(), IIntIds)


def activate(context):
    """Change the context to a local site.
    """
    if not ISite.providedBy(context):
        create_new_sm(context)
    sm = context.getSiteManager()
    if IFiveSiteManager is not None and IFiveSiteManager.providedBy(sm):
        clean_old_five_sm(context, create=True)
    setup_intid(context)


def disable(context, interface):
    """Remove a registered utility.
    """
    sm = context.getSiteManager()
    utility = sm.queryUtility(interface)
    if IFiveSiteManager is not None and IFiveSiteManager.providedBy(sm):
        parent = utility.aq_parent
        name = interface.__name__
        parent.manage_delObjects([name])
    else:
        sm.unregisterUtility(utility, interface)
