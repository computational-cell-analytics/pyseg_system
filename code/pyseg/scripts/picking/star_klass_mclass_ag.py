"""

    Multiclass test for unsupervised and deterministic classification of membrane-bound particles

    Input:  - The STAR file with the particles to classify
            - Classification parameters

    Output: - A set of STAR files with the new classes
            - 2D rotational averaged around membrane normal exemplars and inter-particles averages per class

"""

__author__ = 'Antonio Martinez-Sanchez'


###### Global variables

CDF_TH = 0.95 # Threshold for accumulated correlation

################# Package import

import os
import sys
import time
import pyseg as ps
import numpy as np
from scipy.misc import imsave
from matplotlib import pyplot as plt

########################################################################################
# PARAMETERS
########################################################################################

ROOT_PATH = '/fs/pool/pool-lucic2/antonio/pick_test'

# Input STAR file to classify
in_star = ROOT_PATH + '/klass/mclass_data/test_realist/test_6.star'

# Output directory for the star files
out_dir = ROOT_PATH + '/klass/mclass_data/out_ag/test_realist/test_6'
out_stem = 'klass_ag'

# Particles pre-processing
pp_mask = ROOT_PATH + '/klass/mclass_data/mask_90_0_90_30_nomb.mrc' # '/masks/mask_cyl_160_81_128_20.mrc' #
pp_low_sg = 4 # voxels
pp_npr = 20 # Number of parallel processors if None then auto
ap_pref = None # -3.0 # -1 # 0 # -3 # -2 # -1 # 0 # -3 # None # -40 # -10 # -3 # -6

###### Advanced settings

# Particles pre-processing
pp_3d = True # False
pp_rln_norm = False
pp_2d_norm = True # True
pp_direct = True
pp_n_sset = None # 3000

# CC 2d radial matrix computation parameters
cc_metric = 'cc' # 'cc' or 'similarity'
cc_npr = 20 # None # 1 # None # if None then auto

## Clustering
cu_mode = 'vectors' # 'ncc_2dz' # 'moments' # 'ncc_2dz'
cu_n_comp = 21 # None

# Agglomerative Clustering
ag_n_clusters = 3 # 8
ag_linkage = 'ward' # 'average' # 'complete' #

########################################################################################
# MAIN ROUTINE
########################################################################################

########## Print initial message

print('Test for deterministic classification of a STAR file.')
print('\tAuthor: ' + __author__)
print('\tDate: ' + time.strftime("%c") + '\n')
print('Options:')
print('\tInput STAR file: ' + str(in_star))
print('\tOutput directory: ' + str(out_dir))
print('\tOutput stem for AG: ' + str(out_stem))
print('\tParticles pre-processing:')
print('\t\t-Mask: ' + str(pp_mask))
print('\t\t-Low pass Gaussian filter sigma: ' + str(pp_low_sg) + ' voxels')
if pp_rln_norm:
    print('\t\t-Normalize particles according relion convention.')
if pp_2d_norm:
    print('\t\t-Renormalize particles after the radial averaging.')
if pp_3d:
    print('\t\t-Radial compensation for 3D.')
if pp_npr is None:
    print('\t\t-Number of processes: Auto')
else:
    print('\t\t-Number of processes: ' + str(pp_npr))
if pp_direct:
    print('\t\t-Direct particles loading activated.')
if pp_n_sset:
    print('\t\t-Taking a random subset of: ' + str(pp_n_sset) + ' particles')
if cu_mode == 'ncc_2dz':
    print('\tCC Z-axis radially averages matrix parameters: ')
    print('\t\t-Metric: ' + str(cc_metric))
    if cc_npr is None:
        print('\t\t-Number of processes: Auto')
    else:
        print('\t\t-Number of processes: ' + str(cc_npr))
print('\tClustering: ')
print('\t\t-Mode: ' + str(cu_mode))
if cu_mode != 'ncc_2dz':
    print('\t\t-Number of components: ' + str(cu_n_comp))
print('\t\tAgglomerative clustering classificiation settings: ')
print('\t\t\t-Number of clusters to find: ' + str(ag_n_clusters))
print('\t\t\t-Linkage: ' + str(ag_linkage))
print('')

######### Process

print('Main Routine: ')

print('\tLoading STAR file...')
star = ps.sub.Star()
try:
    star.load(in_star)
    if pp_n_sset:
        print('\t\tCurrent STAR file has ' + str(star.get_nrows()) + ' particles')
        print('\t\tGetting a random subset of ' + str(pp_n_sset) + ' particles')
        star = star.gen_random_subset(pp_n_sset)
    star_class = ps.sub.ClassStar(star)
except ps.pexceptions.PySegInputError as e:
    print('ERROR: input STAR file could not be loaded because of "' + e.get_message() + '"')
    print('Terminated. (' + time.strftime("%c") + ')')
    sys.exit(-1)

