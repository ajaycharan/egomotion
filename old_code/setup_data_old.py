## @package setup_data
#	Functions for setting up the data

import numpy as np
from easydict import EasyDict as edict
import os.path as osp
from pycaffe_config import cfg
import os
import pdb
import subprocess
import matplotlib.pyplot as plt
import mydisplay as mydisp
import h5py as h5
import pickle
import street_utils as su
import street_params as sp
import scipy.misc as scm
from multiprocessing import Pool, Manager, Queue, Process
import time
import copy

##
# Save a list of keys of folders for which aligned data
# is available.  
def save_aligned_keys(prms):
	keys, names = su.get_folder_keys_all(prms)
	with open(prms.paths.proc.folders.aKey,'w') as f:
		for k,n in zip(keys,names):	
			if 'Aligned' in n:
				f.write('%s\n' % k)

##
#Save keys of folders that donot contain aligned data
def save_non_aligned_keys(prms):
	keys, names = su.get_folder_keys_all(prms)
	with open(prms.paths.proc.folders.naKey,'w') as f:
		for (k,n) in zip(keys, names):
			_,suffix  = osp.split(n)
			isAligned = False
			for n2 in names:
				if 'Aligned' in n2 and suffix in n2:
					isAligned=True
			if not isAligned:
				print n

##
# Each folder contains files as prefix.txt, prefix.jpg
# the .txt file contains the metadata and .jpg the image
# Save 'prefix' only when prefix.jpg and prefix.txt both
# are present. 
def read_prefixes_from_folder(dirName):
	allNames = os.listdir(dirName)
	#Extract the prefixes
	imNames   = sorted([f for f in allNames if '.jpg' in f], reverse=True)
	lbNames   = sorted([f for f in allNames if '.txt' in f], reverse=True)
	prefixStr = []
	for (i,imn) in enumerate(imNames):
		imn = imn[0:-4]
		if i>= len(lbNames):
			continue
		if imn in lbNames[i]:
			prefixStr = prefixStr + [imn] 
	return prefixStr

##
#Store prefix of folder with key "key" in file with name "name" 
def save_folder_prefixes_by_id(prms, key, name, forceWrite=False):
	print (key, name)
	fName   = prms.paths.proc.folders.pre % key
	if osp.exists(fName) and (not forceWrite):
		return
	preStrs = read_prefixes_from_folder(name) 
	with open(fName, 'w') as f:
		for p in preStrs:
			f.write('%s \n' % p)
	return None

def _save_folder_prefixes_by_id(args):
	return save_folder_prefixes_by_id(*args)

##
# Save prefix of each folder in a seperate file
def save_folder_prefixes(prms, forceWrite=False):
	fid   = open(prms.paths.proc.folders.key, 'r')
	lines = [l.strip() for l in fid.readlines()]
	fid.close()
	keys, names = [], []
	pool = Pool(processes=32)
	inArgs = []
	for l in lines:
		key, name = l.split()
		inArgs.append((prms, key, name, forceWrite))
	res = pool.map_async(_save_folder_prefixes_by_id, inArgs)
	_   = res.get()
	del pool
	
##
# For each folder find the number of prefixes
# and the number of groups. 	
def save_counts(prms):
	keys,_ = su.get_folder_keys_all(prms)	
	prefixCount = edict()
	groupCount  = edict()
	for k in keys:
		print(k)
		prefix = su.get_prefixes(prms, k)
		prefixCount[k] = len(prefix)
		grps = su.get_target_groups(prms, k)
		groupCount[k] = len(grps)
	pickle.dump({'prefixCount': prefixCount, 'groupCount': groupCount},
						 open(prms.paths.proc.countFile, 'w'))

##
#Get the prefix count
def get_prefix_count(prms):
	data =	pickle.load(open(prms.paths.proc.countFile, 'r'))
	pCount, gCount = data['prefixCount'], data['groupCount']
	return pCount, gCount	

