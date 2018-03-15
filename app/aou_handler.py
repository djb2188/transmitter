import sys
import traceback
import json
from functools import partial
# WCM libraries
import kickshaws as ks
# app modules
import redcap_intake_workflow
import aou_enrollment_workflow
import aou_withdrawal_workflow
from common import *
import aou_common

'''
Handler for REDCap AoU Enrollment Project.
'''

__all__ = ['compose_handler']

log = ks.create_logger(get_log_filepath(), __name__)

study_tag = 'aou'

#------------------------------------------------------------------------------

def _handle(redcap_env, project_id, req):
  '''This func is used by compose_handler below.
  Generally, you won't invoke this func directly.'''
  log.info('=============== Entered. ==================')
  study_cfg = get_study_config('aou')
  # Confirm requesting IP is in whitelist, or bail.
  if not ip_is_whitelisted(req['client_ip'], study_cfg.get('whitelist')):
    log.info('For AoU, client_ip of ' + req['client_ip'] + ' is not whitelisted.')
    return {'status': 403}
  # What 'environment' are we? E.g., different REDCap projects might
  # correspond to dev/test/prod.
  handler_tag = str(redcap_env + str(project_id))
  env_tag = aou_common.get_env_tag_for_handler(handler_tag)
  # Add these to request map; workflows might expect them.
  req['redcap_env'] = redcap_env
  req['project_id'] = project_id
  # Load redcap-spec, jira-spec into the request for workflows to use.
  req['redcap-spec'] = study_cfg.get(env_tag).get('redcap-spec')
  req['jira-spec'] = study_cfg.get(env_tag).get('jira-spec')
  # Ready to run workflows now.
  wf_chain = [redcap_intake_workflow.go
             ,aou_enrollment_workflow.go
             ,aou_withdrawal_workflow.go
            ]
  try:
    rslt = run_workflow_chain(req, wf_chain)
    if rslt.get('response'):
      log.info('Done. Chain result includes response of {}; will use that.'\
               ''.format(str(rslt.get('response'))))
      return rslt.get('response')
    else:
      log.info('Done. Will return 200 response.')
      return {'status': 200} 
  except Exception, e:
    log.error(traceback.format_exc())
    ks.send_email(study_cfg[env_tag]['from-email']
                 ,study_cfg[env_tag]['to-email']
                 ,'Boost Transmitter Exception'
                 ,'Please check the log.')
    log.error('Returning 500; details: ' + str(e))
    return {'status': 500}

def compose_handler(redcap_env, project_id):
  '''This returns a function that only takes a request-shaped
  map -- e.g., a handler function like Metaphor framework expects.
  We're composing a handler function dynamically that
  will already know what redcap_env and project_id it's dealing with.'''
  return partial(_handle, redcap_env, project_id)

