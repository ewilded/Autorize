from burp import ITab
from burp import IBurpExtender
from burp import IHttpListener
from burp import IContextMenuFactory
from burp import IMessageEditorController
from burp import IHttpRequestResponse
from javax.swing import JList
from javax.swing import JTable
from javax.swing import JFrame
from javax.swing import JLabel
from javax.swing import JPanel
from javax.swing import JButton
from javax.swing import JComboBox
from javax.swing import JCheckBox
from javax.swing import JMenuItem
from javax.swing import JTextArea
from javax.swing import JPopupMenu
from javax.swing import JSplitPane
from javax.swing import JScrollPane
from javax.swing import JTabbedPane
from javax.swing import JFileChooser
from javax.swing import DefaultListModel
from javax.swing import JCheckBoxMenuItem
from threading import Lock
from java.io import File
from java.net import URL
from java.awt import Color
from java.awt import Toolkit
from java.awt.event import ItemListener
from java.awt.event import MouseAdapter
from java.awt.event import ActionListener
from java.awt.event import AdjustmentListener
from java.awt.datatransfer import Clipboard
from java.awt.datatransfer import StringSelection
from javax.swing.border import LineBorder
from javax.swing.table import AbstractTableModel
from java.util import LinkedList
from java.util import ArrayList
from java.lang import Integer
from java.lang import String
from java.lang import Math
from java.awt import Dimension
import re
from thread import start_new_thread
from javax.swing import RowFilter
from javax.swing.table import TableRowSorter
from javax.swing import JScrollPane
from javax.swing import BoxLayout
from java.awt import Font
import csv
import sys
import base64
from javax.swing import SwingUtilities
from java.lang import Runnable

#TODO
# - Disable buttons when saving state/restoring state/export
# - Change messages from "Authorization enforced" to "Enforced"
# - Add full headers in addition to cookies

# This code is necessary to maximize the csv field limit for the save and restore functionality
maxInt = sys.maxsize
decrement = True
while decrement:
    decrement = False
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt/10)
        decrement = True

