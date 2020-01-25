import pymel.core as pm
import pymel.core.datatypes as dt
import datetime as time
from maya import OpenMayaUI as omui
import PySide2
from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from shiboken2 import wrapInstance

import sys
sys.path.append('Path to folder where script is')

#--------------------------------------------------------------------------#
#--------------------------------Functions---------------------------------#
#--------------------------------------------------------------------------#
def getKeyCount(jnt):
	numAttr = len(pm.listAttr(jnt, keyable=True))
	count = pm.keyframe(jnt, keyframeCount=True, query=True) / numAttr
	return count


def checkBoxs(*args):
	if loopBox.getValue():
		interpBox.setEnable(False)
	else:
		interpBox.setEnable(True)
		
	if interpBox.getValue():
		loopBox.setEnable(False)
	else:
		loopBox.setEnable(True)


def bakeJoints(jnt, start, end):
	pm.select(jnt)
	pm.bakeResults(simulation=True, t=(start, end), hierarchy=('below'), sampleBy=1, oversamplingRate=1, disableImplicitControl=True, preserveOutsideKeys=True, sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False, removeBakedAnimFromLayer=False, bakeOnOverrideLayer=False, minimizeRotation=True, controlPoints=False, shape=True)


def jntCtrls(list):
	for i, jnt in enumerate(list):
		if i < len(sel) - 1:
			dst1 = pm.joint(list[i + 1], query=True, position=True)
			dst2 = pm.joint(list[i - 1], query=True, position=True)
			rot = jnt.getRotation()
	
			dst3 = []
			dst3.append((dst2[0]) - (dst1[0]))
			dst3.append((dst2[1]) - (dst1[1]))
			dst3.append((dst2[2]) - (dst1[2]))
	
			ctrl = pm.circle(c=(0, 0, 0), nr=dst3, sw=360, r=1, d=3, ut=0, tol=0.0001, s=8, ch=1)[0]
			pm.move(ctrl, dst2)

def slerp(v0, v1, t):
	qm = dt.Quaternion()
	cosHalfTheta = (v0.w * v1.w) + (v0.x * v1.x) + (v0.y * v1.y) + (v0.z * v1.z)
	if abs(cosHalfTheta) >= 1.0:
		qm.w = v0.w
		qm.x = v0.x
		qm.y = v0.y
		qm.z = v0.z
		return qm
	
	halfTheta = dt.acos(cosHalfTheta)
	sinHalfTheta = dt.sqrt(1.0 - cosHalfTheta*cosHalfTheta)
	if dt.fabs(sinHalfTheta) < 0.001:
		qm.w = (v0.w * 0.5 + v1.w * 0.5)
		qm.x = (v0.x * 0.5 + v1.x * 0.5)
		qm.y = (v0.y * 0.5 + v1.y * 0.5)
		qm.z = (v0.z * 0.5 + v1.z * 0.5)
		return qm
		
	ratioA = dt.sin((1 - t) * halfTheta) / sinHalfTheta
	ratioB = dt.sin(t * halfTheta) / sinHalfTheta
	qm.w = (v0.w * ratioA + v1.w * ratioB)
	qm.x = (v0.x * ratioA + v1.x * ratioB)
	qm.y = (v0.y * ratioA + v1.y * ratioB)
	qm.z = (v0.z * ratioA + v1.z * ratioB)
	return qm

def buttonPressed(*args):
	startFrame = minFld.getValue()
	endFrame = maxFld.getValue()
	difference = endFrame - startFrame
	if bakeBox.getValue():
		bakeJoints(root, startFrame, endFrame)
		
	if loopBox.getValue():
		startInterp = endFrame - int(difference * 0.2)
		pm.playbackOptions(min=0, max=difference)
		for jnt in sourceJoints:
			if (startFrame > 1):
				pm.cutKey(jnt, time=(0, startFrame - 1), option='keys')
			pm.cutKey(jnt, time=(startInterp, keyCount), option='keys')
			pm.copyKey(jnt, time=startFrame)
			pm.pasteKey(jnt, time=endFrame)
			for i in range(endFrame - int(difference * 0.2), endFrame):
				pm.currentTime(i)
				pm.setKeyframe(jnt)
		animCrvs = pm.ls(type=['animCurveTA', 'animCurveTL', 'animCurveTT', 'animCurveTU'])
		for item in animCrvs:
			pm.keyframe(item, edit=True, relative=True, timeChange=-startFrame)
		for jnt in sourceJoints:
			pm.cutKey(jnt, time=(-keyCount, 0), option='keys')
			pm.cutKey(jnt, time=(difference+1, keyCount), option='keys')
			pm.copyKey(jnt, time=difference)
			pm.pasteKey(jnt, time=0)
			
	if interpBox.getValue():
		for i in range(startFrame, endFrame):
			for jnt in sourceJoints:
				pm.currentTime(i + 1)
				qt1 = jnt.getRotation().asQuaternion()
				pm.currentTime(i)
				qt2 = jnt.getRotation().asQuaternion()
				newqt1 = slerp(qt1, qt2, 0.5)

				jnt.setRotation(newqt1)
				pm.setKeyframe(jnt)


