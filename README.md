# Transmitter

Simple middleware for REDCap and other systems to support clinical research data integrations.

This software was developed to facilitate _All of Us_ Research Program efforts at Weill Cornell Medicine. All of Us is a national program designed to gather data from one million or more people living in the United States to accelerate research and improve health. More information here: https://allofus.nih.gov.

## Approach and Concepts

### Philosophy

A data-focused, function-oriented approach has been used.   

Key tasks are packaged in *workflow* functions, which can be chained and carried out serially.

Key data is often passed downstream to later functions via baton (in the form of Python maps).

### Loosely coupled, generalizable libraries

Various functionality has been broken out into loosely coupled individual packages that can be reused in other contexts:

* **metaphor** (HTTPS microframework): https://github.com/wcmc-research-informatics/metaphor
* **kickshaws** (general utilities): https://github.com/wcmc-research-informatics/kickshaws
* **pymysqlwrapper**: https://github.com/wcmc-research-informatics/pymysqlwrapper
* **redcaplib**: https://github.com/wcmc-research-informatics/redcaplib
* **jiralib**: https://github.com/wcmc-research-informatics/jiralib

### Routes and handlers

*A handler is a function that receives a request-shaped map, and returns a response-shaped map.*

It's assumed that a study is associated with one (but possibly more, if dev/test/production versions exist) REDCap projects (or other upstream unit/component). 
For each upstream project, there is a single URL endpoint; in turn, that endpoint is handled by a handler function.

**Setting up routes** — the set of routes (endpoints and handler functions for them) can be configured in `main.py`.

**Mapping REDCap projects of handlers** — Two options:

* 1-to-1: A single handler can be dedicated to a single REDCap project
* 1-to-many: A handler can be configured to handle messages from multiple REDCap projects. This can be done via the `compose_handler` pattern, which takes a REDCap environment string, a PID, and returns a handler function. See the `aou_handler` module.


To understand more about how handlers and routing works, see the documentation for **Metaphor**, the underlying HTTPS framework that Transmitter uses: https://github.com/wcmc-research-informatics/metaphor. The inspiration for Metaphor and the "handler-as-function" convention comes from the Ring library (https://github.com/ring-clojure/ring/wiki/Concepts).

#### Handlers for testing and development

Use these handlers for testing and so forth. Both assume the request comes from REDCap; comment out REDCap-specific logic to use with other source systems.

* `stdout_handler.py` — Write the incoming request to stdout.
* `email_test_handler.py` — Send the contents of the request to an email address, and log the event.

### Workflows

*A workflow is a function that receives a request-shaped map, and returns another request-shaped map with one or more additional key-value pairs inserted.*

The bulk of work happens in workflow modules (a handler is mostly a wrapper for workflows):

* receives a data baton (a request-shaped map);
* does work;
* returns that same baton, potentially with new key-value pairs added.

### Workflow chains

You can run a chain of workflows conveniently using the `run_workflow_chain` function in the `common` module.

### Short-circuit a workflow chain

To take advantage of this short-circuiting, use the `run_workflow_chain` function.

If a workflow returns a map that contains the key `'done'` with the value `'yes'`, no subsequent workflows will be invoked. Instead, `'response'` will be retrieved (it should itself be a response-shaped map) from the map and returned.

**Example use case:** when REDCap sends an empty message to 'test' a new DET endpoint (which can be done in the project configuration), the `redcap_intake_workflow` decides that no further work is needed, and no other workflows are carried out.

### Storing data via the EAV store

`eavstore.py` provides an API for an *entity-attribute-value* (EAV) data store. This allows data (such as flags) to be set by various handlers/projects without the need for
a custom database table, etc.

A new study can be onboarded and make use of the EAV store without needing to make database layout changes.

Actually, it uses an entity-attribute-value-version approach: each version is tagged with a timestamp, so the capability to get the version history of a name-value pair can be implemented if desired.

### Handler tags

In the case of REDCap projects, a handler tag is the combination of these two pieces of data:

* REDCap environment: a four-character string such as 'sand' or 'prod'
* the PID

E.g., 'sand2814'

