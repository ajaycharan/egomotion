import os.path as osp
import numpy as np
import street_utils as su
import street_params as sp
import my_pycaffe_utils as mpu
from easydict import EasyDict as edict
import copy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pycaffe_config import cfg
import my_exp_config as mec
import pdb

##
# Parameters required to specify the n/w architecture
def get_nw_prms(**kwargs):
	#return mec.get_nw_prms(**kwargs)
	dArgs = edict()
	dArgs.netName     = 'alexnet'
	dArgs.concatLayer = 'fc6'
	dArgs.concatDrop  = False
	dArgs.contextPad  = 0
	dArgs.imSz        = 227
	dArgs.imgntMean   = True
	dArgs.maxJitter   = 11
	dArgs.randCrop    = False
	dArgs.lossWeight  = 1.0
	dArgs.multiLossProto   = None
	dArgs.ptchStreamNum    = 256
	dArgs.poseStreamNum    = 256
	dArgs.isGray           = False
	dArgs.isPythonLayer    = False
	dArgs.extraFc          = None
	dArgs.numFc5           = None
	dArgs.numConv4         = None
	dArgs.numCommonFc      = None
	dArgs.lrAbove          = None
	dArgs = mpu.get_defaults(kwargs, dArgs)
	if dArgs.numFc5 is not None:
		assert(dArgs.concatLayer=='fc5')
	expStr = 'net-%s_cnct-%s_cnctDrp%d_contPad%d_imSz%d_imgntMean%d_jit%d'\
						%(dArgs.netName, dArgs.concatLayer, dArgs.concatDrop, 
							dArgs.contextPad,
							dArgs.imSz, dArgs.imgntMean, dArgs.maxJitter)
	if dArgs.numFc5 is not None:
		expStr = '%s_numFc5-%d' % (expStr, dArgs.numFc5)
	if dArgs.numConv4 is not None:
		expStr = '%s_numConv4-%d' % (expStr, dArgs.numConv4)
	if dArgs.numCommonFc is not None:
		expStr = '%s_numCommonFc-%d' % (expStr, dArgs.numCommonFc)
	if dArgs.randCrop:
		expStr = '%s_randCrp%d' % (expStr, dArgs.randCrop)
	if not(dArgs.lossWeight==1.0):
		if type(dArgs.lossWeight)== list:
			lStr = ''
			for i,l in enumerate(dArgs.lossWeight):
				lStr = lStr + 'lw%d-%.1f_' % (i,l)
			lStr = lStr[0:-1]
			print lStr
			expStr = '%s_%s' % (expStr, lStr)
		else:
			assert isinstance(dArgs.lossWeight, (int, long, float))
			expStr = '%s_lw%.1f' % (expStr, dArgs.lossWeight)
	if dArgs.multiLossProto is not None:
		expStr = '%s_mlpr%s-posn%d-ptsn%d' % (expStr,
							dArgs.multiLossProto, dArgs.poseStreamNum, dArgs.ptchStreamNum)
	if dArgs.isGray:
		expStr = '%s_grayIm' % expStr
	if dArgs.isPythonLayer:
		expStr = '%s_pylayers' % expStr
	if dArgs.extraFc is not None:
		expStr = '%s_extraFc%d' % (expStr, dArgs.extraFc)
	if dArgs.lrAbove is not None:
		expStr = '%s_lrAbove-%s' % (expStr, dArgs.lrAbove)
	dArgs.expStr = expStr 
	return dArgs 

