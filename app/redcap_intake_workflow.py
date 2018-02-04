import sys
import json
import kickshaws as ks
import redcaplib
from common import *

'''
===============================================================================

-----------------------
REDCAP INTAKE WORKFLOW
-----------------------

This is a workflow that can be used with any REDCap project.

WHAT IT DOES

This workflow does these things: 
  - Confirm that the sender's IP is whitelisted, based on redcap_env and the
    REDCap spec loaded from enclave/redcap-specs.json and the supplied
    redcap_env value.
  - Convert the REDCap DET payload into a Python map
  - Retrieves the full relevant record from REDCAP and adds it to the
    map that this workflow returns.

WHEN TO USE

This should be the very first workflow for any REDCap project handler.

===============================================================================
'''

log = ks.create_logger(get_log_filepath(), __name__)

#------------------------------------------------------------------------------

def go(request):
  '''This workflow is not study-specific; any needed config info
  should have been put into the request map beforehand.
  Expects the request to include the additional following
     key-value pairs:
     - 'redcap_env' -- either 'sand' or 'prod'
     - 'project_id' -- the project ID (AKA pid) as a string
     - 'redcap-spec' -- redcap-spec details as described in README
  ''' 
  try:
    redcap_env = request['redcap_env']
    project_id = request['project_id']
    log.info('Entered -- redcap_env=[{}] and project_id=[{}]' \
             ''.format(redcap_env, project_id))
    # Bail if not a POST request. E.g., IP whitelisted but browser or
    # other utility is just checking the URL for aliveness.
    if request['method'] != 'POST':
      log.info('Method is {}; nothing to do.'.format(request['method']))
      request['done'] = 'yes'
      request['response'] = {'status': 405} 
      return request
    # Parse the REDCap DET payload.
    det_msg = redcaplib.parse_det_payload(request['data'])
    log.info('DET payload: ' + str(det_msg))
    request['det_payload'] = det_msg
    if len(det_msg) == 0:
      log.info('DET payload empty; nothing to do.')
      # This can happen is REDCap 'tests' a DET endpoint to 
      # ensure it's alive. At any rate, no further action needed.
      request['done'] = 'yes'
      request['response'] = {'status': 200}
      return request
    # Sanity-check the payload against what we understand
    # to be the redcap_env and project_id in the current context.
    if int(det_msg['project_id']) != project_id:
      raise RuntimeError('project_id in det payload ('  
                        + det_msg['project_id']
                        + ') does not match what handler (' 
                        + ') expects (' + project_id + ')') 
    # Call REDCap API and retrieve record.
    record_id = det_msg['record']
    rcd = redcaplib.get_full_record(request.get('redcap-spec'), int(record_id))
    log.info('Retrieved full record from REDCap API for record id of: [' + record_id + ']')
    request['record'] = rcd
    # All done. Return.
    return request
  except Exception, e:
    log.error('Exception caught: ' + str(e))
    raise e