##
#Save groups by ids
def save_group_by_id(prms, k, isForceCompute=False):
	'''
		k: folderId
	'''
	opName = prms.paths.label.grps % k
	if (not isForceCompute) and osp.exists(opName):
		print ('File %s exists, skipping computation' % opName)
		return

	print(k)
	imNames, lbNames, prefixes = su.folderid_to_im_label_files(prms, k, opPrefix=True)
	#Determine groups
	grps = su.get_target_groups(prms, k)
	#Read the labels of each group and save them
	grpLabels = edict()
	grpKeyStr = prms.paths.grp.keyStr
	for ig, g in enumerate(grps[0:-1]):
		st = g
		en = grps[ig+1]
		grpKey = grpKeyStr % ig	
		grpLabels[grpKey]      = edict()
		grpLabels[grpKey].num  = en - st
		grpLabels[grpKey].prefix   = []
		grpLabels[grpKey].data     = []
		grpLabels[grpKey].folderId = k
		for i in range(st,en):
			tmpGrp = su.parse_label_file(lbNames[i])
			if tmpGrp is not None:
				grpLabels[grpKey].data.append(tmpGrp)
				grpLabels[grpKey].prefix.append(prefixes[i])
	pickle.dump({'groups': grpLabels}, 
						open(opName, 'w'))	

##
#Save group by id
def _save_group_by_id(args):
	save_group_by_id(*args)	
	return True

##
# Save the groups
def save_groups(prms, isForceCompute=False):
	#keys,_ = su.get_folder_keys_all(prms)	
	keys = su.get_geo_folderids(prms)	
	inArgs = []
	pool = Pool(processes=32)
	for k in keys:
		inArgs.append((prms, k, isForceCompute))
		#save_group_by_id(prms, k, isForceCompute=isForceCompute)
	jobs = pool.map_async(_save_group_by_id, inArgs)	
	res  = jobs.get()
	del pool

##
#Save the group data that only consists of aligned images
def save_group_aligned_by_id(prms, k, isForceCompute=False):
	'''
		k: folderId
	'''
	opName = prms.paths.label.grpsAlgn % k
	if (not isForceCompute) and osp.exists(opName):
		print ('File %s exists, skipping computation' % opName)
		return
	print(k)

	srcName = prms.paths.label.grps % k
	data    = pickle.load(open(srcName,'r'))
	inGrps  = data['groups']

	grpData = edict()
	for gk, g in inGrps.iteritems():
		idx = [i for i,l in enumerate(g.data) if l.align is not None]
		if len(idx)==0:
			continue
		grpData[gk]         = edict()
		grpData[gk].num     = len(idx)
		grpData[gk].prefix  = [g.prefix[i] for i in idx]  
		grpData[gk].data    = [g.data[i] for i in idx]
		grpData[gk].folderId = k
	pickle.dump({'groups': grpData}, 
						open(opName, 'w'))	

##
#Save group by id
def _save_group_aligned_by_id(args):
	save_group_aligned_by_id(*args)	
	return True

##
#Only save the groups that have alignment data
def save_groups_aligned(prms, isForceCompute=False):
	keys,_ = su.get_folder_keys_all(prms)	
	inArgs = []
	pool = Pool(processes=32)
	for k in keys:
		inArgs.append((prms, k, isForceCompute))
	jobs = pool.map_async(_save_group_aligned_by_id, inArgs)	
	res  = jobs.get()
	del pool

##
#Save geo localized groups
def save_geo_groups(prms):
	keys = su.get_folder_keys(prms)
	if prms.geoFence == 'dc-v1':
		for k in keys:
			print (k)
			grpFile  = prms.paths.label.grps % k
			grpDat   = pickle.load(open(grpFile, 'r'))
			grpDat   = grpDat['groups']
			geoGrp   = edict()
			geoKeys  = []
			for gKey, gDat in grpDat.iteritems(): 
				isInside = su.is_group_in_geo(prms, gDat)
				if isInside:
					geoGrp[gKey] = gDat
					geoKeys.append(gKey)
			outName = prms.paths.grp.geoFile % k
			print ('Saving to %s' % outName) 
			pickle.dump({'groups': geoGrp, 'groupIds': geoKeys}, open(outName,'w'))

	elif prms.geoFence == 'dc-v2':
		#This specifies groups a subset of folders
		#so nothing needs to be saved
		pass
	else:
		raise Exception('Cannot save groups')
			

##
#Get the prefixes for a particular geo group
def get_prefixes_geo(prms, folderId):
	data = pickle.load(open(prms.paths.grp.geoFile % folderId))
	grps = data['groups']
	pref = []
	for _,g in grps.iteritems():
		for n in range(g.num):
			pref.append(g.prefix[n].strip())
	return pref

