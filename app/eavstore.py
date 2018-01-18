import pymysqlwrapper as db
from common import *
from kickshaws import *

'''
===============================================================================

-----------------------
      eavstore
-----------------------

This module is a data abstraction layer / API for an
entity-atribute-value (EAV) data store.

What's special about our approach is that we save each 
successive version of an attribute name-value pair, and 
the version history can be queried if desired (to be implemented).

===============================================================================
'''

db_table = 'eav'
db_spec = get_app_config().get('db-spec')

# Should throw exception if there's a database connectivity issue.
# Program should not proceed if so.
db.test_conn(db_spec)

#------------------------------------------------------------------------------

def exists(redcap_env, projectid, recordid, attrname):
  qy1 = '''select count(*) as ttl
          from eav
          where env = %s and projectid = %s
            and recordid = %s
            and attrname = %s	'''
  vals = redcap_env, projectid, recordid, attrname
  ttl =	db.go(db_spec, qy1, vals, db.ReturnKind.SINGLEVAL)
  if ttl > 0: return True
  else: return False

def get_latest_value(redcap_env, projectid, recordid, attrname):
  '''Will return empty string if it can't find anything.'''
  qy2 = '''select ifnull(attrval, 'nil') as attrval
          from eav
          where env = %s and projectid = %s
            and recordid = %s
            and attrname = %s
          order by ts DESC -- put latest value in first row '''
  vals = redcap_env, projectid, recordid, attrname
  # Grab the first value in the first row
  rslt = db.go(db_spec, qy2, vals, db.ReturnKind.SINGLEVAL)
  return rslt

def get_all_versions(redcap_env, projectid, recordid, attrname):
  pass

def put(redcap_env, projectid, recordid, attrname, attrval):
  '''Put a new name-value pair into the store. It will create
  a new version if an older one already exists. Note: returns empty tuple.'''
  stmt = '''insert into eav (env, projectid, recordid, attrname, attrval)
            values (%s, %s, %s, %s, %s) '''
  vals = redcap_env, projectid, recordid, attrname, attrval
  rslt = db.go(db_spec, stmt, vals, commit=True)
  return rslt