class BurpExtender(IBurpExtender, ITab, IHttpListener, IMessageEditorController, AbstractTableModel, IContextMenuFactory):

    def registerExtenderCallbacks(self, callbacks):
        # keep a reference to our callbacks object
        self._callbacks = callbacks
        # obtain an extension helpers object
        self._helpers = callbacks.getHelpers()
        
        # set our extension name
        callbacks.setExtensionName("Autorize")
        
        # create the log and a lock on which to synchronize when adding log entries
        self._log = ArrayList()
        self._lock = Lock()
        self._enfocementStatuses = ["Authorization bypass!","Authorization enforced??? (please configure enforcement detector)","Authorization enforced!"]
        self.intercept = 0
        self.lastCookies = ""

        self.initInterceptionFilters()

        self.initEnforcementDetector()

        self.initEnforcementDetectorUnauthorized()

        self.initExport()

        self.initFilter()        

        self.initConfigurationTab()

        self.initTabs()
        
        self.initCallbacks()

        self.currentRequestNumber = 1
        
        print("Thank you for installing Autorize v0.13 extension")
        print("Created by Barak Tawily and Federico Dotta" )
        print("Contributors: Barak Tawily, Federico Dotta, mgeeky, Marcin Woloszyn")
        print("\nGithub:\nhttps://github.com/Quitten/Autorize")
        return

    def initFilter(self):
        """ initi show tab
        """

        filterLModified = JLabel("Modified:")

        filterLUnauthenticated = JLabel("Unauthenticated:")

        self.showAuthBypassModified = JCheckBox("Authorization bypass!")
        self.showAuthBypassModified.setSelected(True)
        self.showAuthBypassModified.addItemListener(tabTableFilter(self))

        self.showAuthPotentiallyEnforcedModified = JCheckBox("Authorization enforced???")
        self.showAuthPotentiallyEnforcedModified.setSelected(True)
        self.showAuthPotentiallyEnforcedModified.addItemListener(tabTableFilter(self))

        self.showAuthEnforcedModified = JCheckBox("Authorization enforced!")
        self.showAuthEnforcedModified.setSelected(True)
        self.showAuthEnforcedModified.addItemListener(tabTableFilter(self))

        self.showAuthBypassUnauthenticated = JCheckBox("Authorization bypass!")
        self.showAuthBypassUnauthenticated.setSelected(True)
        self.showAuthBypassUnauthenticated.addItemListener(tabTableFilter(self))

        self.showAuthPotentiallyEnforcedUnauthenticated = JCheckBox("Authorization enforced???")
        self.showAuthPotentiallyEnforcedUnauthenticated.setSelected(True)
        self.showAuthPotentiallyEnforcedUnauthenticated.addItemListener(tabTableFilter(self))

        self.showAuthEnforcedUnauthenticated = JCheckBox("Authorization enforced!")
        self.showAuthEnforcedUnauthenticated.setSelected(True)
        self.showAuthEnforcedUnauthenticated.addItemListener(tabTableFilter(self))

        self.showDisabledUnauthenticated = JCheckBox("Disabled")
        self.showDisabledUnauthenticated.setSelected(True)
        self.showDisabledUnauthenticated.addItemListener(tabTableFilter(self))        

        self.filterPnl = JPanel()
	self.filterPnl.setLayout(BoxLayout(self.filterPnl,BoxLayout.PAGE_AXIS))

        self.filterPnl.add(filterLModified)
        self.filterPnl.add(filterLUnauthenticated)
        self.filterPnl.add(self.showAuthBypassModified)
        self.filterPnl.add(self.showAuthPotentiallyEnforcedModified)
        self.filterPnl.add(self.showAuthEnforcedModified)
        self.filterPnl.add(self.showAuthBypassUnauthenticated)
        self.filterPnl.add(self.showAuthPotentiallyEnforcedUnauthenticated)
        self.filterPnl.add(self.showAuthEnforcedUnauthenticated)                
        self.filterPnl.add(self.showDisabledUnauthenticated)

    def initExport(self):
        """ init enforcement detector tab
        """

        exportLabel = JLabel("Export:")

        labelFont = exportLabel.getFont()
        boldFont = Font(labelFont.getFontName(), Font.BOLD, labelFont.getSize())
        exportLabel.setFont(boldFont)

        exportLType = JLabel("File Type:")

        exportFileTypes = ["HTML","CSV"]
        self.exportType = JComboBox(exportFileTypes)
	self.exportType.setMaximumSize(Dimension(200,30))

        exportES = ["All Statuses", "As table filter", self._enfocementStatuses[0], self._enfocementStatuses[1], self._enfocementStatuses[2]]
        self.exportES = JComboBox(exportES)
	self.exportES.setMaximumSize(Dimension(700,30))

        exportLES = JLabel("Statuses:")

        self.exportButton = JButton("Export",actionPerformed=self.export)

        saveRestoreLabel = JLabel("Save / Restore:")
        saveRestoreLabel.setFont(boldFont)    

        self.saveStateButton = JButton("Save state",actionPerformed=self.saveStateAction)

        self.restoreStateButton = JButton("Restore state",actionPerformed=self.restoreStateAction)


        self.exportPnl = JPanel()
	self.exportPnl.setLayout(BoxLayout(self.exportPnl,BoxLayout.Y_AXIS))
        self.exportPnl.add(exportLabel)
        self.exportPnl.add(exportLType)
        self.exportPnl.add(self.exportType)
        self.exportPnl.add(exportLES)
        self.exportPnl.add(self.exportES)
        self.exportPnl.add(self.exportButton)
        self.exportPnl.add(saveRestoreLabel)
        self.exportPnl.add(self.saveStateButton)
        self.exportPnl.add(self.restoreStateButton)

    def initEnforcementDetector(self):
        """ init enforcement detector tab
        """

        # These two variable appears to be unused...
        self.EDFP = ArrayList()
        self.EDCT = ArrayList()

        EDLType = JLabel("Type:")

        EDLContent = JLabel("Content:")

        EDLabelList = JLabel("Filter List:")

        EDStrings = ["Headers (simple string): (enforced message headers contains)", "Headers (regex): (enforced message headers contains)", "Body (simple string): (enforced message body contains)", "Body (regex): (enforced message body contains)", "Full response (simple string): (enforced message contains)", "Full response (regex): (enforced message contains)", "Full response length: (of enforced response)"]
        self.EDType = JComboBox(EDStrings)
	self.EDType.setMaximumSize(Dimension(500,30))
       
        self.EDText = JTextArea("", 5, 30)

        scrollEDText = JScrollPane(self.EDText)
        scrollEDText.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)

        self.EDModel = DefaultListModel()
        self.EDList = JList(self.EDModel)

        scrollEDList = JScrollPane(self.EDList)
        scrollEDList.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)
        scrollEDList.setBorder(LineBorder(Color.BLACK)) 

        self.EDAdd = JButton("Add filter",actionPerformed=self.addEDFilter)
        self.EDDel = JButton("Remove filter",actionPerformed=self.delEDFilter)
        self.EDMod = JButton("Modify filter",actionPerformed=self.modEDFilter)

        AndOrStrings = ["And","Or"]
        self.AndOrType = JComboBox(AndOrStrings)
	self.AndOrType.setMaximumSize(Dimension(500,30))

        self.EDPnl = JPanel()
	self.EDPnl.setLayout(BoxLayout(self.EDPnl,BoxLayout.Y_AXIS))
        self.EDPnl.add(EDLType)
        self.EDPnl.add(self.EDType)
        self.EDPnl.add(EDLContent)
        self.EDPnl.add(scrollEDText)
        self.EDPnl.add(self.EDAdd)
        self.EDPnl.add(self.AndOrType)
        self.EDPnl.add(self.EDDel)
        self.EDPnl.add(self.EDMod)
        self.EDPnl.add(EDLabelList)
        self.EDPnl.add(scrollEDList)

    def initEnforcementDetectorUnauthorized(self):
        """ init enforcement detector tab
        """

        EDLType = JLabel("Type:")

        EDLContent = JLabel("Content:")

        EDLabelList = JLabel("Filter List:")

        EDStrings = ["Headers (simple string): (enforced message headers contains)", "Headers (regex): (enforced message headers contains)", "Body (simple string): (enforced message body contains)", "Body (regex): (enforced message body contains)", "Full response (simple string): (enforced message contains)", "Full response (regex): (enforced message contains)", "Full response length: (of enforced response)"]
        self.EDTypeUnauth = JComboBox(EDStrings)
	self.EDTypeUnauth.setMaximumSize(Dimension(500,30))
       
        self.EDTextUnauth = JTextArea("", 5, 30)

        scrollEDTextUnauth = JScrollPane(self.EDTextUnauth)
        scrollEDTextUnauth.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)  

        self.EDModelUnauth = DefaultListModel()
        self.EDListUnauth = JList(self.EDModelUnauth)

        scrollEDListUnauth = JScrollPane(self.EDListUnauth)
        scrollEDListUnauth.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)
        scrollEDListUnauth.setBorder(LineBorder(Color.BLACK))    

        self.EDAddUnauth = JButton("Add filter",actionPerformed=self.addEDFilterUnauth)
        self.EDDelUnauth = JButton("Remove filter",actionPerformed=self.delEDFilterUnauth)
        self.EDModUnauth = JButton("Modify filter",actionPerformed=self.modEDFilterUnauth)

        AndOrStrings = ["And","Or"]
        self.AndOrTypeUnauth = JComboBox(AndOrStrings) 
	self.AndOrTypeUnauth.setMaximumSize(Dimension(500,30))    

        self.EDPnlUnauth = JPanel()
	self.EDPnlUnauth.setLayout(BoxLayout(self.EDPnlUnauth,BoxLayout.Y_AXIS))
        self.EDPnlUnauth.add(EDLType)
        self.EDPnlUnauth.add(self.EDTypeUnauth)
        self.EDPnlUnauth.add(EDLContent)
        self.EDPnlUnauth.add(scrollEDTextUnauth)
        self.EDPnlUnauth.add(self.EDAddUnauth)
        self.EDPnlUnauth.add(self.AndOrTypeUnauth)
        self.EDPnlUnauth.add(self.EDDelUnauth)
        self.EDPnlUnauth.add(self.EDModUnauth)
        self.EDPnlUnauth.add(EDLabelList)
        self.EDPnlUnauth.add(scrollEDListUnauth)        

    def initInterceptionFilters(self):
        """  init interception filters tab
        """

        IFStrings = ["Scope items only: (Content is not required)","URL Contains (simple string): ","URL Contains (regex): ","URL Not Contains (simple string): ","URL Not Contains (regex): "]
        self.IFType = JComboBox(IFStrings)
       
        self.IFModel = DefaultListModel()
        self.IFList = JList(self.IFModel)

        scrollIFList = JScrollPane(self.IFList)
        scrollIFList.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)
        scrollIFList.setBorder(LineBorder(Color.BLACK))

        # Adding some default interception filters
        self.IFModel.addElement("Scope items only: (Content is not required)")
        self.IFModel.addElement("URL Not Contains (regex): \\.js|css|png|jpg|jpeg|gif|woff|map|bmp|ico$")

        self.IFText = JTextArea("", 5, 30)

        scrollIFText = JScrollPane(self.IFText)
        scrollIFText.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)

        IFLType = JLabel("Type:")

        IFLContent = JLabel("Content:")

        IFLabelList = JLabel("Filter List:")

        self.IFAdd = JButton("Add filter",actionPerformed=self.addIFFilter)
        self.IFDel = JButton("Remove filter",actionPerformed=self.delIFFilter)
        self.IFMod = JButton("Modify filter",actionPerformed=self.modIFFilter)

        self.filtersPnl = JPanel()
        self.filtersPnl.setLayout(None)
        self.filtersPnl.add(IFLType)
        self.filtersPnl.add(self.IFType)
        self.filtersPnl.add(IFLContent)
        self.filtersPnl.add(scrollIFText)
        self.filtersPnl.add(self.IFAdd)
        self.filtersPnl.add(self.IFDel)
        self.filtersPnl.add(self.IFMod)
        self.filtersPnl.add(IFLabelList)
        self.filtersPnl.add(scrollIFList)


    def initConfigurationTab(self):
        """  init configuration tab
        """

        self.prevent304 = JCheckBox("Prevent 304 Not Modified status code")
        self.ignore304 = JCheckBox("Ignore 304/204 status code responses")
        self.ignore304.setSelected(True)

        self.autoScroll = JCheckBox("Auto Scroll")

        self.doUnauthorizedRequest = JCheckBox("Check unauthenticated")
        self.doUnauthorizedRequest.setSelected(True)

        startLabel = JLabel("Authorization checks:")
        self.startButton = JButton("Autorize is off",actionPerformed=self.startOrStop)
        self.startButton.setBackground(Color(255, 100, 91, 255))

        self.clearButton = JButton("Clear List",actionPerformed=self.clearList)

        self.replaceString = JTextArea("Cookie: Insert=injected; header=here;", 5, 30)
        self.replaceString.setWrapStyleWord(True)
        self.replaceString.setLineWrap(True)
        scrollReplaceString = JScrollPane(self.replaceString)
        scrollReplaceString.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)

        self.fetchButton = JButton("Fetch cookies from last request", actionPerformed=self.fetchCookies)
        self.fetchButton.setEnabled(False)

        self.filtersTabs = JTabbedPane()
        self.filtersTabs.addTab("Enforcement Detector", self.EDPnl)
        self.filtersTabs.addTab("Detector Unauthenticated", self.EDPnlUnauth)
        self.filtersTabs.addTab("Interception Filters", self.filtersPnl)
        self.filtersTabs.addTab("Table Filter", self.filterPnl)
        self.filtersTabs.addTab("Save/Restore", self.exportPnl)

        self.pnl = JPanel()
        self.pnl.setLayout(BoxLayout(self.pnl, BoxLayout.PAGE_AXIS))
        self.pnl.add(self.startButton)
        self.pnl.add(self.clearButton)
        self.pnl.add(scrollReplaceString)
        self.pnl.add(self.fetchButton)
        self.pnl.add(startLabel)
        self.pnl.add(self.autoScroll)
        self.pnl.add(self.ignore304)
        self.pnl.add(self.prevent304)
        self.pnl.add(self.doUnauthorizedRequest)
        self.pnl.add(self.filtersTabs)

    def initTabs(self):
        """  init autorize tabs
        """
        
        self.logTable = Table(self)

        #self.logTable.setAutoCreateRowSorter(True)        

        tableWidth = self.logTable.getPreferredSize().width        
        self.logTable.getColumn("ID").setPreferredWidth(Math.round(tableWidth / 50 * 2))
        self.logTable.getColumn("Method").setPreferredWidth(Math.round(tableWidth / 50 * 3))
        self.logTable.getColumn("URL").setPreferredWidth(Math.round(tableWidth / 50 * 25))
        self.logTable.getColumn("Orig. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self.logTable.getColumn("Modif. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self.logTable.getColumn("Unauth. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self.logTable.getColumn("Authorization Enforcement Status").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self.logTable.getColumn("Authorization Unauth. Status").setPreferredWidth(Math.round(tableWidth / 50 * 4))

        self.tableSorter = TableRowSorter(self)
        filter = tableFilter(self)
        self.tableSorter.setRowFilter(filter)
        self.logTable.setRowSorter(self.tableSorter)

        self._splitpane = JSplitPane(JSplitPane.HORIZONTAL_SPLIT)
        self._splitpane.setResizeWeight(1)
        self.scrollPane = JScrollPane(self.logTable)
        self._splitpane.setLeftComponent(self.scrollPane)
        self.scrollPane.getVerticalScrollBar().addAdjustmentListener(autoScrollListener(self))

        copyURLitem = JMenuItem("Copy URL")
        copyURLitem.addActionListener(copySelectedURL(self))
        self.menu = JPopupMenu("Popup")
        self.menu.add(copyURLitem)

        self.tabs = JTabbedPane()
        self._requestViewer = self._callbacks.createMessageEditor(self, False)
        self._responseViewer = self._callbacks.createMessageEditor(self, False)

        self._originalrequestViewer = self._callbacks.createMessageEditor(self, False)
        self._originalresponseViewer = self._callbacks.createMessageEditor(self, False)

        self._unauthorizedrequestViewer = self._callbacks.createMessageEditor(self, False)
        self._unauthorizedresponseViewer = self._callbacks.createMessageEditor(self, False)        

        self.tabs.addTab("Modified Request", self._requestViewer.getComponent())
        self.tabs.addTab("Modified Response", self._responseViewer.getComponent())

        self.tabs.addTab("Original Request", self._originalrequestViewer.getComponent())
        self.tabs.addTab("Original Response", self._originalresponseViewer.getComponent())

        self.tabs.addTab("Unauthenticated Request", self._unauthorizedrequestViewer.getComponent())
        self.tabs.addTab("Unauthenticated Response", self._unauthorizedresponseViewer.getComponent())        

        self.tabs.addTab("Configuration", self.pnl)
        self.tabs.setSelectedIndex(6)
        self._splitpane.setRightComponent(self.tabs)

    def initCallbacks(self):
        """  init callbacks
        """

        # register HTTP listener
        self._callbacks.registerHttpListener(self)

        # customize our UI components
        self._callbacks.customizeUiComponent(self._splitpane)
        self._callbacks.customizeUiComponent(self.logTable)
        self._callbacks.customizeUiComponent(self.scrollPane)
        self._callbacks.customizeUiComponent(self.tabs)
        self._callbacks.customizeUiComponent(self.filtersTabs)
        self._callbacks.registerContextMenuFactory(self)

        # add the custom tab to Burp's UI
        self._callbacks.addSuiteTab(self)


    #
    ## Events functions
    #
    def startOrStop(self, event):
        if self.startButton.getText() == "Autorize is off":
            self.startButton.setText("Autorize is on")
            self.startButton.setBackground(Color.GREEN)
            self.intercept = 1
            #self._callbacks.registerHttpListener(self)
        else:
            self.startButton.setText("Autorize is off")
            self.startButton.setBackground(Color(255, 100, 91, 255))
            self.intercept = 0
            #self._callbacks.removeHttpListener(self)

    def addEDFilter(self, event):
        typeName = self.EDType.getSelectedItem().split(":")[0]
        self.EDModel.addElement(typeName + ": " + self.EDText.getText().strip())
        self.EDText.setText("")

    def delEDFilter(self, event):
        index = self.EDList.getSelectedIndex()
        if not index == -1:
            self.EDModel.remove(index)

    def modEDFilter(self, event):
        index = self.EDList.getSelectedIndex()
        if not index == -1:
            valt = self.EDList.getSelectedValue()
            val = valt.split(":")[1].strip()
            if ("Scope items" not in valt) and ("Content-Len" not in valt):
                self.EDText.setText(val)
            self.EDModel.remove(index)

    def addEDFilterUnauth(self, event):
        typeName = self.EDTypeUnauth.getSelectedItem().split(":")[0]
        self.EDModelUnauth.addElement(typeName + ": " + self.EDTextUnauth.getText().strip())
        self.EDTextUnauth.setText("")

    def delEDFilterUnauth(self, event):
        index = self.EDListUnauth.getSelectedIndex()
        if not index == -1:
            self.EDModelUnauth.remove(index)

    def modEDFilterUnauth(self, event):
        index = self.EDListUnauth.getSelectedIndex()
        if not index == -1:
            valt = self.EDListUnauth.getSelectedValue()
            val = valt.split(":")[1].strip()
            if ("Scope items" not in valt) and ("Content-Len" not in valt):
                self.EDTextUnauth.setText(val)
            self.EDModelUnauth.remove(index)

    def addIFFilter(self, event):
        typeName = self.IFType.getSelectedItem().split(":")[0]
        self.IFModel.addElement(typeName + ": " + self.IFText.getText().strip())
        self.IFText.setText("")

    def delIFFilter(self, event):
        index = self.IFList.getSelectedIndex()
        if not index == -1:
            self.IFModel.remove(index)

    def modIFFilter(self, event):
        index = self.IFList.getSelectedIndex()
        if not index == -1:
            valt = self.IFList.getSelectedValue()
            val = valt.split(":")[1].strip()
            if ("Scope items" not in valt) and ("Content-Len" not in valt):
                self.IFText.setText(val)
            self.IFModel.remove(index)

    def clearList(self, event):
        self._lock.acquire()
        oldSize = self._log.size()
        self._log.clear()
        SwingUtilities.invokeLater(UpdateTableEDT(self,"delete",0, oldSize - 1))
        #self.fireTableRowsDeleted(0, oldSize - 1)
        self._lock.release()

    def fetchCookies(self, event):
        if self.lastCookies:
            self.replaceString.setText(self.lastCookies)

    def export(self, event):
        if self.exportType.getSelectedItem() == "HTML":
            self.exportToHTML()
        else:
            self.exportToCSV()

    def saveStateAction(self, event):
        self.saveState()
        
    def restoreStateAction(self, event):
        self.restoreState()            

    def exportToCSV(self):
        parentFrame = JFrame()
        fileChooser = JFileChooser()
        fileChooser.setSelectedFile(File("AutorizeReport.csv"))
        fileChooser.setDialogTitle("Save Autorize Report")
        userSelection = fileChooser.showSaveDialog(parentFrame)
        if userSelection == JFileChooser.APPROVE_OPTION:
            fileToSave = fileChooser.getSelectedFile()

        enforcementStatusFilter = self.exportES.getSelectedItem()
        csvContent = "id\tMethod\tURL\tOriginal length\tModified length\tUnauthorized length\tAuthorization Enforcement Status\tAuthorization Unauthenticated Status\n"

        for i in range(0,self._log.size()):

            if enforcementStatusFilter == "All Statuses":
                csvContent += "%d\t%s\t%s\t%d\t%d\t%d\t%s\t%s\n" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, self._log.get(i)._enfocementStatus, self._log.get(i)._enfocementStatusUnauthorized)
            elif enforcementStatusFilter == "As table filter":                
                if ((self.showAuthBypassModified.isSelected() and "Authorization bypass!" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthPotentiallyEnforcedModified.isSelected() and "Authorization enforced???" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthEnforcedModified.isSelected() and "Authorization enforced!" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthBypassUnauthenticated.isSelected() and "Authorization bypass!" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and "Authorization enforced???" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showAuthEnforcedUnauthenticated.isSelected() and "Authorization enforced!" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showDisabledUnauthenticated.isSelected() and "Disabled" == self._log.get(i)._enfocementStatusUnauthorized)):
                    csvContent += "%d\t%s\t%s\t%d\t%d\t%d\t%s\t%s\n" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, self._log.get(i)._enfocementStatus, self._log.get(i)._enfocementStatusUnauthorized)
            else:
                if (enforcementStatusFilter == self._log.get(i)._enfocementStatus) or (enforcementStatusFilter == self._log.get(i)._enfocementStatusUnauthorized):
                    csvContent += "%d\t%s\t%s\t%d\t%d\t%d\t%s\t%s\n" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, self._log.get(i)._enfocementStatus, self._log.get(i)._enfocementStatusUnauthorized)
        
        f = open(fileToSave.getAbsolutePath(), 'w')
        f.writelines(csvContent)
        f.close()


    def exportToHTML(self):
        parentFrame = JFrame()
        fileChooser = JFileChooser()
        fileChooser.setSelectedFile(File("AutorizeReport.html"))
        fileChooser.setDialogTitle("Save Autorize Report")
        userSelection = fileChooser.showSaveDialog(parentFrame)
        if userSelection == JFileChooser.APPROVE_OPTION:
            fileToSave = fileChooser.getSelectedFile()

        enforcementStatusFilter = self.exportES.getSelectedItem()
        htmlContent = """<html><title>Autorize Report by Barak Tawily</title>
        <style>
        .datagrid table { border-collapse: collapse; text-align: left; width: 100%; }
         .datagrid {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #006699; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; }
         .datagrid table td, .datagrid table th { padding: 3px 10px; }
         .datagrid table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #0070A8; } .datagrid table thead th:first-child { border: none; }.datagrid table tbody td { color: #00496B; border-left: 1px solid #E1EEF4;font-size: 12px;font-weight: normal; }.datagrid table tbody .alt td { background: #E1EEF4; color: #00496B; }.datagrid table tbody td:first-child { border-left: none; }.datagrid table tbody tr:last-child td { border-bottom: none; }.datagrid table tfoot td div { border-top: 1px solid #006699;background: #E1EEF4;} .datagrid table tfoot td { padding: 0; font-size: 12px } .datagrid table tfoot td div{ padding: 2px; }.datagrid table tfoot td ul { margin: 0; padding:0; list-style: none; text-align: right; }.datagrid table tfoot  li { display: inline; }.datagrid table tfoot li a { text-decoration: none; display: inline-block;  padding: 2px 8px; margin: 1px;color: #FFFFFF;border: 1px solid #006699;-webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; }.datagrid table tfoot ul.active, .datagrid table tfoot ul a:hover { text-decoration: none;border-color: #006699; color: #FFFFFF; background: none; background-color:#00557F;}div.dhtmlx_window_active, div.dhx_modal_cover_dv { position: fixed !important; }
        table {
        width: 100%;
        table-layout: fixed;
        }
        td {
            border: 1px solid #35f;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        td.a {
            width: 13%;
            white-space: nowrap;
        }
        td.b {
            width: 9%;
            word-wrap: break-word;
        }
        </style>
        <body>
        <h1>Autorize Report<h1>
        <div class="datagrid"><table>
        <thead><tr><th width=\"3%\">ID</th><th width=\"5%\">Method</th><th width=\"43%\">URL</th><th width=\"9%\">Original length</th><th width=\"9%\">Modified length</th><th width=\"9%\">Unauthorized length</th><th width=\"11%\">Authorization Enforcement Status</th><th width=\"11%\">Authorization Unauthenticated Status</th></tr></thead>
        <tbody>"""

        for i in range(0,self._log.size()):
            color_modified = ""
            if self._log.get(i)._enfocementStatus == self._enfocementStatuses[0]:
                color_modified = "red"
            elif self._log.get(i)._enfocementStatus == self._enfocementStatuses[1]:
                color_modified = "yellow"
            elif self._log.get(i)._enfocementStatus == self._enfocementStatuses[2]:
                color_modified = "LawnGreen"

            color_unauthorized = ""
            if self._log.get(i)._enfocementStatusUnauthorized == self._enfocementStatuses[0]:
                color_unauthorized = "red"
            elif self._log.get(i)._enfocementStatusUnauthorized == self._enfocementStatuses[1]:
                color_unauthorized = "yellow"
            elif self._log.get(i)._enfocementStatusUnauthorized == self._enfocementStatuses[2]:
                color_unauthorized = "LawnGreen"

            if enforcementStatusFilter == "All Statuses":
                htmlContent += "<tr><td>%d</td><td>%s</td><td><a href=\"%s\">%s</a></td><td>%d</td><td>%d</td><td>%d</td><td bgcolor=\"%s\">%s</td><td bgcolor=\"%s\">%s</td></tr>" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, color_modified, self._log.get(i)._enfocementStatus, color_unauthorized, self._log.get(i)._enfocementStatusUnauthorized)
            elif enforcementStatusFilter == "As table filter":
                if ((self.showAuthBypassModified.isSelected() and "Authorization bypass!" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthPotentiallyEnforcedModified.isSelected() and "Authorization enforced???" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthEnforcedModified.isSelected() and "Authorization enforced!" == self._log.get(i)._enfocementStatus) or
                    (self.showAuthBypassUnauthenticated.isSelected() and "Authorization bypass!" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and "Authorization enforced???" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showAuthEnforcedUnauthenticated.isSelected() and "Authorization enforced!" == self._log.get(i)._enfocementStatusUnauthorized) or
                    (self.showDisabledUnauthenticated.isSelected() and "Disabled" == self._log.get(i)._enfocementStatusUnauthorized)):
                    htmlContent += "<tr><td>%d</td><td>%s</td><td><a href=\"%s\">%s</a></td><td>%d</td><td>%d</td><td>%d</td><td bgcolor=\"%s\">%s</td><td bgcolor=\"%s\">%s</td></tr>" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, color_modified, self._log.get(i)._enfocementStatus, color_unauthorized, self._log.get(i)._enfocementStatusUnauthorized)
            else:
                if (enforcementStatusFilter == self._log.get(i)._enfocementStatus) or (enforcementStatusFilter == self._log.get(i)._enfocementStatusUnauthorized):
                    htmlContent += "<tr><td>%d</td><td>%s</td><td><a href=\"%s\">%s</a></td><td>%d</td><td>%d</td><td>%d</td><td bgcolor=\"%s\">%s</td><td bgcolor=\"%s\">%s</td></tr>" % (self._log.get(i)._id, self._log.get(i)._method, self._log.get(i)._url, self._log.get(i)._url, len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, color_modified, self._log.get(i)._enfocementStatus, color_unauthorized, self._log.get(i)._enfocementStatusUnauthorized)

        htmlContent += "</tbody></table></div></body></html>"
        f = open(fileToSave.getAbsolutePath(), 'w')
        f.writelines(htmlContent)
        f.close()

    # Save state
    def saveState(self):

        parentFrame = JFrame()
        fileChooser = JFileChooser()
        fileChooser.setDialogTitle("State output file")
        userSelection = fileChooser.showSaveDialog(parentFrame)
        
        if userSelection == JFileChooser.APPROVE_OPTION:
            
            exportFile = fileChooser.getSelectedFile()

            with open(exportFile.getAbsolutePath(), 'wb') as csvfile:

                csvwriter = csv.writer(csvfile, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)

                for i in range(0,self._log.size()):

                    tempRequestResponseHost = self._log.get(i)._requestResponse.getHttpService().getHost()
                    tempRequestResponsePort = self._log.get(i)._requestResponse.getHttpService().getPort()
                    tempRequestResponseProtocol = self._log.get(i)._requestResponse.getHttpService().getProtocol()
                    tempRequestResponseRequest = base64.b64encode(self._log.get(i)._requestResponse.getRequest())
                    tempRequestResponseResponse = base64.b64encode(self._log.get(i)._requestResponse.getResponse())

                    tempOriginalRequestResponseHost = self._log.get(i)._originalrequestResponse.getHttpService().getHost()
                    tempOriginalRequestResponsePort = self._log.get(i)._originalrequestResponse.getHttpService().getPort()
                    tempOriginalRequestResponseProtocol = self._log.get(i)._originalrequestResponse.getHttpService().getProtocol()
                    tempOriginalRequestResponseRequest = base64.b64encode(self._log.get(i)._originalrequestResponse.getRequest())
                    tempOriginalRequestResponseResponse   = base64.b64encode(self._log.get(i)._originalrequestResponse.getResponse())

                    if self._log.get(i)._unauthorizedRequestResponse is not None:
                        tempUnauthorizedRequestResponseHost = self._log.get(i)._unauthorizedRequestResponse.getHttpService().getHost()
                        tempUnauthorizedRequestResponsePort = self._log.get(i)._unauthorizedRequestResponse.getHttpService().getPort()
                        tempUnauthorizedRequestResponseProtocol = self._log.get(i)._unauthorizedRequestResponse.getHttpService().getProtocol()
                        tempUnauthorizedRequestResponseRequest = base64.b64encode(self._log.get(i)._unauthorizedRequestResponse.getRequest())
                        tempUnauthorizedRequestResponseResponse = base64.b64encode(self._log.get(i)._unauthorizedRequestResponse.getResponse())
                    else:
                        tempUnauthorizedRequestResponseHost = None
                        tempUnauthorizedRequestResponsePort = None
                        tempUnauthorizedRequestResponseProtocol = None
                        tempUnauthorizedRequestResponseRequest = None
                        tempUnauthorizedRequestResponseResponse = None

                    tempEnforcementStatus = self._log.get(i)._enfocementStatus
                    tempEnforcementStatusUnauthorized  = self._log.get(i)._enfocementStatusUnauthorized           

                    tempRow = [tempRequestResponseHost,tempRequestResponsePort,tempRequestResponseProtocol,tempRequestResponseRequest,tempRequestResponseResponse]
                    tempRow.extend([tempOriginalRequestResponseHost,tempOriginalRequestResponsePort,tempOriginalRequestResponseProtocol,tempOriginalRequestResponseRequest,tempOriginalRequestResponseResponse])
                    tempRow.extend([tempUnauthorizedRequestResponseHost,tempUnauthorizedRequestResponsePort,tempUnauthorizedRequestResponseProtocol,tempUnauthorizedRequestResponseRequest,tempUnauthorizedRequestResponseResponse])
                    tempRow.extend([tempEnforcementStatus,tempEnforcementStatusUnauthorized])

                    csvwriter.writerow(tempRow)

    # Restore state
    def restoreState(self):
        parentFrame = JFrame()
        fileChooser = JFileChooser()
        fileChooser.setDialogTitle("State import file")
        userSelection = fileChooser.showDialog(parentFrame,"Restore")
        
        if userSelection == JFileChooser.APPROVE_OPTION:
            importFile = fileChooser.getSelectedFile()

            with open(importFile.getAbsolutePath(), 'r') as csvfile:

                csvreader = csv.reader(csvfile, delimiter='\t', quotechar='|')

                for row in csvreader:

                    tempRequestResponseHost = row[0]
                    tempRequestResponsePort = row[1]
                    tempRequestResponseProtocol = row[2]
                    tempRequestResponseRequest = base64.b64decode(row[3])
                    tempRequestResponseResponse = base64.b64decode(row[4])

                    tempRequestResponseHttpService = self._helpers.buildHttpService(tempRequestResponseHost,int(tempRequestResponsePort),tempRequestResponseProtocol)
                    tempRequestResponse = IHttpRequestResponseImplementation(tempRequestResponseHttpService,tempRequestResponseRequest,tempRequestResponseResponse)

                    tempOriginalRequestResponseHost = row[5]
                    tempOriginalRequestResponsePort = row[6]
                    tempOriginalRequestResponseProtocol = row[7]
                    tempOriginalRequestResponseRequest = base64.b64decode(row[8])
                    tempOriginalRequestResponseResponse   = base64.b64decode(row[9])

                    tempOriginalRequestResponseHttpService = self._helpers.buildHttpService(tempOriginalRequestResponseHost,int(tempOriginalRequestResponsePort),tempOriginalRequestResponseProtocol)
                    tempOriginalRequestResponse = IHttpRequestResponseImplementation(tempOriginalRequestResponseHttpService,tempOriginalRequestResponseRequest,tempOriginalRequestResponseResponse)
                    
                    checkAuthentication = True
                    if row[10] != '':
                        tempUnauthorizedRequestResponseHost = row[10]
                        tempUnauthorizedRequestResponsePort = row[11]
                        tempUnauthorizedRequestResponseProtocol = row[12]
                        tempUnauthorizedRequestResponseRequest = base64.b64decode(row[13])
                        tempUnauthorizedRequestResponseResponse = base64.b64decode(row[14])
                        tempUnauthorizedRequestResponseHttpService = self._helpers.buildHttpService(tempUnauthorizedRequestResponseHost,int(tempUnauthorizedRequestResponsePort),tempUnauthorizedRequestResponseProtocol)
                        tempUnauthorizedRequestResponse = IHttpRequestResponseImplementation(tempUnauthorizedRequestResponseHttpService,tempUnauthorizedRequestResponseRequest,tempUnauthorizedRequestResponseResponse)
                    else:
                        checkAuthentication = False
                        tempUnauthorizedRequestResponse = None                      

                    tempEnforcementStatus = row[15]
                    tempEnforcementStatusUnauthorized  = row[16]

                    self._lock.acquire()
        
                    row = self._log.size()

                    if checkAuthentication:
                        self._log.add(LogEntry(self.currentRequestNumber,self._callbacks.saveBuffersToTempFiles(tempRequestResponse), self._helpers.analyzeRequest(tempRequestResponse).getMethod(), self._helpers.analyzeRequest(tempRequestResponse).getUrl(), self._callbacks.saveBuffersToTempFiles(tempOriginalRequestResponse),tempEnforcementStatus,self._callbacks.saveBuffersToTempFiles(tempUnauthorizedRequestResponse),tempEnforcementStatusUnauthorized))
                    else:
                        self._log.add(LogEntry(self.currentRequestNumber,self._callbacks.saveBuffersToTempFiles(tempRequestResponse), self._helpers.analyzeRequest(tempRequestResponse).getMethod(), self._helpers.analyzeRequest(tempRequestResponse).getUrl(), self._callbacks.saveBuffersToTempFiles(tempOriginalRequestResponse),tempEnforcementStatus,None,tempEnforcementStatusUnauthorized))

                    SwingUtilities.invokeLater(UpdateTableEDT(self,"insert",row,row))
                    #self.fireTableRowsInserted(row, row)
                    self.currentRequestNumber = self.currentRequestNumber + 1
                    self._lock.release()

                lastRow = self._log.size()
                if lastRow > 0:
                    cookies = self.getCookieFromMessage(self._log.get(lastRow - 1)._requestResponse)
                    if cookies:
                        self.lastCookies = cookies
                        self.fetchButton.setEnabled(True)

    #
    # implement IContextMenuFactory
    #
    def createMenuItems(self, invocation):
        responses = invocation.getSelectedMessages()
        if responses > 0:
            ret = LinkedList()
            requestMenuItem = JMenuItem("Send request to Autorize")
            cookieMenuItem = JMenuItem("Send cookie to Autorize")
            requestMenuItem.addActionListener(handleMenuItems(self,responses[0], "request"))
            cookieMenuItem.addActionListener(handleMenuItems(self, responses[0], "cookie"))   
            ret.add(requestMenuItem)
            ret.add(cookieMenuItem)
            return ret
        return None

    #
    # implement ITab
    #
    def getTabCaption(self):
        return "Autorize"
    
    def getUiComponent(self):
        return self._splitpane
        
    #
    # extend AbstractTableModel
    #
    
    def getRowCount(self):
        try:
            return self._log.size()
        except:
            return 0

    def getColumnCount(self):
        return 8

    def getColumnName(self, columnIndex):
        data = ['ID','Method', 'URL', 'Orig. Length', 'Modif. Length', "Unauth. Length",
                "Authorization Enforcement Status", "Authorization Unauth. Status"]
        try:
            return data[columnIndex]
        except IndexError:
            return ""

    def getColumnClass(self, columnIndex):
        data = [Integer, String, String, Integer, Integer, Integer, String, String]
        try:
            return data[columnIndex]
        except IndexError:
            return ""

    def getValueAt(self, rowIndex, columnIndex):
        logEntry = self._log.get(rowIndex)
        if columnIndex == 0:
            return logEntry._id
        if columnIndex == 1:
            return logEntry._method
        if columnIndex == 2:
            return logEntry._url.toString()
        if columnIndex == 3:
            response = logEntry._originalrequestResponse.getResponse()
            return len(logEntry._originalrequestResponse.getResponse()) - self._helpers.analyzeResponse(response).getBodyOffset()
        if columnIndex == 4:
            response = logEntry._requestResponse.getResponse()
            return len(logEntry._requestResponse.getResponse()) - self._helpers.analyzeResponse(response).getBodyOffset()
        if columnIndex == 5:
            if logEntry._unauthorizedRequestResponse is not None:
                response = logEntry._unauthorizedRequestResponse.getResponse()
                return len(logEntry._unauthorizedRequestResponse.getResponse()) - self._helpers.analyzeResponse(response).getBodyOffset()
            else:
                return 0
        if columnIndex == 6:
            return logEntry._enfocementStatus   
        if columnIndex == 7:
            return logEntry._enfocementStatusUnauthorized        
        return ""

    #
    # implement IMessageEditorController
    # this allows our request/response viewers to obtain details about the messages being displayed
    #
    
    def getHttpService(self):
        return self._currentlyDisplayedItem.getHttpService()

    def getRequest(self):
        return self._currentlyDisplayedItem.getRequest()

    def getResponse(self):
        return self._currentlyDisplayedItem.getResponse()


    #
    # implement IHttpListener
    #
    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        cookies = self.getCookieFromMessage(messageInfo)
        if cookies:
            self.lastCookies = cookies
            self.fetchButton.setEnabled(True)        

        #if (self.intercept == 1) and (toolFlag != self._callbacks.TOOL_EXTENDER):
        if (self.intercept == 1) and (toolFlag == self._callbacks.TOOL_PROXY):
            if self.prevent304.isSelected():
                if messageIsRequest:
                    requestHeaders = list(self._helpers.analyzeRequest(messageInfo).getHeaders())
                    newHeaders = list()
                    found = 0
                    for header in requestHeaders:
                        if not "If-None-Match:" in header and not "If-Modified-Since:" in header:
                            newHeaders.append(header)
                            found = 1
                    if found == 1:
                        requestInfo = self._helpers.analyzeRequest(messageInfo)
                        bodyBytes = messageInfo.getRequest()[requestInfo.getBodyOffset():]
                        bodyStr = self._helpers.bytesToString(bodyBytes)
                        messageInfo.setRequest(self._helpers.buildHttpMessage(newHeaders, bodyStr))


            if not messageIsRequest:
                # Requests with the same cookies of the Autorize cookies are not intercepted
                if not self.replaceString.getText() in self._helpers.analyzeRequest(messageInfo).getHeaders():
                    if self.ignore304.isSelected():
                        firstHeader = self._helpers.analyzeResponse(messageInfo.getResponse()).getHeaders()[0]
                        if "304" in firstHeader or "204" in firstHeader:
                           return

                    if self.IFList.getModel().getSize() == 0:

                        #cookies = self.getCookieFromMessage(messageInfo)
                        #if cookies:
                            #self.lastCookies = cookies
                            #self.fetchButton.setEnabled(True)

                        self.checkAuthorization(messageInfo,self._helpers.analyzeResponse(messageInfo.getResponse()).getHeaders(),self.doUnauthorizedRequest.isSelected())
                    
                    else:
                        urlString = str(self._helpers.analyzeRequest(messageInfo).getUrl())

                        do_the_check = 1

                        for i in range(0,self.IFList.getModel().getSize()):

                            if self.IFList.getModel().getElementAt(i).split(":")[0] == "Scope items only":
                                currentURL = URL(urlString)
                                if not self._callbacks.isInScope(currentURL):
                                    do_the_check = 0
                            if self.IFList.getModel().getElementAt(i).split(":")[0] == "URL Contains (simple string)":
                                if self.IFList.getModel().getElementAt(i)[30:] not in urlString:
                                    do_the_check = 0
                            if self.IFList.getModel().getElementAt(i).split(":")[0] == "URL Contains (regex)":
                                regex_string = self.IFList.getModel().getElementAt(i)[22:]
                                if not re.match(regex_string, urlString, re.IGNORECASE) is None:
                                    do_the_check = 0  
                            if self.IFList.getModel().getElementAt(i).split(":")[0] == "URL Not Contains (simple string)":
                                if self.IFList.getModel().getElementAt(i)[34:] in urlString:
                                    do_the_check = 0
                            if self.IFList.getModel().getElementAt(i).split(":")[0] == "URL Not Contains (regex)":
                                regex_string = self.IFList.getModel().getElementAt(i)[26:]
                                if re.match(regex_string, urlString, re.IGNORECASE) is None:
                                    do_the_check = 0                                                                       

                        if do_the_check:

                            # In this position only the cookies of intercepted requests are taken
                            #cookies = self.getCookieFromMessage(messageInfo)
                            #if cookies:
                                #self.lastCookies = cookies
                                #self.fetchButton.setEnabled(True)

                            self.checkAuthorization(messageInfo,self._helpers.analyzeResponse(messageInfo.getResponse()).getHeaders(),self.doUnauthorizedRequest.isSelected())


    def sendRequestToAutorizeWork(self,messageInfo):
        if messageInfo.getResponse() is None:
            message = self.makeMessage(messageInfo,False,False)
            requestResponse = self.makeRequest(messageInfo, message)
            self.checkAuthorization(requestResponse,self._helpers.analyzeResponse(requestResponse.getResponse()).getHeaders(),self.doUnauthorizedRequest.isSelected())
        else:
            request = messageInfo.getRequest()
            response = messageInfo.getResponse()
            httpService = messageInfo.getHttpService()
            newHttpRequestResponse = IHttpRequestResponseImplementation(httpService,request,response)
            newHttpRequestResponsePersisted = self._callbacks.saveBuffersToTempFiles(newHttpRequestResponse)
            self.checkAuthorization(newHttpRequestResponsePersisted,self._helpers.analyzeResponse(messageInfo.getResponse()).getHeaders(),self.doUnauthorizedRequest.isSelected())

    def makeRequest(self, messageInfo, message):
        requestURL = self._helpers.analyzeRequest(messageInfo).getUrl()
        return self._callbacks.makeHttpRequest(self._helpers.buildHttpService(str(requestURL.getHost()), int(requestURL.getPort()), requestURL.getProtocol() == "https"), message)

    def makeMessage(self, messageInfo, removeOrNot, authorizeOrNot):
        requestInfo = self._helpers.analyzeRequest(messageInfo)
        headers = requestInfo.getHeaders()
        if removeOrNot:
            headers = list(headers)
            removeHeaders = ArrayList()
            removeHeaders.add(self.replaceString.getText()[0:self.replaceString.getText().index(":")])

            for header in headers[:]:
                for removeHeader in removeHeaders:
                    if removeHeader in header:
                        headers.remove(header)

            if authorizeOrNot:
                headers.append(self.replaceString.getText())

        msgBody = messageInfo.getRequest()[requestInfo.getBodyOffset():]
        return self._helpers.buildHttpMessage(headers, msgBody)

    def checkBypass(self,oldStatusCode,newStatusCode,oldContentLen,newContentLen,filters,requestResponse,andOrEnforcement):
        response = requestResponse.getResponse()
        analyzedResponse = self._helpers.analyzeResponse(response)
        impression = ""

        if oldStatusCode == newStatusCode:
            if oldContentLen == newContentLen:
                impression = self._enfocementStatuses[0]
            else:

                if len(filters) > 0:

                    if andOrEnforcement == "And":
                        andEnforcementCheck = True
                        auth_enforced = 1
                    else:
                        andEnforcementCheck = False
                        auth_enforced = 0
                    
                    for filter in filters:

                        if str(filter).startswith("Headers (simple string): "):
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not filter[25:] in self._helpers.bytesToString(requestResponse.getResponse()[0:analyzedResponse.getBodyOffset()]):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and filter[25:] in self._helpers.bytesToString(requestResponse.getResponse()[0:analyzedResponse.getBodyOffset()]):
                                    auth_enforced = 1

                        if str(filter).startswith("Headers (regex): "):
                            regex_string = filter[17:]
                            p = re.compile(regex_string, re.IGNORECASE)                        
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not p.search(self._helpers.bytesToString(requestResponse.getResponse()[0:analyzedResponse.getBodyOffset()])):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and p.search(self._helpers.bytesToString(requestResponse.getResponse()[0:analyzedResponse.getBodyOffset()])):
                                    auth_enforced = 1

                        if str(filter).startswith("Body (simple string): "):
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not filter[22:] in self._helpers.bytesToString(requestResponse.getResponse()[analyzedResponse.getBodyOffset():]):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and filter[22:] in self._helpers.bytesToString(requestResponse.getResponse()[analyzedResponse.getBodyOffset():]):
                                    auth_enforced = 1

                        if str(filter).startswith("Body (regex): "):
                            regex_string = filter[14:]
                            p = re.compile(regex_string, re.IGNORECASE)
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not p.search(self._helpers.bytesToString(requestResponse.getResponse()[analyzedResponse.getBodyOffset():])):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and p.search(self._helpers.bytesToString(requestResponse.getResponse()[analyzedResponse.getBodyOffset():])):
                                    auth_enforced = 1

                        if str(filter).startswith("Full response (simple string): "):
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not filter[31:] in self._helpers.bytesToString(requestResponse.getResponse()):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and filter[31:] in self._helpers.bytesToString(requestResponse.getResponse()):
                                    auth_enforced = 1

                        if str(filter).startswith("Full response (regex): "):
                            regex_string = filter[23:]
                            p = re.compile(regex_string, re.IGNORECASE)
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not p.search(self._helpers.bytesToString(requestResponse.getResponse())):
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and p.search(self._helpers.bytesToString(requestResponse.getResponse())):
                                    auth_enforced = 1

                        if str(filter).startswith("Full response length: "):
                            if andEnforcementCheck:
                                if auth_enforced == 1 and not str(len(response)) == filter[22:].strip():
                                    auth_enforced = 0
                            else:
                                if auth_enforced == 0 and str(len(response)) == filter[22:].strip():
                                    auth_enforced = 1
                
                else:
                    # If no enforcement detectors are set and the HTTP response is the same, the impression is yellow
                    auth_enforced = 0
                
                if auth_enforced:
                    impression = self._enfocementStatuses[2]
                else:
                    impression = self._enfocementStatuses[1]
                         
        else:
            impression = self._enfocementStatuses[2]

        return impression

    def checkAuthorization(self, messageInfo, originalHeaders, checkUnauthorized):
        oldResponse = messageInfo.getResponse()
        message = self.makeMessage(messageInfo, True, True)
        requestResponse = self.makeRequest(messageInfo, message)
        newResponse = requestResponse.getResponse()
        analyzedResponse = self._helpers.analyzeResponse(newResponse)
        
        oldStatusCode = originalHeaders[0]
        newStatusCode = analyzedResponse.getHeaders()[0]
        oldContentLen = self.getResponseContentLength(oldResponse)
        newContentLen = self.getResponseContentLength(newResponse)

        # Check unauthorized request
        if checkUnauthorized:
            messageUnauthorized = self.makeMessage(messageInfo, True, False)
            requestResponseUnauthorized = self.makeRequest(messageInfo, messageUnauthorized)
            unauthorizedResponse = requestResponseUnauthorized.getResponse()
            analyzedResponseUnauthorized = self._helpers.analyzeResponse(unauthorizedResponse)  
            statusCodeUnauthorized = analyzedResponseUnauthorized.getHeaders()[0]
            contentLenUnauthorized = self.getResponseContentLength(unauthorizedResponse)

        EDFilters = self.EDModel.toArray()

        impression = self.checkBypass(oldStatusCode,newStatusCode,oldContentLen,newContentLen,EDFilters,requestResponse,self.AndOrType.getSelectedItem())

        if checkUnauthorized:
            EDFiltersUnauth = self.EDModelUnauth.toArray()
            impressionUnauthorized = self.checkBypass(oldStatusCode,statusCodeUnauthorized,oldContentLen,contentLenUnauthorized,EDFiltersUnauth,requestResponseUnauthorized,self.AndOrTypeUnauth.getSelectedItem())

        self._lock.acquire()
        
        row = self._log.size()
        method = self._helpers.analyzeRequest(messageInfo.getRequest()).getMethod()
        
        if checkUnauthorized:
            self._log.add(LogEntry(self.currentRequestNumber,self._callbacks.saveBuffersToTempFiles(requestResponse), method, self._helpers.analyzeRequest(requestResponse).getUrl(),messageInfo,impression,self._callbacks.saveBuffersToTempFiles(requestResponseUnauthorized),impressionUnauthorized)) # same requests not include again.
        else:
            self._log.add(LogEntry(self.currentRequestNumber,self._callbacks.saveBuffersToTempFiles(requestResponse), method, self._helpers.analyzeRequest(requestResponse).getUrl(),messageInfo,impression,None,"Disabled")) # same requests not include again.
        
        SwingUtilities.invokeLater(UpdateTableEDT(self,"insert",row,row))
        #self.fireTableRowsInserted(row, row)
        self.currentRequestNumber = self.currentRequestNumber + 1
        self._lock.release()
        
    def getResponseContentLength(self, response):
        return len(response) - self._helpers.analyzeResponse(response).getBodyOffset()

    #def getContentLength(self, analyzedResponseHeaders):
    #    for header in analyzedResponseHeaders:
    #        if "Content-Length:" in header:
    #            return header;
    #    return "null"

    def getCookieFromMessage(self, messageInfo):
        headers = list(self._helpers.analyzeRequest(messageInfo.getRequest()).getHeaders())
        for header in headers:
            if header.strip().lower().startswith("cookie:"):
                return header
        return None

