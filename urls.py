# -*- coding: utf-8 -*-
"""URL definitions."""
from tipfy.routing import Rule

rules = [
    Rule('/', name='direct-web-interface', handler='direct.handlers.IndexHandler'),
    Rule('/flushmemcache', name='direct-web-interface', handler='direct.handlers.FlushMemcacheHandler'),
    Rule('/getstat', name='direct-web-interface', handler='direct.handlers.GetStatHandler'),
    Rule('/campaign', name='direct-web-interface', handler='direct.handlers.CampaignHandler'),
    Rule('/savecampaign', name='direct-web-interface', handler='direct.handlers.SaveCampaignHandler'),
    Rule('/updatestat', name='direct-web-interface', handler='direct.handlers.UpdateStatHandler'),
    Rule('/updaterest', name='direct-web-interface', handler='direct.handlers.UpdateRestHandler'),
    Rule('/updatecampanystat', name='direct-web-interface', handler='direct.handlers.UpdateCampanyStatHandler'),
    Rule('/controlcampaign', name='direct-web-interface', handler='direct.handlers.ControlCampaignHandler'),
    Rule('/invoice', name='direct-web-interface', handler='direct.handlers.CreateInvoiceHandler'),
    Rule('/change', name='direct-web-interface', handler='direct.handlers.ChangeControlHandler'),
    Rule('/startcampaign', name='direct-web-interface', handler='direct.handlers.StartCampaignHandler'),
    Rule('/stopcampaign', name='direct-web-interface', handler='direct.handlers.StopCampaignHandler')
]
