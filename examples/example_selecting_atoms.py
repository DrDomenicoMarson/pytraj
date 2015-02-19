import os
import numpy as np
import unittest
from pytraj.base import *
from pytraj import io as mdio
from pytraj.AtomSelect import AtomSelect
from pytraj.decorators import no_test

def main():
    traj = FrameArray("../tests/data/md1_prod.Tc5b.x", "../tests/data/Tc5b.top")
    top = traj.top
    frame = traj[0]

    # indexing frame
    print(frame[top("@CA")])

    # using AtomMask instance
    atm = AtomMask("@CA")
    top.set_integer_mask(atm)
    print(frame[atm])

    # using AtomSelect
    asl = AtomSelect()
    asl.top = traj.top
    asl.selected_frame = frame
    print(asl.select("@CA"))

    # timing
    # TODO : not reproduce cpptraj output
    from time import time
    t0 = time()
    ref = mdio.load("../tests/data/Tc5b.crd", "../tests/data/Tc5b.top")[0].get_subframe(":2-12@CA :12-16@H", top=traj.top)
    arrrmsd = np.empty(traj.size)
    for idx, frame in enumerate(traj):
        arr0 = frame[top(":2-12@CA :12-16@H")]
        framenew = Frame(arr0.shape[0])
        framenew.set_from_crd(arr0.flatten())
        arrrmsd[idx] = ref.rmsd(framenew)
    print("time = %s" % (time()-t0))

    print(len(arrrmsd))
    print(arrrmsd[:10])
        
if __name__ == "__main__":
    main()