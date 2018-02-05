import traceback
from functools import partial
import kickshaws as ks
from common import *

'''
Handler for HemOnc study in REDCap.
'''

__all__ = ['compose_handler']

log = ks.create_logger(get_log_filepath(), __name__)

study_tag = 'hemonc'

#------------------------------------------------------------------------------

def _handle(redcap_env, project_id, req):
  '''This func is used by compose_handler below.
  Generally, you won't invoke this func directly.'''
  log.info('in')
  study_cfg = get_study_config(study_tag)
  # Confirm requesting IP is in whitelist, or bail.
  if not ip_is_whitelisted(req['client_ip'], study_cfg.get('whitelist')):
    log.info('For {} study, client_ip of {} is not whitelisted.'\
             ''.format(study_tag, req.get('client_ip')))
    return {'status': 403}
  log.info('This handler does not do anything yet.')
  log.info('out')
  return {'status': 200} 

def compose_handler(redcap_env, project_id):
  '''This returns a function that only takes a request-shaped
  map -- e.g., a handler function like Metaphor framework expects.
  We're composing a handler function dynamically that
  will already know what redcap_env and project_id it's dealing with.'''
  return partial(_handle, redcap_env, project_id)

