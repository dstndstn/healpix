from __future__ import print_function, division

import pytest

import numpy as np
from numpy.testing import assert_allclose, assert_equal

from astropy import units as u
from astropy.coordinates import Longitude, Latitude

from ..core import (nside_to_pixel_area, nside_to_pixel_resolution,
                    nside_to_npix, npix_to_nside, healpix_to_lonlat,
                    lonlat_to_healpix, interpolate_bilinear,
                    healpix_neighbors)


def test_nside_to_pixel_area():
    resolution = nside_to_pixel_area(256)
    assert_allclose(resolution.value, 1.5978966540475428e-05)
    assert resolution.unit == u.sr


def test_nside_to_pixel_resolution():
    resolution = nside_to_pixel_resolution(256)
    assert_allclose(resolution.value, 13.741945647269624)
    assert resolution.unit == u.arcmin


def test_nside_to_npix():
    npix = nside_to_npix(4)
    assert npix == 192

    npix = nside_to_npix([4, 4])
    assert_equal(npix, 192)

    with pytest.raises(ValueError) as exc:
        nside_to_npix(15)
    assert exc.value.args[0] == 'nside should be a power of two'


def test_npix_to_nside():
    nside = npix_to_nside(192)
    assert nside == 4

    nside = npix_to_nside([192, 192])
    assert_equal(nside, 4)

    with pytest.raises(ValueError) as exc:
        npix_to_nside(7)
    assert exc.value.args[0] == 'Number of pixels should be divisible by 12'

    with pytest.raises(ValueError) as exc:
        npix_to_nside(12 * 8 * 9)
    assert exc.value.args[0] == 'Number of pixels is not of the form 12 * nside ** 2'


# For the following tests, the numerical accuracy of this function is already
# tested in test_cython_api.py, so we focus here on functionality specific to
# the Python functions.


@pytest.mark.parametrize('order', ['nested', 'ring'])
def test_healpix_to_lonlat(order):

    lon, lat = healpix_to_lonlat([1, 2, 3], 4, order=order)

    assert isinstance(lon, Longitude)
    assert isinstance(lat, Latitude)

    index = lonlat_to_healpix(lon, lat, 4, order=order)

    assert_equal(index, [1, 2, 3])

    lon, lat = healpix_to_lonlat([1, 2, 3], 4,
                                 dx=[0.1, 0.2, 0.3],
                                 dy=[0.5, 0.4, 0.7], order=order)

    assert isinstance(lon, Longitude)
    assert isinstance(lat, Latitude)

    index, dx, dy = lonlat_to_healpix(lon, lat, 4, order=order, return_offsets=True)

    assert_equal(index, [1, 2, 3])
    assert_allclose(dx, [0.1, 0.2, 0.3])
    assert_allclose(dy, [0.5, 0.4, 0.7])


def test_healpix_to_lonlat_invalid():

    dx = [0.1, 0.4, 0.9]
    dy = [0.4, 0.3, 0.2]

    with pytest.raises(ValueError) as exc:
        lon, lat = healpix_to_lonlat([-1, 2, 3], 4)
    assert exc.value.args[0] == 'healpix_index should be in the range [0:192]'

    with pytest.raises(ValueError) as exc:
        lon, lat = healpix_to_lonlat([1, 2, 3], 5)
    assert exc.value.args[0] == 'nside should be a power of two'

    with pytest.raises(ValueError) as exc:
        lon, lat = healpix_to_lonlat([1, 2, 3], 4, order='banana')
    assert exc.value.args[0] == "order should be 'nested' or 'ring'"

    with pytest.raises(ValueError) as exc:
        lon, lat = healpix_to_lonlat([1, 2, 3], 4, dx=[-0.1, 0.4, 0.5], dy=dy)
    assert exc.value.args[0] == 'dx should be in the range [0:1]'

    with pytest.raises(ValueError) as exc:
        lon, lat = healpix_to_lonlat([1, 2, 3], 4, dx=dx, dy=[-0.1, 0.4, 0.5])
    assert exc.value.args[0] == 'dy should be in the range [0:1]'


@pytest.mark.parametrize('order', ['nested', 'ring'])
def test_interpolate_bilinear(order):
    values = np.ones(192) * 3
    result = interpolate_bilinear([1, 3, 4] * u.deg, [3, 2, 6] * u.deg,
                                  values, order=order)
    assert_allclose(result, [3, 3, 3])


def test_interpolate_bilinear_invalid():

    values = np.ones(133)
    with pytest.raises(ValueError) as exc:
        interpolate_bilinear([1, 3, 4] * u.deg, [3, 2, 6] * u.deg, values)
    assert exc.value.args[0] == 'Number of pixels should be divisible by 12'

    values = np.ones(192)
    with pytest.raises(ValueError) as exc:
        interpolate_bilinear([1, 3, 4] * u.deg, [3, 2, 6] * u.deg,
                             values, order='banana')
    assert exc.value.args[0] == "order should be 'nested' or 'ring'"


@pytest.mark.parametrize('order', ['nested', 'ring'])
def test_healpix_neighbors(order):

    neighbours = healpix_neighbors([1, 2, 3], 4, order=order)

    if order == 'nested':
        expected = [[90, 69, 0],
                    [0, 71, 2],
                    [2, 77, 8],
                    [3, 8, 9],
                    [6, 9, 12],
                    [4, 3, 6],
                    [94, 1, 4],
                    [91, 0, 1]]
    else:
        expected = [[16, 19, 22],
                    [6, 8, 10],
                    [5, 7, 9],
                    [0, 1, 2],
                    [3, 0, 1],
                    [2, 3, 0],
                    [8, 10, 4],
                    [7, 9, 11]]

    assert_equal(neighbours, expected)


def test_healpix_neighbors_invalid():

    with pytest.raises(ValueError) as exc:
        healpix_neighbors([-1, 2, 3], 4)
    assert exc.value.args[0] == 'healpix_index should be in the range [0:192]'

    with pytest.raises(ValueError) as exc:
        healpix_neighbors([1, 2, 3], 5)
    assert exc.value.args[0] == 'nside should be a power of two'

    with pytest.raises(ValueError) as exc:
        healpix_neighbors([1, 2, 3], 4, order='banana')
    assert exc.value.args[0] == "order should be 'nested' or 'ring'"