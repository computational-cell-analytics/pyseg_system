"""

    Performs Univariate 2nd order analysis to a SetListTomograms object by tomograms

    Input:  - A STAR file with a set of ListTomoParticles pickles (SetListTomograms object input)
            - Analysis settings

    Output: - Plots by tomograms:
                + Number of particles by list
                + Particles densities by list
                + Plots by list:
                    * Univariate 2nd order analysis against random simulation
            - Global plots:
                + Global univariate 2nd order analysis against random simulation by list

"""

################# Package import

import os
import pickle
import numpy as np
import scipy as sp
import sys
import time
from pyorg import pexceptions, sub, disperse_io, surf
from pyorg.globals import unpickle_obj, clean_dir
from pyorg.surf.model import ModelCSRV, gen_tlist
from pyorg.surf.utils import list_tomoparticles_pvalues
from matplotlib import pyplot as plt, rcParams
try:
    import pickle as pickle
except ImportError:
    import pickle

###### Global variables

__author__ = 'Antonio Martinez-Sanchez'

BAR_WIDTH = .35

rcParams['axes.labelsize'] = 14
rcParams['xtick.labelsize'] = 14
rcParams['ytick.labelsize'] = 14

########################################################################################
# PARAMETERS
########################################################################################

ROOT_PATH = '/fs/pool/pool-lucic2/antonio/workspace/psd_an/ex/syn2'

# Input STAR file
in_star = ROOT_PATH + '/org/ncol/ltomos/ltomos_ncol/all_ncol_ltomos_surfs.star' # '/org/col/ltomos/ltomos_preb_tether_pstb_xd5nm_amin10/all_preb_tether_pstb_xd5nm_amin10_ltomos_surfs.star' # '/org/pst/ltomos/ltomos_all_pst_pre_ss15px_v6/all_pst_pre_ltomos_surf.star'
in_wspace = ROOT_PATH + '/org/ncol/uni_2nd//all_ncol_ss7.31px_sim200_wspace.pkl' # (Insert a path to recover a pickled workspace instead of doing a new computation)

# Output directory
out_dir = ROOT_PATH + '/org/ncol/uni_2nd/'
out_stem = 'all_ncol_ss7.31px_sim200_2' # 'all_preb_tether_pstb_xd5nm_amin10_sim10'

# Analysis variables
ana_res = 0.684 # nm/voxel
ana_rg = np.arange(5, 150, 10) # in nm
ana_shell_thick = None # 15 # 5
ana_rdf = False
ana_fmm = True

# P-value computation settings
# Simulation model (currently only CSRV)
p_nsims = 200 # 5
p_per = 5 # %

# Multiprocessing options
mp_npr = 10 # None means Auto

##### Advanced settings

ana_border = True
ana_conv_iter = None # 100
ana_max_iter = None # 100000

# Particle surface
p_vtp = None # ROOT_PATH + '/in/yeast_80S/yeast_80S_21A_mirr_centered.vtp'

# Figure saving options
fig_fmt = '.png' # if None they are displayed instead

# Plotting options
pt_sim_v = True
pt_cmap = plt.get_cmap('gist_rainbow')

########################################################################################
# MAIN ROUTINE
########################################################################################

###### Additional functionality

# Computes IC from a matrix of measurements (n_arrays, array_samples)
def compute_ic(per, sims):
    if len(sims.shape) == 1:
        return sims, sims, sims
    ic_low = np.percentile(sims, per, axis=0, interpolation='linear')
    ic_med = np.percentile(sims, 50, axis=0, interpolation='linear')
    ic_high = np.percentile(sims, 100 - per, axis=0, interpolation='linear')
    return ic_low, ic_med, ic_high

# Computes pvalue from a matrix of simulations (n_arrays, array_samples)
def compute_pvals(exp_med, sims):
    n_sims = float(sims.shape[0])
    p_vals = np.zeros(shape=exp_med.shape, dtype=np.float32)
    for i, exp in enumerate(exp_med):
        sim_slice = sims[:, i]
        p_vals[i] = float((exp >= sim_slice).sum()) / n_sims
    return p_vals