print('\tLoading and pre-processing the particles...')
try:
    mask = ps.disperse_io.load_tomo(pp_mask)
    star_class.load_particles(mask, low_sg=pp_low_sg, avg_norm=pp_2d_norm, rln_norm=pp_rln_norm, rad_3D=pp_3d,
                              npr=pp_npr, debug_dir=None, ref_dir=None, direct_rec=pp_direct)
    star_class.save_particles(out_dir+'/all_particles', out_stem, masks=True, stack=True)
    imsave(out_dir+'/all_particles/global_mask.png', star_class.get_global_mask())
except ps.pexceptions.PySegInputError as e:
    print('ERROR: Particles could not be loaded because of "' + e.get_message() + '"')
    print('Terminated. (' + time.strftime("%c") + ')')
    sys.exit(-1)

if cu_mode == 'ncc_2dz':
    print('\tBuilding the NCC matrix...')
    try:
        star_class.build_ncc_z2d(metric=cc_metric, npr=cc_npr)
    except ps.pexceptions.PySegInputError as e:
        print('ERROR: The NCC matrix could not be created because of "' + e.get_message() + '"')
        print('Terminated. (' + time.strftime("%c") + ')')
        sys.exit(-1)
elif cu_mode == 'vectors':
    print('\tBuilding vectors...')
    try:
        star_class.build_vectors()
    except ps.pexceptions.PySegInputError as e:
        print('ERROR: The NCC matrix could not be created because of "' + e.get_message() + '"')
        print('Terminated. (' + time.strftime("%c") + ')')
        sys.exit(-1)
    print('\tPCA dimensionality reduction...')
    try:
        evs = star_class.vectors_dim_reduction(n_comp=cu_n_comp, method='pca')
        ids_evs_sorted = np.argsort(evs)[::-1]
    except ps.pexceptions.PySegInputError as e:
        print('ERROR: Classification failed because of "' + e.get_message() + '"')
        print('Terminated. (' + time.strftime("%c") + ')')
        sys.exit(-1)
    plt.figure()
    plt.bar(np.arange(1, len(evs) + 1) - 0.25, evs[ids_evs_sorted], width=0.5, linewidth=2)
    plt.xlim(0, len(evs) + 1)
    plt.xticks(list(range(1, len(evs) + 1)))
    plt.xlabel('#eigenvalue')
    plt.ylabel('fraction of total correlation')
    plt.tight_layout()
    plt.savefig(out_dir + '/' + out_stem + '_evs.png', dpi=300)
    cdf_evs, evs_sorted = np.zeros(shape=len(evs), dtype=np.float32), np.sort(evs)[::-1]
    cdf_evs[0] = evs_sorted[0]
    th_x = None
    for i in range(len(evs_sorted)):
        cdf_evs[i] = evs_sorted[:i + 1].sum()
        if (cdf_evs[i] >= CDF_TH) and (th_x is None):
            th_x = i + 1
    plt.figure()
    plt.bar(np.arange(1, len(evs) + 1) - 0.25, cdf_evs, width=0.5, linewidth=2)
    plt.xlim(0, len(evs) + 1)
    plt.ylim(0, 1)
    if th_x is not None:
        plt.plot((th_x + 0.5, th_x + 0.5), (0, 1), color='k', linewidth=2, linestyle='--')
    plt.xticks(list(range(1, len(evs) + 1)))
    plt.xlabel('#eigenvalue')
    plt.ylabel('Accumulated fraction of total correlation')
    plt.tight_layout()
    plt.savefig(out_dir + '/' + out_stem + '_cdf_evs.png', dpi=300)

print('\tPreparing the ground truth...')
k_set = list(set(star.get_column_data('_rlnClassNumber')))
gt_im, gt_bc = dict().fromkeys(k_set), dict().fromkeys(k_set)
gt_np, gt_nn = dict().fromkeys(k_set), dict().fromkeys(k_set)
gt_tp, gt_fp, gt_fn = dict().fromkeys(k_set), dict().fromkeys(k_set), dict().fromkeys(k_set)
gt_tpr, gt_fpr = dict().fromkeys(k_set), dict().fromkeys(k_set)
gt_pr, gt_f1 = dict().fromkeys(k_set), dict().fromkeys(k_set)
for i, k_id in enumerate(star.get_column_data('_rlnClassNumber')):
    try:
        gt_im[k_id].append(star.get_element(key='_rlnImageName', row=i))
    except AttributeError:
        gt_im[k_id] = [star.get_element(key='_rlnImageName', row=i),]
    try:
        gt_np[k_id] += 1
    except TypeError:
        gt_np[k_id] = 1
    gt_bc[k_id] = list()
    gt_nn[k_id] = 0
    gt_tp[k_id], gt_fp[k_id], gt_fn[k_id] = 0, 0, 0
    gt_tpr[k_id], gt_fpr[k_id] = 0, 0
    gt_pr[k_id], gt_f1[k_id] = 0, 0

print('\tAgglomerative clustering classification...')
try:
    star_class.agglomerative_clustering(mode_in=cu_mode, n_clusters=ag_n_clusters, linkage=ag_linkage, knn=None,
                                        verbose=True)