#
# extend JTable to handle cell selection
#
    
class Table(JTable):

    def __init__(self, extender):
        self._extender = extender
        self.setModel(extender)
        self.addMouseListener(mouseclick(self._extender))
        self.getColumnModel().getColumn(0).setPreferredWidth(450)
        self.setRowSelectionAllowed(True)
        return

    def prepareRenderer(self, renderer, row, col):
        comp = JTable.prepareRenderer(self, renderer, row, col)
        value = self._extender.getValueAt(self._extender.logTable.convertRowIndexToModel(row), col)

        if col == 6 or col == 7:
            if value == "Authorization bypass!":
                comp.setBackground(Color(255,135,31))
            elif value == "Authorization enforced??? (please configure enforcement detector)" :
                comp.setBackground(Color(255,255,133))
            elif value == "Authorization enforced!":
                comp.setBackground(Color(192,250,20))
        else:
            comp.setBackground(Color.white)

        return comp
    
    def changeSelection(self, row, col, toggle, extend):
        # show the log entry for the selected row
        logEntry = self._extender._log.get(self._extender.logTable.convertRowIndexToModel(row))
        self._extender._requestViewer.setMessage(logEntry._requestResponse.getRequest(), True)
        self._extender._responseViewer.setMessage(logEntry._requestResponse.getResponse(), False)
        self._extender._originalrequestViewer.setMessage(logEntry._originalrequestResponse.getRequest(), True)
        self._extender._originalresponseViewer.setMessage(logEntry._originalrequestResponse.getResponse(), False)

        if logEntry._unauthorizedRequestResponse is not None:
            self._extender._unauthorizedrequestViewer.setMessage(logEntry._unauthorizedRequestResponse.getRequest(), True)
            self._extender._unauthorizedresponseViewer.setMessage(logEntry._unauthorizedRequestResponse.getResponse(), False)
        else:
            self._extender._unauthorizedrequestViewer.setMessage("Request disabled", True)
            self._extender._unauthorizedresponseViewer.setMessage("Response disabled", False)

        self._extender._currentlyDisplayedItem = logEntry._requestResponse

        if col == 3:
            self._extender.tabs.setSelectedIndex(3)
        elif col == 4 or col == 6:
            self._extender.tabs.setSelectedIndex(1)
        elif col == 5 or col == 7:
            self._extender.tabs.setSelectedIndex(5)
        else:
            self._extender.tabs.setSelectedIndex(2)

        JTable.changeSelection(self, row, col, toggle, extend)
        return