# Units conversion
ana_rg_v = ana_rg / ana_res
ana_shell_thick_v = None
if ana_shell_thick is not None:
    ana_shell_thick_v = float(ana_shell_thick) / ana_res

########## Print initial message

print('Univariate second order analysis for a ListTomoParticles by tomograms.')
print('\tAuthor: ' + __author__)
print('\tDate: ' + time.strftime("%c") + '\n')
print('Options:')
print('\tOutput directory: ' + str(out_dir))
print('\tOuput stem: ' + str(out_stem))
print('\tInput STAR file: ' + str(in_star))
if in_wspace is not None:
    print('\tLoad workspace from: ' + in_wspace)
print('\tOrganization analysis settings: ')
print('\t\t-Range of radius: ' + str(ana_rg) + ' nm')
print('\t\t-Range of radius: ' + str(ana_rg_v) + ' voxels')
if ana_shell_thick is None:
    print('\t\t-Spherical neighborhood')
else:
    print('\t\t-Shell neighborhood with thickness: ' + str(ana_shell_thick) + ' nm')
    print('\t\t-Shell neighborhood with thickness: ' + str(ana_shell_thick_v) + ' voxels')
    if ana_rdf:
        print('\t\t-RDF activated.')
if in_wspace is None:
    if (ana_conv_iter is not None) and (ana_max_iter is not None):
        print('\t\t-Convergence number of samples for stochastic volume estimations: ' + str(ana_conv_iter))
        print('\t\t-Maximum number of samples for stochastic volume estimations: ' + str(ana_max_iter))
    else:
        if ana_fmm:
            print('\t\t-FMM for distance metric computation.')
        else:
            print('\t\t-DT for distance transform computation.')
    if mp_npr is None:
        print('\t\t-Number of processors: Auto')
    else:
        print('\t\t-Number of processors: ' + str(mp_npr))
print('\tP-Value computation setting:')
print('\t\t-Percentile: ' + str(p_per) + ' %')
print('\t\t-Number of instances for simulations: ' + str(p_nsims))
print('\t\t-Particle surface: ' + str(p_vtp))
if fig_fmt is not None:
    print('\tStoring figures:')
    print('\t\t-Format: ' + str(fig_fmt))
else:
    print('\tPlotting settings: ')
print('\t\t-Colormap: ' + str(pt_cmap))
if pt_sim_v:
    print('\t\t-Verbose simulation activated!')
print('')

######### Process

print('Main Routine: ')
mats_lists, gl_lists = None, None

out_stem_dir = out_dir + '/' + out_stem
print('\tCleaning the output dir: ' + out_stem)
if os.path.exists(out_stem_dir):
    clean_dir(out_stem_dir)
else:
    os.makedirs(out_stem_dir)
out_tomos_dir = out_stem_dir + '/tomos'
os.makedirs(out_tomos_dir)

