from __future__ import absolute_import, print_function, division

import numpy as np
from .actions import CpptrajActions
from .datasets import CpptrajDatasetList
from .decorators import _register_pmap
from ._get_common_objects import _get_data_from_dtype, _super_dispatch
from .base_holder import BaseDataHolder
from ._shared_methods import iterframe_master

__all__ = ['DatasetHBond', 'hbond']


def to_amber_mask(txtlist):
    """Convert hbond lables to amber mask, example 'ASP_16@OD1-ARG_18@N-H to ':16@OD1 :18@H'.
    This converter is good to measure the hbond distance over time.

    >>> list(to_amber_mask(['ASP_16@OD1-ARG_18@N-H',]))
    [(':16@OD1 :18@H', ':16@OD1 :18@H :18@N')]
    """
    _txt = txtlist[:]

    for mask in _txt:
        if 'UU' not in mask and 'UV' not in mask:
            mask = mask.replace("_", " ").replace("-", " ").split()
            donor_mask = ''.join((':', mask[1]))
            second_res = mask[3].split('@')[0]
            aceptor_mask = ':' + "".join((second_res, '@', mask[4]))
            another = ' :' + mask[3]

            distance_mask = ' '.join((donor_mask, aceptor_mask))
            angle_mask = ''.join((distance_mask, another))
            yield distance_mask, angle_mask


class DatasetHBond(BaseDataHolder):
    """Hold data for hbond analysis
    """

    def __str__(self):
        root_msg = "<pytraj.hbonds.DatasetHBond"
        more_info = "donor_aceptor pairs : %s>" % len(self.donor_aceptor)
        return root_msg + "\n" + more_info

    def __repr__(self):
        return str(self)

    @property
    def donor_aceptor(self):
        '''return a list of donor and aceptor
        '''
        return self.data.grep(["solventhb", "solutehb"], mode='aspect').keys()

    def _amber_mask(self):
        return np.array(list(to_amber_mask(self._old_keys))).T


def _update_key_hbond(_dslist):

    # SER_20@O-SER_20@OG-HG --> SER20_O-SER20_OG-HG
    for d0 in _dslist:
        d0.key = d0.key.replace("_", "")
        d0.key = d0.key.replace("@", "_")

    for d0 in _dslist:
        if d0.key == 'HB00000[UU]':
            d0.key = 'total_solute_hbonds'


@_register_pmap
@_super_dispatch()
def hbond(traj,
          mask="",
          solvent_donor=None,
          solvent_acceptor=None,
          distance=3.0,
          angle=135.,
          image=False,
          series=True,
          cpp_options='',
          dtype='hbond',
          frame_indices=None,
          top=None):
    """(combined with cpptraj doc) Searching for Hbond donors/acceptors in region specified by ``mask``.
    Hydrogen bond is defined as A-HD, where A is acceptor heavy atom, H is hydrogen, D is
    donor heavy atom. Hydrogen bond is formed when A to D distance < distance cutoff and A-H-D angle
    > angle cutoff; if `angle` < 0 it is ignored.

    Parameters
    ----------
    traj : Trajectory-like
    mask : {str, 1D array-like}
        Atom mask for searching hbond. If this `mask` is specify, cpptraj will
        automatically search for donors and acceptors.
    solvent_donor : {None, str}, default None
    solvent_acceptor: {None, str}, deafult None
        if solvent_acceptor and solvent_donor are None, cpptraj only search hbond for 
        if solvent_donor and solvent_acceptor are NOT None, cpptraj will search for hbond
        between solute and solvent too.
    distance : float, default 3.0 (angstrom)
        hbond distance cut off
    angle : float, 135.0 degree
        hbond angle cut off
    dtype : return output's type, default 'hbond'
    image : bool, default False
    series : bool, default True
        - output time series (array of 1 and 0) for hbond or not.
        - if False, you must specify dtype='dataset'
    cpp_options : str
        additional cpptraj options. For example you can explicitly specify donormask and
        acceptormask. 

        - If ``donormask`` is specified but not ``acceptormask``, acceptors will be
          automatically searched for in ``mask``.

        - If ``acceptormask`` is specified but not donormask, donors will be
        automatically search for in ``mask``. 

        - If both ``donormask`` and ``acceptormask`` are specified no automatic searching will
          occur.


    Returns
    -------
    out : DatasetHBond if series is True else return 'DatasetList'
          
    Notes
    -----
    - pytraj use 'series' as default. In cpptraj, you need to explicitly specify 'series'.
    - if 'series' is False, the 'dtype' argument will be ignored.

    See also
    --------
    to_amber_mask


    Examples
    --------
    >>> import pytraj as pt
    >>> traj = pt.load_sample_data('tz2')
    >>> # search hbond without including solvent
    >>> data = pt.search_hbonds(traj, ':5,8')
    >>> data
    <pytraj.hbonds.DatasetHBond
    donor_aceptor pairs : 2>
    >>> data.donor_aceptor
    ['LYS8_O-GLU5_N-H', 'GLU5_O-LYS8_N-H']
    >>> data.values
    array([[2, 2, 0, ..., 1, 1, 1],
           [1, 1, 0, ..., 1, 1, 1],
           [1, 1, 0, ..., 0, 0, 0]], dtype=int32)
    >>> # search hbond including solvent
    >>> hbonds = pt.search_hbonds(traj, ':5,8', solvent_donor=':WAT@O', solvent_acceptor=':WAT')
    >>> hbonds
    <pytraj.hbonds.DatasetHBond
    donor_aceptor pairs : 8>
    >>> hbonds.donor_aceptor
    ['LYS8_O-GLU5_N-H', 'GLU5_O-LYS8_N-H', 'LYS8_HZ1-V', 'LYS8_HZ2-V', 'GLU5_OE2-V', 'GLU5_O-V', 'GLU5_OE1-V', 'LYS8_HZ3-V']
    >>> # 'GLU5_O-V' mean non-specific hbond between GLU5_O and solvent (:WAT in this case)
    """
    dslist = CpptrajDatasetList()
    act = CpptrajActions.Action_Hbond()

    s_donor = "solventdonor " + str(solvent_donor) if solvent_donor else ""
    s_acceptor = "solventacceptor " + \
        str(solvent_acceptor) if solvent_acceptor else ""
    _dist = 'dist ' + str(distance)
    _angle = 'angle ' + str(angle)
    _image = 'image' if image else ''
    _series = 'series' if series else ''
    _options = cpp_options

    command = " ".join(
        (_series, mask, s_donor, s_acceptor, _dist, _angle, _image, _options))

    # need to get correct frame number
    act.read_input(command, top=top, dslist=dslist)
    act.process(top)

    for idx, frame in enumerate(iterframe_master(traj)):
        act.do_action(frame, idx=idx)

    act.post_process()

    old_keys = dslist.keys()
    _update_key_hbond(dslist)
    if dtype == 'dataframe':
        # return DataFrame.T to have better visual effect
        return dslist.to_dataframe().T
    elif dtype == 'hbond':
        if series:
            dslist_new = _get_data_from_dtype(dslist, dtype='dataset')
            hdata = DatasetHBond(dslist_new)
            hdata._old_keys = old_keys
            return hdata
        else:
            raise ValueError(
                'series=False does not work with dtype="hbond", try dtype="dataset"')
    else:
        return _get_data_from_dtype(dslist, dtype=dtype)