##
#Get all the geo prefixes
def get_prefixes_geo_all(prms):
	keys = su.get_folder_keys(prms)
	pref = edict()
	for k in keys:
		pref[k] = get_prefixes_geo(prms, k)
	return pref

##
#Helper for save_cropped_images_geo
def _write_im(prms, readList, outNames, rootDir):
	if prms.isAligned:
		rootDir = osp.join(cfg.STREETVIEW_DATA_MAIN, 
							'pulkitag/data_sets/streetview/raw/ssd105/Amir/WashingtonAligned/')
	else:
		raise Exception('rootDir is not defined')
	rdNames = su.prefix2imname(prms, readList)
	for r in range(len(rdNames)):
		#print (rdNames[r][0], outNames[r])
		im       = scm.imread(osp.join(rootDir, rdNames[r][0]))
		#Resize
		h, w, ch = im.shape
		hSt = max(0,int(h/2 - prms.rawImSz/2))
		wSt = max(0,int(w/2 - prms.rawImSz/2))
		hEn = min(h, int(hSt + prms.rawImSz))
		wEn = min(w, int(wSt + prms.rawImSz))
		im =  im[hSt:hEn, wSt:wEn, :] 
		#Save the image
		scm.imsave(outNames[r], im)

#For dc-v1 geofencing follow this procedure
#for storing the images
def save_croppped_images_dc_v1(prms):
	pref    = get_prefixes_geo_all(prms)
	imKeys  = edict()
	imCount = 0 		
	l1Count, l2Count = 0,0
	l1Max = 1e+6
	l2Max = 1e+3
	readList  = []
	outNames  = []
	for k in pref.keys():
		imKeys[k]= edict()
		rootFolder = su.id2name_folder(k)
		print (k, imCount)
		for i in range(len(pref[k])):
			imNum  = imCount % 1000
			imName = 'l1-%d/l2-%d/im%04d.jpg' % (l1Count, l2Count, imNum)
			imKeys[k][pref[k][i]] = imName
			imName = osp.join(prms.paths.proc.im.dr, imName)
			imDir,_ = osp.split(imName)
			sp._mkdir(imDir)
			readList.append((k, pref[k][i], None, None))
			outNames.append(imName)
			
			#Increment the counters
			imCount = imCount + 1
			l1Count = int(np.floor(imCount/l1Max))
			l2Count = int(np.floor((imCount % l1Max)/l2Max))
			
			#Write the images if needed
			if (imCount >= l2Max and (imCount % l2Max)==0):
				print (imCount)
				_write_im(prms, readList, outNames)	
				readList, outNames = [], []
	_write_im(prms, readList, outNames)
	pickle.dump({'imKeys':imKeys}, open(prms.paths.proc.im.keyFile,'w'))	


##
#Helper for save_cropped_images_by_folderid
def _write_im_v2(prms, inNames, outNames, crpList, isForceWrite=False):
	N = len(inNames)
	assert N == len(outNames)
	assert N == len(crpList)
	for i in range(N):
		if osp.exists(outNames[i]) and not isForceWrite:
			continue
		im         = scm.imread(inNames[i])
		h, w, ch = im.shape
		if crpList[i] is not None:
			cy, cx = crpList[i][0], crpList[i][1] 
		else:
			cy, cx = h/2, w/2
		#Crop
		hSt = min(h, max(0,int(cy - prms.rawImSz/2)))
		wSt = min(w, max(0,int(cx - prms.rawImSz/2)))
		hEn = min(h, int(hSt + prms.rawImSz))
		wEn = min(w, int(wSt + prms.rawImSz))
		imSave = np.zeros((prms.rawImSz, prms.rawImSz,3)).astype(np.uint8)
		hL, wL  = hEn - hSt, wEn - wSt
		#print hSt, hEn, wSt, wEn
		imSave[0:hL, 0:wL,:] =  im[hSt:hEn, wSt:wEn, :] 
		#Save the image
		dirName, _ = osp.split(outNames[i])
		sp._mkdir(dirName)
		scm.imsave(outNames[i], imSave)

def _write_im_v2_p(args):
	_write_im_v2(*args)
	return True