##
# Parameters that specify the learning
def get_lr_prms(**kwargs):	
	#return mec.get_lr_prms()
	dArgs = edict()
	dArgs.batchsize = 128
	dArgs.stepsize  = 20000	
	dArgs.base_lr   = 0.001
	dArgs.max_iter  = 250000
	dArgs.gamma     = 0.5
	dArgs.weight_decay = 0.0005
	dArgs.clip_gradients = -1
	dArgs.debug_info = False
	dArgs  = mpu.get_defaults(kwargs, dArgs)
	#Make the solver 
	debugStr = '%s' % dArgs.debug_info
	debugStr = debugStr.lower()
	del dArgs['debug_info']
	solArgs = edict({'test_iter': 100, 'test_interval': 1000,
						 'snapshot': 2000, 
							'debug_info': debugStr})
	print dArgs.keys()
	for k in dArgs.keys():
		if k in ['batchsize']:
			continue
		solArgs[k] = copy.deepcopy(dArgs[k])
	dArgs.solver = mpu.make_solver(**solArgs)	
	expStr = 'batchSz%d_stepSz%.0e_blr%.5f_mxItr%.1e_gamma%.2f_wdecay%.6f'\
					 % (dArgs.batchsize, dArgs.stepsize, dArgs.base_lr,
							dArgs.max_iter, dArgs.gamma, dArgs.weight_decay)
	if not(dArgs.clip_gradients==-1):
		expStr = '%s_gradClip%.1f' % (expStr, dArgs.clip_gradients)
	dArgs.expStr = expStr
	return dArgs 

##
# Parameters for fine-tuning
def get_finetune_prms(**kwargs):
	'''
		sourceModelIter: The number of model iterations of the source model to consider
		fine_max_iter  : The maximum iterations to which the target model should be trained.
		lrAbove        : If learning is to be performed some layer. 
		fine_base_lr   : The base learning rate for finetuning. 
 		fineRunNum     : The run num for the finetuning.
		fineNumData    : The amount of data to be used for the finetuning. 
		fineMaxLayer   : The maximum layer of the source n/w that should be considered.  
	''' 
	dArgs = edict()
	dArgs.base_lr = 0.001
	dArgs.runNum  = 1
	dArgs.maxLayer = None
	dArgs.lrAbove  = None
	dArgs.dataset  = 'sun'
	dArgs.maxIter  = 40000
	dArgs.extraFc     = False
	dArgs.extraFcDrop = False
	dArgs.sourceModelIter = 60000 
	dArgs = mpu.get_defaults(kwargs, dArgs)
 	return dArgs 


def get_caffe_prms(nwPrms, lrPrms, finePrms=None, 
									 isScratch=True, deviceId=1,
									 runNum=0, resumeIter=0):
	#return mec.get_caffe_prms() 
	caffePrms = edict()
	caffePrms.deviceId  = deviceId
	caffePrms.isScratch = isScratch
	caffePrms.nwPrms    = copy.deepcopy(nwPrms)
	caffePrms.lrPrms    = copy.deepcopy(lrPrms)
	caffePrms.finePrms  = copy.deepcopy(finePrms)
	caffePrms.resumeIter = resumeIter

	expStr = nwPrms.expStr + '/' + lrPrms.expStr
	if finePrms is not None:
		expStr = expStr + '/' + finePrms.expStr
	if runNum > 0:
		expStr = expStr + '_run%d' % runNum
	caffePrms['expStr'] = expStr
	caffePrms['solver'] = lrPrms.solver
	return caffePrms


def get_default_caffe_prms(deviceId=1):
	return mec.get_default_caffe_prms()
	nwPrms = get_nw_prms()
	lrPrms = get_lr_prms()
	cPrms  = get_caffe_prms(nwPrms, lrPrms, deviceId=deviceId)
	return cPrms

##
#Merge the definition of multiple layers
def _merge_defs(defs): 
	allDef = copy.deepcopy(defs[0])
	for d in defs[1:]:
		setNames = ['TRAIN', 'TEST']
		for s in setNames:
			trNames = d.get_all_layernames(phase=s)
			for t in trNames:
				trLayer = d.get_layer(t, phase=s)		
				allDef.add_layer(t, trLayer, phase=s)
	return allDef

##
#
def get_windowfile_rootdir(prms):
	mainDataDr = cfg.STREETVIEW_DATA_READ_IM
	if prms.isAligned:
		if prms.geoFence is not None and not(prms.rawImSz == 640):
			rootDir = osp.join(mainDataDr,
									 'pulkitag/data_sets/streetview/proc/resize-im/im%d/' % prms.rawImSz)
		else:
			rootDir = osp.join(mainDataDr, 
									'pulkitag/data_sets/streetview/raw/ssd105/Amir/WashingtonAligned/')
	else:
			rootDir = osp.join(mainDataDr,
									 'pulkitag/data_sets/streetview/proc/resize-im/im%d/' % prms.rawImSz)
		#raise Exception('rootDir is not defined')
	return rootDir

