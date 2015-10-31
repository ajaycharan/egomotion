import read_liberty_patches as rlp
import my_exp_ptch as mept
import street_exp as se
import my_pycaffe as mp
import my_pycaffe_utils as mpu
import my_pycaffe_io as mpio
import matplotlib.pyplot as plt
import vis_utils as vu
import numpy as np
import caffe
import copy
from os import path as osp

def modify_params(paramStr, key, val):
	params = paramStr.strip().split('--')
	newStr = ''
	for i,p in enumerate(params):
		if len(p) ==0:
			continue
		if not(len(p.split()) == 2):
			continue
		k, v = p.split()
		if k.strip() == key:
			v = val
		newStr = newStr + '--%s %s ' % (k,v)
	return newStr

def get_fpr(recall, pdScore, gtLabel):
	pdScore = copy.deepcopy(pdScore)
	gtLabel = copy.deepcopy(gtLabel)
	N = sum(gtLabel==1)
	M = sum(gtLabel==0)
	assert(N+M == gtLabel.shape[0])
	idx = np.argsort(pdScore)
	#Sort in Decreasing Order
	pdScore = pdScore[idx[::-1]]
	gtLabel = gtLabel[idx[::-1]]
	posCount = np.cumsum(gtLabel==1)/float(N)
	threshIdx = np.where((posCount > recall)==True)[0][0]
	print (threshIdx, 'Thresh: %f' % pdScore[threshIdx])
	pdLabel   = pdScore >= pdScore[threshIdx]
	pdLabel   = pdLabel[0:threshIdx]
	gtLabel   = gtLabel[0:threshIdx]
	err       = len(pdLabel) - np.sum(pdLabel==gtLabel)
	fpr       = err/float(threshIdx)
	return fpr
	
def get_liberty_ptch_proto(prms, cPrms, modelIter):
	exp       = se.setup_experiment(prms, cPrms)
	libPrms   = rlp.get_prms()
	wFile     = libPrms.paths.wFile

	netDef    = mpu.ProtoDef(exp.files_['netdef'])
	paramStr  = netDef.get_layer_property('window_data', 'param_str')[1:-1]
	paramStr  = modify_params(paramStr, 'source', wFile)
	paramStr  = modify_params(paramStr, 'root_folder', libPrms.paths.jpgDir)
	paramStr  = modify_params(paramStr, 'batch_size', 100)
	netDef.set_layer_property('window_data', ['python_param', 'param_str'], 
						'"%s"' % paramStr, phase='TEST')
	netDef.set_layer_property('window_data', ['python_param', 'param_str'], 
						'"%s"' % paramStr)
	defFile = 'test-files/ptch_liberty_test.prototxt'
	netDef.write(defFile)
	return defFile

def test_ptch(prms, cPrms, modelIter, isLiberty=True):
	exp       = se.setup_experiment(prms, cPrms)
	if isLiberty:
		defFile   = get_liberty_ptch_proto(prms, cPrms, modelIter)
	else:
		defFile   = exp.files_['netdef']
	modelFile = exp.get_snapshot_name(modelIter)
	caffe.set_mode_gpu()
	net = caffe.Net(defFile, modelFile, caffe.TEST)

	gtLabel, pdScore, acc = [], [], []
	for i in range(10):
		data = net.forward(['ptch_label','ptch_fc', 'accuracy'])
		print (sum(data['ptch_label'].squeeze()==1))
		gtLabel.append(copy.deepcopy(data['ptch_label'].squeeze()))
		score   = np.exp(data['ptch_fc'])
		score   = score/(np.sum(score,1).reshape(score.shape[0],1))
		pdScore.append(copy.deepcopy(score[:,1]))
		acc.append(copy.deepcopy(data['accuracy']))
	gtLabel = np.concatenate(gtLabel)
	pdScore = np.concatenate(pdScore)
	return gtLabel, pdScore, acc


def vis_liberty_ptch():
	libPrms   = rlp.get_prms()
	wFile     = libPrms.paths.wFile
	wDat      = mpio.GenericWindowReader(wFile)
	rootDir   = libPrms.paths.jpgDir
	plt.ion()
	fig = plt.figure()
	while True:
		imNames, lbs = wDat.read_next()
		imNames  = [osp.join(rootDir, n.split()[0]) for n in imNames]
		figTitle = '%d' % lbs[0][0]
		im1      = plt.imread(imNames[0])
		im2      = plt.imread(imNames[1])
		vu.plot_pairs(im1, im2, fig=fig, figTitle=figTitle)	
		inp = raw_input('Press a key to continue')
		if inp=='q':
			return
	
def make_pascal3d_generic_window():
	srcFile  = '/data1/pulkitag/data_sets/pascal_3d/window_file_%s.txt'
	outFile  = '/data1/pulkitag/data_sets/pascal_3d/generic_window_file_%s.txt'
	setNames = ['train', 'val']
	for s in setNames:
		iFile = srcFile % s
		oFile = outFile % s
		with open(iFile) as fi:
			lines = fi.readlines()
			N     = len(lines)
			oFid  = mpio.GenericWindowWriter(oFile, N, 1, 3)
			for l in lines:
				pass