except ps.pexceptions.PySegInputError as e:
    print('ERROR: Classification failed because of "' + e.get_message() + '"')
    print('Terminated. (' + time.strftime("%c") + ')')
    sys.exit(-1)
star_class.update_relion_classes()
split_stars = star_class.get_split_stars()

print('\t\tEvaluating the classification:')
print('\t\t\t-Finding the most representative output classes: ')
ko_set = list(range(len(split_stars)))
ko_ids = dict().fromkeys(list(range(len(split_stars))))
for ko_id, split_star in enumerate(split_stars):
    for row in range(split_star.get_nrows()):
        img = split_star.get_element('_rlnImageName', row)
        for k_id in gt_im.keys():
            if img in gt_im[k_id]:
                try:
                    ko_ids[ko_id].append(k_id)
                except AttributeError:
                    ko_ids[ko_id] = [k_id,]
ko_mr = dict().fromkeys(list(ko_ids.keys()))
for ko_id, ids in zip(iter(ko_ids.keys()), iter(ko_ids.values())):
    ko_mr[ko_id] = np.argmax(np.bincount(np.asarray(ids)))
for k_id in gt_tp.keys():
    hold_np = 0
    for ko_id, k_id_max in zip(iter(ko_mr.keys()), iter(ko_mr.values())):
        if k_id_max == k_id:
            gt_bc[k_id].append(ko_id)
            hold_np += len(ko_ids[ko_id])
    print('\t\t\t\t+Class ' + str(k_id) + ': NP=' + str(gt_np[k_id]))
    print('\t\t\t\t\t*Classes associated ' + str(gt_bc[k_id]) + ': NPf=' + str(hold_np))
    for kk_id in gt_tp.keys():
        if kk_id != k_id:
            gt_nn[k_id] += gt_np[kk_id]
print('\t\t\t-Computing the metrics: ')
for k_id in gt_tp.keys():
    for ko_id in gt_bc[k_id]:
        hold = (np.asarray(ko_ids[ko_id]) == k_id).sum()
        gt_tp[k_id] += hold
        hold = (np.asarray(ko_ids[ko_id]) != k_id).sum()
        gt_fp[k_id] += hold
    for kk_id in gt_bc.keys():
        if kk_id != k_id:
            for ko_id in gt_bc[kk_id]:
                hold = (np.asarray(ko_ids[ko_id]) == k_id).sum()
                gt_fn[k_id] += hold
    gt_tpr[k_id] = gt_tp[k_id] / float(gt_np[k_id])
    gt_fpr[k_id] = gt_fp[k_id] / float(gt_nn[k_id])
    try:
        gt_pr[k_id] = gt_tp[k_id] / float(gt_tp[k_id] + gt_fp[k_id])
    except ZeroDivisionError:
        gt_pr[k_id] = 0
    try:
        gt_f1[k_id] = 2. * (gt_pr[k_id] * gt_tpr[k_id]) / (gt_pr[k_id] + gt_tpr[k_id])
    except ZeroDivisionError:
        gt_f1[k_id] = 0
    print('\t\t\t\t+Class ' + str(k_id) + ': ')
    print('\t\t\t\t\t->TP=' + str(gt_tp[k_id]) + ', FP=' + str(gt_fp[k_id]) + ', FN=' + str(gt_fn[k_id]))
    print('\t\t\t\t\t->TPR=' + str(gt_tpr[k_id]) + ', FPR=' + str(gt_fpr[k_id]))
    print('\t\t\t\t\t->P=' + str(gt_pr[k_id]) + ', F1=' + str(gt_f1[k_id]))
print('\t\t\t-Computing global metrics: ')
print('\t\t\t-Global metrics: ')
gt_tpr, gt_pr = np.asarray(list(gt_tpr.values()), dtype=np.float32), np.asarray(list(gt_pr.values()), dtype=np.float32)
precision = gt_pr.mean()
recall = gt_tpr.mean()
print('\t\t\t\t+Precision=' + str(precision))
print('\t\t\t\t+Recall=' + str(recall))
print('\t\t\t\t+F1-score=' + str(2.*(precision*recall)/(precision+recall)))

print('\t\tStoring the results...')
try:
    star_class.save_star(out_dir, out_stem, parse_rln=True, mode='gather')
    star_class.save_star(out_dir, out_stem, parse_rln=True, mode='split')
    star_class.save_star(out_dir, out_stem, mode='particle')
    star_class.save_class(out_dir, out_stem, purge_k=0, mode='exemplars')
    star_class.save_class(out_dir, out_stem, purge_k=0, mode='averages')
except ps.pexceptions.PySegInputError as e:
    print('ERROR: Result could not be stored because of "' + e.get_message() + '"')
    print('Terminated. (' + time.strftime("%c") + ')')
    sys.exit(-1)

print('Terminated. (' + time.strftime("%c") + ')')