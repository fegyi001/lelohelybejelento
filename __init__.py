# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LelohelyBejelento
                                 A QGIS plugin
 Lelőhely-bejelentő készítő modul
                             -------------------
        begin                : 2013-03-08
        copyright            : (C) 2013 by Padányi-Gulyás Gergely
        email                : gergely.padanyi@mnm-nok.gov.hu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def name():
    return u"Lelőhely bejelentő készítő (LBK)"

def description():
    return u"(Hungarian) Lelőhely-bejelentő készítő plugin"

def version():
    return u"Version 0.1"

def icon():
    return u"icon.png"

def qgisMinimumVersion():
    return u"1.8"

def author():
    return u"Padányi-Gulyás Gergely"

def email():
    return u"gergely.padanyi@gmail.com"

def classFactory(iface):
    # load LelohelyBejelento class from file LelohelyBejelento
    from lelohelybejelento import LelohelyBejelento
    return LelohelyBejelento(iface)
