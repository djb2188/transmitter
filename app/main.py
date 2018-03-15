import sys
import json
# WCM libraries
import metaphor
from kickshaws import *
# app modules
from common import *
# app modules - handlers
import stdout_handler
import test_email_handler
import hello_world_handler
import aou_handler
import legacy_handler
import hemonc_handler

cfg = get_app_config() 
log = create_logger(get_log_filepath(), 'transmitter-main')

def main():
  '''In this function we set up a collection of route handlers, and
  then we start up the listener. A route handler is a function
  the takes a *single* argument, a request-shaped map (see README).
  '''
  routes = {

    # Hello world endpoint for testing:
    '/hello-world': hello_world_handler.handle

    # Test project on sandbox server
    ,'/sand1090': stdout_handler.handle 

    # AoU DEV project (pid 2897) on REDCap prod server
    ,'/prod2897': aou_handler.compose_handler('prod', 2897)

    # AoU TST project (pid 2911) on REDCap prod server
    ,'/prod2911' : aou_handler.compose_handler('prod', 2911)

    # AoU Production project (pid 2525) on REDCap prod server:
    ,'/prod2525': aou_handler.compose_handler('prod', 2525)

    # HemOnc DEV project (pid 3027) on REDCap prod server:
    ,'/prod3027': imux_handlers(
                    legacy_handler.compose_handler(get_study_config('hemonc').get('whitelist'))
                   ,hemonc_handler.compose_handler('prod', 3027))

  }
  path_to_key = cfg['path-to-key']
  path_to_pem = cfg['path-to-pem']
  log.info('-----------------------------------------------------')
  log.info('---------------STARTING TRANSMITTER------------------')
  metaphor.listen(routes, 2814, path_to_key, path_to_pem, None, logger=log)
  return 

if __name__ == "__main__": main()