class LogEntry:

    def __init__(self, id, requestResponse, method, url, originalrequestResponse, enforcementStatus, unauthorizedRequestResponse, enforcementStatusUnauthorized):
        self._id = id
        self._requestResponse = requestResponse
        self._originalrequestResponse = originalrequestResponse
        self._method = method
        self._url = url
        self._enfocementStatus =  enforcementStatus
        self._unauthorizedRequestResponse = unauthorizedRequestResponse
        self._enfocementStatusUnauthorized =  enforcementStatusUnauthorized
        return

class mouseclick(MouseAdapter):

    def __init__(self, extender):
        self._extender = extender

    def mouseReleased(self, evt):
        if evt.button == 3:
            self._extender.menu.show(evt.getComponent(), evt.getX(), evt.getY())


class autoScrollListener(AdjustmentListener):
    def __init__(self, extender):
        self._extender = extender

    def adjustmentValueChanged(self, e):
        if self._extender.autoScroll.isSelected() is True:
            e.getAdjustable().setValue(e.getAdjustable().getMaximum())

class copySelectedURL(ActionListener):
    def __init__(self, extender):
        self._extender = extender

    def actionPerformed(self, e):
        stringSelection = StringSelection(str(self._extender._helpers.analyzeRequest(self._extender._currentlyDisplayedItem).getUrl()))
        clpbrd = Toolkit.getDefaultToolkit().getSystemClipboard()
        clpbrd.setContents(stringSelection, None)