"""Returns a list of parents from child to root"""
def getParentPath(currentJoint, jointNames):
	jointNames.append(currentJoint)
	jointParent = currentJoint.getParent()
	if (jointParent) and (str(type(jointParent)) == 'joint'):
		print currentJoint
		getParentPath(jointParent, jointNames)
	return jointNames

"""Removes rotate limitations"""
def removeRotLimits(node):
	for child in node.getChildren():
		pm.transformLimits(child, erx=(0, 0), ery=(0, 0), erz=(0, 0))
		if child.numChildren() > 0:
			removeRotLimits(child)

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
			parentMatrix *= node.getOrientation().asMatrix() * nodeRot
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
		
		tRot = pm.getAttr(targetChild + '.rotate', t=0)
		tRot = dt.EulerRotation(tRot[0], tRot[1], tRot[2]).asMatrix() 
		finalRotation = tRot * translatedRotation
		
		"""Get rotation values from the translated rotation matrix and set key for target"""
		eulRot = dt.EulerRotation(finalRotation)
		eulRot = dt.degrees(eulRot)
		pm.setAttr(targetChild + '.rotate', eulRot.x, eulRot.y, eulRot.z)
		
		"""If joint is root, then also set translation"""
		if sourceChild.getParent() is None:
			sKmove = pm.getAttr(sourceChild + '.translate', time=x)
			pm.setAttr(targetChild + '.translate', sKmove[0], sKmove[1], sKmove[2])

		pm.setKeyframe(targetChild, t=(x), edit=True)
		


#--------------------------------------------------------------------------#
#---------------------------Global Variables-------------------------------#
#--------------------------------------------------------------------------#
root = pm.ls(sl=True)
targetJoints = []
sourceJoints = []

if len(root) < 2:
	keyCount = getKeyCount(root)
	sourceJoints.append(root[0])
	getChildrenPath(root[0], sourceJoints)
	removeRotLimits(root[0])
	pm.transformLimits(root[0], erx=(0, 0), ery=(0, 0), erz=(0, 0))
else:
	keyCount = getKeyCount(root[0])
	sourceJoints.append(root[0])
	targetJoints.append(root[1])
	getChildrenPath(root[0], sourceJoints)
	getChildrenPath(root[1], targetJoints)
	removeRotLimits(root[0])
	removeRotLimits(root[1])
	pm.transformLimits(root[0], erx=(0, 0), ery=(0, 0), erz=(0, 0))
	pm.transformLimits(root[1], erx=(0, 0), ery=(0, 0), erz=(0, 0))

allJnts = pm.ls(type='joint')
pm.currentTime(0, edit=True)
counter = 0
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

		
#--------------------------------------------------------------------------#
#------------------------------User Interface------------------------------#
#--------------------------------------------------------------------------#
if len(root) < 2:
	win = pm.window(title='My Window')
	layout = pm.columnLayout()
	loopBox = pm.checkBox(label = 'Loop', value=False, parent=layout, onc=checkBoxs, ofc=checkBoxs)
	interpBox = pm.checkBox(label = 'Interpolate', value=False, parent=layout, onc=checkBoxs, ofc=checkBoxs)
	bakeBox = pm.checkBox(label = 'Bake animation', value=False, parent=layout)
	minTxt = pm.text( label='Min key', align='center', parent=layout)
	minFld = pm.intField(min=0, max=keyCount-1, parent=layout)
	maxTxt = pm.text( label='Max key', align='center', parent=layout)
	maxFld = pm.intField(min=0, max=keyCount-1, parent=layout)
	run = pm.button(label='Run', parent=layout)
	transfer = pm.button(label='Transfer Animation', parent=layout)
	run.setCommand(buttonPressed)
	win.show()

if len(root) > 1:
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
			ui.Transfer.clicked.connect( self.TransferAnimation )
			ui.lUp.pressed.connect( self.moveLUP )
			ui.lUp.released.connect( self.rMoveLUP )
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
		def rMoveLUP( self ):
			deltaTimer = 0
		
		def moveLUP( self ):
			deltaTimer = 1
			while deltaTimer != 0:
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
	
			for x in range(keyCount):
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
		
	ui = loadUI('Path to the .ui file')
	cont = UIController(ui)