##
#Crop and save all images in folder with id "folderId"
def save_crop_images_by_folderid(prms, folderId,
							 isForceWrite=False, isParallel=False):
	
	keyFile = prms.paths.proc.im.folder.keyFile % folderId
	if osp.exists(keyFile):
		print ('%s exists, skipping' % keyFile)
		return

	#Get the groups
	grps = su.get_groups(prms, folderId, setName=None)
	if grps == []:
		print ('%s is excluded for some reason' % folderId)
		return

	#Get the root folder
	rootFolder = su.id2name_folder(prms, folderId)
	svFolder   = prms.paths.proc.im.folder.dr % folderId
	#Go through the pictures in all the groups
	imCount, lCount = 0, 0
	lMax    = 1e+3
	imKeys  = edict()
	inList, outList, crpList = [], [], []
	inArgs = []
	for gk, g in grps.iteritems():
		prefix = [pr.strip() for pr in g.prefix]
		for (i,p) in enumerate(prefix):
			inName    = osp.join(rootFolder, p + '.jpg')
			outName   = 'l-%d/im%04d.jpg' % (lCount, imCount % int(lMax)) 			
			imKeys[p] = outName
			outName   = osp.join(svFolder, outName) 
			inList.append(inName)
			outList.append(outName)
			if g.data[i].align is not None:
				crpList.append(g.data[i].align.loc)
			else:
				crpList.append(None)
		
			#Increment the counters
			imCount = imCount + 1
			lCount = int(np.floor(imCount/lMax))

			if (imCount > lMax and (imCount % lMax)==0):
				#Save the image
				print (folderId, imCount)
				if isParallel:
					inArgs.append([prms, inList, outList, crpList, isForceWrite])
				else:	
					_write_im_v2(prms, inList, outList, crpList, isForceWrite)
				inList, outList, crpList = [], [], []

	#Writethe images out finally	
	if isParallel:
		inArgs.append([prms, inList, outList, crpList, isForceWrite])
	else:	
		_write_im_v2(prms, inList, outList, crpList, isForceWrite)
	if isParallel:
		pool = Pool(processes=10)
		jobs = pool.map_async(_write_im_v2_p, inArgs)	
		res  = jobs.get()
		del pool
	pickle.dump({'imKeys':imKeys}, open(keyFile,'w'))	

#Wrapper for save_crop_images_by_folderid
def _save_crop_images_by_folderid(args):
	save_crop_images_by_folderid(*args)
	return True

##
# For every folder save cropped images
def save_cropped_images(prms, isForceWrite=False):
	if prms.geoFence == 'dc-v1':
		save_cropped_images_dc_v1(prms)
		return
	elif prms.geoFence is None:
		print ('Image Cropping is only defined for cropped parts')
		return
	#Get all the keys
	#folderKeys = su.get_folder_keys(prms)
	folderKeys = su.get_geo_folderids(prms)
	inArgs = []
	for k in folderKeys:
		inArgs.append([prms, k, isForceWrite])
	pool = Pool(processes=10)
	jobs = pool.map_async(_save_crop_images_by_folderid, inArgs)	
	res  = jobs.get()
	del pool


