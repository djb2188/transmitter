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

-----------------------
AoU Enrollment Workflow
-----------------------

WHAT IT DOES

Determine if a REDCap record indicates enrollment based on
our rule(s); then create an Jira enrollment ticket if we
haven't done so before (we use the database to keep track of
this.) 

The OBC team will then transcribe the participant data into
the CTMS (CREST) as a new enrollment.

WHEN TO USE

Call this workflow after the redcap_intake_workflow.

===============================================================================
'''

log = ks.create_logger(get_log_filepath(), __name__)
aou_config = get_study_config('aou')
study_details = aou_common.get_study_details()

#------------------------------------------------------------------------------
# jira strings when creating tickets

jira_summary = study_details.get('pi')
protocol_num = study_details.get('protocol-number')
jira_test_msg = ' [THIS IS A TEST TICKET; DO NOT PROCESS]'
jira_kind = 'Enrollment'
message = 'This is an automatically generated ticket.  Although PDFs of '\
          'participant consent forms are not available for this study, '\
          'please transcribe participant information from this ticket to '\
          'CREST.  If you have questions or comments, please contact '\
          'its-aou@med.cornell.edu.'
description_template = 'Name: $FIRST$ $LAST$ (MRN: $MRN$)\nDate Enrolled:'\
    ' $DATE_ENROLLED$\nProtocol: {}\n\n{}'.format(protocol_num, message)

eav_attrname_jira = 'jira-enrollment-ticket-created'

#------------------------------------------------------------------------------

def have_created_jira_ticket(redcap_env, projectid, recordid):
  '''Returns true or False'''
  log.info('Checking whether we have created Jira enrollment ticket before'\
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

def store_ticket_id(redcap_env, projectid, recordid, ticket_id):
  '''Store the Jira ticket ID in the db; useful for enrollment
  reconciliation later, etc.'''
  attrname = 'obc-enrollment-ticket-id'
  rslt = eav.put(redcap_env, projectid, recordid, attrname, ticket_id)
  log.info('Stored ticket id [{}] in db for record id [{}]'.format(ticket_id, recordid))
  return rslt

def create_jira_ticket(redcap_env, projectid, rcd):
  '''Creates jira ticket, returns result. Also attaches the jira_spec
  data structure and env_tag to the result for subsequent functions to use.'''
  name_first = rcd['name_first']
  name_last = rcd['name_last']
  mrn = rcd['mrn']
  date_enrolled = today_as_str()  
  if rcd.get('enroll_date', '') != '':
    date_enrolled = rcd.get('enroll_date')
  description = (
      description_template
        .replace('$FIRST$', name_first)
        .replace('$LAST$', name_last)
        .replace('$MRN$', mrn)
        .replace('$DATE_ENROLLED$', date_enrolled))
  env_tag = aou_common.get_env_tag_for_handler(str(redcap_env + str(projectid)))
  jira_spec = aou_config.get(env_tag).get('jira-spec')
  jira_project = aou_config.get(env_tag).get('jira-project')
  my_summary = jira_summary
  if env_tag != 'prod' and jira_project == 'OBC':
    my_summary += jira_test_msg
  additional_fields = {}
  if jira_project == 'OBC':
    additional_fields['customfield_10070'] = protocol_num
  result = jira.create_issue(jira_spec
                            ,jira_project
                            ,jira_kind
                            ,my_summary
                            ,description
                            ,None              # exclude assignee 
                            ,additional_fields)
  try:
    ks.send_email(aou_config.get(env_tag).get('jira-ping-from-email')
        ,aou_config.get(env_tag).get('jira-ping-to-email')
        ,'jira enrollment result'
        ,str(result) + "\n" + "record: "+rcd['record_id'] + "\n" + str(redcap_env + str(projectid)))
  except Exception, ex:
    log.error('Attempting to send Jira ping email but failed: ' + str(ex))
  if result['status'] != 201:
    raise Exception(str(result))
  log.info('Created Jira enrollment ticket; details: {}'.format(result))
  return result

def should_create_jira_ticket(redcap_env, pid, rcd):
  '''Rules:
    If the field "mrn" has a value AND
    If the field "pmi_id_test" has a value AND
    If the field "dob" has a value AND
    If the field "pmi_dob" has a value AND
    If the values of "dob" and "pmi_dob" are equal AND
    If we have NOT previously created a Jira enrollment ticket 
      for the participant ID
    THEN
      create a new Jira enrollment ticket.'''
  if rcd['mrn'] and rcd['pmi_id_test'] and rcd['dob'] and rcd['pmi_dob']:
    if rcd['dob'] == rcd['pmi_dob']:
      if not have_created_jira_ticket(redcap_env, pid, rcd['record_id']):
        log.info('This is a new enrollment.')
        return True
      else:
        log.info('The required fields are present but the database flag'\
          ' indicates an enrollment Jira ticket has already been made.')
    else:
      log.info('Warning: dob and pmi_dob did not match.')
  else:
    log.info('One or more needed fields blank; this is not a new enrollment.')
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
      o new_enrollment    value of 'yes' or 'no'
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
      log.info('This is a new enrollment; will create Jira enrollment ticket.')
      rslt = create_jira_ticket(redcap_env, project_id, record)
      log.info('Created ticket; will insert new data into database (flag and ticket id).')
      ticket_id = json.loads(rslt.get('payload')).get('key') 
      store_ticket_id(redcap_env, project_id, record_id, ticket_id)
      set_jira_ticket_created_flag(redcap_env, project_id, record_id)
      log.info('{} flag set for {}'.format(eav_attrname_jira, record_id))
      req['new_enrollment'] = 'yes'
    else:
      log.info('This was not deemed a new enrollment. No action taken.')
      req['new_enrollment'] = 'no'
  except Exception, ex:
    log.exception(ex)
    raise ex
  log.info('Exiting.')
  return req

#------------------------------------------------------------------------------
# archived

def __not_used__transition_to_begin_crest_reg(jira_spec, ticket_id):
  '''Transitions an OBC Enrollment ticket from "Open" status all the
  way to "In Review (CREST)" status. Returns 204 (an HTTP status)
  if all goes well.'''
  # These are determined by using the following URL, which gives the
  # available transitions for the ticket's current status:
  #   GET /rest/api/2/issue/{issueIdOrKey}/transitions
  transitions = ['61' #'Begin HRBAF Review'
                ,'71' #'Begin Patient Review'
                ,'81'] #'Begin CREST Registration'
  success_status = 204 # this is the HTTP status Jira returns for trans success.
  for trid in transitions:
    rslt = jira.do_transition(jira_spec, ticket_id, trid)
    msg = 'transition {} for ticket {}: {}'.format(trid, ticket_id, str(rslt))
    if rslt.get('status') != success_status:
      log.error(msg)
      return rslt.get('status')
    else:
      log.info(msg)
      #raise Exception('transition {} failed for ticket {}'.format(trid, ticket_id)
  return success_status 

# TODO modify approach so that result arg does not need jira-spec
# loaded into it.
def __not_used__transition_jira_ticket(result):
  '''Transition ticket from Open to Begin CREST Registration;
  This is a higher-level function that in turn ultimately calls
    transition_to_begin_crest_reg().
  Arguments:
    - result: the result from create_jira_ticket, with addl
      items added: jira-spec, and env-tag.
  Returns transition result (straight from jiralib.do_transition)
    ... or {status:'-1'} if we didn't try (e.g. ticket is not OBC, etc.)'''
  if result['status'] != 201:
    return {'status': -1}
  ticket_id = json.loads(result.get('payload')).get('key')
  # This transition is specific to the OBC Jira project.
  if "OBC" not in ticket_id:
    log.info('Will not transition; ticket is not an OBC ticket.')
    return {'status': -1}
  jira_spec = result.get('jira-spec') # should've been added by create_jira_ticket
  env_tag = result.get('env-tag')
  transition_rslt = transition_to_begin_crest_reg(jira_spec, ticket_id)
  msg = 'ticket {} transition result: {}'.format(ticket_id, transition_rslt)
  if transition_rslt == 204: log.info(msg)
  else: log.error(msg)
  # Set assignee -- after transitions, assignee has changed.
  jira_user = aou_config.get(env_tag).get('jira-user')
  log.info('About to set ticket {} to assignee of {}.'\
           ''.format(ticket_id, jira_user))
  assignee_rslt = jira.set_assignee(jira_spec, ticket_id, jira_user)
  if assignee_rslt.get('status') != 204:
    raise Exception('Failed to set ticket {} to assignee {}.'\
                    ''.format(ticket_id, jira_user))
  else: log.info('assignee update was a success.')
  try:
    ks.send_email(aou_config.get(env_tag).get('jira-ping-from-email')
        ,aou_config.get(env_tag).get('jira-ping-to-email')
        ,'jira enrollment transitions result'
        ,str('ticket {} transition result: {}'.format(ticket_id, transition_rslt)))
  except Exception, ex:
    log.error('Attempting to send Jira ping email but failed: ' + str(ex))
  return transition_rslt

