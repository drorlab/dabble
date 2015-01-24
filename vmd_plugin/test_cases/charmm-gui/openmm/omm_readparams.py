"""
Generated by CHARMM-GUI (http://www.charmm-gui.org) v1.6

omm_readparams.py

This module is for reading parameters in OpenMM.

Correspondance: j712l362@ku.edu or wonpil@ku.edu
Last update: November 11, 2014
"""

import os

from simtk.unit import *
from simtk.openmm import *
from simtk.openmm.app import *

def read_psf(filename):
    psf = CharmmPsfFile(filename)
    return psf

def read_crd(filename):
    crd = CharmmCrdFile(filename)
    return crd

def read_params(path):
    parFiles = ()
    for parFile in os.listdir(path):
        fileext = parFile.split('.')[-1]
        if fileext == 'prm' or fileext == 'rtf' or fileext == 'str':
            parFiles += ( path+'/'+parFile, )

    params = CharmmParameterSet( *parFiles )
    return params

def read_box(psf, filename):
    for line in open(filename, 'r'):
        segments = line.split('=')
        if segments[0].strip() == "BOXLX": boxlx = float(segments[1])
        if segments[0].strip() == "BOXLY": boxly = float(segments[1])
        if segments[0].strip() == "BOXLZ": boxlz = float(segments[1])
    psf.setBox(boxlx*angstroms, boxly*angstroms, boxlz*angstroms)
    return psf

def gen_box(psf, crd):
    coords = crd.positions

    min_crds = [coords[0][0], coords[0][1], coords[0][2]]
    max_crds = [coords[0][0], coords[0][1], coords[0][2]]

    for coord in coords:
        min_crds[0] = min(min_crds[0], coord[0])
        min_crds[1] = min(min_crds[1], coord[1])
        min_crds[2] = min(min_crds[2], coord[2])
        max_crds[0] = max(max_crds[0], coord[0])
        max_crds[1] = max(max_crds[1], coord[1])
        max_crds[2] = max(max_crds[2], coord[2])

    boxlx = max_crds[0]-min_crds[0]
    boxly = max_crds[1]-min_crds[1]
    boxlz = max_crds[2]-min_crds[2]

    psf.setBox(boxlx, boxly, boxlz)
    return psf