##
#Adapt the ProtoDef for the data layers
#Helper function for setup_experiment
def _adapt_data_proto(protoDef, prms, cPrms, finePrms=None):
	if finePrms is not None:
		rootDir = finePrms['paths']['imRootDir']
	else:
		rootDir = get_windowfile_rootdir(prms)
	#Set the mean file
	mainDataDr = cfg.STREETVIEW_DATA_MAIN
	if cPrms.nwPrms.imgntMean:
		if cPrms.nwPrms.isGray:
			fName = osp.join(mainDataDr, 'pulkitag/caffe_models/ilsvrc2012_mean_gray.binaryproto')
		else:
			fName = osp.join(mainDataDr, 'pulkitag/caffe_models/ilsvrc2012_mean.binaryproto')

	if not cPrms.nwPrms.isPythonLayer: 
		#Get the source file for the train and test layers
		protoDef.set_layer_property('window_data', ['generic_window_data_param', 'source'],
				'"%s"' % prms['paths']['windowFile']['train'], phase='TRAIN')
		protoDef.set_layer_property('window_data', ['generic_window_data_param', 'source'],
				'"%s"' % prms['paths']['windowFile']['test'], phase='TEST')

		#Set the root folder
		protoDef.set_layer_property('window_data', ['generic_window_data_param', 'root_folder'],
				'"%s"' % rootDir, phase='TRAIN')
		protoDef.set_layer_property('window_data', ['generic_window_data_param', 'root_folder'],
				'"%s"' % rootDir, phase='TEST')
		
		#Set the batch size
		protoDef.set_layer_property('window_data', ['generic_window_data_param', 'batch_size'],
				'%d' % cPrms.lrPrms.batchsize , phase='TRAIN')

		for p in ['TRAIN', 'TEST']:
			#Random Crop
			protoDef.set_layer_property('window_data', ['generic_window_data_param', 'random_crop'],
				'%s' % str(cPrms.nwPrms.randCrop).lower(), phase=p)
			#isGray
			protoDef.set_layer_property('window_data', ['generic_window_data_param', 'is_gray'],
				'%s' % str(cPrms.nwPrms.isGray).lower(), phase=p)
			#maxJitter
			protoDef.set_layer_property('window_data', ['generic_window_data_param', 'max_jitter'],
				cPrms.nwPrms.maxJitter, phase=p)
			#Context Pad
			protoDef.set_layer_property('window_data', ['generic_window_data_param', 'context_pad'],
				cPrms.nwPrms.contextPad, phase=p)
			#Image Size
			protoDef.set_layer_property('window_data', ['generic_window_data_param', 'crop_size'],
				cPrms.nwPrms.imSz, phase=p)
			#Mean file
			protoDef.set_layer_property('window_data', ['transform_param', 'mean_file'],
				'"%s"' % fName, phase=p)
	else:
		#Python layer
		if cPrms.nwPrms.isGray:
			grayStr = 'is_gray'
		else:
			grayStr = 'no-is_gray'
		
		for p in ['TRAIN', 'TEST']:
			paramStr = '"--source %s --root_folder %s --crop_size %d\
							  --batch_size %d --%s --mean_file %s --resume_iter %d"'
			if p == 'TRAIN':
				batchSz = cPrms.lrPrms.batchsize
				if finePrms is not None:
					paramStr = '"%s --jitter_amt %d --jitter_pct %f"'\
											 % (paramStr[1:-1], finePrms.jitter_amt, finePrms.jitter_pct) 
			else:
				batchSz = 50
			if finePrms is not None:
				winFile = finePrms['paths']['windowFile'][p.lower()]
			else:
				winFile = prms['paths']['windowFile'][p.lower()]
			params = paramStr % (winFile,
								rootDir, cPrms.nwPrms.imSz, batchSz, 
								grayStr, fName, cPrms.resumeIter)
			protoDef.set_layer_property('window_data', ['python_param', 'param_str'],
																	 params, phase=p)
	#Splitting for Siamese net
	if prms.isSiamese and cPrms.nwPrms.isGray:
		protoDef.set_layer_property('slice_pair', ['slice_param', 'slice_point'],
		1)
	