## Requirements
* Python 2.7
* pip
* virtualenv
* MySQL database


## Deployment and Configuration

### MySQL

Create the `eav` table using `sql/creat-eav-table.sql`.

### Application Folders

Create runtime and staging folders.

~~~
mkdir transmitter-staging
mkdir transmitter
~~~

In the `transmitter` folder, which is where the application will live and will be the working directory for the process, create the enclave folder, which is where all configuration files will live:

~~~
cd transmitter
mkdir enclave
~~~

### Inbox Folder


### enclave/transmitter-config.json

This should be a JSON file with the following structure:

~~~
{"logfile": "log/transmitter.log"
"path-to-key": "/home/pki/private.key"
,"path-to-pem": "/home/pki/public.pem"
,"db-spec":
  { "host" : "localhost"
  , "user" : "X"
  , "password" : "X"
  , "db" : "nihpmi"
  , "charset" : "utf8mb4"
  }
}
~~~

* `"path-to-key"` can be `null` if your .pem file contains all public and private items.


### Handler-specific configuration

Each study should have its own configuration file.


#### enclave/aou-config.json

For the _All of Us_ Research Program, the configuration file is named `aou-config.json` file, which is required and should live in `enclave`.

~~~
{"study-details":
  {"pi": "X"
  ,"protocol-number":"X"
  }
,
"whitelist": ["X","X"]
,
"envs":
  {"prod2911": "test"
  ,"prod2525": "prod"}
,
"test":
  {"redcap-spec":
    {"api-url": "https://server:port/redcap_protocols/api/" 
    ,"token": "X"
    ,"username":"X"}
  ,"jira-spec":
    {"user": "X"
    ,"pass": "X"
    ,"issue-url": "https://server:port/rest/api/2/issue/"}
  ,"jira-project": "X"
  ,"jira-user": "X"
  ,"from-email":""
  ,"to-email": "X"
  ,"jira-ping-from-email":"X"
  ,"jira-ping-to-email": "X"
  }
,"prod":
  {"redcap-spec":
    {"api-url": "https://server:port/redcap_protocols/api/"
    ,"token": "X"
    ,"username":"X"}
  ,"jira-spec":
    {"user": "X"
    ,"pass": "X"
    ,"issue-url": "https://server:port/rest/api/2/issue/"}
  ,"jira-project": "X"
  ,"jira-user": "X"
  ,"from-email":""
  ,"to-email": "X"
  ,"jira-ping-from-email":"X"
  ,"jira-ping-to-email": "X"
  }
}
~~~

Customize the configuration values to suit. 

* The primary email address is for sending notifications of errors (though that might expand in the future).
* The "whitelist" should contain IP addresses, e.g., of REDCap servers.

### virtualenv

Create a virtualenv for the process to run in; from the `transmitter` folder, run:

    mkdir venv
    virtualenv venv

### Deploying code and dependencies

From the `transmitter-staging` folder, run:

~~~
git clone https://github.com/wcmc-research-informatics/transmitter .
~~~

Edit the `deploy.sh` script so that the folders you created are what the
DIR and STAGEDIR variables point to (this will be system-dependent). 

Then activate the virtualenv and run the deploy script(which retrieves dependencies and then copy files over from the staging folder into the live `transmitter` folder):

~~~
source ../transmitter/venv/bin/activate
./deploy.sh
~~~


### Starting the process

Ensure you're inside the virtualenv, then start:

~~~
cd ../transmitter
source venv/bin/activate
nohup python main.py >> out.log 2>&1 &
~~~

You can also configure the process as a daemon; the exact method varies depending on the Linux distro you're using.

## Updating your installation
To pull in the latest version, use the steps detailed in **Deploying code anad dependencies** above, but replace the `git clone ...` command with simply this (again, run this from the `transmitter-staging` folder:

~~~
git pull
~~~

## Logging

Logs are written to the `log` folder, using the filename set in `transmitter-config.json`. The logging process is self-cleaning over time; see the **kickshaws** library for implementation: https://github.com/wcmc-research-informatics/kickshaws.

The log folder is created automatically by `deploy.sh` if it doesn't already exist.

