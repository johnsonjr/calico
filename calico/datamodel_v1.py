# -*- coding: utf-8 -*-
# Copyright 2015 Metaswitch Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
calico.datamodel
~~~~~~~~~~~~~~~~

Shared etcd data-model definitions for version 1 of the data model.

This file is versioned.  The idea is that only back-compatible changes
should be made to this file and non-back-compatible changes should be
made in a new copy of the file with revved version suffix.  That allows
us to maintain multiple copies of the data model in parallel during
migrations.
"""
import logging
import re

_log = logging.getLogger(__name__)

# All Calico data is stored under this path.
ROOT_DIR = "/calico"

# Current versions
FELIX_VERSION = "/v1"
OPENSTACK_VERSION = "/v1"

# OpenStack data is stored under this path.
OPENSTACK_DIR = ROOT_DIR + "/openstack"
OPENSTACK_VERSION_DIR = OPENSTACK_DIR + OPENSTACK_VERSION

# Status data and reporting
FELIX_STATUS_DIR = ROOT_DIR + "/felix" + FELIX_VERSION + "/host"

# Data that flows from orchestrator to felix is stored under a versioned
# sub-tree.
VERSION_DIR = ROOT_DIR + FELIX_VERSION
# Global ready flag.  Stores 'true' or 'false'.
READY_KEY = VERSION_DIR + "/Ready"
# Global config (directory).
CONFIG_DIR = VERSION_DIR + '/config'
HOST_DIR = VERSION_DIR + '/host'
POLICY_DIR = VERSION_DIR + '/policy'
PROFILE_DIR = POLICY_DIR + "/profile"

# Key used for leader election by Neutron mechanism drivers.
NEUTRON_ELECTION_KEY = OPENSTACK_VERSION_DIR + '/neutron_election'

# Regex to match profile rules, capturing the profile ID in capture group
# "profile_id".
RULES_KEY_RE = re.compile(
    r'^' + PROFILE_DIR + r'/(?P<profile_id>[^/]+)/rules')
# Regex to match profile tags, capturing the profile ID in capture group
# "profile_id".
TAGS_KEY_RE = re.compile(
    r'^' + PROFILE_DIR + r'/(?P<profile_id>[^/]+)/tags')
# Regex to match endpoints, captures "hostname" and "endpoint_id".  Works for
# endpoint configuration and endpoint status paths.
ENDPOINT_KEY_RE = re.compile(
    r'^(?:' + HOST_DIR + r'|' + FELIX_STATUS_DIR + r')'
    r'/(?P<hostname>[^/]+)/'
    r'workload/'
    r'(?P<orchestrator>[^/]+)/'
    r'(?P<workload_id>[^/]+)/'
    r'endpoint/(?P<endpoint_id>[^/]+)')

HOST_IP_KEY_RE = re.compile(r'^' + HOST_DIR +
                            r'/(?P<hostname>[^/]+)/bird_ip')

IPAM_V4_CIDR_KEY_RE = re.compile(r'^' + VERSION_DIR +
                                 r'/ipam/v4/pool/(?P<encoded_cidr>[^/]+)')

ENDPOINT_STATUS_UP = "up"
ENDPOINT_STATUS_DOWN = "down"
ENDPOINT_STATUS_ERROR = "error"


def dir_for_host(hostname):
    return HOST_DIR + "/%s" % hostname


def dir_for_per_host_config(hostname):
    return dir_for_host(hostname) + "/config"


def dir_for_felix_status(hostname):
    return FELIX_STATUS_DIR + "/%s" % hostname


def key_for_last_status(hostname):
    return dir_for_felix_status(hostname) + "/last_reported_status"


def key_for_status(hostname):
    return dir_for_felix_status(hostname) + "/status"


def key_for_endpoint(host, orchestrator, workload_id, endpoint_id):
    return (HOST_DIR + "/%s/workload/%s/%s/endpoint/%s" %
            (host, orchestrator, workload_id, endpoint_id))


def key_for_profile(profile_id):
    return PROFILE_DIR + "/" + profile_id


def key_for_profile_rules(profile_id):
    return PROFILE_DIR + "/%s/rules" % profile_id


def key_for_profile_tags(profile_id):
    return PROFILE_DIR + "/%s/tags" % profile_id


def key_for_config(config_name):
    return CONFIG_DIR + "/%s" % config_name


def get_profile_id_for_profile_dir(key):
    """
    :param str key: etcd key.
    :returns The profile ID if this is a profile dir or None if not.
    """
    key = key.rstrip('/')
    if "/" not in key:
        return None
    prefix, final_node = key.rsplit("/", 1)
    return final_node if prefix == PROFILE_DIR else None


def get_endpoint_id_from_key(key):
    m = ENDPOINT_KEY_RE.match(key)
    if m:
        # Got an endpoint.
        host = m.group("hostname")
        orch = m.group("orchestrator")
        workload_id = m.group("workload_id")
        endpoint_id = m.group("endpoint_id")
        combined_id = EndpointId(host, orch, workload_id, endpoint_id)
        return combined_id
    else:
        return None


def hostname_from_status_key(key):
    """
    Get hostname from a status key (or None if this is not a status key).

    :param: key for felix status
            expected key format: FELIX_STATUS_DIR/<hostname>/
                                                      <some path or not>/status
    """
    if not key.startswith(FELIX_STATUS_DIR) or not key.endswith("/status"):
        return None
    in_host_dir = key[len(FELIX_STATUS_DIR + '/'):]
    path = in_host_dir.split('/', 1)
    hostname = path[0]
    return hostname


class EndpointId(object):
    __slots__ = ["host", "orchestrator", "workload", "endpoint"]

    def __init__(self, host, orchestrator, workload, endpoint):
        # We intern these strings since they can occur in many IDs.  The
        # host and orchestrator are trivially repeated for all endpoints
        # on a host.  The others get repeated over time.
        self.host = intern(host.encode("utf8"))
        self.orchestrator = intern(orchestrator.encode("utf8"))
        self.workload = intern(workload.encode("utf8"))
        self.endpoint = intern(endpoint.encode("utf8"))

    @property
    def path_for_status(self):
        return "/".join([FELIX_STATUS_DIR, self.host,
                         "workload", self.orchestrator, self.workload,
                         "endpoint", self.endpoint])

    def __str__(self):
        return self.__class__.__name__ + ("<%s>" % self.endpoint)

    def __repr__(self):
        return self.__class__.__name__ + ("(%r,%r,%r,%r)" % (self.host,
                                                             self.orchestrator,
                                                             self.workload,
                                                             self.endpoint))

    def __eq__(self, other):
        if other is self:
            return True
        if not isinstance(other, EndpointId):
            return False
        return (other.endpoint == self.endpoint and
                other.workload == self.workload and
                other.host == self.host and
                other.orchestrator == self.orchestrator)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.endpoint) + hash(self.workload)