##
#The proto definitions for the data
def make_data_proto(prms, cPrms, finePrms=None):
	baseFilePath = prms.paths.baseNetsDr
	if cPrms.nwPrms.isPythonLayer:
		dataFile     = osp.join(baseFilePath, 'data_layers_python.prototxt')
	else:
		dataFile     = osp.join(baseFilePath, 'data_layers.prototxt')
	dataDef      = mpu.ProtoDef(dataFile)
	sliceFlag   = True
	fineSiamFlag    = False
	if len(prms.labelNames)==1 and prms.labelNames[0]=='nrml':
		sliceFlag = False
	if finePrms is not None and not finePrms.isSiamese:
		sliceFlag = False
		fineSiamFlag = True

	if len(prms.labelNames)==1 or fineSiamFlag:
		lbName = '"%s_label"' % prms.labelNames[0]
		top2 = mpu.make_key('top', ['top'])
		for ph in ['TRAIN', 'TEST']:
			dataDef.set_layer_property('window_data', top2, lbName, phase=ph)
			if not sliceFlag:
				dataDef.set_layer_property('window_data', 'top', 
																		'"data"', phase=ph)
	if sliceFlag:
		#Add slicing of labels	
		sliceFile = '%s_layers.prototxt' % prms.labelNameStr
		sliceDef  = mpu.ProtoDef(osp.join(baseFilePath, sliceFile))
		dataDef   = _merge_defs([dataDef, sliceDef])

	#Set to the new window files
	_adapt_data_proto(dataDef, prms, cPrms, finePrms=finePrms)
	return dataDef

##
#Make the proto for the computations
def make_net_proto(prms, cPrms, finePrms=None):
	baseFilePath = prms.paths.baseNetsDr
	isSiamese = False
	if prms.isSiamese:
		isSiamese = True
	if finePrms is not None and not finePrms.isSiamese:
		isSiamese = False
	if isSiamese:
		netFileStr = '%s_window_siamese_%s.prototxt'
	else:
		netFileStr = '%s_window_%s.prototxt'

	netFile = netFileStr % (cPrms.nwPrms.netName,
												 cPrms.nwPrms.concatLayer) 
	netFile = osp.join(baseFilePath, netFile)
	netDef  = mpu.ProtoDef(netFile)

	if cPrms.nwPrms.extraFc is not None:
		#Changethe name of the existing common_fc to common_fc_prev
		netDef.rename_layer('common_fc', 'common_fc_prev')
		netDef.set_layer_property('common_fc_prev', 'top', '"%s"' % 'common_fc_prev')
		#Rename the params
		netDef.set_layer_property('common_fc_prev', ['param', 'name'], '"%s"' % 'common_fc_prev_w')
		netDef.set_layer_property('common_fc_prev', ['param', 'name'],
							 '"%s"' % 'common_fc_prev_b', propNum=[1,0])
		netDef.rename_layer('relu_common', 'relu_common_prev')
		netDef.set_layer_property('relu_common_prev', 'top', '"%s"' % 'common_fc_prev')
		netDef.set_layer_property('relu_common_prev', 'bottom', '"%s"' % 'common_fc_prev')
		#Add the new layer
		eName   = 'common_fc'
		lastTop = 'common_fc_prev'
		fcLayer = mpu.get_layerdef_for_proto('InnerProduct', eName, lastTop,
                          **{'top': eName, 'num_output': cPrms.nwPrms.extraFc})
		reLayer = mpu.get_layerdef_for_proto('ReLU', 'relu_common', eName, **{'top': eName})
		netDef.add_layer(eName, fcLayer)
		netDef.add_layer('relu_common', reLayer)

	if cPrms.nwPrms.numFc5 is not None:
		netDef.set_layer_property('fc5', ['inner_product_param', 'num_output'], 
								'%d' % cPrms.nwPrms.numFc5)
		if prms.isSiamese:
			netDef.set_layer_property('fc5_p', ['inner_product_param', 'num_output'], 
									'%d' % cPrms.nwPrms.numFc5)
	
	if cPrms.nwPrms.numConv4 is not None:
		netDef.set_layer_property('conv4', ['convolution_param', 'num_output'], 
								'%d' % cPrms.nwPrms.numConv4)
		if prms.isSiamese:
			netDef.set_layer_property('conv4_p', ['convolution_param', 'num_output'], 
								'%d' % cPrms.nwPrms.numConv4)

	if cPrms.nwPrms.numCommonFc is not None:
		netDef.set_layer_property('common_fc', ['inner_product_param', 'num_output'], 
								'%d' % cPrms.nwPrms.numCommonFc)

	if cPrms.nwPrms.concatDrop:
		dropLayer = mpu.get_layerdef_for_proto('Dropout', 'drop-%s' % 'common_fc', 'common_fc',
                            **{'top': 'common_fc', 'dropout_ratio': 0.5})
		netDef.add_layer('drop-%s' % 'common_fc', dropLayer, 'TRAIN')

	if finePrms is not None:
		netDef.rename_layer('common_fc', 'common_fc_fine')

	return netDef

