import sys
import kickshaws as ks
import redcaplib as rc
from common import *

__all__ = ['handle']

FROM_EMAIL = 'X'
TO_EMAIL = 'X'

log = ks.create_logger(get_log_filepath(), __name__)

def handle(req):
  try:
    pyld = rc.parse_det_payload(req['data']) 
    log.info('Parsed contents of DET payload: ' + str(pyld))
    msg = 'Received trigger payload from REDCap. Details: \n' \
          'REDCap Server IP: {} \n' \
          'Project ID: {} \n' \
          'Record ID: {} \n' \
          ''.format(req['client_ip'], pyld['project_id'], pyld['record'])
    log.info('Sending email, body is: \n' + msg)
    ks.send_email(FROM_EMAIL, TO_EMAIL, 'Transmitter Test Email', msg)
    return {'status': 200}
  except Exception, e:
    log.error('Got error; returning status 500; details: ' + str(e))
    return {'status': 500 } 

