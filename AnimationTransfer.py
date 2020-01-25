"""
Daniel Bengtsson
2018-06-27
UD1439 H17 Lp23 Tillämpade animationstekniker
"""
import pymel.core as pm
import pymel.core.datatypes as dt
from maya import OpenMayaUI as omui
import PySide2
from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from shiboken2 import wrapInstance

import sys
sys.path.append('C:/Users/<Username>/Desktop')


###################################GlobalVars#########################################
pm.currentTime(0, edit=True)
root = pm.ls(sl=True)
counter = 0

"""If both skeletons have the same amount of joints"""
targetJoints = []
sourceJoints = []
targetJoints.append(root[1])
sourceJoints.append(root[0])
jointNames = []
jointOrientations = []
skipSJoints = []
skipTJoints = []
takeSList = []
takeTList = []
newSList = []
newTList = []
sParentMatrixes = []
tParentMatrixes = []
sBindPoseInversed = []
tBindPoseInversed = []

###################################Functions##########################################


"""Returns a list of parents from child to root"""
def getParentPath(currentJoint, jointNames):
	jointNames.append(currentJoint)
	jointParent = currentJoint.getParent()
	if (jointParent):
		getParentPath(jointParent, jointNames)
	return jointNames

"""Returns a list of parents from root to child"""
def getChildrenPath(node, list):
	for child in node.getChildren():
		list.append(child)
		if child.numChildren() > 0:
			getChildrenPath(child, list)

"""Returns Parent Matrix"""
def sRotation(sourceNames):
	parentMatrix = dt.Matrix()
	for node in sourceNames:
		if (node is not sourceNames[0]):
			nodeRot = pm.getAttr(node + '.rotate', time=0)
			nodeRot = dt.EulerRotation(nodeRot[0], nodeRot[1], nodeRot[2]).asMatrix()
			parentMatrix = parentMatrix * node.getOrientation().asMatrix() * nodeRot
	return parentMatrix


"""Create list of parent matrixes"""
def assembleTheParentMatrixes(jointList, newMatrixes):
	for currentJoint in jointList:
		if (jointNames):
			jointNames[:] = []
		if currentJoint.getParent() is not None:
			sourceNames = getParentPath(currentJoint, jointNames)
			newMatrixes.append(sRotation(sourceNames))
		else:
			newMatrixes.append(dt.Matrix())


"""Returns the index of where the source joint is in the target list"""
def searchID(child, list):
	counter = 0
	nChild = str(child)
	for i, item in enumerate(list):
		nItem = str(item)
		if nItem == nChild:
			counter = i
	return counter

"""Return a list of all source joints bindposes"""
def getBindPoses(sourceList, newList):
	for joints in sourceList:
		bindPose = pm.getAttr(joints + '.rotate', t=0)
		bindPose = dt.EulerRotation(bindPose[0], bindPose[1], bindPose[2]).asMatrix()
		newList.append(bindPose.transpose())
	
"""Takes the list of string objects created from the QTListWidget and turns the objects into joints"""
def replaceList(list1, list2):
	newList = []
	for item in list1:
		for oldItem in list2:
			if item == oldItem:
				newList.append(oldItem)
	return newList

"""Loops through both the source and targets children"""
def setJointRotation(sourceList, targetList, x, sParentMat, tParentMat):
	for i, (sourceChild, targetChild) in enumerate(zip(sourceList, targetList)):
		
		"""Get keyframe rotations as k"""
		k = pm.getAttr(sourceChild + '.rotate', time=x)
		k = dt.EulerRotation(k[0], k[1], k[2]).asMatrix()
		
		"""Create isolatedRotation"""
		isolatedRotation = sBindPoseInversed[i] * k
		
		"""Change of basis to world space rotation"""
		sOrientation = sourceChild.getOrientation().asMatrix()
		sOrientationInversed = sOrientation.transpose()
		sParentsInversed = sParentMat[i].transpose()
		worldspaceRotation = sOrientationInversed * sParentsInversed * isolatedRotation * sParentMat[i] * sOrientation
		
		"""Second change of basis to the space of target"""
		tOrientation = targetChild.getOrientation().asMatrix()
		tOrientationInversed = tOrientation.transpose()
		tParentsInversed = tParentMat[i].transpose()
		translatedRotation = tOrientation * tParentMat[i] * worldspaceRotation * tParentsInversed * tOrientationInversed
		
		#tRot = pm.getAttr(targetChild + '.rotate', t=0)
		#tRot = dt.EulerRotation(tRot[0], tRot[1], tRot[2]).asMatrix() 
		#finalRotation = tRot * translatedRotation
		
		"""Get rotation values from the translated rotation matrix and set key for target"""
		eulRot = dt.EulerRotation(translatedRotation)
		eulRot = dt.degrees(eulRot)
		pm.setAttr(targetChild + '.rotate', eulRot.x, eulRot.y, eulRot.z)
		
		"""If joint is root, then also set translation"""
		if sourceChild.getParent() is None:
			sKmove = pm.getAttr(sourceChild + '.translate', time=x)
			pm.setAttr(targetChild + '.translate', sKmove[0], sKmove[1], sKmove[2])

		pm.setKeyframe(targetChild, t=(x), edit=True)
			



######################################UI############################################
def getMayaWin():
	mayaWinPtr = omui.MQtUtil.mainWindow( )
	mayaWin = wrapInstance( long( mayaWinPtr ), QtWidgets.QMainWindow )