##
#Save the splits data
def save_train_test_splits(prms, isForceWrite=False):
	if prms.splits.dist is None:
		save_train_test_splits_old(prms, isForceWrite=isForceWrite)
		return None

	trFolderKeys, teFolderKeys = sp.get_train_test_defs(prms.geoFence, prms.splits.ver)
	allFolderKeys              = su.get_folder_keys(prms)

	#Load the test groups
	teGrps = edict()
	for tef in teFolderKeys:
		fName = prms.paths.proc.splitsFile % tef
		teGrps[tef] = su.get_groups(prms, tef, setName=None)
		trKeys      = []
		teKeys      = teGrps[tef].keys()
		#Save the splits
		splits = edict()
		splits.train = trKeys	
		splits.test  = teKeys
		#Save the data		
		pickle.dump({'splits': splits}, open(fName, 'w'))

	return
	#Ensure that train and test groups are far away
	for trf in trFolderKeys:
		fName = prms.paths.proc.splitsFile % trf
		if osp.exists(fName) and not isForceWrite:
			print ('%s exists, skipping computation' % fName)
			continue
		trGrps    = su.get_groups(prms, trf, setName=None)
		grps      = copy.deepcopy(trGrps)
		trKeys    = trGrps.keys()
		teKeys    = []
		for tef in teFolderKeys:
			trKeys = p_filter_groups_by_dist(prms, grps, teGrps[tef])
			print ('%s - Before: %d, After: %d' % (trf, len(trGrps.keys()), len(trKeys)))
			grps   = edict()
			#Filter the groups
			for t in trKeys:
				grps[t] = trGrps[t]				 
		#Save the splits
		splits = edict()
		splits.train = trKeys	
		splits.test  = teKeys
		#Save the data		
		pickle.dump({'splits': splits}, open(fName, 'w'))

	#The remainder of folders have no train/test examples
	trteKeys  = list(set(trFolderKeys) | set(teFolderKeys))
	otherKeys = [k for k in allFolderKeys if k not in trteKeys]
	for k in otherKeys:
		trKeys, teKeys = [], []	 
		#Save the splits
		splits = edict()
		splits.train = trKeys	
		splits.test  = teKeys
		#Save the data		
		fName = prms.paths.proc.splitsFile % k
		pickle.dump({'splits': splits}, open(fName, 'w'))

##
#
def print_before_after_split_counts(prms):
	trFolderKeys, teFolderKeys = sp.get_train_test_defs(prms.geoFence, prms.splits.ver)
	for tr in trFolderKeys:
		fName = prms.paths.proc.splitsFile % tr
		dat   = pickle.load(open(fName, 'r'))
		splitLen = len(dat['splits']['train'])
		origGrps = su.get_groups(prms, tr, setName=None)
		print '%s, after: %d, before: %d' % (tr, splitLen, len(origGrps.keys()))

##
#The old hacky way of generating train-test splits
def save_train_test_splits_old(prms, isForceWrite=False):
	keys = su.get_folder_keys(prms)
	for k in keys:
		fName = prms.paths.proc.splitsFile % k
		if os.path.exists(fName) and isForceWrite:
			print('%s already exists' % fName)
			#inp = raw_input('Are you sure you want to overwrite')
			#if not (inp == 'y'):
			#	return
		if osp.exists(fName) and not isForceWrite:
			print ('%s exists, skipping' % fName)	
			continue

		#Form the random seed
		randSeed  = prms.splits.randSeed + 2 * int(k)	
		randState = np.random.RandomState(randSeed) 
		#Read the groups of the fodler
		grps = ['%07d' % ig for (ig,g) in enumerate(su.get_target_groups(prms, k)[0:-1])]
		N    = len(grps)
		print('Folder: %s, num groups: %d' % (k,N))
		teN  = int((prms.splits.tePct/100.0) * N)	
		perm = randState.permutation(N)
		tePerm = perm[0:teN]
		#Form an extended testing set to exclude the neighbors
		valPerm = []
		print ('Extending test set for buffering against closeness to train set')
		for t in tePerm:
			st = max(0, t - prms.splits.teGap)
			en = min(len(grps), t + prms.splits.teGap+1)
			valPerm = valPerm + [v for v in range(st, en)]
		print ('Form the train set')
		#Form the training set
		trPerm = [t for t in perm if t not in valPerm]
		splits = edict()
		splits.train = [grps[g] for g in trPerm]		
		splits.test  = [grps[g] for g in tePerm]
		splits.val   = [grps[g] for g in valPerm if g not in tePerm]
		#Save the data		
		pickle.dump({'splits': splits}, open(fName, 'w'))



##
#Save the normal data
def save_normals(prms):
	if prms.isAligned:
		ids = get_folder_keys_aligned(prms)
	else:
		ids = get_folder_keys_all(prms)
	for i in ids:
		count = 0
		imFiles, labelFiles = folderid_to_im_label_files(prms,i)
		with open(prms.paths.label.nrml % i, 'w') as fid:
			for (imf,lbf) in zip(imFiles,labelFiles):
				if np.mod(count,1000)==1:
					print(count)
				lb = parse_label_file(lbf)
				_, imfStr = osp.split(imf)
				fid.write('%s \t %f \t %f \t %f\n' % (imfStr,lb.nrml[0],
											lb.nrml[1], lb.nrml[2]))
				count += 1


