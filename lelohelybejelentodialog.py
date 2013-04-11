# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LelohelyBejelentoDialog
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
"""

import locale
import re
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from ui_lelohelybejelento import Ui_LelohelyBejelento
import listak
import codecs
import os

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

locale.setlocale(locale.LC_ALL, "")

class LelohelyBejelentoDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_LelohelyBejelento()
        self.ui.setupUi(self)
        self.curr_dir = QgsApplication.applicationDirPath()

        """disable some line edits"""
        self.ui.CRSAzon.setEnabled(False)
        self.ui.Datum.setEnabled(False)
        self.ui.PontosJelleg.setEnabled(False)
        self.ui.PontosKor.setEnabled(False)
        self.ui.EgyebAllapot.setEnabled(False)
        self.ui.EgyebVeszely.setEnabled(False)
        self.ui.EgyebMuzeum.setEnabled(False)

        """connections"""
        self.ui.Megye.currentIndexChanged.connect(self.TelepulesToMegye)
        self.ui.JellegCombo.activated.connect(self.enablePontosJelleg)
        self.ui.KorCombo.activated.connect(self.enablePontosKor)
        self.ui.AddJellegKorButton.clicked.connect(self.addJellegKor)
        self.ui.RemoveJellegKorButton.clicked.connect(self.removeJellegKor)
        self.ui.LelohelyAllapot.currentIndexChanged.connect(self.SwitchEgyebAllapot)
        self.ui.LelohelyVeszely.currentIndexChanged.connect(self.SwitchEgyebVeszely)
        self.ui.AddForrasButton.clicked.connect(self.addIsmertseg)
        self.ui.RemoveForrasButton.clicked.connect(self.removeIsmertseg)
        self.ui.AddTevekenysegButton.clicked.connect(self.addTevekenyseg)
        self.ui.RemoveTevekenysegButton.clicked.connect(self.removeTevekenyseg)
        self.ui.Muzeum.currentIndexChanged.connect(self.SwitchEgyebMuzeum)
        self.ui.Calendar.clicked.connect(self.setDate)
        self.ui.SaveToXMLButton.clicked.connect(self.saveFileBrowserDialog)
        self.ui.LoadFromXMLButton.clicked.connect(self.loadFileBrowserDialog)

        """lists"""
        #default option which will be put at the top of some lists
        self.pleaseSelect = u'-- KÉREM VÁLASSZON --'
        self.EgyebText = u'EGYÉB:'
        #create a list from the listak.py, using two sorting: first is to make no difference between upper- and lowercase letters, second is to sort correctly utf8 characters
        #megye
        self.fullMegyeLista = []
        for full in listak.telepulesLista:
            self.fullMegyeLista.append(full[1])
        self.megyeListaSet = list(set(self.fullMegyeLista))
        self.megyeLista = sorted(self.megyeListaSet, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.megyeLista.insert(0, self.pleaseSelect)
        for megye in self.megyeLista:
            self.ui.Megye.insertItem(self.megyeLista.index(megye), QtGui.QApplication.translate("LelohelyBejelento", megye, None, QtGui.QApplication.UnicodeUTF8))
        self.ui.Megye.setCurrentIndex(0)
        #telepules
        self.fullTelepulesLista = []
        for full in listak.telepulesLista:
            self.fullTelepulesLista.append(full[0])
        self.telepulesListaSet = list(set(self.fullTelepulesLista))
        self.telepulesLista = sorted(self.telepulesListaSet, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.telepulesLista.insert(0, self.pleaseSelect)
        for telepules in self.telepulesLista:
            self.ui.Telepules.insertItem(self.telepulesLista.index(telepules), u'%s' % telepules)
        self.ui.Telepules.setCurrentIndex(0)
        #jelleg
        self.jellegLista = sorted(listak.jellegLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.jellegFirst = u'-- JELLEG --'
        self.jellegLista.insert(0, self.jellegFirst)
        self.jellegLista.append(self.EgyebText)
        for jelleg in self.jellegLista:
            self.ui.JellegCombo.insertItem(self.jellegLista.index(jelleg), u'%s' % jelleg)
        self.ui.JellegCombo.setCurrentIndex(0)
        #kor
        self.korLista = listak.korLista
        self.korFirst = u'-- KOR --'
        self.korLista.insert(0, self.korFirst)
        self.EgyebKorText = u'PONTOSABB MEGHATÁROZÁS:'
        self.korLista.append(self.EgyebKorText)
        for kor in self.korLista:
            self.ui.KorCombo.insertItem(self.korLista.index(kor), u'%s' % kor)
        self.ui.KorCombo.setCurrentIndex(0)
        #allapot
        self.allapotLista = sorted(listak.allapotLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.allapotLista.insert(0, self.pleaseSelect)
        self.allapotLista.append(self.EgyebText)
        for allapot in self.allapotLista:
            self.ui.LelohelyAllapot.insertItem(self.allapotLista.index(allapot), u'%s' % allapot)
        self.ui.LelohelyAllapot.setCurrentIndex(0)
        #veszely
        self.veszelyLista = sorted(listak.veszelyLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.veszelyLista.insert(0, self.pleaseSelect)
        self.veszelyLista.append(self.EgyebText)
        for veszely in self.veszelyLista:
            self.ui.LelohelyVeszely.insertItem(self.veszelyLista.index(veszely), u'%s' % veszely)
        self.ui.LelohelyVeszely.setCurrentIndex(0)
        #ismertseg
        self.ismertLista = sorted(listak.ismertLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.ismertLista.insert(0, self.pleaseSelect)
        for ismertseg in self.ismertLista:
            self.ui.Ismertseg.insertItem(self.ismertLista.index(ismertseg), u'%s' % ismertseg)
        self.ui.Ismertseg.setCurrentIndex(0)
        #forras
        self.forrasLista = sorted(listak.forrasLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.forrasLista.insert(0, self.pleaseSelect)
        for forras in self.forrasLista:
           self.ui.ForrasTipusValue.insertItem(self.forrasLista.index(forras), u'%s' % forras)
        self.ui.ForrasTipusValue.setCurrentIndex(0)
        #muzeumok
        self.megyeiMuzeumLista = sorted(listak.megyeiMuzeumLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        self.megyeiMuzeumLista.insert(0, self.pleaseSelect)
        self.megyeiMuzeumLista.append(self.EgyebText)
        for megyeiMuzeum in self.megyeiMuzeumLista:
            self.ui.Muzeum.insertItem(self.megyeiMuzeumLista.index(megyeiMuzeum), u'%s' % megyeiMuzeum)
        self.ui.Muzeum.setCurrentIndex(0)
        #tajolas
        self.tajolasLista = sorted(listak.tajolasLista, key=lambda v: v.upper(), cmp=locale.strcoll)
        for tajolas in self.tajolasLista:
            self.ui.PDFMapOrientation.insertItem(self.tajolasLista.index(tajolas), u'%s' % tajolas)
        self.ui.PDFMapOrientation.setCurrentIndex(1) # 0 == portrait, 1 == landscape, default is landscape
        #meretarany
        self.tizezerId = 0
        self.meretaranyLista = listak.meretaranyLista
        for meretarany in self.meretaranyLista:
            self.ui.PDFMapScale.insertItem(self.meretaranyLista.index(meretarany), u'%s' % str(meretarany))
            if str(meretarany) == u'10000':
                self.tizezerId = self.meretaranyLista.index(meretarany)
        self.ui.PDFMapScale.setCurrentIndex(self.tizezerId)
        #felbontas
        self.felbontasLista = listak.felbontasLista
        for felbontas in self.felbontasLista:
            self.ui.PDFMapResolution.insertItem(self.felbontasLista.index(felbontas), u'%s' % felbontas)
        self.ui.PDFMapResolution.setCurrentIndex(2) #200dpi
        #terkep cime
        self.PDFMapTitleDefault = u'Lelőhely-bejelentő térkép'
        self.ui.PDFMapTitle.setText(self.PDFMapTitleDefault)

    """set Telepules list according to Megye when the user changes the Megye combo box"""
    def TelepulesToMegye(self):
        self.currMegye = self.ui.Megye.currentText()
        self.ui.Telepules.clear()
        if u'%s' % self.currMegye == u'%s' % self.pleaseSelect: #if no megye was chosen, add a full list for the telepules
            #some workaround still needed, not very elegant
            self.fullTelepulesLista = []
            for full in listak.telepulesLista:
                self.fullTelepulesLista.append(full[0])
            self.telepulesListaSet = list(set(self.fullTelepulesLista))
            self.telepulesLista = sorted(self.telepulesListaSet, key=lambda v: v.upper(), cmp=locale.strcoll)
            self.telepulesLista.insert(0, self.pleaseSelect)
            for telepules in self.telepulesLista:
                self.ui.Telepules.insertItem(self.telepulesLista.index(telepules), u'%s' % telepules)
        else:
            self.TelepulesToMegyeList = []
            for full in listak.telepulesLista:
                if u'%s' % full[1] == u'%s' % self.currMegye: #find all the telepules from the original list that are in the current megye
                    self.TelepulesToMegyeList.append(full[0])
                else:
                    pass
            self.TelepulesToMegyeList.insert(0, self.pleaseSelect)
            for telepules in self.TelepulesToMegyeList:
                self.ui.Telepules.insertItem(self.TelepulesToMegyeList.index(telepules), u'%s' % telepules)

    """setting Lelohely nev"""
    def setLeloNev(self, output):
        self.ui.LeloNev.setText(u'%s' % output)
    def clearLeloNev(self):
        self.ui.LeloNev.clear()

    """setting coordinate system"""
    def setCRSAzon(self, output):
        self.ui.CRSAzon.setText(u'%s' % output)
    def clearCRSAzon(self):
        self.ui.CRSAzon.clear()

    """jelleg && kor table"""
    def jellegComboValue(self):
        return self.ui.JellegCombo.currentText().trimmed()
    def korComboValue(self):
        return self.ui.KorCombo.currentText().trimmed()
    def pontosJellegValue(self):
        return self.ui.PontosJelleg.text().trimmed()
    def pontosKorValue(self):
        return self.ui.PontosKor.text().trimmed()
    def enablePontosJelleg(self):
        if self.jellegComboValue() == self.EgyebText:
            self.ui.PontosJelleg.setEnabled(True)
            self.ui.PontosJelleg.clear()
        else:
            self.ui.PontosJelleg.setEnabled(False)
            self.ui.PontosJelleg.clear()
    def enablePontosKor(self):
        if self.korComboValue() == self.EgyebKorText:
            self.ui.PontosKor.setEnabled(True)
            self.ui.PontosKor.clear()
        else:
            self.ui.PontosKor.setEnabled(False)
            self.ui.PontosKor.clear()
    def addJellegKor(self):
        self.value0 = self.jellegComboValue()
        if self.value0 == self.EgyebText:
            self.value0 = self.pontosJellegValue()
        self.value1 = self.korComboValue()
        if self.value1 == self.EgyebKorText:
            self.value1 = self.pontosKorValue()
        if self.value0 == self.jellegFirst or self.value1 == self.korFirst or self.value0 == '' or self.value1 == '':
            pass
        else:
            #how many rows are in the table
            self.sorszam = self.ui.JellegKorTable.rowCount()
            #if the jelleg+kor combination exists, do nothing
            self.JellegKorElemek = [] #create empty list
            self.JellegKorRange = range(self.sorszam) #create a range from the row count (0, 1, ...)
            for row in self.JellegKorRange: #iterate over the rows
                self.JellegKorTuple = (self.ui.JellegKorTable.item(row, 0).text(), self.ui.JellegKorTable.item(row, 1).text()) #create a tuple from each rows: (value0, value1)
                self.JellegKorElemek.append((self.JellegKorTuple)) #add the tuple to the list: [(tuple1), (tuple2), ...]
            self.JellegKorInsertTuple = (self.value0, self.value1) #create a tuple from the values that I intend to insert: (value0, value1)
            if self.JellegKorInsertTuple in self.JellegKorElemek: #if the tuple is in the list, do nothing
                pass
            #if the combination does not exist, insert the values into a new row
            else:
                #insert new row to the next place
                self.ui.JellegKorTable.insertRow(self.sorszam)
                #retrieve data from the combo boxes (actual state)
                #add data to the new row
                self.ui.JellegKorTable.setItem(self.sorszam, 0, QtGui.QTableWidgetItem(self.value0))
                self.ui.JellegKorTable.setItem(self.sorszam, 1, QtGui.QTableWidgetItem(self.value1))
    def removeJellegKor(self):
        self.selectedRow = self.ui.JellegKorTable.currentRow()
        self.ui.JellegKorTable.removeRow(self.selectedRow)

    def SwitchEgyebAllapot(self):
        if self.ui.LelohelyAllapot.currentText() == self.EgyebText:
            self.ui.EgyebAllapot.setEnabled(True)
        else:
            self.ui.EgyebAllapot.clear()
            self.ui.EgyebAllapot.setEnabled(False)

    """ismertseg table"""
    def forrasComboValue(self):
        return self.ui.ForrasTipusValue.currentText().trimmed()
    def addIsmertseg(self):
        self.forras = self.forrasComboValue()
        if self.forras == self.pleaseSelect:
            pass
        else:
            self.ismertsegSorszam = self.ui.ForrasTable.rowCount()
            self.ui.ForrasTable.insertRow(self.ismertsegSorszam)
            self.ui.ForrasTable.setItem(self.ismertsegSorszam, 0, QtGui.QTableWidgetItem(self.forras))
    def removeIsmertseg(self):
        self.selectedForrasRow = self.ui.ForrasTable.currentRow()
        self.ui.ForrasTable.removeRow(self.selectedForrasRow)

    """tevekenyseg table"""
    def addTevekenyseg(self):
        self.tevekenysegSorszam = self.ui.TevekenysegTable.rowCount()
        self.ui.TevekenysegTable.insertRow(self.tevekenysegSorszam)
    def removeTevekenyseg(self):
        self.selectedTevekenysegRow = self.ui.TevekenysegTable.currentRow()
        self.ui.TevekenysegTable.removeRow(self.selectedTevekenysegRow)

    def SwitchEgyebVeszely(self):
        if self.ui.LelohelyVeszely.currentText() == self.EgyebText:
            self.ui.EgyebVeszely.setEnabled(True)
        else:
            self.ui.EgyebVeszely.clear()
            self.ui.EgyebVeszely.setEnabled(False)

    def SwitchEgyebMuzeum(self):
        if self.ui.Muzeum.currentText() == self.EgyebText:
            self.ui.EgyebMuzeum.setEnabled(True)
        else:
            self.ui.EgyebMuzeum.clear()
            self.ui.EgyebMuzeum.setEnabled(False)

    """Calendar widget"""
    def setDate(self):
        self.selDate = self.ui.Calendar.selectedDate().toString('yyyy.MM.dd.')
        self.ui.Datum.setText(u'%s' % str(self.selDate))

    """replace empty cells with '-' """
    def replaceEmptyCells(self):
        if self.ui.Utca.text() == '':
            self.ui.Utca.setText('-')
        if self.ui.Hazszam.text() == '':
            self.ui.Hazszam.setText('-')
        if self.ui.KOHAzon.text() == '':
            self.ui.KOHAzon.setText('-')
        if self.ui.LeloNev.text() == '':
            self.ui.LeloNev.setText('-')
        if self.ui.CRSAzon.text() == '':
            self.ui.CRSAzon.setText(u'ismeretlen')
        if self.ui.EOVSzelveny.text() == '':
            self.ui.EOVSzelveny.setText('-')
        if self.ui.HRSZ.text() == '':
            self.ui.HRSZ.setText('-')
        if self.ui.FoldrLeiras.toPlainText() == '':
            self.ui.FoldrLeiras.setPlainText('-')
        if self.ui.Pontossag.text() == '':
            self.ui.Pontossag.setText('-')
        if self.ui.BejelentoNev.text() == '':
            self.ui.BejelentoNev.setText('-')
        if self.ui.BejelentoMunkahely.text() == '':
            self.ui.BejelentoMunkahely.setText('-')
        if self.ui.Megjegyzes.toPlainText() == '':
            self.ui.Megjegyzes.setPlainText('-')
        if self.ui.Datum.text() == '':
            self.ui.Datum.setText('-')
        if self.ui.PDFMapTitle.text() == '':
            self.ui.PDFMapTitle.setText('-')

    def changeCurrDir(self, newDir):
        if(newDir):
            self.dirname, self.filename = os.path.split(os.path.abspath(newDir))
            self.curr_dir = self.dirname
        else:
            pass

    """save to XML button press"""
    def saveFileBrowserDialog(self):
        self.saveFileName = QtGui.QFileDialog.getSaveFileName(self, u'Mentés XML fájlba', self.curr_dir, u'XML Fájlok (*.xml)')
        self.changeCurrDir(self.saveFileName)
        #self.saveFileName = QtGui.QFileDialog.getSaveFileName(self, u'Mentés XML fájlba', 'C:/Users/fegyi/.qgis/python/plugins', u'XML Fájlok (*.xml)')
        self.saveFName = codecs.open(self.saveFileName, "w", "utf-8")

        self.replaceEmptyCells()

        self.saveFName.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.saveFName.write('<metadata xml:lang="hu">\n')

        self.saveFName.write('<Section01 title="' + unicode(self.ui.Section01.title()) + '">\n')
        self.saveFName.write('<Megye>' + unicode(self.ui.Megye.currentText()) + '</Megye>\n')
        self.saveFName.write('<Telepules>' + unicode(self.ui.Telepules.currentText()) + '</Telepules>\n')
        self.saveFName.write('<Utca>' + unicode(self.ui.Utca.text()) + '</Utca>\n')
        self.saveFName.write('<Hazszam>' + unicode(self.ui.Hazszam.text()) + '</Hazszam>\n')
        self.saveFName.write('<KOHAzon>' + unicode(self.ui.KOHAzon.text()) + '</KOHAzon>\n')
        self.saveFName.write('</Section01>\n')

        self.saveFName.write('<Section02 title="' + unicode(self.ui.Section02.title()) + '">\n')
        self.saveFName.write('<LeloNev>' + unicode(self.ui.LeloNev.text()) + '</LeloNev>\n')
        self.saveFName.write('</Section02>\n')

        self.saveFName.write('<Section03 title="' + unicode(self.ui.Section03.title()) + '">\n')
        self.saveFName.write('<CRSAzon>' + unicode(self.ui.CRSAzon.text()) + '</CRSAzon>\n')
        self.saveFName.write('<EOVSzelveny>' + unicode(self.ui.EOVSzelveny.text()) + '</EOVSzelveny>\n')
        self.saveFName.write('<HRSZ>' + unicode(self.ui.HRSZ.text()) + '</HRSZ>\n')
        self.saveFName.write('<FoldrLeiras>' + unicode(self.ui.FoldrLeiras.toPlainText()) + '</FoldrLeiras>\n')
        self.saveFName.write('<Pontossag>' + unicode(self.ui.Pontossag.text()) + '</Pontossag>\n')
        self.saveFName.write('</Section03>\n')

        self.saveFName.write('<Section04 title="' + unicode(self.ui.Section04.title()) + '">\n')
        #iterate over the JellegKor table rows
        self.JellegKorTableRowCount = self.ui.JellegKorTable.rowCount() #number of rows
        self.RangeJellegKorTableRowCount = range(self.JellegKorTableRowCount) #create range from the number of rows: range(8) = [0, 1, 2, ...7]
        for rowCount in self.RangeJellegKorTableRowCount: #iterate over rows
            self.saveFName.write('<JellegKor%s>\n' % str(rowCount))
            self.saveFName.write('<Jelleg%s>' % str(rowCount) + unicode(self.ui.JellegKorTable.item(rowCount, 0).text()) + '</Jelleg%s>\n' % str(rowCount))
            self.saveFName.write('<Kor%s>' % str(rowCount) + unicode(self.ui.JellegKorTable.item(rowCount, 1).text()) + '</Kor%s>\n' % str(rowCount))
            self.saveFName.write('</JellegKor%s>\n' % str(rowCount))
        self.saveFName.write('</Section04>\n')

        self.saveFName.write('<Section05 title="' + unicode(self.ui.Section05.title()) + '">\n')
        if self.ui.EgyebAllapot.isEnabled():
            self.saveFName.write('<LelohelyAllapot>' + unicode(self.ui.EgyebAllapot.text()) + '</LelohelyAllapot>\n')
        else:
            self.saveFName.write('<LelohelyAllapot>' + unicode(self.ui.LelohelyAllapot.currentText()) + '</LelohelyAllapot>\n')
        self.saveFName.write('</Section05>\n')

        self.saveFName.write('<Section06 title="' + unicode(self.ui.Section06.title()) + '">\n')
        if self.ui.EgyebVeszely.isEnabled():
            self.saveFName.write('<LelohelyVeszely>' + unicode(self.ui.EgyebVeszely.text()) + '</LelohelyVeszely>\n')
        else:
            self.saveFName.write('<LelohelyVeszely>' + unicode(self.ui.LelohelyVeszely.currentText()) + '</LelohelyVeszely>\n')
        self.saveFName.write('</Section06>\n')

        """Section07: A lelőhely ismertsége"""
        self.saveFName.write('<Section07 title="' + unicode(self.ui.Section07.title()) + '">\n')
        self.saveFName.write('<Ismertseg>%s</Ismertseg>' % unicode(self.ui.Ismertseg.currentText()))
        self.ForrasTableRowCount = self.ui.ForrasTable.rowCount()
        self.RangeForrasTableRowCount = range(self.ForrasTableRowCount)
        for rowCount in self.RangeForrasTableRowCount:
            self.saveFName.write('<Forrasok%s>\n' % str(rowCount))
            self.saveFName.write('<ForrasTipus%s>' % str(rowCount) + unicode(self.ui.ForrasTable.item(rowCount, 0).text()) + '</ForrasTipus%s>\n' % str(rowCount))
            self.saveFName.write('<Szerzo%s>' % str(rowCount) + unicode(self.ui.ForrasTable.item(rowCount, 1).text()) + '</Szerzo%s>\n' % str(rowCount))
            self.saveFName.write('<Cim%s>' % str(rowCount) + unicode(self.ui.ForrasTable.item(rowCount, 2).text()) + '</Cim%s>\n' % str(rowCount))
            self.saveFName.write('<Jelzet%s>' % str(rowCount) + unicode(self.ui.ForrasTable.item(rowCount, 3).text()) + '</Jelzet%s>\n' % str(rowCount))
            self.saveFName.write('</Forrasok%s>\n' % str(rowCount))
        self.saveFName.write('</Section07>\n')

        self.saveFName.write('<Section08 title="' + unicode(self.ui.Section08.title()) + '">\n')
        self.TevekenysegTableRowCount = self.ui.TevekenysegTable.rowCount()
        self.RangeTevekenysegTableRowCount = range(self.TevekenysegTableRowCount)
        for rowCount in self.RangeTevekenysegTableRowCount:
            self.saveFName.write('<Tevekenyseg%s>\n' % str(rowCount))
            self.saveFName.write('<Ev%s>' % str(rowCount) + unicode(self.ui.TevekenysegTable.item(rowCount, 0).text()) + '</Ev%s>\n' % str(rowCount))
            self.saveFName.write('<Tevekeny%s>' % str(rowCount) + unicode(self.ui.TevekenysegTable.item(rowCount, 1).text()) + '</Tevekeny%s>\n' % str(rowCount))
            self.saveFName.write('<Nev%s>' % str(rowCount) + unicode(self.ui.TevekenysegTable.item(rowCount, 2).text()) + '</Nev%s>\n' % str(rowCount))
            self.saveFName.write('<Megjegyzes%s>' % str(rowCount) + unicode(self.ui.TevekenysegTable.item(rowCount, 3).text()) + '</Megjegyzes%s>\n' % str(rowCount))
            self.saveFName.write('</Tevekenyseg%s>\n' % str(rowCount))
        self.saveFName.write('</Section08>\n')

        self.saveFName.write('<Section09 title="' + unicode(self.ui.Section09.title()) + '">\n')
        if self.ui.EgyebMuzeum.isEnabled():
            self.saveFName.write('<Muzeum>' + unicode(self.ui.EgyebMuzeum.text()) + '</Muzeum>\n')
        else:
            self.saveFName.write('<Muzeum>' + unicode(self.ui.Muzeum.currentText()) + '</Muzeum>\n')
        self.saveFName.write('</Section09>\n')

        self.saveFName.write('<Section10 title="' + unicode(self.ui.Section10.title()) + '">\n')
        self.saveFName.write('<BejelentoNev>' + unicode(self.ui.BejelentoNev.text()) + '</BejelentoNev>\n')
        self.saveFName.write('<BejelentoMunkahely>' + unicode(self.ui.BejelentoMunkahely.text()) + '</BejelentoMunkahely>\n')
        self.saveFName.write('</Section10>\n')

        self.saveFName.write('<Section11 title="' + unicode(self.ui.Section11.title()) + '">\n')
        self.saveFName.write('<Megjegyzes>' + unicode(self.ui.Megjegyzes.toPlainText()) + '</Megjegyzes>\n')
        self.saveFName.write('</Section11>\n')

        self.saveFName.write('<Section12 title="' + unicode(self.ui.Section12.title()) + '">\n')
        self.saveFName.write('<Datum>' + unicode(self.ui.Datum.text()) + '</Datum>\n')
        self.saveFName.write('</Section12>\n')

        self.saveFName.write('</metadata>\n')
        self.saveFName.close()

    """load from XML button press"""
    #how to retrieve the desired string from the xml file using regular expressions
    def ItemLoad(self, Item, MyString):
        self.ItemLine = re.findall("<%s>.*$" % Item, MyString, re.MULTILINE) #find all the lines that has the attribute like eg. <LeloNev>
        self.ItemLine0 = self.ItemLine[0] #chose the first found element
        self.ItemToLoad = re.split('<|>', self.ItemLine0)[2] #split the element eg. <LeloNev>Lapos-hegy</LeloNev> -> Lapos-hegy
        return self.ItemToLoad

    #how to retrieve the desired combo box index
    def ComboBoxLoad(self, ComboBox, ComboElement):
        self.ComboBoxCount = ComboBox.count() #count number of elements in combo box
        self.ComboBoxCountRange = range(self.ComboBoxCount) #create range, eg. count=8 -> range(8) = (0, 1, 2...7)
        for element in self.ComboBoxCountRange: #iterate over elements
            if ComboElement in ComboBox.itemText(element): #if the desired string is among the elements
                self.ComboBoxIndex = element #get the index of the combo box element
        return self.ComboBoxIndex

    def loadFileBrowserDialog(self):
        self.loadFileName = QtGui.QFileDialog.getOpenFileName(self, u'Betöltés XML fájlból', self.curr_dir, u'XML Fájlok (*.xml)') #open dialog
        self.changeCurrDir(self.loadFileName)
        #self.loadFileName = QtGui.QFileDialog.getOpenFileName(self, u'Betöltés XML fájlból', r'C:\Users\fegyi\.qgis\python\plugins\LelohelyBejelento\files', u'XML Fájlok (*.xml)') #open dialog
        self.loadFName = codecs.open(self.loadFileName, "r", "utf-8") #load file
        self.content = self.loadFName.read() #read content and save it into a variable 'content'
        self.loadFName.close() #close the file, the content is still usable

        self.MegyeLoad = self.ItemLoad('Megye', self.content)
        self.MegyeLoadIndex = self.ComboBoxLoad(self.ui.Megye, self.MegyeLoad)
        self.ui.Megye.setCurrentIndex(self.MegyeLoadIndex)

        self.TelepulesLoad = self.ItemLoad('Telepules', self.content)
        self.TelepulesLoadIndex = self.ComboBoxLoad(self.ui.Telepules, self.TelepulesLoad)
        self.ui.Telepules.setCurrentIndex(self.TelepulesLoadIndex)

        self.ui.Utca.clear()
        self.UtcaLoad = self.ItemLoad('Utca', self.content)
        self.ui.Utca.setText(self.UtcaLoad)

        self.ui.Hazszam.clear()
        self.HazszamLoad = self.ItemLoad('Hazszam', self.content)
        self.ui.Hazszam.setText(self.HazszamLoad)

        self.ui.KOHAzon.clear()
        self.KOHAzonLoad = self.ItemLoad('KOHAzon', self.content)
        self.ui.KOHAzon.setText(self.KOHAzonLoad)

        #a click-on is more preferable
        self.ui.LeloNev.clear()
        self.LeloNevLoad = self.ItemLoad('LeloNev', self.content)
        self.ui.LeloNev.setText(self.LeloNevLoad)

        self.ui.EOVSzelveny.clear()
        self.EOVSzelvenyLoad = self.ItemLoad('EOVSzelveny', self.content)
        self.ui.EOVSzelveny.setText(self.EOVSzelvenyLoad)

        self.ui.HRSZ.clear()
        self.HRSZLoad = self.ItemLoad('HRSZ', self.content)
        self.ui.HRSZ.setText(self.HRSZLoad)

        self.ui.FoldrLeiras.clear()
        self.FoldrLeirasLoad = self.ItemLoad('FoldrLeiras', self.content)
        self.ui.FoldrLeiras.setPlainText(self.FoldrLeirasLoad)

        self.ui.Pontossag.clear()
        self.PontossagLoad = self.ItemLoad('Pontossag', self.content)
        self.ui.Pontossag.setText(self.PontossagLoad)

        self.ui.JellegKorTable.clearContents() #clear all text in the table
        self.JellegKorRowCount = self.ui.JellegKorTable.rowCount() #number of rows (they are empty now)
        self.JellegKorRowRange = range(self.JellegKorRowCount) #create a range from number of rows
        for row in self.JellegKorRowRange:
            self.ui.JellegKorTable.removeRow(row) #remove the appropriate row
        self.JellegKorCount = len(re.findall("<JellegKor.*$", self.content, re.MULTILINE)) #how many JellegKor rows are in the xml file, eg. 3
        self.JellegKorCountRange = range(self.JellegKorCount) #in case of 3, it is [0, 1, 2]
        for i in self.JellegKorCountRange:
            self.Jelleg = self.ItemLoad('Jelleg%s' % i, self.content) #find all elements in list that begin with 'Jelleg'
            self.Kor = self.ItemLoad('Kor%s' % i, self.content) #find all elements in list that begin with 'Kor'
            self.ui.JellegKorTable.insertRow(i) #insert row into the appropriate place
            self.ui.JellegKorTable.setItem(i, 0, QtGui.QTableWidgetItem(self.Jelleg)) #insert value into the first column
            self.ui.JellegKorTable.setItem(i, 1, QtGui.QTableWidgetItem(self.Kor)) #insert value into the second column

        self.LelohelyAllapotLoad = self.ItemLoad('LelohelyAllapot', self.content)
        self.LelohelyAllapotIndex = self.ComboBoxLoad(self.ui.LelohelyAllapot, self.LelohelyAllapotLoad)
        if self.ui.LelohelyAllapot.itemText(self.LelohelyAllapotIndex) == self.LelohelyAllapotLoad: #some workaround needed: check if the index is bound to the right string
            self.ui.LelohelyAllapot.setCurrentIndex(self.LelohelyAllapotIndex) #in this case, set the current index correctly
            self.ui.EgyebAllapot.clear()
            self.ui.EgyebAllapot.setEnabled(False)
        else:
            self.ui.LelohelyAllapot.setCurrentIndex(self.ui.LelohelyAllapot.count() - 1) #if this is not the case, set the current index to the last one (count() -1)
            self.ui.EgyebAllapot.setEnabled(True) #enable the Egyeb text line edit
            self.ui.EgyebAllapot.setText(self.LelohelyAllapotLoad) #and load the content

        self.LelohelyVeszelyLoad = self.ItemLoad('LelohelyVeszely', self.content)
        self.LelohelyVeszelyIndex = self.ComboBoxLoad(self.ui.LelohelyVeszely, self.LelohelyVeszelyLoad)
        if self.ui.LelohelyVeszely.itemText(self.LelohelyVeszelyIndex) == self.LelohelyVeszelyLoad:
            self.ui.LelohelyVeszely.setCurrentIndex(self.LelohelyVeszelyIndex)
            self.ui.EgyebVeszely.clear()
            self.ui.EgyebVeszely.setEnabled(False)
        else:
            self.ui.LelohelyVeszely.setCurrentIndex(self.ui.LelohelyVeszely.count() - 1)
            self.ui.EgyebVeszely.setEnabled(True)
            self.ui.EgyebVeszely.setText(self.LelohelyVeszelyLoad)

        self.IsmertsegLoad = self.ItemLoad('Ismertseg', self.content) # some workaround needed
        self.IsmertsegComboCount = self.ui.Ismertseg.count()
        self.IsmertsegComboRange = range(self.IsmertsegComboCount)
        for element in self.IsmertsegComboRange:
            if self.IsmertsegLoad == self.ui.Ismertseg.itemText(element):
                self.IsmertsegLoadIndex = element
        self.ui.Ismertseg.setCurrentIndex(self.IsmertsegLoadIndex)

        self.ui.ForrasTable.clearContents()
        self.ForrasRowCount = self.ui.ForrasTable.rowCount()
        self.ForrasRowRange = range(self.ForrasRowCount)
        for row in self.ForrasRowRange:
            self.ui.ForrasTable.removeRow(row)
        self.ForrasCount = len(re.findall("<Forrasok.*$", self.content, re.MULTILINE))
        self.ForrasCountRange = range(self.ForrasCount)
        for i in self.ForrasCountRange:
            self.ForrasTipus = self.ItemLoad('ForrasTipus%s' % i, self.content)
            self.Szerzo = self.ItemLoad('Szerzo%s' % i, self.content)
            self.Cim = self.ItemLoad('Cim%s' % i, self.content)
            self.Jelzet = self.ItemLoad('Jelzet%s' % i, self.content)
            self.ui.ForrasTable.insertRow(i)
            self.ui.ForrasTable.setItem(i, 0, QtGui.QTableWidgetItem(self.ForrasTipus))
            self.ui.ForrasTable.setItem(i, 1, QtGui.QTableWidgetItem(self.Szerzo))
            self.ui.ForrasTable.setItem(i, 2, QtGui.QTableWidgetItem(self.Cim))
            self.ui.ForrasTable.setItem(i, 3, QtGui.QTableWidgetItem(self.Jelzet))

        self.ui.TevekenysegTable.clearContents()
        self.TevekenysegRowCount = self.ui.TevekenysegTable.rowCount()
        self.TevekenysegRowRange = range(self.TevekenysegRowCount)
        for row in self.TevekenysegRowRange:
            self.ui.TevekenysegTable.removeRow(row)
        self.TevekenysegCount = len(re.findall("<Tevekenyseg.*$", self.content, re.MULTILINE))
        self.TevekenysegCountRange = range(self.TevekenysegCount)
        for i in self.TevekenysegCountRange:
            self.Ev = self.ItemLoad('Ev%s' % i, self.content)
            self.Tevekeny = self.ItemLoad('Tevekeny%s' % i, self.content)
            self.Nev = self.ItemLoad('Nev%s' % i, self.content)
            self.Megjegyzes = self.ItemLoad('Megjegyzes%s' % i, self.content)
            self.ui.TevekenysegTable.insertRow(i)
            self.ui.TevekenysegTable.setItem(i, 0, QtGui.QTableWidgetItem(self.Ev))
            self.ui.TevekenysegTable.setItem(i, 1, QtGui.QTableWidgetItem(self.Tevekeny))
            self.ui.TevekenysegTable.setItem(i, 2, QtGui.QTableWidgetItem(self.Nev))
            self.ui.TevekenysegTable.setItem(i, 3, QtGui.QTableWidgetItem(self.Megjegyzes))

        self.MuzeumLoad = self.ItemLoad('Muzeum', self.content)
        self.MuzeumIndex = self.ComboBoxLoad(self.ui.Muzeum, self.MuzeumLoad)
        if self.ui.Muzeum.itemText(self.MuzeumIndex) == self.MuzeumLoad:
            self.ui.Muzeum.setCurrentIndex(self.MuzeumIndex)
            self.ui.EgyebMuzeum.clear()
            self.ui.EgyebMuzeum.setEnabled(False)
        else:
            self.ui.Muzeum.setCurrentIndex(self.ui.Muzeum.count() - 1)
            self.ui.EgyebMuzeum.setEnabled(True)
            self.ui.EgyebMuzeum.setText(self.MuzeumLoad)

        self.ui.BejelentoNev.clear()
        self.BejelentoNevLoad = self.ItemLoad('BejelentoNev', self.content)
        self.ui.BejelentoNev.setText(self.BejelentoNevLoad)

        self.ui.BejelentoMunkahely.clear()
        self.BejelentoMunkahelyLoad = self.ItemLoad('BejelentoMunkahely', self.content)
        self.ui.BejelentoMunkahely.setText(self.BejelentoMunkahelyLoad)

        self.ui.Megjegyzes.clear()
        self.MegyjegyzesLoad = self.ItemLoad('Megjegyzes', self.content)
        self.ui.Megjegyzes.setPlainText(self.MegyjegyzesLoad)

        self.ui.Datum.clear()
        self.DatumLoad = self.ItemLoad('Datum', self.content)
        self.ui.Datum.setText(self.DatumLoad)