class handleMenuItems(ActionListener):
    def __init__(self, extender, messageInfo, menuName):
        self._extender = extender
        self._menuName = menuName
        self._messageInfo = messageInfo

    def actionPerformed(self, e):
        if self._menuName == "request":
            start_new_thread(self._extender.sendRequestToAutorizeWork,(self._messageInfo,))

        if self._menuName == "cookie":
            self._extender.replaceString.setText(self._extender.getCookieFromMessage(self._messageInfo))

class tabTableFilter(ItemListener):
    def __init__(self, extender):
        self._extender = extender

    def itemStateChanged(self, e):
        self._extender.tableSorter.sort()

class tableFilter(RowFilter):

    def __init__(self, extender):
        self._extender = extender

    def include(self, entry):

        if self._extender.showAuthBypassModified.isSelected() and "Authorization bypass!" == entry.getValue(6):
            return True
        elif self._extender.showAuthPotentiallyEnforcedModified.isSelected() and "Authorization enforced??? (please configure enforcement detector)" == entry.getValue(6):
            return True
        elif self._extender.showAuthEnforcedModified.isSelected() and "Authorization enforced!" == entry.getValue(6):
            return True
        elif self._extender.showAuthBypassUnauthenticated.isSelected() and "Authorization bypass!" == entry.getValue(7):
            return True
        elif self._extender.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and "Authorization enforced??? (please configure enforcement detector)" == entry.getValue(7):
            return True
        elif self._extender.showAuthEnforcedUnauthenticated.isSelected() and "Authorization enforced!" == entry.getValue(7):
            return True 
        elif self._extender.showDisabledUnauthenticated.isSelected() and "Disabled" == entry.getValue(7):
            return True                        
        else:
            return False

