import sys
import json
import datetime
import kickshaws as ks
import pymysqlwrapper as db
import redcaplib as rc
import jiralib as jira
from common import *
import aou_common
import eavstore as eav

__all__ = ['go']

'''
===============================================================================

------------------------------
REDCap AoU Withdrawal Workflow
------------------------------

WHAT IT DOES

This workflow determines if the REDCap record indicates the 
participant's withdrawal from the study -- it does this specifically
by looking at the 'withdrawal_date' field. If non-empty, ee check
the the db see if an OBC Jira withdrawal ticket has been made
before; if not, we create the ticket and set the flag in the db.
  The OBC team will then transcribe the participant data into
the CTMS (CREST) as a widthdrawal.

WHEN TO USE

Call this workflow *after* the redcap_aou_enrollment workflow.

===============================================================================
'''
#------------------------------------------------------------------------------
# load specs and config

log = ks.create_logger(get_log_filepath(), __name__)
aou_config = get_study_config('aou')
study_details = aou_common.get_study_details()

#------------------------------------------------------------------------------
# jira strings when creating tickets

jira_test_msg = ' [THIS IS A TEST TICKET; DO NOT PROCESS]'
jira_kind = 'Disenrollment'

#------------------------------------------------------------------------------
# db flag

eav_attrname_jira = 'jira-withdrawal-ticket-created'

def have_created_jira_ticket(redcap_env, projectid, recordid):
  '''Returns true or False'''
  log.info('Checking whether we have created Jira withdrawal ticket before'\
           ' for: REDCap env: [{}], projectid: [{}], recordid: [{}]'\
           ''.format(redcap_env, projectid, recordid))
  if eav.exists(redcap_env, projectid, recordid, eav_attrname_jira):
    rslt = eav.get_latest_value(redcap_env, projectid, recordid, eav_attrname_jira)    
    if rslt == 'yes':
      return True
    else:
      return False
  else:
    return False

def set_jira_ticket_created_flag(redcap_env, projectid, recordid):
  attrval = 'yes'
  rslt = eav.put(redcap_env, projectid, recordid, eav_attrname_jira, attrval)
  return rslt

def calc_date_withdrawn(rcd):
  '''Currently, the presence of 'withdrawal_date' means withdrawal occurred.'''
  return rcd.get('withdrawal_date')

def create_jira_ticket(redcap_env, projectid, rcd):
  name_first = rcd['name_first']
  name_last = rcd['name_last']
  mrn = rcd['mrn']
  name_mrn = name_first + ' ' + name_last + ' (' + mrn + ')'
  date_withdrawn = calc_date_withdrawn(rcd)
  env_tag = aou_common.get_env_tag_for_handler(str(redcap_env + str(projectid)))
  jira_spec = aou_config.get(env_tag).get('jira-spec')
  jira_project = aou_config.get(env_tag).get('jira-project')
  jira_summary = study_details.get('pi')
  protocol_num = study_details.get('protocol-number')
  if env_tag != 'prod' and jira_project == 'OBC':
    jira_summary += jira_test_msg
  additional_fields = {}
  if jira_project == 'OBC':
    additional_fields['customfield_10190'] = name_mrn
    additional_fields['customfield_10070'] = protocol_num
    additional_fields['customfield_10191'] = date_withdrawn
    # customfield_10193 below is Withdrawal Reason; 10424 means "Pt. Withdrew"
    additional_fields['customfield_10193'] = {'id': '10424'}
  result = jira.create_issue(jira_spec
                            ,jira_project
                            ,jira_kind
                            ,jira_summary
                            ,None              # exclude description
                            ,None              # exclude assignee
                            ,additional_fields)
  try:
    ks.send_email(aou_config.get(env_tag).get('jira-ping-from-email')
        ,aou_config.get(env_tag).get('jira-ping-to-email')
        ,'jira withdrawal result'
        ,str(result) + "\n" + "record: "+rcd['record_id'] + "\n" + str(redcap_env + str(projectid)))
  except Exception, ex:
    log.error('Attempting to send Jira ping email but failed: ' + str(ex))
  if result.get('status') != 201:
    raise Exception(str(result))
  log.info('Created Jira withdrawal ticket; details: {}'.format(result))
  return result

def should_create_jira_ticket(redcap_env, pid, rcd):
  '''IF withdrawal_date is not empty
     AND flag is db is missing or set to 'no'
     THEN create a new Jira withdrawal ticket.'''
  if rcd.get('withdrawal_date','') != '':
      if not have_created_jira_ticket(redcap_env, pid, rcd['record_id']):
        log.info('This is a new withdrawal.')
        return True
      else:
        log.info('Participant withdrawn but Jira withdrawal ticket'\
                 ' already created sometime in the past.')
        return False
  else:
    log.info('Determination: this is not a withdrawal event.')
  return False

#------------------------------------------------------------------------------
# driver

def go(req):
  '''The incoming request-shaped map should have these keys:
      o client_ip         core
      o method            core
      o path              core
      o redcap_env        from redcap_aou_handler
      o project_id        from redcap_aou_handler
      o det_payload       added by redcap_intake_workflow
      o record            added by redcap_intake_workflow 
  This function returns this same request with an additional
  key-value pair:
      o new_withdrawal  value of 'yes' or 'no'
  ''' 
  log.info('Entered.')
  redcap_env = req['redcap_env']
  project_id = req['project_id']
  # In newer REDCap versions, sometimes record is a list;
  # we only want first part in that case.
  record = {}
  if type(req['record']) is list:
    record = req['record'][0]
  else:
    record = req['record']
  record_id = record['record_id']
  try:
    log.info('About to run should_create_jira_ticket function.')
    if should_create_jira_ticket(redcap_env, project_id, record):
      log.info('About to create withdrawal ticket.')
      rslt = create_jira_ticket(redcap_env, project_id, record)
      log.info('Created ticket; will update flag in database.')
      set_jira_ticket_created_flag(redcap_env, project_id, record_id)
      log.info('{} flag set for {}'.format(eav_attrname_jira, record_id))
      req['new_withdrawal'] = 'yes'
    else:
      log.info('This was not deemed a new withdrawal. No action taken.')
      req['new_withdrawal'] = 'no'
  except Exception, ex:
    log.exception(ex)
    raise ex
  log.info('Exiting.')
  return req

