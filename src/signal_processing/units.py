"""ADC counts <-> volts conversion for the ADS1292R.

The ADS1292R reports each channel as a 24-bit two's-complement code. Per the TI
datasheet, for a fully differential input the output code relates to the input
voltage as::

    code = 2^23 * gain * Vin / Vref

so the inverse conversion is::

    Vin = code * Vref / (2^23 * gain)

This is only correct if ``vref_volts`` and ``pga_gain`` match the ADS1292R's actual
register configuration (CONFIG2 reference selection, CHxSET gain bits). This project
does not assume any particular value — both must be supplied explicitly (see
``src.config.ADS1292RConfig``, populated from the Settings dialog) and are marked
TO BE VERIFIED ON HARDWARE until confirmed against the real firmware.
"""

from __future__ import annotations

import numpy as np


def adc_counts_to_volts(
    counts: np.ndarray | float,
    vref_volts: float,
    pga_gain: float,
    resolution_bits: int = 24,
) -> np.ndarray | float:
    """Convert raw ADS1292R ADC counts to volts.

    Args:
        counts: raw signed ADC code(s), already sign-extended.
        vref_volts: reference voltage actually configured in the ADS1292R (CONFIG2).
        pga_gain: PGA gain actually configured for the channel (CHxSET).
        resolution_bits: ADC resolution in bits (24 for ADS1292R).

    Raises:
        ValueError: if vref_volts or pga_gain is not a positive number.
    """
    if vref_volts <= 0:
        raise ValueError("vref_volts must be a positive, confirmed reference voltage")
    if pga_gain <= 0:
        raise ValueError("pga_gain must be a positive, confirmed PGA gain")
    full_scale = 2 ** (resolution_bits - 1)
    return np.asarray(counts, dtype=np.float64) * vref_volts / (full_scale * pga_gain)


def volts_to_microvolts(volts: np.ndarray | float) -> np.ndarray | float:
    return np.asarray(volts, dtype=np.float64) * 1e6


def volts_to_millivolts(volts: np.ndarray | float) -> np.ndarray | float:
    return np.asarray(volts, dtype=np.float64) * 1e3
