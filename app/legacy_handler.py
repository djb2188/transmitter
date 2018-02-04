import requests
import traceback
import kickshaws as ks
from common import *
import redcaplib as rc

'''
RACIE Legacy Handler: route to legacy service.
'''

__all__ = ['handle']

racie_legacy_url = 'http://localhost:80/index/'

log = ks.create_logger(get_log_filepath(), __name__)

def handle(req):
  '''Route to RACIE Legacy service. Assumes we're always POSTing.'''
  log.info('in')
  status = -1
  try:
    raw_data = (req.get('data', ''))
    log.info('DET payload from REDCap: {}'.format(raw_data))
    log.info('About to call RACIE Legacy...')
    outgoing_data = rc.parse_det_payload(raw_data)
    rslt = requests.post(racie_legacy_url, data=outgoing_data)
    status = rslt.status_code
    msg = rslt.text
    log.info('Result of RACIE Legacy call: status is {}; message is {}.'\
             ''.format(status, msg))
    log.info('out')
    return {'status': status}
  except Exception, ex:
    log.error(traceback.format_exc())
    ks.send_email(study_cfg[env_tag]['from-email']
                 ,study_cfg[env_tag]['to-email']
                 ,'Boost Transmitter Exception'
                 ,'Please check the log.')
    return {'status': 500}