if in_wspace is None:

    print('\tLoading input data...')
    star = sub.Star()
    try:
        star.load(in_star)
    except pexceptions.PySegInputError as e:
        print('ERROR: input STAR file could not be loaded because of "' + e.get_message() + '"')
        print('Terminated. (' + time.strftime("%c") + ')')
        sys.exit(-1)
    set_lists = surf.SetListTomoParticles()
    part_vtps = dict()
    for row in range(star.get_nrows()):
        ltomos_pkl = star.get_element('_psPickleFile', row)
        ltomos = unpickle_obj(ltomos_pkl)
        set_lists.add_list_tomos(ltomos, ltomos_pkl)
        try:
            if p_vtp is not None:
                part_vtp = disperse_io.load_poly(p_vtp)
            else:
                part_vtp = disperse_io.load_poly(star.get_element('_suSurfaceVtpSim', row))
        except pexceptions.PySegInputError as e:
            print('ERROR: reference particle surface file could not be loaded because of "' + e.get_message() + '"')
            print('Terminated. (' + time.strftime("%c") + ')')
            sys.exit(-1)
        lkey = os.path.split(ltomos_pkl)[1]
        short_key_idx = lkey.index('_')
        short_key = lkey[:short_key_idx]
        part_vtps[short_key] = part_vtp

    print('\tBuilding the dictionaries...')
    lists_count, tomos_count = 0, 0
    lists_dic = dict()
    lists_hash, tomos_hash = dict(), dict()
    tomos_np, tomos_den, tomos_exp, tomos_sim = dict(), dict(), dict(), dict()
    lists_np, lists_den, lists_exp, lists_sim, lists_color = dict(), dict(), dict(), dict(), dict()
    tmp_sim_folder = out_dir + '/tmp_gen_list_' + out_stem
    set_lists_dic = set_lists.get_lists()
    for lkey, llist in zip(iter(set_lists_dic.keys()), iter(set_lists_dic.values())):
        fkey = os.path.split(lkey)[1]
        print('\t\t-Processing list: ' + fkey)
        short_key_idx = fkey.index('_')
        short_key = fkey[:short_key_idx]
        print('\t\t\t+Short key found: ' + short_key)
        try:
            lists_dic[short_key]
        except KeyError:
            lists_dic[short_key] = llist
            lists_hash[lists_count] = short_key
            lists_np[short_key], lists_den[short_key], lists_exp[short_key], lists_sim[short_key] = None, None, \
                                                                                                    list(), list()
            lists_count += 1
    for lkey, llist in zip(iter(set_lists_dic.keys()), iter(set_lists_dic.values())):
        llist_tomos_dic = llist.get_tomos()
        for tkey, ltomo in zip(iter(llist_tomos_dic.keys()), iter(llist_tomos_dic.values())):
            try:
                tomos_np[tkey]
            except KeyError:
                tomos_hash[tkey] = tomos_count
                tomos_np[tkey], tomos_den[tkey] = list(), list()
                tomos_exp[tkey], tomos_sim[tkey] = dict.fromkeys(list(lists_dic.keys())), dict.fromkeys(list(lists_dic.keys()))
                tomos_count += 1
    for lkey in lists_np.keys():
        lists_np[lkey] = np.zeros(shape=tomos_count, dtype=np.float32)
    for lkey in lists_den.keys():
        lists_den[lkey] = np.zeros(shape=tomos_count, dtype=np.float32)
    for tkey in tomos_exp.keys():
        for lkey in lists_dic.keys():
            tomos_exp[tkey][lkey], tomos_sim[tkey][lkey] = list(), list()

    print('\tLIST COMPUTING LOOP:')
    sim_obj_set = surf.SetListSimulations()
    for lkey in lists_hash.values():

        llist = lists_dic[lkey]
        sim_obj_list = surf.ListSimulations()
        print('\t\t-Processing list: ' + lkey)
        part_vtp = part_vtps[lkey]

        print('\t\t\t+Tomograms computing loop:')
        for tkey in tomos_hash.keys():

            print('\t\t\t\t*Processing tomogram: ' + tkey) # os.path.split(tkey)[1]
            try:
                ltomo = llist.get_tomo_by_key(tkey)
            except KeyError:
                print('\t\t\t\t\t-Tomogram with key ' + tkey + ' is not in the list ' + lkey + ' , continuing...')
                continue
            if ltomo.get_num_particles() <= 0:
                print('\t\t\t\t\t-WARNING: no particles to process, continuing...')
                continue
            if not ltomo.ensure_embedding():
                print('WARNING: Not all particles are embedded for list ' + str(lkey) + ' and tomogram ' + str(tkey))
                continue

            print('\t\t\t\t\t-Computing the number of particles...')
            hold_np = ltomo.get_num_particles()
            tomos_np[tkey].append(hold_np)
            lists_np[lkey][tomos_hash[tkey]] = hold_np

            print('\t\t\t\t\t-Computing density by area...')
            hold_den = ltomo.compute_global_density()
            tomos_den[tkey].append(hold_den)
            lists_den[lkey][tomos_hash[tkey]] = hold_den

            print('\t\t\t\t\t-Computing univariate second order metrics...')
            hold_arr = ltomo.compute_uni_2nd_order(ana_rg_v, thick=ana_shell_thick_v, border=ana_border,
                                                   conv_iter=ana_conv_iter, max_iter=ana_max_iter, fmm=ana_fmm,
                                                   rdf=ana_rdf, npr=mp_npr)
            if hold_arr is not None:
                tomos_exp[tkey][lkey].append(hold_arr)
                for i in range(ltomo.get_num_particles()):
                    lists_exp[lkey].append(hold_arr)

            print('\t\t\t\t\t-Simulating univariate second order metrics...')
            model_csrv = ModelCSRV()
            hold_arr = ltomo.simulate_uni_2nd_order(p_nsims, model_csrv, part_vtp, 'center', ana_rg_v, border=ana_border,
                                                    thick=ana_shell_thick_v, fmm=ana_fmm,
                                                    conv_iter=ana_conv_iter, max_iter=ana_max_iter, rdf=ana_rdf,
                                                    npr=mp_npr)
            if hold_arr is not None:
                sim_obj = surf.Simulation(ana_rg, ana_shell_thick, np.array(hold_arr))
                sim_obj_list.insert_simulation(tkey, sim_obj)
                for arr in hold_arr:
                    tomos_sim[tkey][lkey].append(arr)
                    for i in range(ltomo.get_num_particles()):
                        lists_sim[lkey].append(arr)

        sim_obj_set.insert_list_simulations(lkey, sim_obj_list)

    out_wspace = out_dir + '/' + out_stem + '_wspace.pkl'
    print('\tPickling computation workspace in: ' + out_wspace)
    wspace = (lists_count, tomos_count,
              lists_hash, tomos_hash,
              tomos_np, tomos_den, tomos_exp, tomos_sim,
              lists_np, lists_den, lists_exp, lists_sim, lists_color)
    with open(out_wspace, "wb") as fl:
        pickle.dump(wspace, fl)
        fl.close()

    out_lsims = out_dir + '/' + out_stem + '_lsims.pkl'
    print('\tPickling the list of simulations results: ' + out_lsims)
    with open(out_lsims, "wb") as fl:
        print(type(sim_obj_set))
        pickle.dump(sim_obj_set, fl)
        fl.close()

