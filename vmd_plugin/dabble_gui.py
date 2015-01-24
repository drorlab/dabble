# dabble.py
# By Robin M. Betz
# 21 January 2015
# Loosely based off saute3.py from DESRES


USAGE = '''usage: %prog solute.maeff output.maeff

Embed solute.maeff in a tiled membrane and prepare solvent ions.'''
VERSION = '%prog '

WELCOME_SCREEN = '''
 ===============================================
|               _      _      _                 |
|             >(.)__ <(.)__ =(.)__              |
|              (___/  (___/  (___/              | 
|                                               |
|                    DABBLE                     |
|                 _      _      _               |
|              __(.)< __(.)> __(.)=             |
|              \___)  \___)  \___)              |
|                                               |
|         VMD Plug-in by Robin Betz, 2015       |
|               Stanford University             |
 ===============================================
'''

import argparse
import os, tempfile
import VMD, molecule
from sys import stdout
from Tkinter import *

############################################################
#                       PLUGIN STUFF                       #
############################################################


class dabble:
    __MEMBRANE_SYSTEM_PATH = '%s/equilibrated_tall_POPC_TIP3P_system.mae' %os.path.dirname(os.path.abspath(__file__))

    def start_dabble() :
        return dabble().root

    VMD.registerExtensionMenu("Dabble", start_dabble)

    def __init__(self):
        # Initialize window to readable sizes
        self.root = Tk()
        self.root.title("Dabble")
        self.root.option_add("*Font", "Arial 14")

        # Output file text box
        Label(self.root, text="Desired name for output mae file").grid(row=0)
        self.out_entry = Entry(self.root)
        self.out_entry.grid(row=0, column=1)

        # Membrane MAE file text box
        Label(self.root, text="Path to membrane mae file").grid(row=1)
        self.mem_entry = Entry(self.root)
        self.mem_entry.grid(row=1, column=1)

        # Membrane selection
        Label(self.root, text="Solute atom selection (default 'ctnumber 1')").grid(row=2)
        self.mes_entry = Entry(self.root)
        self.mes_entry.grid(row=2, column=1)

        button = Button(self.root, command=self.main_wrapper, text="GO!!!!!")
        button.grid(row=3)

    def main_wrapper(self):
        # Gather up the arguments
        i='0' # id of molecule to get
        o=self.out_entry.get()
        M=self.mem_entry.get()
        B=self.mes_entry.get()

        # Validate the input

        # Assemble the command string
        args = [i, o]
        if M : args.extend(["-M", M])
        if B : args.extend(["-B", B])
        
        print args
        self.dabble_main(args)
    

############################################################
#                           MAIN                           #
############################################################
 
    def make_logger(self, quiet=False):
        def logger(s):
            if not quiet:
                stdout.write(s)
                stdout.flush()
        return logger
   
    
    def dabble_main(self, args):
        parser = argparse.ArgumentParser(usage=USAGE)#prog='dabble', usage=USAGE, version=VERSION)
# Positional arguments TODO: Better text
        parser.add_argument('solute_filename')
        parser.add_argument('output_filename')
