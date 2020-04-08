#!/usr/bin/env python
# Copyright 2017 ARC Centre of Excellence for Climate Systems Science
# author: Scott Wales <scott.wales@unimelb.edu.au>
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
Database connection functions

.. class:: clef.db.Session

    :class:`sqlalchemy.orm.session.Session` connected to the MAS database

    :func:`connect()` must be called before creating any new sessions
"""

import sqlalchemy
import sqlalchemy.exc

from getpass import getpass
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from .exception import ClefException

#default_url = 'postgresql://clef.nci.org.au:5432/postgres'
default_url = 'postgresql://reidb1.nci.org.au:5432/clef'

Session = sessionmaker()


def connect(url=default_url, user=None, debug=False):
    """Connect to the MAS database and sets up the session

    Args:
        url: Database URL
        user: Username (password will be prompted via ``getpass``)
        debug: Print debugging information

    Returns:
        :class:`sqlalchemy.engine.Engine`
    """
    _url = make_url(url)

    if user is not None:
        """
        Manually specified user
        """
        _url.username = user
        _url.password = getpass("Password for user %s: " % user)

    engine = create_engine(_url, echo=debug)
    Session.configure(bind=engine)

    try:
        c = engine.connect()
        c.close()
    except sqlalchemy.exc.OperationalError:
        raise ClefException('Failed to authenticate with NCI MAS database\n'+
                            'You need to be part of one of the CMIP groups: oi10, al33, rr3.\n'+
                            'If you are already please contact the NCI helpdesk')

    return engine