else:
    print('\tLoading the workspace: ' + in_wspace)
    with open(in_wspace, 'r') as pkl:
        wspace = pickle.load(pkl)
    lists_count, tomos_count = wspace[0], wspace[1]
    lists_hash, tomos_hash = wspace[2], wspace[3]
    tomos_np, tomos_den, tomos_exp, tomos_sim = wspace[4], wspace[5], wspace[6], wspace[7]
    lists_np, lists_den, lists_exp, lists_sim, lists_color = wspace[8], wspace[9], wspace[10], wspace[11], wspace[12]

print('\tPrinting lists hash: ')
for id, lkey in zip(iter(lists_hash.keys()), iter(lists_hash.values())):
    print('\t\t-[' + str(id) + '] -> [' + lkey + ']')
print('\tPrinting tomograms hash: ')
for tkey, val in zip(iter(tomos_hash.keys()), iter(tomos_hash.values())):
    print('\t\t-[' + tkey + '] -> [' + str(val) + ']')

# Getting the lists colormap
n_lists = len(list(lists_hash.keys()))
for i, lkey in zip(iter(lists_hash.keys()), iter(lists_hash.values())):
    lists_color[lkey] = pt_cmap(1.*i/n_lists)

print('\tTOMOGRAMS PLOTTING LOOP: ')

print('\t\t-Plotting the number of particles...')
for tkey, ltomo in zip(iter(tomos_np.keys()), iter(tomos_np.values())):
    tkey_short = os.path.splitext(os.path.split(tkey)[1])[0]
    plt.figure()
    plt.title('Num. particles for ' + tkey_short)
    plt.ylabel('Num. particles')
    plt.xlabel('Classes')
    for i, nparts in enumerate(ltomo):
        lkey = lists_hash[i]
        plt.bar(int(lkey), nparts, width=0.75, color=lists_color[lkey], label=lkey)
    plt.xticks(BAR_WIDTH + np.arange(n_lists), np.arange(n_lists))
    plt.legend(loc=1)
    plt.tight_layout()
    if fig_fmt is None:
        plt.show(block=True)
    else:
        hold_dir = out_tomos_dir + '/' + tkey.replace('/', '_')
        if not os.path.exists(hold_dir):
            os.makedirs(hold_dir)
        plt.savefig(hold_dir + '/np.png')
    plt.close()

