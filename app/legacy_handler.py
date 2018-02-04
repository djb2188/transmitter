import requests
import traceback
import kickshaws as ks
from common import *

'''
RACIE Legacy Handle: route to legacy service.
'''

__all__ = ['handle']

log = ks.create_logger(get_log_filepath(), __name__)

def handle(req):
  '''Route to RACIE Legacy service. Assumes we're always POSTing.'''
  log.info('in')
  url = 'http://localhost:80/index/' 
  status = -1
  try:
    pyld = (req.get('data', ''))
    log.info('About to call RACIE Legacy with this payload: {}'.format(pyld))
    # Note that the data arg below can be a string; will not be modified.
    # This is what we want since we're just handing off the payload from
    # the incoming request.
    rslt = requests.post(url, data=pyld) 
    status = rslt.status_code
    log.info('Result of RACIE Legacy call: {} -- .'.format(status))
    log.info('out')
    return {'status': status}
  except Exception, ex:
    log.error(traceback.format_exc())
    ks.send_email(study_cfg[env_tag]['from-email']
                 ,study_cfg[env_tag]['to-email']
                 ,'Boost Transmitter Exception'
                 ,'Please check the log.')
    return {'status': 500}