def loadUI( path ):
	loader = QUiLoader()
	uiFile = QFile( path )
	
	dirIconShapes = ""
	buff = None
	
	if uiFile.exists():
		dirIconShapes = path
		uiFile.open( QFile.ReadOnly )
		
		buff = QByteArray( uiFile.readAll() )
		uiFile.close()
	else:
		print "UI file missing! Exiting..."
		exit(-1)

	fixXML( path, buff )
	qbuff = QBuffer()
	qbuff.open( QBuffer.ReadOnly | QBuffer.WriteOnly )
	qbuff.write( buff )
	qbuff.seek( 0 )
	ui = loader.load( qbuff, parentWidget = getMayaWin() )
	ui.path = path
	
	return ui


def fixXML( path, qbyteArray ):
	# first replace forward slashes for backslashes
	if path[-1] != '/':
		path += '/'
	path = path.replace( "/", "\\" )

	# construct whole new path with <pixmap> at the begining
	tempArr = QByteArray( "<pixmap>" + path + "\\" )

	# search for the word <pixmap>
	lastPos = qbyteArray.indexOf( "<pixmap>", 0 )
	while lastPos != -1:
		qbyteArray.replace( lastPos, len( "<pixmap>" ), tempArr )
		lastPos = qbyteArray.indexOf( "<pixmap>", lastPos + 1 )
	return


class UIController:	
	def __init__( self, ui ):
		
		getChildrenPath(root[0], sourceJoints)
		getChildrenPath(root[1], targetJoints)
		# Connect each signal to it's slot one by one
		ui.Transfer.clicked.connect( self.TransferAnimation )
		ui.lUp.clicked.connect( self.moveLUP )
		ui.lDown.clicked.connect( self.moveLDOWN )
		ui.lDelete.clicked.connect( self.removeSJointList )
		ui.rUp.clicked.connect( self.moveRUP )
		ui.rDown.clicked.connect( self.moveRDOWN )
		ui.rDelete.clicked.connect( self.removeTJointList )
		ui.rootLine.returnPressed.connect( self.fillSourceList )
		ui.rootLine2.returnPressed.connect( self.fillTargetList )
		
		
		self.ui = ui
		ui.setWindowFlags( Qt.WindowStaysOnTopHint )
		ui.show()

	def moveLUP( self ):
		index = ui.SourceJointsList.currentRow()
		item = ui.SourceJointsList.takeItem(index)
		ui.SourceJointsList.insertItem(index - 1, item)
		ui.SourceJointsList.setCurrentRow(index - 1)

	def moveLDOWN( self ):
		index = ui.SourceJointsList.currentRow()
		item = ui.SourceJointsList.takeItem(index)
		ui.SourceJointsList.insertItem(index + 1, item)
		ui.SourceJointsList.setCurrentRow(index + 1)

	def moveRUP( self ):
		index = ui.TargetJointsList.currentRow()
		item = ui.TargetJointsList.takeItem(index)
		ui.TargetJointsList.insertItem(index - 1, item)
		ui.TargetJointsList.setCurrentRow(index - 1)
		
	def moveRDOWN( self ):
		index = ui.TargetJointsList.currentRow()
		item = ui.TargetJointsList.takeItem(index)
		ui.TargetJointsList.insertItem(index + 1, item)
		ui.TargetJointsList.setCurrentRow(index + 1)

	def TransferAnimation( self ):
		"""Make list out of widget items"""
		counter = ui.SourceJointsList.count()
		for i in range(counter):
			item = ui.SourceJointsList.item(i)
			takeSList.append(item.text())
			item = ui.TargetJointsList.item(i)
			takeTList.append(item.text())
			item = None
		
		"""Replace string items with joint items"""
		newTList = replaceList(takeTList, targetJoints)
		newSList = replaceList(takeSList, sourceJoints)

		"""Get inversed bind poses"""
		getBindPoses(newSList, sBindPoseInversed)
		getBindPoses(newTList, tBindPoseInversed)
		
		"""Calculate joint parent matrix"""
		assembleTheParentMatrixes(newSList, sParentMatrixes)
		assembleTheParentMatrixes(newTList, tParentMatrixes)

		keyframeCount = (pm.keyframe(root[0], q=True, keyframeCount=True) / 10)
		for x in range(keyframeCount):
			print "KEY FRAME: " + str(x) + "!"
			pm.currentTime(x, edit=True)
			setJointRotation(newSList, newTList, x, sParentMatrixes, tParentMatrixes)
			

	def fillSourceList( self ):
		for i in range(len(sourceJoints)):
			jointName = str(sourceJoints[i])
			ui.SourceJointsList.addItem(jointName)
			
	def fillTargetList( self ):
		for i in range(len(targetJoints)):
			jointName = str(targetJoints[i])
			ui.TargetJointsList.addItem(jointName)
			
	def removeSJointList( self ):
		index = ui.SourceJointsList.currentRow()
		item = ui.SourceJointsList.takeItem(index)
		skipSJoints.append(item.text())
		item = None
		
	def removeTJointList( self ):
		index = ui.TargetJointsList.currentRow()
		item = ui.TargetJointsList.takeItem(index)
		skipTJoints.append(item.text())
		item = None
		
######################################Main############################################
"""Loading UI"""
ui = loadUI('C:/Users/<Username>/Desktop/QtAnimTransferUI.ui')
cont = UIController(ui)