print('\t\t-Plotting densities...')
for tkey, ltomo in zip(iter(tomos_den.keys()), iter(tomos_den.values())):
    tkey_short = os.path.splitext(os.path.split(tkey)[1])[0]
    plt.figure()
    plt.title('Density for ' + tkey_short)
    plt.ylabel('Density (np/vol)')
    plt.xlabel('Classes')
    for i, den in enumerate(ltomo):
        lkey = lists_hash[i]
        plt.bar(int(lkey), den, width=0.75, color=lists_color[lkey], label=lkey)
    plt.xticks(BAR_WIDTH + np.arange(n_lists), np.arange(n_lists))
    plt.legend(loc=4)
    plt.tight_layout()
    if fig_fmt is None:
        plt.show(block=True)
    else:
        hold_dir = out_tomos_dir + '/' + tkey.replace('/', '_')
        if not os.path.exists(hold_dir):
            os.makedirs(hold_dir)
        plt.savefig(hold_dir + '/den.png')
    plt.close()

print('\t\t-Plotting 2nd order metric...')
for tkey, ltomo in zip(iter(tomos_exp.keys()), iter(tomos_exp.values())):
    p_values = dict()
    tkey_short = os.path.splitext(os.path.split(tkey)[1])[0]
    for lkey, arr in zip(iter(tomos_exp[tkey].keys()), iter(tomos_exp[tkey].values())):
        try:
            arr = arr[0]
            hold_sim = tomos_sim[tkey][lkey]
            if len(hold_sim) > 0:
                ic_low, ic_med, ic_high = compute_ic(p_per, np.asarray(hold_sim))
                p_values[lkey] = compute_pvals(arr, np.asarray(hold_sim))
        except IndexError:
            print('\t\t\t+WARNING: no data for tomogram ' + tkey + ' and list ' + lkey)
            continue
        plt.figure()
        plt.title('Univariate 2nd order for ' + tkey_short + ' and ' + lkey)
        if ana_shell_thick is None:
            plt.ylabel('Ripley\'s L')
        else:
            if ana_rdf:
                plt.ylabel('Radial Distribution Function')
            else:
                plt.ylabel('Ripley\'s O')
        plt.xlabel('Distance [nm]')
        plt.plot(ana_rg, arr, color=lists_color[lkey], label=lkey)

        plt.legend(loc=4)
        try:
            # plt.plot(ana_rg, ic_low, 'k--')
            plt.plot(ana_rg, ic_med, 'k', label='SIMULATED')
            # plt.plot(ana_rg, ic_high, 'k--')
        except NameError:
            pass
        plt.fill_between(ana_rg, ic_low, ic_high, alpha=0.5, color='gray', edgecolor='w')
        # plt.ylim(-9, 8)
        plt.grid(True)
        plt.tight_layout()
        if fig_fmt is None:
            plt.show(block=True)
        else:
            hold_dir = out_tomos_dir + '/' + tkey.replace('/', '_')
            if not os.path.exists(hold_dir):
                os.makedirs(hold_dir)
            plt.savefig(hold_dir + '/uni_' + lkey + '.png')
        plt.close()

    plt.figure()
    plt.title('Clustering p-value for ' + tkey_short)
    plt.ylabel('p-value')
    plt.xlabel('Distance [nm]')
    try:
        for lkey, vals in zip(iter(p_values.keys()), iter(p_values.values())):
            plt.plot(ana_rg, vals, color=lists_color[lkey], linestyle='-', label=lkey)
    except IndexError:
        print('\t\t\t+WARNING: no p-values for list: ' + lkey)
    plt.legend(loc=4)
    plt.tight_layout()
    if fig_fmt is None:
        plt.show(block=True)
    else:
        hold_dir = out_tomos_dir + '/' + tkey.replace('/', '_')
        if not os.path.exists(hold_dir):
            os.makedirs(hold_dir)
        plt.savefig(hold_dir + '/pvals.png')
    plt.close()