class IHttpRequestResponseImplementation(IHttpRequestResponse):

    def __init__(self, service, req, res):
        
        self._httpService = service
        self._request = req
        self._response = res
        self._comment = None
        self._highlight = None

    def getComment(self):
        return self._comment

    def getHighlight(self):
        return self._highlight

    def getHttpService(self):
        return self._httpService

    def getRequest(self):
        return self._request

    def getResponse(self):
        return self._response

    def setComment(self,c):
        self._comment = c

    def setHighlight(self,h):
        self._highlight = h

    def setHttpService(self,service):
        self._httpService = service

    def setRequest(self,req):
        self._request = req

    def setResponse(self,res):
        self._response = res


class UpdateTableEDT(Runnable):
    def __init__(self,extender,action,firstRow,lastRow):
        self._extender=extender
        self._action=action
        self._firstRow=firstRow
        self._lastRow=lastRow

    def run(self):
        #print SwingUtilities.isEventDispatchThread()
        if self._action == "insert":
            self._extender.fireTableRowsInserted(self._firstRow, self._lastRow)
        elif self._action == "update":
            self._extender.fireTableRowsUpdated(self._firstRow, self._lastRow)
        elif self._action == "delete":
            self._extender.fireTableRowsDeleted(self._firstRow, self._lastRow)
        else:
            print("Invalid action in UpdateTableEDT")


        
