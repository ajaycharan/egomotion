import street_exp_v2 as sev2
import street_process_data as spd
import street_config as cfg
import pickle
import python

REAL_PATH = cfg.REAL_PATH

#First lets make a proper test set :) 
def make_test_set(dPrms, numTest=100000):
	listName = dPrms['paths'].exp.other.grpList % 'test'
	data     = pickle.load(open(listName, 'r'))	
	grpDat   = []
	grpCount = []
	numGrp   = 0
	for i,g in enumerate(data['grpFiles']):
		grpDat.append(pickle.load(open(g, 'r'))['groups'])
		grpCount.append(len(grpDat[i]))
		print ('Groups in %s: %d' % (g, grpCount[i]))
		numGrp += grpCount[i]
	print ('Total number of groups: %d' % numGrp)
	grpSampleProb = [float(i)/float(numGrp) for i in grpCount]
	randSeed  = 7
	randState = np.random.RandomState(randSeed) 
	elms      = []
	for t in range(numTest):
		breakFlag = False
		while not breakFlag:
			rand   =  randState.multinomial(1, grpSampleProb)
			grpIdx =  np.where(rand==1)[0][0]
			ng     =  randState.randint(low=0, high=grpCount[grpIdx])
			grp    =  grpDat[ng]
			l1     =  randState.permutation(grp.num)[0]
			l2     =  randState.permutation(grp.num)[0]
			if l1==l2:
				rd = randState.rand()
				#Sample the same image rarely
				if rd < 0.85:
					continue
			elm = [folderId, grp.cropImNames[l1], grp.cropImNames[l2]]
			lb  = slu.get_pose_delta(dPrms		
		
				
		
	