print('\t\t-Plotting 2nd order metric (all simulations)...')
plt.figure()
plt.title('Univariate 2nd order for all simulations')
hold_sim_vals = dict()
for tkey, ltomo in zip(iter(tomos_exp.keys()), iter(tomos_exp.values())):
    p_values = dict()
    tkey_short = os.path.splitext(os.path.split(tkey)[1])[0]
    for lkey, arr in zip(iter(tomos_exp[tkey].keys()), iter(tomos_exp[tkey].values())):
        try:
            hold_sims = np.asarray(tomos_sim[tkey][lkey], dtype=np.float32)
            for hold_sim in hold_sims:
                plt.plot(ana_rg, hold_sim, color=lists_color[lkey], alpha=.3)
                try:
                    hold_sim_vals[lkey].append(hold_sim)
                except KeyError:
                    hold_sim_vals[lkey] = list()
                    hold_sim_vals[lkey].append(hold_sim)
        except IndexError:
            print('\t\t\t+WARNING: no data for tomogram ' + tkey + ' and list ' + lkey)
            continue
        if ana_shell_thick is None:
            plt.ylabel('Ripley\'s L')
        else:
            if ana_rdf:
                plt.ylabel('Radial Distribution Function')
            else:
                plt.ylabel('Ripley\'s O')
for lkey, vals in zip(iter(hold_sim_vals.keys()), iter(hold_sim_vals.values())):
    vals_mat = np.asarray(vals, dtype=np.float32)
    lbl = lkey
    plt.plot(ana_rg, np.median(vals_mat, axis=0), color=lists_color[lkey], label=lbl, linewidth=3.0, linestyle='--')
plt.xlabel('Distance [nm]')
plt.grid(True)
plt.legend(loc=4)
plt.tight_layout()
if fig_fmt is None:
    plt.show(block=True)
else:
    plt.savefig(out_tomos_dir + '/uni_sims.png')
plt.close()

print('\tLISTS PLOTTING LOOP: ')

out_lists_dir = out_stem_dir + '/lists'
os.makedirs(out_lists_dir)

print('\t\t-Plotting the number of particles...')
n_tomos = len(list(tomos_hash.keys()))
for lkey, tlist in zip(iter(lists_np.keys()), iter(lists_np.values())):
    plt.figure()
    plt.title('Num. particles for ' + lkey)
    plt.ylabel('Num. particles')
    plt.xlabel('Tomograms')
    for i, nparts in enumerate(tlist):
        plt.bar(i, nparts, width=0.75)
    plt.xticks(BAR_WIDTH + np.arange(n_tomos), np.arange(n_tomos))
    plt.tight_layout()
    if fig_fmt is None:
        plt.show(block=True)
    else:
        hold_dir = out_lists_dir + '/' + lkey
        if not os.path.exists(hold_dir):
            os.makedirs(hold_dir)
        plt.savefig(hold_dir + '/np_lists.png')
    plt.close()

print('\t\t-Plotting densities...')
plt.figure()
# plt.title('Densities for ' + lkey)
plt.ylabel('Density [#/$\mu m^3$]')
# plt.xlabel('Tomograms')
count, ticks = 1, dict()
ana_res_3_i = 1. / float((1e-3 * ana_res)**3)
plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
for lkey, tlist in zip(iter(lists_den.keys()), iter(lists_den.values())):
    arr = tlist[np.where(tlist > 0)[0]]
    den_low, den_med, den_high = np.percentile(arr, p_per), np.percentile(arr, 50), np.percentile(arr, 100 - p_per)
    den_low, den_med, den_high = den_low * ana_res_3_i, den_med * ana_res_3_i, den_high * ana_res_3_i
    plt.bar(count, den_med, width=.40, color=lists_color[lkey], edgecolor='k', linewidth=2)
    plt.errorbar(count, den_med, yerr=np.asarray([[den_med - den_low, den_high - den_med], ]).reshape(2, 1),
                 ecolor='k', elinewidth=4, capthick=4, capsize=8)
    ticks[lkey] = count
    count += 1
