# -*- coding: utf-8 -*-
"""
Parcel Locator - Plugin de QGIS para buscar referencias catastrales y hacer zoom a su ubicación. También permite obtener la referencia catastral por provincia, municipio, polígono y parcela para luego buscar dicha referencia. Es necesario establecer el SRS correcto. 
"""

def classFactory(iface):
    from .parcel_locator import ParcelLocator
    return ParcelLocator(iface)