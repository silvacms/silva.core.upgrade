
# Monkeys for backward compatibility.
# Support for broken site manager.


import ZODB.broken
import zope.security.proxy
import zope.component.hooks
import zope.site.hooks
import zope.site.site

def setSite(site=None):
    if site is None:
        sm = zope.component.getGlobalSiteManager()
    else:

        # We remove the security proxy because there's no way for
        # untrusted code to get at it without it being proxied again.

        # We should really look look at this again though, especially
        # once site managers do less.  There's probably no good reason why
        # they can't be proxied.  Well, except maybe for performance.

        site = zope.security.proxy.removeSecurityProxy(site)
        sm = site.getSiteManager()
        if isinstance(sm, ZODB.broken.Broken):
            # If the site manager is broken don't set it.
            return

    zope.component.hooks.siteinfo.site = site
    zope.component.hooks.siteinfo.sm = sm
    try:
        del zope.component.hooks.siteinfo.adapter_hook
    except AttributeError:
        pass

zope.site.hooks.setSite = setSite
zope.component.hooks.setSite = setSite

def threadSiteSubscriber(ob, event):
    setSite(ob)

zope.site.site.threadSiteSubscriber = threadSiteSubscriber