plt.xticks(list(ticks.values()), list(ticks.keys()))
plt.tight_layout()
if fig_fmt is None:
    plt.show(block=True)
else:
    plt.savefig(out_lists_dir + '/den_lists.png')
plt.close()

print('\t\t-Plotting 2nd order metric...')
sims, do_pval = list(), True
exps_low, exps_med, exps_high = list(), list(), list()
for lkey, tlist in zip(iter(lists_exp.keys()), iter(lists_exp.values())):
    plt.figure()
    # plt.title('Univariate 2nd order for ' + lkey)
    if ana_shell_thick is None:
        plt.ylabel('Ripley\'s L')
    else:
        if ana_rdf:
            plt.ylabel('Radial Distribution Function')
        else:
            plt.ylabel('Ripley\'s O')
    plt.xlabel('Distance [nm]')
    # Getting experimental IC
    exp_low, exp_med, exp_high = compute_ic(p_per, np.asarray(tlist))
    # plt.plot(ana_rg, exp_low, color=lists_color[lkey], linestyle='--', label=lkey)
    plt.plot(ana_rg, exp_med, color=lists_color[lkey], linestyle='-', linewidth=2.0, label=lkey)
    # plt.plot(ana_rg, exp_high, color=lists_color[lkey], linestyle='--', label=lkey)
    plt.fill_between(ana_rg, exp_low, exp_high, alpha=0.3, color=lists_color[lkey], edgecolor='w')
    sims += lists_sim[lkey]
    exps_low.append(exp_low)
    exps_med.append(exp_med)
    exps_high.append(exp_high)
    # Getting simulations IC
    hold_sim = np.asarray(lists_sim[lkey])
    hold_sim[np.isnan(hold_sim) | np.isinf(hold_sim)] = 0
    ic_low, ic_med, ic_high = compute_ic(p_per, np.asarray(hold_sim))
    try:
        # plt.plot(ana_rg, ic_low, 'k--')
        plt.plot(ana_rg, ic_med, 'k', linewidth=2.0)
        # plt.plot(ana_rg, ic_high, 'k--')
    except (NameError, ValueError):
        do_pval = False
    plt.fill_between(ana_rg, ic_low, ic_high, alpha=0.5, color='gray', edgecolor='w')
    plt.tight_layout()
    plt.xlim((0, ana_rg[-1]))
    # plt.ylim((-9, 8))
    # extraticks = [5,]
    # plt.xticks(list(plt.xticks()[0]) + extraticks)
    if fig_fmt is None:
        plt.show(block=True)
    else:
        # plt.show(block=True)
        plt.savefig(out_lists_dir + '/uni_lists_' + str(lkey) + '.png', dpi=600)
    plt.close()
sims = np.asarray(hold_sim)
out_fspace = out_dir + '/' + out_stem + '_fspace.pkl'
print('\tPickling figue in: ' + out_fspace)
fspace = (ana_rg,
          exps_low, exps_med, exps_high,
          ic_low, ic_med, ic_high)
with open(out_fspace, "wb") as fl:
    pickle.dump(fspace, fl)
    fl.close()

if do_pval:
    print('\t\t-Plotting clustering p-value...')
    plt.figure()
    plt.title('Clustering significance')
    plt.ylabel('p-value')
    plt.xlabel('Distance [nm]')
    p_per_lim = 1. - .01 * p_per
    plt.plot((ana_rg[0], ana_rg[-1]), (p_per_lim, p_per_lim), color='k', linestyle='--')
    for lkey, tlist in zip(iter(lists_exp.keys()), iter(lists_exp.values())):
        exp_med = compute_ic(p_per, np.asarray(tlist))[1]
        p_values = compute_pvals(exp_med, sims)
        plt.plot(ana_rg, p_values, color=lists_color[lkey], linestyle='-', label=lkey)
    plt.legend(loc=4)
    plt.tight_layout()
    if fig_fmt is None:
        plt.show(block=True)
    else:
        plt.savefig(out_lists_dir + '/pvals_lists.png')
    plt.close()

print('Successfully terminated. (' + time.strftime("%c") + ')')
