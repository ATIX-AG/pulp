# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
[[wiki]]
title: Jobs RESTful Interface
description: RESTful interface providing access to pulp jobs.
Job object fields:
 * id, str, unique id (usually a uuid) for the job.
 * tasks, list of Task, list of related tasks.
Task object fields:
 * id, str, unique task id
 * job_id, str, the job id
 * class_name, str, name of the class, if the task's method is an instance method
 * method_name, str, name of the pulp library method that was called
 * state, str, one of several valid states of the tasks lifetime: waiting, running, finished, error, timed_out, canceled, reset, suspended
 * failure_threshold, int, number of failures allowed this task before it is no longer scheduled
 * cancel_attempts, int, the number of times cancel was called on this task
 * callable, str, pickled task method
 * args, str, pickled arguments for the task method
 * kwargs, str, picked keyword arguments for the task method
 * progress, object or nil, object representing the pulp library call's progress, nill if no information is available
 * timeout, str, pickled timedelta representing the time limit for the task's run
 * schedule_threshold, str, pickled timedelta representing a max difference between the scheduled_time and start_time before an error is logged
 * _progress_callback, str, pickled method allowing progress information to be recorded by the task
 * start_time, str, pickled datetime showing the start time of the task
 * finish_time, str, pickled datetime showing the finish time of the task
 * result, str, pickled result of the task call
 * exception, str, pickled error, if one occurred
 * traceback, str, pickled traceback, if one occured
"""

import web
import logging
from gettext import gettext as _
from pulp.server import async
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.auth.authorization import READ
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

log = logging.getLogger('pulp')


# jobs controller -------------------------------------------------------------

class Jobs(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        [[wiki]]
        title: Get All Jobs
        description: Get a list of all jobs currently in the system
        method: GET
        path: /jobs/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of job objects
        """
        jobs = {}
        for task in async.all_async():
            job_id = task['job_id']
            if  job_id is None:
                continue
            job = jobs.get(job_id)
            if job is None:
                job = dict(id=job_id, tasks=[])
                jobs[job_id] = job
            job['tasks'].append(task)
        return self.ok(jobs)


class Job(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        [[wiki]]
        title: Get A Job
        description: Get a Job object for a specific job
        method: GET
        path: /jobs/<id>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if no such job
        return: Job object
        """
        found = async.find_async(job_id=id)
        if not found:
            return self.not_found(_('job %s, not-found') % id)
        job = {}
        tasks = []
        job['id'] = id
        job['tasks'] = tasks
        for task in found:
            t = self._task_to_dict(task)
            tasks.append(t)
        return self.ok(job)

# web.py application -----------------------------------------------------------

_urls = (
    '/$', Jobs,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', Job,
)

application = web.application(_urls, globals())