# Flag arguments 
        parser.add_argument('-B', '--solute-selection', dest='solute_bb_sel',
                          default='ctnumber 1', type='string',
                          help='solute.maeff atomsel to compute bounding box           '
                               '[default: "ctnumber 1"]')
        parser.add_argument('-L', '--lipid-selection', dest='lipid_sel',
                          default='lipid or resname POPS', type='string',
                          help='atomsel for the lipids in the membrane [default: '
                               '"lipid or resname POPS"]')
        parser.add_argument('-C','--lipic-clash-check',dest='clash_lipids',
                          help='atomsel for lipids with rings (i.e. cholesterol)       '
                               'that might clash with other lipids.')
        parser.add_argument('-M', '--custom-membrane-system', dest='membrane_system',
                          default=self.__MEMBRANE_SYSTEM_PATH,  type='string',
                          help='custom membrane system path (must be a mae file)       '
                               '[default: built-in POPC + TIP3P]')
        parser.add_argument('-c', '--cation',
                          default='Na', type='string',
                          help='specify cation "Na" or "K"                             '
                               '[default: "Na"]')
        parser.add_argument('--move-solute', dest='z_move',
                          default=0, type='float',
                          help='value added to solute z coordinates                    '
                               '[default: 0]')
    # Edit: defaults for z_buf and xy_buf are set in main code, so that we can tell if a stupid user specifies both a buffer and absolute dimensions.
        parser.add_argument('-z', '--z-buffer-dist', dest='z_buf', default=20.0,
                          type='float',
                          help='buffer distance in the membrane normal direction.      '
                               '[default 20.0 angstroms]')
        parser.add_argument('-m', '--membrane-buffer-dist', dest='xy_buf', default=45.0,
                          type='float',
                          help='buffer distance through the membrane.                  '
                               '[default: 45.0 angstroms]')
        parser.add_argument('-s', '--salt-concentration', dest='salt_conc',
                          default=0.150, type='float',
                          help='desired salt concentration.                            '
                               '[default: 0.150 M]')
        parser.add_argument('-q', '--quiet', dest='quiet',
                          action='store_true', default=False)
        parser.add_argument('-d', '--lipid-dist', dest='lipid_dist',
                          default=1.75, type='float',
                          help='minimum distance from solute to lipid acyl group       '
                               '[default: 1.75]')
    # Edit: users can now specify the absolte dimensions of their system.
        parser.add_argument('-a','--absolute-dim', type='string',
                           dest='user_dims',
                           help='comma separated list of dimensions for system         '
                                '(x and y dimensions are one number)                   '
                                '[default: system defined by buffers]')
        parser.add_argument('--absolute-xy', type='float', default=None,
                          dest='user_xy', 
                          help='Specifies the xy dimension.  Takes precedence over buffer-based calculation.')
        parser.add_argument('--absolute-z', type='float', default=None,
                          dest='user_z',
                          help="Specifies the z dimension.  Takes precedence over buffer-based calculation.")
    # Edit: users can specify components of the protein that are "lipid-friendly" and should not be used when calculating which lipids are clashing with the protein
    # (i.e.: lipid tails, periferal membrane proteins)
        parser.add_argument('-f','--lipid-friendly-sel', type='string',
                          dest='lipid_friendly_sel',
                          help='atomsel for parts of the protein that are              '
                               '"lipid-friendly" and should not be used when           '
                               'calculating which lipids are clashing with             '
                               'the protein (i.e.: lipid tails, sidechains of          '
                               'peripheral membrane proteins)                           ')
        opts = parser.parse_args(args)
        
        log = self.make_logger(opts.quiet)
        
        log(WELCOME_SCREEN)
        
        log('\n\n')
    
        log('launching VMD...')
        
        import dabblelib
        
        log('done.\n\n')
    
        log('analyzing solute...\n')
        solute_id = molecule.load('mae',opts.solute_filename)
        solute_sel = dabblelib.get_solute_sel(molid=solute_id)
    
        log('solute_sel = "%s"\nsolute_bb_sel = "%s"\n\n' % (solute_sel, opts.solute_bb_sel))
        if solute_sel != opts.solute_bb_sel:
            log('WARNING:  solute_bb_sel != solute_sel\n')
            
        log('computing the size of the periodic cell...')
        
        xy_size, z_size, dxy_sol, dxy_tm, dz_full = dabblelib.get_cell_size(opts.xy_buf,
                                                                           opts.z_buf,
                                                                           opts.solute_bb_sel,
                                                                           molid=solute_id,
                                                                           z_move=opts.z_move)
    
        log('done.\nsolute xy diameter is %.2f (%.2f in the transmembrane region).\nsolute+membrane z diameter is %.2f\n' % (dxy_sol, dxy_tm, dz_full))
    
        if not opts.user_dims:
            if opts.user_xy:
                xy_size = opts.user_xy
            x_size = xy_size
            y_size = xy_size
            if opts.user_z:
                z_size = opts.user_z
    
        else:
           log("WARNING:  deprecated interface:  please use --absolute-xy and --absolute-z to specify absolute dimensions.\n")
           dims=map(float, opts.user_dims.split(','))
           if len(dims) != 2:
              parser.error('User must supply x and y dimensions as one number, along with a dimension, or user defaults for buffers')
           x_size=dims[0]
           y_size=dims[0]
           z_size=dims[1]
           xy_size=dims[0]
    
        log('system size will be %.2f x %.2f x %.2f\n\n' % (x_size, y_size, z_size))
    
        log('xy solvent buffer: %4.1f\nxy transmembrane buffer: %4.1f\nz solvent buffer: %4.1f\n\n' % (xy_size - dxy_sol, xy_size - dxy_tm, z_size - dz_full))
        
        log('loading membrane patch...')
        x_mem, y_mem, z_mem = dabblelib.get_system_dimensions(filename=opts.membrane_system)
        log('done. patch dimensions are %.3f x %.3f x %.3f\n\n' % (x_mem, y_mem, z_mem))
    
        log('tiling membrane patch...')
        tiled_membrane_filename = tempfile.mktemp(suffix='mae', prefix='dabble_membrane_tmp')
        times_x, times_y, times_z = dabblelib.tile_membrane_patch(opts.membrane_system, tiled_membrane_filename, xy_size, z_size)
        log('done. membrane patch tiled %d x %d x %d times.\n\n' % (times_x, times_y, times_z))
        
        log('combining solute and tiled membrane patch...')
        dabblelib.read_combined_mae_file([solute_filename,tiled_membrane_filename])
        os.remove(tiled_membrane_filename)
        log('done.\n\n')
    
        log('selecting cation %s...' % opts.cation)
        count = dabblelib.set_cations(opts.cation, solute_sel)
        log('done.\n\n')
        
        log('centering the membrane system on the origin...')
    
        dabblelib.center_membrane_system(solute_sel, opts.lipid_sel)    
        log('done.\n\n')
    
        log('translating solute...')
        dabblelib.move(solute_sel, (0, 0, opts.z_move))
        log('done.\n\n')
        
        # set "keep" mask to all atoms
        dabblelib.init_atoms()    
        log('removing molecules outside of the periodic cell...')
        
        # cut away atoms in the z direction
        dabblelib.remove_z_residues(z_size, solute_sel)
        
        # cut away atoms outside of the cell
        dabblelib.remove_xy_residues(xy_size, solute_sel, opts.lipid_sel)
        dabblelib.set_cell_to_square_prism(xy_size, z_size)
        
        log('done.\n\n')
    
        inner, outer = dabblelib.lipid_composition(opts.lipid_sel)
        log('Initial membrane composition:\ninner leaflet:')
        for r, n in sorted(inner.items()):
            log('  %d %s' % (n, r))
        log('\nouter leaflet:')
        for r, n in sorted(outer.items()):
            log('  %d %s' % (n, r))
        log('\n\n')
        
        
        log('removing water and lipids that clash with the protein...')
        
        if opts.lipid_friendly_sel:
           dabblelib.remove_overlapping_residues(solute_sel,
                                                opts.lipid_sel,
                                                lipid_friendly_sel=opts.lipid_friendly_sel,
                                                lipid_dist=opts.lipid_dist)
        else:
           dabblelib.remove_overlapping_residues(solute_sel,
                                                opts.lipid_sel,
                                                lipid_dist=opts.lipid_dist)
        
        log('done.\n\n')
        
        log('removing lipid molecules that could possibly stick through aromatic rings...')
        
        dangerous_lipids_removed = dabblelib.remove_lipids_near_rings(solute_sel, opts.lipid_sel)
        dangerous_lipids2lipids_removed=0
        lipid_stuck_on_protein=0
    
        if opts.clash_lipids:   
           edge_dim=xy_size*0.5*0.9
           pointy_lipid_type='((' + opts.lipid_sel  + ') and not (' + opts.clash_lipids + ')) and (abs(x)> %f or  abs(y) > %f)' % (edge_dim, edge_dim)
           ring_lipid_type=opts.clash_lipids + ' and (abs(x)> %f or  abs(y) > %f)'  % (edge_dim, edge_dim)
           dangerous_lipids2lipids_removed = dabblelib.remove_lipid_boundary_clash(pointy_lipid_type,ring_lipid_type)
           lipid_stuck_on_protein = dabblelib.remove_lipids_near_rings(solute_sel, opts.clash_lipids, ring_sel='noh and protein and not backbone',dist=1.25)
        
        lipids_removed=dangerous_lipids_removed+dangerous_lipids2lipids_removed+lipid_stuck_on_protein
        
        log('done. removed %d atoms.\n' % lipids_removed)
        log('      %d atoms from lipids going through HIS,PHE,TYR,TRP. \n' % dangerous_lipids_removed)
        log('      %d atoms from one lipid going through another. \n' % dangerous_lipids2lipids_removed)
        log('      %d atoms from lipid getting stuck by a sidechain. \n' % lipid_stuck_on_protein)
        
        inner, outer = dabblelib.lipid_composition(opts.lipid_sel)
        log('Final membrane composition:\ninner leaflet:')
        for r, n in sorted(inner.items()):
            log('  %d %s' % (n, r))
        log('\nouter leaflet:')
        for r, n in sorted(outer.items()):
            log('  %d %s' % (n, r))
        log('\n\n')
            
    
        log('************************************************************\n')
        log('solute net charge is %+d and system net charge is %+d\n' % (dabblelib.get_net_charge(solute_sel), dabblelib.get_system_net_charge()))
        log('************************************************************\n')
        log('\n')
        
        pos_ions_needed, neg_ions_needed, num_waters, total_cations, total_anions, cation_conc, anion_conc = dabblelib.get_num_salt_ions_needed(opts.salt_conc, cation=opts.cation)
    
        fmts = 'solvent will comprise %d waters, %d %s (%.3f M), and %d Cl (%.3f M) ions.\n'
        log(fmts % (num_waters, total_cations, opts.cation, cation_conc, total_anions, anion_conc))
        
        log('converting %d waters to %d new %s ions and %d new chloride ions...' % (pos_ions_needed + neg_ions_needed, pos_ions_needed, opts.cation, neg_ions_needed))
    
        for i in xrange(pos_ions_needed):
            dabblelib.add_salt_ion(opts.cation)
        for i in xrange(neg_ions_needed):
            dabblelib.add_salt_ion('Cl')
    
        log('done.\n\n')
        
        log('writing system with %d atoms (containing %d lipid molecules and %d water molecules) to "%s"...' % (dabblelib.num_atoms_remaining(), dabblelib.num_lipids_remaining(opts.lipid_sel), dabblelib.num_waters_remaining(), output_filename))
        
        dabblelib.write_remaining_atoms(output_filename)
        
        log('done.\n\n')
    
        log('[exit]\n')
    
    
    if __name__ == '__main__':
        dabble_main(sys.argv)
    
    