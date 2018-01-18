from common import *
from kickshaws import *

__all__ = ['handle']

log = create_logger(get_log_filepath(), __name__)

def handle(request):
  log.info('Handling request. Will return status 200.')
  return {'status':200
         ,'content-type': 'text/plain'
         ,'body': 'Hello world!'} 

