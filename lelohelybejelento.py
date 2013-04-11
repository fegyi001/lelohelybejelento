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
C:\QuantumGIS_Lisboa\bin
pyrcc4 -o "C:\Users\gergely.padanyi\.qgis\python\plugins\LelohelyBejelento\resources.py" "C:\Users\gergely.padanyi\.qgis\python\plugins\LelohelyBejelento\resources.qrc"
pyuic4 -o "C:\Users\gergely.padanyi\.qgis\python\plugins\LelohelyBejelento\ui_lelohelybejelento.py" "C:\Users\gergely.padanyi\.qgis\python\plugins\LelohelyBejelento\ui_lelohelybejelento.ui"
pyuic4 -o "C:\Users\fegyi\.qgis\python\plugins\LelohelyBejelento\ui_lelohelybejelento.py" "C:\Users\fegyi\.qgis\python\plugins\LelohelyBejelento\ui_lelohelybejelento.ui"

When your plugin is ready to be shared with the QGIS community, upload it to the QGIS plugin repository at http://plugins.qgis.org/plugins. Make sure to package it properly in zip format and test the zip before adding it to the repository.
When you add it to the repository, your plugin will show up in the Plugin Installer in QGIS, making it available for download and install by the community.
"""

# Import the PyQt and QGIS libraries
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from lelohelybejelentodialog import LelohelyBejelentoDialog

#other imports
import locale
import re
import math
import os

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class LelohelyBejelento:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # refernce to map canvas
        self.canvas = self.iface.mapCanvas()

        # the identify tool will emit a QgsPoint on every click
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        # create our GUI dialog
        self.dlg = LelohelyBejelentoDialog()
        # create a list to hold our selected feature ids
        self.selectList = []
        # current layer ref (set in handleLayerChange)
        self.cLayer = None
        # current layer dataProvider ref (set in handleLayerChange)
        self.provider = None
        #maprenderer and composition
        self.mapRenderer = self.canvas.mapRenderer()
        self.c = QgsComposition(self.mapRenderer)
        self.printer = QPrinter()
        self.printer.setOrientation(QPrinter.Portrait)
        #self.printer.setPaperSize(QPrinter.A4)

        self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "python/plugins/lelohelybejelento"
        self.qgis_dir = str(QgsApplication.applicationDirPath())
        self.svg_dir = str(QgsApplication.svgPath())

        # initialize locale
        localePath = ""
        locale = QSettings().value("locale/userLocale").toString()[0:2]

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/lelohelybejelento_" + locale + ".qm"

        if QFileInfo(localePath).exists():
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        #start with the first tab
        self.dlg.ui.tabWidget.setCurrentIndex(0)

        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/lelohelybejelento/icon.png"), u"Lelőhely-bejelentő készítő", self.iface.mainWindow())

        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)
        self.dlg.ui.SavePDFButton.clicked.connect(self.savePDF)
        self.dlg.ui.PDFMapPrint.clicked.connect(self.printPDFMap)
        self.dlg.ui.Errors.clicked.connect(self.printErrors)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Lelőhely-bejelentő", self.action)

        # connect to the currentLayerChanged signal of QgsInterface
        result = QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.handleLayerChange)

        # connect to the selectFature custom function to the map canvas click event
        QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&Lelőhely-bejelentő", self.action)
        self.iface.removeToolBarIcon(self.action)

    def handleLayerChange(self, layer):
        self.cLayer = self.canvas.currentLayer()
        if self.cLayer:
            self.provider = self.cLayer.dataProvider()

    def selectFeature(self, point, button):
        # reset selection list on each new selection2
        self.clearFields() #clear all fields except those which were checked
        self.selectList = []
        pntGeom = QgsGeometry.fromPoint(point)
        pntBuff = pntGeom.buffer( (self.canvas.mapUnitsPerPixel() * 2),0)
        rect = pntBuff.boundingBox()
        if self.cLayer:
            self.allLayers = self.canvas.layers()
            #self.createCPG(self.cLayer)
            self.feat = QgsFeature()
            # create the select statement
            self.provider.select([],rect) # the arguments mean no attributes returned, and do a bbox filter with our buffered rectangle to limit the amount of features
            while self.provider.nextFeature(self.feat):
                # if the feat geom returned from the selection intersects our point then put it in a list
                if self.feat.geometry().intersects(pntBuff):
                    self.selectList.append(self.feat.id())
            if self.selectList:
                # make the actual selection
                self.cLayer.setSelectedFeatures([self.selectList[0]])
                self.bbox = self.cLayer.boundingBoxOfSelected()
                self.bboxCenter = self.bbox.center()
                if self.bbox.width() > self.bbox.height():
                    self.dlg.ui.PDFMapOrientationTip.setText(u'Javasolt: fekvő')
                else:
                    self.dlg.ui.PDFMapOrientationTip.setText(u'Javasolt: álló')
                #coordinate system check
                self.crsEPSG = self.cLayer.crs().epsg()
                if self.crsEPSG == 0:    #if the layer has no coordinate system
                    self.dlg.setCRSAzon(u"Ismeretlen")
                    QMessageBox.information(self.iface.mainWindow(), u"Ismeretlen koordinátarendszer", u"<center>A kiválasztott elemet tartalmazó réteghez nem tartozik ismert vetületi rendszer!<center>")
                else:
                    self.crsDescr = self.cLayer.crs().description()
                    self.crsLong = "EPSG:%s - %s" % (self.crsEPSG, self.crsDescr)
                    self.dlg.setCRSAzon(self.crsLong)

                    if self.crsEPSG != 23700:
                        QMessageBox.information(self.iface.mainWindow(), u"Hibás koordinátarendszer", u"<center>A kiválasztott elemet tartalmazó réteg nem EOV vetületi rendszerű<br />(%s)</center>" % self.crsLong)
                    else:
                        pass
                #fetch attribute values
                self.sList = []
                self.columns = self.provider.fields()
                self.columnKeys = self.columns.keys()
                self.columnValues = self.columns.values()
                #find the attribute column id for column 'NEV', eg. self.nameColumnId = 1
                for colName in self.columnValues:
                    if colName.name() == u'NEV': #the column 'NEV' exists
                        self.nameColumnId = self.columnValues.index(colName)
                        self.sList.append(self.nameColumnId)
                        self.provider.featureAtId(self.feat.id(), self.feat, False, self.sList) #grab 0th feature attributes at 'NEV'
                        self.map = self.feat.attributeMap()
                        for key, value in self.map.items():
                            self.dlg.ui.LeloNev.setText(u"%s" % value.toString())
                    else: #the column 'NEV' doesn't exist
                        self.nameColumnId = None
                        self.dlg.ui.LeloNev.clear()
        else:
                QMessageBox.information( self.iface.mainWindow(), u"Nincs aktív réteg", u"<center>Kérem válassza ki a lelőhelyeket tartalmazó réteget!<center>" )

    def writeData(self):
        if self.columnValues == None: #it doesn't exist
            pass
        else:
            pass
        self.caps = self.cLayer.dataProvider().capabilities()
        self.selFeat = self.cLayer.selectedFeatures()[0] #the first selected feature
        self.selFeatId = int(self.selFeat.id()) #eg. 5
        if self.caps & QgsVectorDataProvider.ChangeAttributeValues:
            self.attrs = {1: QVariant(unicode(self.dlg.ui.LeloNev.text()))}
            self.cLayer.dataProvider().changeAttributeValues({self.selFeatId: self.attrs})

        """if self.nameColumnId == None: #if the 'NEV' column doesn't exists
            self.addColumns = [] #list of QgsField objects to be added
            self.nevField = QgsField(u'NEV', QVariant.String) #create the new field as a QgsField object
            self.addColumns.append(self.nevField) #appends the QgsField to the list
            self.provider.addAttributes(self.addColumns) #appends 'NEV' column to the attribute table
            self.canvas.refresh()
            self.feat.addAttribute(0, QVariant(10))
            '''self.columns = self.provider.fields()
            self.columnKeys = self.columns.keys()
            self.columnValues = self.columns.values()
            for colName in self.columnValues:
                if colName == self.nevField:
                    self.nameColumnId == self.columnValues.index(colName)
                else:
                    self.nameColumnId = None
            self.feat.setAttributeMap({self.nameColumnId: QVariant(u'hahahahahaaaaa')})

            #self.feat.setAttributeMap({self.nameColumnId: QVariant(u"kamu lelohely")})'''
        else:
            self.feat.addAttribute(1, QVariant(u"halloo"))
            QMessageBox.information( self.iface.mainWindow(), u"Nincs aktív réteg", u"<center>valamit csináltam!!<center>" )"""

    def createCPG(self, cLayer):
        source = cLayer.source() #C:/Users/Fegyi/.qgis/python/plugins/shp/lh_minta_eov2.shp
        sourceSplit = str(source).split('/') #['C:', 'Users', 'Fegyi', '.qgis', 'python', 'plugins', 'shp', 'lh_minta_eov2.shp']
        fileName = sourceSplit[-1] #'lh_minta_eov2.shp'
        del sourceSplit[-1] #['C:', 'Users', 'Fegyi', '.qgis', 'python', 'plugins', 'shp']
        extensionSplit = fileName.split('.') #['lh_minta_eov2', 'shp']
        del extensionSplit[-1] #remaining ['lh_minta_eov2']
        extensionSplit.append('cpg') #['lh_minta_eov2', 'cpg']
        cpgJoin = '.'.join(extensionSplit) #'lh_minta_eov2.cpg'
        sourceSplit.append(cpgJoin) #['C:', 'Users', 'Fegyi', '.qgis', 'python', 'plugins', 'shp', 'lh_minta_eov2.cpg']
        finalFileName = '/'.join(sourceSplit) #'C:/Users/Fegyi/.qgis/python/plugins/shp/lh_minta_eov2.cpg'

        open(finalFileName, "w").close() #empty the file
        f = open(finalFileName, "w") #open the file
        f.write(u"UTF-8") #insert this line
        f.close() #close the file

    def insertItem(self, title, comp, addPos, itemPos, rect1, rect2, hAlign, font, frame): #function to easily insert label items
        comp.addItem(title)
        self.position += addPos
        title.setItemPosition(itemPos, self.position)
        title.setRect(0, 0, rect1, rect2)
        title.setMargin(0)
        title.setHAlign(hAlign)
        title.setFont(font)
        title.setFrameEnabled(frame)
        pen = QPen()
        pen.setWidthF(0.1)
        pen.setJoinStyle(Qt.MiterJoin)
        title.setPen(pen)

    def checkMultilines(self, item, rect1):
        font = item.font()
        textWidth = item.textWidthMillimeters(font, item.text()) + 10 #the +10 is needed only in some cases, but it is best left there
        if textWidth > rect1:
            sorok = int(math.ceil(textWidth / rect1))
            multisor = sorok * 4.3 #maybe some workaround needed why 4.2
            item.setRect(0, 0, rect1, multisor)
            self.position += multisor - self.sorkoz

    def checkTableMultilines(self, columnList): #columnList: tuple of QgsComposerLabel object and its length in the table
        multiLine = []
        multiLine.append(0) #default is 0, if any multilines has to be added they will be appended here
      for column in columnList:
    		font = column[0].font()
    		textWidth = column[0].textWidthMillimeters(font, column[0].text()) + 5 #the +5 is needed only in some cases, but it is best left there
    		if textWidth > column[1]:
                 sorok = int(math.ceil(textWidth / column[1])) #0 if no plus line needed
                 multiLine.append(sorok)
    	multiLineMax = max(multiLine) #maximum number of multilines eg. [1, 0, 2, 0] --> 2
    	multisor = multiLineMax * 4.3
        if multiLineMax > 0:
            for column in columnList:
                column[0].setRect(0, 0, column[1], multisor)
            self.position += multisor - self.sorkoz
        else:
            pass

    def mmtoinch(self, mm):
        self.inch = mm * 0.0393700787
        return self.inch

    def changeCurrDir(self, newDir):
        self.dirname, self.filename = os.path.split(os.path.abspath(newDir))
        self.dlg.curr_dir = self.dirname

    """print map PDF"""
    def printMapPDFPrintAction(self, composition):
        self.saveMapPDFFileName = QtGui.QFileDialog.getSaveFileName(self.dlg, u'Mentés PDF fájlba', self.dlg.curr_dir, u'PDF Fájlok (*.pdf)') #curr_dir is always the last dir where a pdf file was saved
        self.changeCurrDir(self.saveMapPDFFileName)
        self.mapPDFPrinter = QPrinter()
        self.mapPDFPrinter.setOutputFormat(QPrinter.PdfFormat)
        self.mapPDFPrinter.setPageMargins(25, 25, 25, 25, QPrinter.Millimeter) #left, top, right, bottom, units
        self.mapPDFPrinter.setOutputFileName(self.saveMapPDFFileName)
        self.mapPDFPrinter.setPaperSize(QSizeF(composition.paperWidth(), composition.paperHeight()), QPrinter.Millimeter) #handles size and orientation as well
        self.mapPDFPrinter.setFullPage(True)
        self.mapPDFPrinter.setColorMode(QPrinter.Color)
        self.mapPDFPrinter.setResolution(composition.printResolution())
        self.mapPDFPainter = QPainter(self.mapPDFPrinter)
        self.mapPDFPrinter.setFontEmbeddingEnabled(True)
        #now comes something very important: to print to the whole page!
        self.paperRectMM = QRectF(0, 0, self.pWidth, self.pHeight)
        self.paperRectPixel = QRectF(self.mmtoinch(0)*self.mapPDFPrinter.resolution(), self.mmtoinch(0)*self.mapPDFPrinter.resolution(), self.mmtoinch(self.pWidth)*self.mapPDFPrinter.resolution(), self.mmtoinch(self.pHeight)*self.mapPDFPrinter.resolution())
        composition.render(self.mapPDFPainter, self.paperRectPixel, self.paperRectMM)
        self.mapPDFPainter.end()

    """compose pdf map (portrait or landscape orientation)"""
    def printPDFMap(self):
        #check if the user selected an element or not
        if len(self.selectList) == 0:
            QMessageBox.information(self.iface.mainWindow(), u"Hiba", u"<center>Nem választott ki lelőhelyet!</center>")
            pass
        else:
            self.mapc = QgsComposition(self.mapRenderer)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.pWidth = 210.0
                self.pHeight = 297.0
            else:
                self.pWidth = 297.0
                self.pHeight = 210.0
            self.mapc.setPaperSize(self.pWidth, self.pHeight)
            self.mapc.setPlotStyle(QgsComposition.Print)
            self.mapc.setPrintResolution(int(self.dlg.ui.PDFMapResolution.currentText()))

            #composer map
            self.leptek = int(self.dlg.ui.PDFMapScale.currentText())
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.compWidth = 190
                self.compHeight = 227.5
            else:
                self.compWidth = 272.5
                self.compHeight = 155
            self.composerMap = QgsComposerMap(self.mapc, 0, 0, self.compWidth, self.compHeight)
            #set the extent so that the selected item is in the centre of the map
            self.compWidthMapUnits = (self.leptek / 1000) * self.compWidth #convert the item width to meters
            self.compHeightMapUnits = (self.leptek / 1000) * self.compHeight #convert the item height to meters
            self.compNewExtent = QgsRectangle(self.bboxCenter[0] - (self.compWidthMapUnits / 2), self.bboxCenter[1] - (self.compHeightMapUnits / 2), self.bboxCenter[0] + (self.compWidthMapUnits / 2), self.bboxCenter[1] + (self.compHeightMapUnits / 2))
            self.composerMap.setNewExtent(self.compNewExtent)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.composerMap.setItemPosition(10, 22.5)
            else:
                self.composerMap.setItemPosition(15, 22.5)
            self.mapc.addItem(self.composerMap)
            self.composerMap.setNewScale(self.leptek)
            self.cLayer.removeSelection()
            self.canvas.refresh()

            self.composerMap.setGridEnabled(True)
            self.composerMap.setGridIntervalX(self.leptek * 0.05) #in case of 10000 --> 500 m
            self.composerMap.setGridIntervalY(self.leptek * 0.05)
            self.composerMap.setGridStyle(1) #cross
            self.composerMap.setCrossLength(1.5)
            self.composerMap.setShowGridAnnotation(True)
            self.composerMap.setGridAnnotationDirection(3) #parallel to rectangle
            self.composerMap.setGridAnnotationPosition(1) #distance to rectangle
            self.composerMap.setGridAnnotationPrecision(0)

            #main title
            self.mainTitle = QgsComposerLabel(self.mapc)
            self.mapc.addItem(self.mainTitle)
            self.mainTitle.setText(self.dlg.ui.PDFMapTitle.text())
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.mainTitle.setItemPosition(10, 7.5)
                self.mainTitle.setRect(0, 0, 190, 10)
            else:
                self.mainTitle.setItemPosition(15, 7.5)
                self.mainTitle.setRect(0, 0, 272.5, 10)
            self.mainTitle.setHAlign(4) #align to center horizontally
            self.mainTitle.setVAlign(128)
            self.mainTitleFont = QFont()
            self.mainTitleFont.setPointSize(11)
            self.mainTitleFont.setBold(True)
            self.mainTitle.setFont(self.mainTitleFont)
            self.mainTitle.setFrame(1)
            self.mainTitleBrush = QBrush()
            self.mainTitleBrush.setStyle(Qt.SolidPattern)
            self.mainTitleBrush.setColor(QColor(255, 255, 190))
            self.mainTitle.setBrush(self.mainTitleBrush)
            #self.mainTitlePen = QPen()
            #self.mainTitlePen.setWidthF(1)
            #self.mainTitlePen.setJoinStyle(Qt.MiterJoin)
            #self.mainTitle.setPen(self.mainTitlePen)

            #sub title
            self.subTitle = QgsComposerLabel(self.mapc)
            self.mapc.addItem(self.subTitle)
            self.subTitle.setText(unicode(self.dlg.ui.LeloNev.text()))
            self.subTitleFont = QFont()
            self.subTitleFont.setPointSize(10)
            self.subTitle.setFont(self.subTitleFont)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.subTitle.setItemPosition(90, 255)
                self.subTitle.setRect(0, 0, 110, 25)
            else:
                self.subTitle.setItemPosition(177.5, 182.5)
                self.subTitle.setRect(0, 0, 110, 17.5)
            self.subTitle.setHAlign(4) #align to center horizontally
            self.subTitle.setVAlign(128)
            self.subTitle.setFrame(1)
            self.subTitleBrush = QBrush()
            self.subTitleBrush.setStyle(Qt.SolidPattern)
            self.subTitleBrush.setColor(QColor(190, 232, 255))
            self.subTitle.setBrush(self.subTitleBrush)

            #scale
            self.scale = QgsComposerScaleBar(self.mapc)
            self.scale.setComposerMap(self.composerMap)
            self.mapc.addItem(self.scale)
            self.scale.setStyle('Numeric')
            self.scaleFont = QFont()
            self.scaleFont.setPointSize(12)
            self.scale.setFont(self.scaleFont)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.scale.setItemPosition(10, 255)
                self.scale.setRect(0, 0, 45, 10)
            else:
                self.scale.setItemPosition(15, 182.5)
                self.scale.setRect(0, 0, 40, 7.5)
            self.scale.setAlignment(1) #??
            self.scale.setFrame(0)

            #scalebar
            self.scaleBar = QgsComposerScaleBar(self.mapc)
            self.scaleBar.setComposerMap(self.composerMap)
            self.mapc.addItem(self.scaleBar)
            self.scaleBar.setStyle('Single Box')
            self.scaleBarFont = QFont()
            self.scaleBarFont.setPointSize(8)
            self.scaleBar.setFont(self.scaleBarFont)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.scaleBar.setItemPosition(10, 267.5)
                self.scaleBar.setRect(0, 0, 77.5, 13.7)
            else:
                self.scaleBar.setItemPosition(15, 190)
                self.scaleBar.setRect(0, 0, 157.5, 11.2)
            self.scaleBar.setNumUnitsPerSegment(self.leptek / 50)
            self.scaleBar.setNumMapUnitsPerScaleBarUnit(1)
            self.scaleBar.setUnitLabeling(u'méter')
            self.scaleBar.setHeight(2)
            self.scaleBar.setFrame(0)

            #north arrow
            self.northArrow = QgsComposerPicture(self.mapc)
            self.mapc.addItem(self.northArrow)
            if self.dlg.ui.PDFMapOrientation.currentIndex() == 0: #portrait
                self.northArrow.setItemPosition(55, 255)
                self.northArrow.setRect(0, 0, 15, 10.4496)
            else:
                self.northArrow.setItemPosition(57.5, 181.127)
                self.northArrow.setRect(0, 0, 15, 10.4496)
            self.northArrow.setPictureFile(r'%snorth_arrows\north-arrow_3_simple_symmetric_triangular.svg' % self.svg_dir)
            self.northArrow.setFrame(0)

            self.printMapPDFPrintAction(self.mapc)
            self.cLayer.setSelectedFeatures([self.selectList[0]])

    """refresh PDF"""
    def refreshPDFView(self):
        self.dlg.replaceEmptyCells()
        self.mapRenderer = self.canvas.mapRenderer()
        self.c = QgsComposition(self.mapRenderer)
        self.c.setPaperSize(210.0, 297.0)
        #self.paperItem = QgsPaperItem(self.c) --> I don't remember what it is for
        #self.paperItem.initialize() #--> I don't remember what it is for, but there is no method 'initialize', at least not in python
        self.c.setPlotStyle(QgsComposition.Print)

        self.mainTextSize = 10
        self.position = 0 #start position
        self.nagykoz = 1 #space between sections, default: 1
        self.sorkoz = 4.8 #space between lines
        self.szunet = '  ' #space between title and text

        self.TitleFont = QFont()
        self.TitleFont.setFamily("Times New Roman")
        self.TitleFont.setPointSize(14)
        self.SubTitleFont = QFont()
        self.SubTitleFont.setFamily("Times New Roman")
        self.SubTitleFont.setPointSize(8)
        self.TextFont = QFont()
        self.TextFont.setFamily("Times New Roman")
        self.TextFont.setPointSize(self.mainTextSize)
        self.TextFontItalic = QFont()
        self.TextFontItalic.setFamily("Times New Roman")
        self.TextFontItalic.setPointSize(self.mainTextSize)
        self.TextFontItalic.setItalic(True)

        self.mainTitle = QgsComposerLabel(self.c)
        self.insertItem(title=self.mainTitle, comp=self.c, addPos=12.5, itemPos=10, rect1=187.5, rect2=5.5, hAlign=4, font=self.TitleFont, frame=False)
        self.mainTitle.setText(u"LELŐHELY-BEJELENTŐ ADATLAP")
        self.subTitle = QgsComposerLabel(self.c)
        self.insertItem(title=self.subTitle, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4, hAlign=4, font=self.SubTitleFont, frame=False)
        self.subTitle.setText(u"Az 5/2010. (VIII. 18.) NEFMI rendelet 13. § (5) bekezdése és az 5. melléklet szerinti formanyomtatvány")

        self.position += 3

        self.Section01 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section01, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section01.setText(u"1. %s" % self.dlg.ui.Section01.title()) #1. A lelőhely megjelölése
        self.MegyeTelepules = QgsComposerLabel(self.c)
        self.insertItem(title=self.MegyeTelepules, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.MegyeTelepules.setText(u"1.1 Megye, város, település:%s%s megye, %s" % (self.szunet, self.dlg.ui.Megye.currentText(), self.dlg.ui.Telepules.currentText()))
        self.checkMultilines(self.MegyeTelepules, 182.5)
        self.UtcaHazszam = QgsComposerLabel(self.c)
        self.insertItem(title=self.UtcaHazszam, comp=self.c, addPos=self.sorkoz, itemPos=33.5, rect1=164, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.UtcaHazszam.setText(u"utca, házszám:%s%s %s" % (self.szunet, self.dlg.ui.Utca.text(), self.dlg.ui.Hazszam.text()))
        self.checkMultilines(self.UtcaHazszam, 164)
        self.KOHAzon = QgsComposerLabel(self.c)
        self.insertItem(title=self.KOHAzon, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.KOHAzon.setText(u"1.2 Nyilvántartási azonosító száma:%s%s" % (self.szunet, self.dlg.ui.KOHAzon.text()))
        self.checkMultilines(self.KOHAzon, 182.5)

        self.position += self.nagykoz

        self.Section02 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section02, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section02.setText(u"2. %s:%s%s" % (self.dlg.ui.Section02.title(), self.szunet, self.dlg.ui.LeloNev.text())) #2. A lelőhely neve(i)
        self.checkMultilines(self.Section02, 187.5)

        self.position += self.nagykoz

        self.Section03 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section03, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section03.setText(u"3. %s" % self.dlg.ui.Section03.title()) #3. A lelőhely pontos helye (a melléklet térképen berajzolva)
        self.CRSAzon = QgsComposerLabel(self.c)
        self.insertItem(title=self.CRSAzon, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.CRSAzon.setText(u"3.1 %s:%s%s" % (self.dlg.ui.CRSName.text(), self.szunet, self.dlg.ui.CRSAzon.text()))
        self.checkMultilines(self.CRSAzon, 182.5)
        self.EOVSzelveny = QgsComposerLabel(self.c)
        self.insertItem(title=self.EOVSzelveny, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.EOVSzelveny.setText(u"3.2 %s:%s%s" % (self.dlg.ui.MapNumberName.text(), self.szunet, self.dlg.ui.EOVSzelveny.text()))
        self.checkMultilines(self.EOVSzelveny, 182.5)
        self.HRSZ = QgsComposerLabel(self.c)
        self.insertItem(title=self.HRSZ, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.HRSZ.setText(u"3.3 %s:%s%s" % (self.dlg.ui.HRSZName.text(), self.szunet, self.dlg.ui.HRSZ.text()))
        self.checkMultilines(self.HRSZ, 182.5)
        self.FoldrLeirasLabel = QgsComposerLabel(self.c)
        self.insertItem(title=self.FoldrLeirasLabel, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.FoldrLeirasLabel.setText(u"3.4 %s:" % self.dlg.ui.GeoDescriptionName.text())
        self.FoldrLeiras = QgsComposerLabel(self.c)
        self.insertItem(title=self.FoldrLeiras, comp=self.c, addPos=self.sorkoz, itemPos=21, rect1=176.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.FoldrLeiras.setText(self.dlg.ui.FoldrLeiras.toPlainText())
        self.checkMultilines(self.FoldrLeiras, rect1=176.5)
        self.Pontossag = QgsComposerLabel(self.c)
        self.insertItem(title=self.Pontossag, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Pontossag.setText(u"3.5 %s:%s%s" % (self.dlg.ui.AccuracyName.text(), self.szunet, self.dlg.ui.Pontossag.text()))
        self.checkMultilines(self.Pontossag, 182.5)

        self.position += self.nagykoz

        self.Section04 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section04, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section04.setText(u"4. %s" % self.dlg.ui.Section04.title()) #4. A lelőhelyen talált régészeti jelenségek adatai
        self.JellegKorRows = self.dlg.ui.JellegKorTable.rowCount()
        self.JellegKorRange = range(self.JellegKorRows)
        if self.JellegKorRows > 0:
            self.JellegHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.JellegHeader, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=91.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.JellegHeader.setText(u"jellege:")
            self.KorHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.KorHeader, comp=self.c, addPos=0, itemPos=106.25, rect1=91.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.KorHeader.setText(u"kora:")
            for row in self.JellegKorRange:
                self.JellegKorColumnList = [] #create empty list for the columns for multiline check
                self.JellegRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.JellegRow, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=91.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.JellegRow.setText(self.dlg.ui.JellegKorTable.item(row, 0).text())
                self.JellegKorColumnList.append((self.JellegRow, 91.25)) #add tuple to the column list
                self.KorRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.KorRow, comp=self.c, addPos=0, itemPos=106.25, rect1=91.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.KorRow.setText(self.dlg.ui.JellegKorTable.item(row, 1).text())
                self.JellegKorColumnList.append((self.KorRow, 91.25)) #add tuple to the column list
                self.checkTableMultilines(self.JellegKorColumnList) #check for multilines
        else:
            self.Section04.setText(u"4.%s:%s-" % (self.dlg.ui.Section04.title(), self.szunet))

        self.position += self.nagykoz

        self.Section05 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section05, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        if self.dlg.ui.EgyebAllapot.isEnabled():
            self.Section05.setText(u"5. %s:%s%s" % (self.dlg.ui.Section05.title(), self.szunet, self.dlg.ui.EgyebAllapot.text())) #5. A lelőhely állapota
            self.checkMultilines(self.Section05, 187.5)
        else:
            self.Section05.setText(u"5. %s:%s%s" % (self.dlg.ui.Section05.title(), self.szunet, self.dlg.ui.LelohelyAllapot.currentText()))
            self.checkMultilines(self.Section05, 187.5)

        self.position += self.nagykoz

        self.Section06 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section06, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        if self.dlg.ui.EgyebVeszely.isEnabled():
            self.Section06.setText(u"6. %s:%s%s" % (self.dlg.ui.Section06.title(), self.szunet, self.dlg.ui.EgyebVeszely.text())) #6. A lelőhely veszélyeztetettsége
            self.checkMultilines(self.Section06, 187.5)
        else:
            self.Section06.setText(u"6. %s:%s%s" % (self.dlg.ui.Section06.title(), self.szunet, self.dlg.ui.LelohelyVeszely.currentText()))
            self.checkMultilines(self.Section06, 187.5)

        self.position += self.nagykoz

        self.Section07 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section07, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section07.setText(u"7. %s:%s%s" % (self.dlg.ui.Section07.title(), self.szunet, self.dlg.ui.Ismertseg.currentText())) #7. A lelőhely ismertsége
        self.ForrasTableRows = self.dlg.ui.ForrasTable.rowCount()
        self.ForrasTableRange = range(self.ForrasTableRows)
        if self.dlg.ui.Ismertseg.currentIndex() == int(1): #ismertseg = 'ismert'
            if self.ForrasTableRows > 0: #there are rows in the table
                self.ForrasTipusHeader = QgsComposerLabel(self.c)
                self.insertItem(title=self.ForrasTipusHeader, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=20, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
                self.ForrasTipusHeader.setText(u"forrás típ.:")
                self.SzerzoHeader = QgsComposerLabel(self.c)
                self.insertItem(title=self.SzerzoHeader, comp=self.c, addPos=0, itemPos=35, rect1=61.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
                self.SzerzoHeader.setText(u"szerző:")
                self.CimHeader = QgsComposerLabel(self.c)
                self.insertItem(title=self.CimHeader, comp=self.c, addPos=0, itemPos=96.25, rect1=61.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
                self.CimHeader.setText(u"cím:")
                self.JelzetHeader = QgsComposerLabel(self.c)
                self.insertItem(title=self.JelzetHeader, comp=self.c, addPos=0, itemPos=157.5, rect1=40, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
                self.JelzetHeader.setText(u"jelzet:")
                for row in self.ForrasTableRange:
                    self.ForrasTableColumnList = [] #create empty list for the columns for multiline check
                    self.ForrasTipusRow = QgsComposerLabel(self.c)
                    self.insertItem(title=self.ForrasTipusRow, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=20, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                    self.ForrasTipusRow.setText(self.dlg.ui.ForrasTable.item(row, 0).text())
                    self.ForrasTableColumnList.append((self.ForrasTipusRow, 20)) #add tuple to the column list
                    self.SzerzoRow = QgsComposerLabel(self.c)
                    self.insertItem(title=self.SzerzoRow, comp=self.c, addPos=0, itemPos=35, rect1=61.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                    self.SzerzoRow.setText(self.dlg.ui.ForrasTable.item(row, 1).text())
                    self.ForrasTableColumnList.append((self.SzerzoRow, 61.25)) #add tuple to the column list
                    self.CimRow = QgsComposerLabel(self.c)
                    self.insertItem(title=self.CimRow, comp=self.c, addPos=0, itemPos=96.25, rect1=61.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                    self.CimRow.setText(self.dlg.ui.ForrasTable.item(row, 2).text())
                    self.ForrasTableColumnList.append((self.CimRow, 61.25)) #add tuple to the column list
                    self.JelzetRow = QgsComposerLabel(self.c)
                    self.insertItem(title=self.JelzetRow, comp=self.c, addPos=0, itemPos=157.5, rect1=40, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                    self.JelzetRow.setText(self.dlg.ui.ForrasTable.item(row, 3).text())
                    self.ForrasTableColumnList.append((self.JelzetRow, 40)) #add tuple to the column list
                    self.checkTableMultilines(self.ForrasTableColumnList) # check for multilines
            else:
                pass
        else:
            pass

        self.position += self.nagykoz

        self.Section08 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section08, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.TevekenysegTableRows = self.dlg.ui.TevekenysegTable.rowCount()
        self.TevekenysegTableRange = range(self.TevekenysegTableRows)
        if self.TevekenysegTableRows > 0:
            self.Section08.setText(u"8. %s" % self.dlg.ui.Section08.title()) #7. A lelőhelyen végzett tevékenység
            self.EvHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.EvHeader, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=20, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.EvHeader.setText(u"év:")
            self.TevekenyHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.TevekenyHeader, comp=self.c, addPos=0, itemPos=35, rect1=50, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.TevekenyHeader.setText(u"tevékenység:")
            self.NevHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.NevHeader, comp=self.c, addPos=0, itemPos=85, rect1=56.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.NevHeader.setText(u"név:")
            self.MegjegyzesHeader = QgsComposerLabel(self.c)
            self.insertItem(title=self.MegjegyzesHeader, comp=self.c, addPos=0, itemPos=141.25, rect1=56.25, rect2=4.8, hAlign=4, font=self.TextFontItalic, frame=True)
            self.MegjegyzesHeader.setText(u"megjegyzés:")
            for row in self.TevekenysegTableRange:
                self.TevekenysegTableColumnList = [] #create empty list for the columns for multiline check
                self.EvRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.EvRow, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=20, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.EvRow.setText(self.dlg.ui.TevekenysegTable.item(row, 0).text())
                self.TevekenysegTableColumnList.append((self.EvRow, 20)) #add tuple to the column list
                self.TevekenyRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.TevekenyRow, comp=self.c, addPos=0, itemPos=35, rect1=50, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.TevekenyRow.setText(self.dlg.ui.TevekenysegTable.item(row, 1).text())
                self.TevekenysegTableColumnList.append((self.TevekenyRow, 50)) #add tuple to the column list
                self.NevRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.NevRow, comp=self.c, addPos=0, itemPos=85, rect1=56.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.NevRow.setText(self.dlg.ui.TevekenysegTable.item(row, 2).text())
                self.TevekenysegTableColumnList.append((self.NevRow, 56.25)) #add tuple to the column list
                self.MegjegyzesRow = QgsComposerLabel(self.c)
                self.insertItem(title=self.MegjegyzesRow, comp=self.c, addPos=0, itemPos=141.25, rect1=56.25, rect2=4.8, hAlign=4, font=self.TextFont, frame=True)
                self.MegjegyzesRow.setText(self.dlg.ui.TevekenysegTable.item(row, 3).text())
                self.TevekenysegTableColumnList.append((self.MegjegyzesRow, 56.25)) #add tuple to the column list
                self.checkTableMultilines(self.TevekenysegTableColumnList) #check for multilines
        else:
            self.Section08.setText(u"8. %s:%s-" % (self.dlg.ui.Section08.title(), self.szunet))

        self.position += self.nagykoz

        self.Section09 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section09, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        if self.dlg.ui.EgyebMuzeum.isEnabled():
            self.Section09.setText(u"9. %s:%s%s" % (self.dlg.ui.Section09.title(), self.szunet, self.dlg.ui.EgyebMuzeum.text())) #9. A leleteket fogadó múzeum
            self.checkMultilines(self.Section09, 187.5)
        else:
            self.Section09.setText(u"9. %s:%s%s" % (self.dlg.ui.Section09.title(), self.szunet, self.dlg.ui.Muzeum.currentText()))
            self.checkMultilines(self.Section09, 187.5)

        self.position += self.nagykoz

        self.Section10 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section10, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section10.setText(u"10. %s" % self.dlg.ui.Section10.title()) #10. A bejelentő természetes személyazonosító adatai, munkahelye
        self.BejelentoNev = QgsComposerLabel(self.c)
        self.insertItem(title=self.BejelentoNev, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.BejelentoNev.setText(u"10.1 Név:%s%s" % (self.szunet, self.dlg.ui.BejelentoNev.text()))
        self.checkMultilines(self.BejelentoNev, 182.5)
        self.BejelentoMunkahely = QgsComposerLabel(self.c)
        self.insertItem(title=self.BejelentoMunkahely, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.BejelentoMunkahely.setText(u"10.2 Munkahely:%s%s" % (self.szunet, self.dlg.ui.BejelentoMunkahely.text()))
        self.checkMultilines(self.BejelentoMunkahely, 182.5)

        self.position += self.nagykoz
        self.printer.newPage()

        self.Section11 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section11, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section11.setText(u"11. %s:" % self.dlg.ui.Section11.title()) #11. Megjegyzés
        self.Megjegyzes = QgsComposerLabel(self.c)
        self.insertItem(title=self.Megjegyzes, comp=self.c, addPos=self.sorkoz, itemPos=15, rect1=182.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Megjegyzes.setText(u"%s" % self.dlg.ui.Megjegyzes.toPlainText())
        self.checkMultilines(self.Megjegyzes, 182.5)

        self.position += self.nagykoz

        self.Section12 = QgsComposerLabel(self.c)
        self.insertItem(title=self.Section12, comp=self.c, addPos=self.sorkoz, itemPos=10, rect1=187.5, rect2=4.8, hAlign=0, font=self.TextFont, frame=False)
        self.Section12.setText(u"12. %s:%s%s" % (self.dlg.ui.Section12.title(), self.szunet, self.dlg.ui.Datum.text())) #12. A bejelentés kelte
        self.checkMultilines(self.Section12, 187.5)

    def savePDF(self):
        self.refreshPDFView()
        #self.savePDFFileName = QtGui.QFileDialog.getSaveFileName(self.dlg, u'Mentés PDF fájlba', 'C:/Users/fegyi/.qgis/python/plugins/LelohelyBejelento/files', u'PDF Fájlok (*.pdf)')
        #self.savePDFFileName = QtGui.QFileDialog.getSaveFileName(self.dlg, u'Mentés PDF fájlba', 'C:/Users/gergely.padanyi/.qgis/python/plugins/LelohelyBejelento/files', u'PDF Fájlok (*.pdf)')
        self.savePDFFileName = QtGui.QFileDialog.getSaveFileName(self.dlg, u'Mentés PDF fájlba', self.dlg.curr_dir, u'PDF Fájlok (*.pdf)')
        self.changeCurrDir(self.savePDFFileName)
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setPageMargins(25, 25, 25, 25, QPrinter.Millimeter) #left, top, right, bottom, units
        self.printer.setOutputFileName(self.savePDFFileName)
        self.printer.setPaperSize(QSizeF(self.c.paperWidth(), self.c.paperHeight()), QPrinter.Millimeter)
        self.printer.setFullPage(True)
        self.printer.setPrintRange(0) #all pages
        self.printer.setColorMode(QPrinter.Color)
        self.printer.setResolution(150)
        self.printer.setFontEmbeddingEnabled(True)
        #self.paperNumber = int(math.ceil(self.position / self.c.paperHeight()))
        #self.paperNumberRange = range(self.paperNumber)
        self.pdfPainter = QPainter(self.printer)
        self.pdfPainter.begin(self.printer)
        self.paperRectMM = self.printer.pageRect(QPrinter.Millimeter)
        self.paperRectPixel = self.printer.pageRect(QPrinter.DevicePixel)
        self.c.render(self.pdfPainter, self.paperRectPixel, self.paperRectMM)
        self.pdfPainter.end()

    """Find all errors (empty fields)"""
    def checkErrors(self):
        self.OKErrors = []
        if len(self.selectList) == 0: #no elements were selected
            self.OKErrors.append(u'<b>Nincs kijelölve elem!</b>')
        if self.dlg.ui.Megye.currentIndex() == 0:
            self.OKErrors.append(u'Megye')
        if self.dlg.ui.Telepules.currentIndex() == 0:
            self.OKErrors.append(u'Település')
        if self.dlg.ui.LeloNev.text() == '' or self.dlg.ui.LeloNev.text() == '-':
            self.OKErrors.append(u'A lelőhely neve(i)')
        if self.dlg.ui.CRSAzon.text() == '':
            self.OKErrors.append(u'A mellékelt térkép(vetület) fajtája')
        if self.dlg.ui.FoldrLeiras.toPlainText() == '' or self.dlg.ui.FoldrLeiras.toPlainText() == '-':
            self.OKErrors.append(u'Földrajzi leírás')
        if self.dlg.ui.Pontossag.text() == '' or self.dlg.ui.Pontossag.text() == '-':
            self.OKErrors.append(u'Pontosság')
        if self.dlg.ui.JellegKorTable.rowCount() == 0:
            self.OKErrors.append(u'A lelőhelyen található régészeti jelenségek adatai')
        if self.dlg.ui.LelohelyAllapot.currentIndex() == 0:
            self.OKErrors.append(u'A lelőhely állapota')
        if self.dlg.ui.EgyebAllapot.isEnabled() and self.dlg.ui.EgyebAllapot.text() == '':
            self.OKErrors.append(u'A lelőhely állapota (egyéb)')
        if self.dlg.ui.LelohelyVeszely.currentIndex() == 0:
            self.OKErrors.append(u'A lelőhely veszélyeztetettsége')
        if self.dlg.ui.EgyebVeszely.isEnabled() and self.dlg.ui.EgyebVeszely.text() == '':
            self.OKErrors.append(u'A lelőhely veszélyeztetettsége (egyéb)')
        if self.dlg.ui.Ismertseg.currentIndex() == 0:
            self.OKErrors.append(u'A lelőhely ismertsége')
        if self.dlg.ui.Muzeum.currentIndex() == 0:
            self.OKErrors.append(u'A leleteket fogadó múzeum')
        if self.dlg.ui.EgyebMuzeum.isEnabled() and self.dlg.ui.EgyebMuzeum.text() == '':
            self.OKErrors.append(u'A leleteket befogadó múzeum (egyéb)')
        if self.dlg.ui.BejelentoNev.text() == '':
            self.OKErrors.append(u'A bejelentő neve')
        if self.dlg.ui.BejelentoMunkahely.text() == '':
            self.OKErrors.append(u'A bejelentő munkahelye')
        if self.dlg.ui.Datum.text() == '':
            self.OKErrors.append(u'A bejelentés kelte')
        self.allOKErrors = u'<br />'.join(self.OKErrors)

    def printErrors(self):
        self.checkErrors()
        if len(self.OKErrors) > 0:
            QMessageBox.information(self.iface.mainWindow(), u"Hiányos adatok", u"<center>Kérem pótolja a következő hiányosságokat (%s hiba):</center><br />%s" % (str(len(self.OKErrors)), self.allOKErrors))
        else:
            QMessageBox.information(self.iface.mainWindow(), u"Nincs hiba", u"<center>A plugin nem talált hibát</center>")

    """recursive function for error checking"""
    def execRecur(self):
        self.dlg.show() #show the dialog
        result = self.dlg.exec_() #run the dialog event loop
        if result == 1: #see if OK was pressed
            #self.writeData()
            if len(self.selectList) > 0:
                self.selectList = []
                self.cLayer.removeSelection()
            '''self.checkErrors() #check for errors
            if len(self.OKErrors) > 0: #if there are any errors
                QMessageBox.information(self.iface.mainWindow(), u"Hiányos adatok", u"<center>Kérem pótolja a következő hiányosságokat (%s hiba):</center><br />%s" % (str(len(self.OKErrors)), self.allOKErrors))
                self.execRecur() #start this function again
            else:
                self.writeData() #write some data to the attribute table'''

    def clearFields(self):
        self.dlg.ui.tabWidget.setCurrentIndex(0)
        if self.dlg.ui.chckMegye.isChecked(): #if the checkbuttons are checked, save values
            pass
        else:
            self.dlg.ui.Megye.setCurrentIndex(0)
        if self.dlg.ui.chckTelepules.isChecked():
            pass
        else:
            self.dlg.ui.Telepules.setCurrentIndex(0)
        self.dlg.ui.Utca.clear()
        self.dlg.ui.Hazszam.clear()
        self.dlg.ui.KOHAzon.clear()
        self.dlg.ui.LeloNev.clear()
        self.dlg.ui.CRSAzon.clear()
        self.dlg.ui.EOVSzelveny.clear()
        self.dlg.ui.HRSZ.clear()
        self.dlg.ui.FoldrLeiras.clear()
        if self.dlg.ui.chckPontossag.isChecked():
            self.savePontossag = self.dlg.ui.Pontossag.text().trimmed()
            self.dlg.ui.Pontossag.setText(self.savePontossag)
        else:
            self.dlg.ui.Pontossag.clear()
        self.dlg.ui.JellegCombo.setCurrentIndex(0)
        self.dlg.ui.KorCombo.setCurrentIndex(0)
        self.dlg.ui.JellegKorTable.setRowCount(0)
        self.dlg.ui.LelohelyAllapot.setCurrentIndex(0)
        self.dlg.ui.LelohelyVeszely.setCurrentIndex(0)
        self.dlg.ui.Ismertseg.setCurrentIndex(0)
        self.dlg.ui.ForrasTipusValue.setCurrentIndex(0)
        self.dlg.ui.ForrasTable.setRowCount(0)
        self.dlg.ui.TevekenysegTable.setRowCount(0)
        if self.dlg.ui.chckMuzeum.isChecked():
            pass
        else:
            self.dlg.ui.Muzeum.setCurrentIndex(0)
        if self.dlg.ui.chckBejelentoNev.isChecked():
            self.saveBejelentoNev = self.dlg.ui.BejelentoNev.text().trimmed()
            self.dlg.ui.BejelentoNev.setText(self.saveBejelentoNev)
        else:
            self.dlg.ui.BejelentoNev.clear()
        if self.dlg.ui.chckBejelentoMunkahely.isChecked():
            self.saveBejelentoMunkahely = self.dlg.ui.BejelentoMunkahely.text().trimmed()
            self.dlg.ui.BejelentoMunkahely.setText(self.saveBejelentoMunkahely)
        else:
            self.dlg.ui.BejelentoMunkahely.clear()
        self.dlg.ui.Megjegyzes.clear()
        if self.dlg.ui.chckDatum.isChecked():
            self.saveDatum = self.dlg.ui.Datum.text().trimmed()
            self.dlg.ui.Datum.setText(self.saveDatum)
        else:
            self.dlg.ui.Datum.clear()
        if self.dlg.ui.chckPDFMapOrientation.isChecked():
            pass
        else:
            self.dlg.ui.PDFMapOrientation.setCurrentIndex(1)
        if self.dlg.ui.chckPDFMapScale.isChecked():
            pass
        else:
            self.dlg.ui.PDFMapScale.setCurrentIndex(self.dlg.tizezerId)
        if self.dlg.ui.chckPDFMapResolution.isChecked():
            pass
        else:
            self.dlg.ui.PDFMapResolution.setCurrentIndex(2)
        if self.dlg.ui.chckPDFMapTitle.isChecked():
            pass
        else:
            self.dlg.ui.PDFMapTitle.setText(self.dlg.PDFMapTitleDefault)

    # run method that performs all the real work
    def run(self):
        # set the current layer immediately if it exists, otherwise it will be set on user selection
        self.cLayer = self.iface.mapCanvas().currentLayer()
        if self.cLayer:
            self.provider = self.cLayer.dataProvider()
        # make identify the tool we'll use
        self.canvas.setMapTool(self.clickTool)
        #start recursive dialog function
        self.execRecur()
        #if everything is fine, save some settings if checkbox is checked
        self.clearFields()