##
# The proto definitions for the loss
def make_loss_proto(prms, cPrms):
	baseFilePath = prms.paths.baseNetsDr
	lbDefs = []
	if not(type(cPrms.nwPrms.lossWeight) == list):
		lossWeight = [cPrms.nwPrms.lossWeight] * len(prms.labels)
	else:
		lossWeight = cPrms.nwPrms.lossWeight
	if cPrms.nwPrms.multiLossProto is not None:
		assert(prms.isMultiLabel)
		fName = '%s_%s_loss_layers.prototxt' % (prms.labelNameStr, 
							cPrms.nwPrms.multiLossProto)	
		fName = osp.join(baseFilePath,fName)
		lbDef  = mpu.ProtoDef(fName)
		#Modify pose parameters
		poseLb = prms.labels[prms.labelNames.index('pose')]
		poseIdx    = prms.labelNames.index('pose')
		lbDef.set_layer_property('pose_fc', ['inner_product_param', 'num_output'],
						 '%d' % poseLb.lbSz_)
		lbDef.set_layer_property('pose_stream_fc', ['inner_product_param', 'num_output'],
						 '%d' % cPrms.nwPrms.poseStreamNum)
		lbDef.set_layer_property('pose_loss', 'loss_weight', '%f' % lossWeight[poseIdx])
		#Modify ptch parameters
		ptchLb  = prms.labels[prms.labelNames.index('ptch')]
		ptchIdx = prms.labelNames.index('ptch')
		lbDef.set_layer_property('ptch_fc', ['inner_product_param', 'num_output'],
						 '%d' % ptchLb.lbSz_)
		lbDef.set_layer_property('ptch_stream_fc', ['inner_product_param', 'num_output'],
						 '%d' % cPrms.nwPrms.ptchStreamNum)
		lbDef.set_layer_property('ptch_loss', 'loss_weight', '%f' % lossWeight[ptchIdx])
		return lbDef

	if prms.isSiamese and 'nrml' in prms.labelNames:
		defFile = osp.join(baseFilePath, 'nrml_loss_layers.prototxt')
		nrmlDef1 = mpu.ProtoDef(defFile)
		nrmlDef2 = mpu.ProtoDef(defFile)
		#Structure the two defs
		nrmlDef1.set_layer_property('nrml_fc', 'name', '"nrml_1_fc"')
		nrmlDef1.set_layer_property('nrml_1_fc','top', '"nrml_1_fc"')
		nrmlDef2.set_layer_property('nrml_fc', 'name', '"nrml_2_fc"')
		nrmlDef2.set_layer_property('nrml_2_fc','top', '"nrml_2_fc"')
		#Merge the two defs			 	
		lbDef = _merge_defs(nrmlDef1, nrmlDef2)
		lbDefs.append(lbDef)
	elif 'nrml' in prms.labelNames:
		idx    = prms.labelNames.index('nrml')
		lbInfo = prms.labels[idx]
		if not(lbInfo.loss_ == 'classify'):
			defFile = osp.join(baseFilePath, 'nrml_loss_layers.prototxt')
			lbDef   = mpu.ProtoDef(defFile)
			lbDef.set_layer_property('nrml_loss', 'loss_weight', '%f' % lossWeight[idx])
		else:
			defFile = osp.join(baseFilePath, 'nrml_loss_classify_layers.prototxt')
			lbDef   = mpu.ProtoDef(defFile)
			lbDef.set_layer_property('nrml_fc_1',['inner_product_param', 'num_output'],
						 '%d' % lbInfo.numBins_)
			lbDef.set_layer_property('nrml_fc_2',['inner_product_param', 'num_output'],
						 '%d' % lbInfo.numBins_)
			lbDef.set_layer_property('nrml_loss_1', 'loss_weight', '%f' % lossWeight[idx])
			lbDef.set_layer_property('nrml_loss_2', 'loss_weight', '%f' % lossWeight[idx])
			lbDef.set_layer_property('nrml_loss_1', ['loss_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
			lbDef.set_layer_property('nrml_loss_2', ['loss_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
			lbDef.set_layer_property('nrml_accuracy_1', ['accuracy_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
			lbDef.set_layer_property('nrml_accuracy_2', ['accuracy_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
		lbDefs.append(lbDef)
	if 'ptch' in prms.labelNames:
		idx     = prms.labelNames.index('ptch')
		defFile = osp.join(baseFilePath, 'ptch_loss_layers.prototxt')
		lbDef   = mpu.ProtoDef(defFile)
		lbDef.set_layer_property('ptch_loss', 'loss_weight', '%f' % lossWeight[idx])
		lbDefs.append(lbDef)
	if 'pose' in prms.labelNames:
		idx     = prms.labelNames.index('pose')
		lbInfo  = prms.labels[idx]
		if lbInfo.loss_ in ['l2', 'l1', 'logl1']:
			if lbInfo.loss_ in ['l2']:
				defFile = osp.join(baseFilePath, 'pose_loss_layers.prototxt')
			elif lbInfo.loss_ in ['l1']:
				defFile = osp.join(baseFilePath, 'pose_loss_l1_layers.prototxt')
			else:
				defFile = osp.join(baseFilePath, 'pose_loss_log_l1_layers.prototxt')
			lbDef   = mpu.ProtoDef(defFile)
			lbDef.set_layer_property('pose_fc', ['inner_product_param', 'num_output'],
							 '%d' % lbInfo.lbSz_)
			if lbInfo.loss_ in ['l2']:
				lbDef.set_layer_property('pose_loss', 'loss_weight', '%f' % lossWeight[idx])
			else:
				print ('FOR L1 LOSS, LOSS WEIFHT DOESNT WORK')
		elif lbInfo.loss_ in ['classify']:
			defFile = osp.join(baseFilePath, 'pose_loss_classify_layers.prototxt')
			lbDef   = mpu.ProtoDef(defFile)
			fcNames = ['yaw', 'pitch']
			for fc in fcNames:
				lbDef.set_layer_property('%s_fc' % fc,['inner_product_param', 'num_output'],
							 '%d' % lbInfo.numBins_)
				lbDef.set_layer_property('%s_loss' % fc, 'loss_weight', '%f' % lossWeight[idx])
				lbDef.set_layer_property('%s_loss' % fc, ['loss_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
				lbDef.set_layer_property('%s_accuracy' % fc, ['accuracy_param', 'ignore_label'], 
						 '%d' % lbInfo.numBins_)
		else:
			raise Exception ('Loss Type %s not recognized' % lbInfo.loss_)
		lbDefs.append(lbDef)
	lbDef = _merge_defs(lbDefs)
	#Replace the EuclideanLoss with EuclideanLossWithIgnore 
	l2Layers = lbDef.get_layernames_from_type('EuclideanLoss')
	for ll in l2Layers:
		lbDef.set_layer_property(ll, 'type', '"EuclideanLossWithIgnore"')
	return lbDef	

##
#Setup the experiment
def setup_experiment(prms, cPrms, finePrms=None):
	#Get the protodef for the n/w architecture
	netDef   = make_net_proto(prms, cPrms, finePrms=finePrms)
	#Data protodef
	dataDef  = make_data_proto(prms, cPrms, finePrms=finePrms)
	#Loss protodef
	lossDef  = make_loss_proto(prms, cPrms)
	#Merge all defs
	protoDef = _merge_defs([dataDef, netDef, lossDef])
	if finePrms is None:
		if cPrms.nwPrms.lrAbove is not None:
			protoDef.set_no_learning_until(cPrms.nwPrms.lrAbove)
			print ('Setting no learning until %s' % cPrms.nwPrms.lrAbove)
		#Get the solver definition file
		solDef   = cPrms['solver']
	else:
		if finePrms.lrAbove is not None:
			protoDef.set_no_learning_until(finePrms.lrAbove)
			print ('Setting no learning until %s' % finePrms.lrAbove)
		solDef   = finePrms['solver']
	#Experiment Object	
	caffeExp = get_experiment_object(prms, cPrms)
	caffeExp.init_from_external(solDef, protoDef)

	#Result paths
	caffeExp.paths = edict()
	caffeExp.paths.testImVis = osp.join(prms.paths.res.testImVisDr,
														 prms.expName, cPrms.expStr)
	sp._mkdir(caffeExp.paths.testImVis)	
	caffeExp.paths.testImVis = osp.join(caffeExp.paths.testImVis, 'im%05d.jpg')
	return caffeExp

##
#Write the files for running the experiment. 
def make_experiment(prms, cPrms, isFine=False, 
										srcModelFile=None, srcDefFile=None):
	'''
		Specifying the srcModelFile is a hack to overwrite a model file to 
		use with pretraining. 
	'''
	resumeIter = cPrms.resumeIter
	if resumeIter == 0:
		resumeIter = None
	if isFine:
		caffeExp = setup_experiment_finetune(prms, cPrms, srcDefFile=srcDefFile)
		if srcModelFile is None:
			#Get the model name from the source experiment.
			srcCaffeExp  = setup_experiment(prms, cPrms)
			if cPrms['fine']['modelIter'] is not None:
				modelFile = srcCaffeExp.get_snapshot_name(cPrms['fine']['modelIter'])
			else:
				modelFile = None
	else:
		caffeExp  = setup_experiment(prms, cPrms)
		modelFile = None

	if resumeIter is not None:
		modelFile = None

	if srcModelFile is not None:
		modelFile = srcModelFile

	caffeExp.make(modelFile=modelFile, resumeIter=resumeIter)
	return caffeExp	

##
#Setup experiment from previous
def setup_experiment_from_previous(srcPrms, srcCPrms, prms, cPrms, srcModelIter):
	#For resuming the training
	resumeIter = cPrms.resumeIter
	if resumeIter == 0:
		resumeIter = None
	#Get the srcExperiment Model File
	srcExp    = setup_experiment(srcPrms, srcCPrms)
	modelFile = srcExp.get_snapshot_name(srcModelIter)
	if not osp.exists(modelFile):
		raise Exception('MODEL FILE DOESNOT EXIST')

	#Name the target experiment appropriately  
	prms['expName'] = 'fine-FROM/%s/%s_srcModelIter%dK/fine-TO/'\
							 % (srcPrms['expName'], cPrms['expStr'], int(srcModelIter/1000))
	exp = setup_experiment(prms, cPrms)
	return exp, modelFile


##
#Make an experiment by initializaing from a previos experiment
def make_experiment_from_previous(srcPrms, srcCPrms, prms, cPrms,
													 srcModelIter):

	exp, modelFile = setup_experiment_from_previous(srcPrms, srcCPrms, prms, cPrms, 
													srcModelIter)
	exp.make(modelFile=modelFile)
	return exp	

##
#Setup experiment for finetuning
def setup_experiment_for_finetune(srcPrms, srcCPrms, finePrms, srcModelIter):
	srcPrms = copy.deepcopy(srcPrms)
	srcCPrms = copy.deepcopy(srcCPrms)
	finePrms = copy.deepcopy(finePrms)
	#Get the srcExperiment Model File
	srcExp    = setup_experiment(srcPrms, srcCPrms)
	modelFile = srcExp.get_snapshot_name(srcModelIter)
	if not osp.exists(modelFile):
		print modelFile
		raise Exception('MODEL FILE DOESNOT EXIST')

	#Name the target experiment appropriately  
	srcPrms['expName'] = 'fine-FROM/%s/%s_srcModelIter%dK/fine-TO/%s'\
							 % (srcPrms['expName'], srcCPrms['expStr'], int(srcModelIter/1000),
			            finePrms['expName'])
	exp = setup_experiment(srcPrms, srcCPrms, finePrms)
	return exp, modelFile

def make_experiment_for_finetune(srcPrms, srcCPrms, finePrms, srcModelIter):
	exp, modelFile = setup_experiment_for_finetune(srcPrms, srcCPrms, finePrms, 
													srcModelIter)
	exp.make(modelFile=modelFile)
	return exp	

def get_experiment_accuracy(prms, cPrms=None, lossName=None):
	if cPrms is None:
		exp = prms
	else:
		exp     = setup_experiment(prms, cPrms)
	logFile = exp.expFile_.logTrain_	
	#For getting the names of losses
	if cPrms is not None:	
		lossDef  = make_loss_proto(prms, cPrms)
		lNames    = lossDef.get_all_layernames()
		lossNames = [l for l in lNames if 'loss' in l or 'acc' in l]
		if lossName is not None:
			assert lossName in lossNames
			lossNames = [lossName]
	else:
		lossNames = lossName
	#print (lossNames)
	return log2loss(logFile, lossNames)

def plot_experiment_accuracy(prms, cPrms=None, svFile=None,
								isTrainOnly=False, isTestOnly=False, ax=None,
								lossName=None):
	testData, trainData = get_experiment_accuracy(prms, cPrms, lossName=lossName)
	if ax is None:
		plt.figure()
		ax = plt.subplot(111)
	if not isTestOnly:
		for k in trainData.keys():
			if lossName is not None and not (k in lossName):
				continue
			if k == 'iters':
				continue
			ax.plot(trainData['iters'][1:], trainData[k][1:],'b',  linewidth=3.0)
	if not isTrainOnly:
		for k in testData.keys():
			if lossName is not None and not (k in lossName):
				continue
			if k == 'iters':
				continue
			ax.plot(testData['iters'][1:], testData[k][1:],'r',  linewidth=3.0)
	if svFile is not None:
		with PdfPages(svFile) as pdf:
			pdf.savefig()
	return ax


def read_log(fileName):
	'''
	'''
	fid = open(fileName,'r')
	trainLines, trainIter = [], []
	testLines, testIter   = [], []
	iterNum   = None
	iterStart = False
	#Read the test lines in the log
	while True:
		try:
			l = fid.readline()
			if not l:
				break
			if 'Iteration' in l:
				iterNum  = int(l.split()[5][0:-1])
				iterStart = True
			if 'Test' in l and ('loss' in l or 'acc' in l):
				testLines.append(l)
				if iterStart:
					testIter.append(iterNum)
					iterStart = False
			if 'Train' in l and ('loss' in l or 'acc' in l):
				trainLines.append(l)
				if iterStart:
					trainIter.append(iterNum)
					iterStart = False
		except ValueError:
			print 'Error in reading .. Skipping line %s ' % l
	fid.close()
	return testLines, testIter, trainLines, trainIter

##
#Read the loss values from a log file
def log2loss(fName, lossNames):
	testLines, testIter, trainLines, trainIter = read_log(fName)
	N = len(lossNames)
	#print N, len(testLines), testIter
	#assert(len(testLines)==N*len(testIter), 'Error in test Lines')
	#assert(len(trainLines)==N*len(trainIter), 'Error in train lines')
		
	testData, trainData = {}, {}
	for t in lossNames:
		testData[t], trainData[t] = [], []
		#Parse the test data
		for l in testLines:
			if t in l:
				data = l.split()
				#print data
				assert data[8] == t, data
				idx = data.index('=')
				testData[t].append(float(data[idx+1]))
		#Parse the train data
		for l in trainLines:
			if t in l:
				data = l.split()
				assert data[8] == t
				idx = data.index('=')
				trainData[t].append(float(data[idx+1]))
	for t in lossNames:
		testData[t]  = np.array(testData[t])
		trainData[t] = np.array(trainData[t])
	testData['iters']  = np.array(testIter)
	trainData['iters'] = np.array(trainIter)
	return testData, trainData

def get_experiment_object(prms, cPrms):
	caffeExp = mpu.CaffeExperiment(prms['expName'], cPrms['expStr'], 
							prms['paths']['expDir'], prms['paths']['snapDir'],
						  deviceId=cPrms['deviceId'])
	return caffeExp



